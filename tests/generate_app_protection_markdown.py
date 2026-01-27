"""Generate llm_ready_sas_markdown from App Protection Policy PDF and write to disk for manual editing."""
import os
import io
from pathlib import Path
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling_core.types.io import DocumentStream
import secrets
import string

from src.text_indexing.doc_parser import parse_document
from src.text_indexing.image_filter import capture_page_images
from src.text_indexing.storage import AzureBlobStorage


def generate_app_protection_markdown():
    """Process App Protection Policy PDF and generate llm_ready_sas_markdown, write to disk."""

    # Path to source PDF
    pdf_path = Path("source_docs/App Protection Policy v1.0.pdf")

    if not pdf_path.exists():
        print(f"Error: PDF not found at {pdf_path}")
        return

    print(f"Loading PDF from {pdf_path}")
    pdf_bytes = pdf_path.read_bytes()
    file_name = pdf_path.name

    # Setup docling converter (same as LayoutAwareIngestor)
    pipeline_options = PdfPipelineOptions()
    pipeline_options.generate_picture_images = True
    pipeline_options.images_scale = 2.0
    pipeline_options.generate_page_images = True
    pipeline_options.do_ocr = True
    pipeline_options.do_table_structure = True
    pipeline_options.generate_parsed_pages = True

    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )

    # Setup Azure blob storage (required for image uploads)
    blob_container = os.getenv("AZURE_STORAGE_CONTAINER", "qdrant-ingest-docs")
    conn_str = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
    if not conn_str:
        print("Warning: AZURE_STORAGE_CONNECTION_STRING not found. Generating markdown without uploading images to Azure.")
        print("Images will be referenced as local placeholders.")
        storage = None
    else:
        storage = AzureBlobStorage(container=blob_container, connection_string=conn_str)

    print("Converting PDF with docling...")
    # Convert with docling
    ds = DocumentStream(name=file_name, stream=io.BytesIO(pdf_bytes))
    conv_res = converter.convert(ds)
    doc = conv_res.document

    if not doc:
        raise RuntimeError("Docling conversion returned no document")

    print("Parsing document structure...")
    # Parse document structure (no banned images for this generation)
    doc, collected = parse_document(
        doc,
        banned_hashes=[],
        phash_threshold=15,
    )

    # Get safe base name for blob storage
    safe_base = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in Path(file_name).stem)
    project_name = os.getenv("AZURE_STORAGE_PROJECT_NAME", "dummy")
    document_folder = f"{project_name}/{safe_base}"
    storage_base_path = f"{project_name}/processed_images"

    # Capture page images from docling
    if storage:
        page_sas_urls = capture_page_images(conv_res, storage, document_folder)
        print(f"Captured {len(page_sas_urls)} page images")
    else:
        page_sas_urls = []
        print("Skipping page image capture (no Azure storage)")

    # Build LLM-ready markdown by iterating through collected items in order
    # Interleaves text and images as they appear in the document
    final_sas_markdown = []
    high_res_assets = []

    print("Processing text and images...")
    for item in collected:
        if item["type"] == "text":
            content = item["content"]
            final_sas_markdown.append(content)

        elif item["type"] == "image":
            pil_img = item["image"]
            page = item.get("page", 0)

            # Generate unique ID
            unique_hex = ''.join(secrets.choice(string.hexdigits.lower()) for _ in range(4))

            if storage:
                # Convert PIL image to bytes
                img_byte_arr = io.BytesIO()
                pil_img.save(img_byte_arr, format='PNG')
                img_bytes = img_byte_arr.getvalue()

                # Upload to blob storage
                filename = f"visual_{unique_hex}_page_{page}.png"
                sas_url = storage.upload_and_get_sas(img_bytes, filename, storage_base_path, days=365)

                # Add markdown image syntax
                final_sas_markdown.append(f"![{unique_hex}]({sas_url})")

                # Track in high_res_assets for metadata
                high_res_assets.append({
                    "sas_url": sas_url,
                    "page": page,
                    "id": unique_hex,
                    "filename": filename
                })
            else:
                # Create placeholder for local development
                placeholder_url = f"./hash_images/placeholder_{unique_hex}_page_{page}.png"
                final_sas_markdown.append(f"![{unique_hex}]({placeholder_url})")

                # Track in high_res_assets for metadata
                high_res_assets.append({
                    "sas_url": placeholder_url,
                    "page": page,
                    "id": unique_hex,
                    "filename": f"placeholder_{unique_hex}_page_{page}.png"
                })

    # Join with double newline to separate text and images
    llm_ready_sas_markdown = "\n\n".join(final_sas_markdown)

    print(f"Generated markdown with {len([i for i in collected if i['type'] == 'text'])} text blocks and {len(high_res_assets)} images")
    print(f"Total markdown length: {len(llm_ready_sas_markdown)} characters")

    # Create output directory
    output_dir = Path("markdown_exports/app_protection_manual_edit")
    output_dir.mkdir(parents=True, exist_ok=True)

    # Write markdown to file
    output_file = output_dir / "app_protection_llm_ready_markdown.md"
    output_file.write_text(llm_ready_sas_markdown, encoding="utf-8")

    print(f"\nMarkdown written to: {output_file}")
    print(f"\nYou can now manually edit the markdown to reorder URLs and related text.")
    print(f"After editing, the file can be used for demo ingestion.")

    # Also write a summary file
    summary_file = output_dir / "summary.txt"
    summary_content = f"""App Protection Policy Markdown Generation Summary
=============================================

Source PDF: {pdf_path}
Generated: {output_file}

Statistics:
- Text blocks: {len([i for i in collected if i['type'] == 'text'])}
- Images: {len(high_res_assets)}
- Page images: {len(page_sas_urls)}
- Markdown length: {len(llm_ready_sas_markdown)} characters

Next Steps:
1. Edit {output_file} to reorder URLs and text as needed
2. Use the edited markdown for demo ingestion
"""
    summary_file.write_text(summary_content, encoding="utf-8")
    print(f"Summary written to: {summary_file}")


if __name__ == "__main__":
    generate_app_protection_markdown()