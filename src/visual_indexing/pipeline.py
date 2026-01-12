from __future__ import annotations

import base64
import io
import os
import subprocess
import tempfile
import uuid
from dataclasses import dataclass
from typing import List, Tuple

import pypdfium2 as pdfium
from byaldi.colpali import ColPali
from loguru import logger
from PIL import Image
from qdrant_client import QdrantClient
from qdrant_client.http import models

from config.settings import get_settings


def _is_docx(stream: bytes) -> bool:
    # DOCX is a zip; signature starts with PK.
    return stream.startswith(b"PK")


def _convert_docx_to_pdf_bytes(docx_bytes: bytes) -> bytes:
    """
    Convert DOCX to PDF using libreoffice/unoconv. Requires libreoffice-headless.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "input.docx")
        pdf_path = os.path.join(tmpdir, "input.pdf")
        with open(docx_path, "wb") as f:
            f.write(docx_bytes)

        try:
            subprocess.run(
                [
                    "libreoffice",
                    "--headless",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    tmpdir,
                    docx_path,
                ],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError as exc:
            raise RuntimeError(
                "libreoffice not found. Install libreoffice-headless for DOCX->PDF conversion."
            ) from exc
        with open(pdf_path, "rb") as f:
            return f.read()


def _materialize_pdf(stream: bytes) -> bytes:
    if _is_docx(stream):
        logger.debug("Detected DOCX stream; converting to PDF for visual indexing")
        return _convert_docx_to_pdf_bytes(stream)
    if stream.startswith(b"%PDF"):
        return stream
    raise ValueError("Unsupported file format for visual indexing. Provide PDF or DOCX.")


def _render_pdf_to_images(pdf_bytes: bytes, dpi: int = 300) -> List[Tuple[int, Image.Image]]:
    """
    Render PDF pages to PIL images at the desired DPI using pypdfium2.
    """
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_pdf:
        tmp_pdf.write(pdf_bytes)
        tmp_pdf_path = tmp_pdf.name

    images: List[Tuple[int, Image.Image]] = []
    pdf = pdfium.PdfDocument(tmp_pdf_path)
    try:
        for page_index in range(len(pdf)):
            page = pdf[page_index]
            # PDF default is 72 DPI; scale to requested DPI.
            pil_image = page.render(scale=dpi / 72).to_pil()
            images.append((page_index + 1, pil_image))
    finally:
        pdf.close()
        os.remove(tmp_pdf_path)
    return images


def _image_to_base64(pil_image: Image.Image, max_size: int = 768) -> str:
    """
    Downscale to a manageable square thumbnail before base64 encoding.
    """
    img = pil_image.copy()
    img.thumbnail((max_size, max_size))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def process_pdf_to_visual_embeddings(stream: bytes, dpi: int = 300) -> List[Tuple[int, Image.Image]]:
    """
    Convert incoming PDF/DOCX bytes to page-level images ready for ColPali embedding.
    """
    pdf_bytes = _materialize_pdf(stream)
    pages = _render_pdf_to_images(pdf_bytes, dpi=dpi)
    logger.debug("Rendered {} pages at {} DPI", len(pages), dpi)
    return pages


@dataclass
class VisualHit:
    page_number: int
    score: float
    file_id: str
    image_base64: str
    payload: dict


class VisualIndexer:
    """
    Vision-first pipeline using ColPali (PaliGemma-3B) + Qdrant multi-vector (MaxSim).
    """

    def __init__(self, collection: str | None = None) -> None:
        self.settings = get_settings()
        self.collection = collection or self.settings.qdrant_collection_visual
        self.client = QdrantClient(
            url=self.settings.qdrant_url, api_key=self.settings.qdrant_api_key
        )
        self.model = ColPali.from_pretrained("vidore/colpali", device_map="auto")
        self.dim = getattr(self.model, "embedding_dim", 768)
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        """
        Create Qdrant collection for multi-vector storage if it does not exist.
        MaxSim is applied server-side: for each query vector, Qdrant computes the maximum
        similarity across the page's vectors, then averages those maxima.
        """
        vectors_config = models.VectorsConfig(
            multi=models.MultiVectorConfig(
                distance=models.Distance.COSINE,
                size=self.dim,
            )
        )
        self.client.recreate_collection(
            collection_name=self.collection,
            vectors_config=vectors_config,
            optimizers_config=models.OptimizersConfigDiff(default_segment_number=2),
        )
        logger.info("Ensured Qdrant collection '{}' (multi-vector, dim={})", self.collection, self.dim)

    def _embed_page(self, image: Image.Image) -> List[List[float]]:
        """
        Generate multi-vector embeddings for a single page image.
        """
        vectors = self.model.encode_image(image)  # type: ignore[attr-defined]
        return vectors  # expected shape: list of vectors (multi-vector)

    def _embed_query(self, text: str) -> List[List[float]]:
        return self.model.encode_text(text)  # type: ignore[attr-defined]

    def upsert_document(self, file_id: str, stream: bytes) -> None:
        """
        Process PDF/DOCX stream, compute ColPali embeddings per page, and upsert to Qdrant.
        Payload stores file_id + page_number + thumbnail for quick preview.
        """
        pages = process_pdf_to_visual_embeddings(stream)
        points = []
        for page_number, image in pages:
            vectors = self._embed_page(image)
            thumbnail = _image_to_base64(image, max_size=512)
            points.append(
                models.PointStruct(
                    id=str(uuid.uuid4()),
                    vector=models.MultiVector(vectors=vectors),
                    payload={
                        "file_id": file_id,
                        "page_number": page_number,
                        "thumbnail_base64": thumbnail,
                    },
                )
            )
        logger.info("Upserting {} pages into collection {}", len(points), self.collection)
        self.client.upsert(collection_name=self.collection, points=points)

    def search_visual(self, query_text: str, top_k: int = 3) -> List[VisualHit]:
        """
        Search the visual index using a text query.

        MaxSim explanation:
        - ColPali produces a set of vectors per query (one per token/patch).
        - For each page, Qdrant applies MaxSim: it takes each query vector,
          finds the most similar page vector, then averages those maxima.
        """
        query_vectors = self._embed_query(query_text)
        results = self.client.search(
            collection_name=self.collection,
            query_vector=models.MultiVector(vectors=query_vectors),
            limit=top_k,
            with_payload=True,
        )
        hits: List[VisualHit] = []
        for res in results:
            payload = res.payload or {}
            hits.append(
                VisualHit(
                    page_number=payload.get("page_number"),
                    file_id=payload.get("file_id"),
                    image_base64=payload.get("thumbnail_base64"),
                    score=res.score,  # type: ignore[arg-type]
                    payload=payload,
                )
            )
        return hits

