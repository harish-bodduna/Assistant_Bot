from __future__ import annotations

import uuid
from typing import Dict, Any

from qdrant_client import QdrantClient
from qdrant_client.http import models


def upsert_markdown(client: QdrantClient, collection: str, embed_model, embed_markdown: str, payload: Dict[str, Any]):
    vec = embed_model.get_text_embedding(embed_markdown)
    point = models.PointStruct(
        id=str(uuid.uuid4()),
        vector=vec,
        payload=payload,
    )
    client.upsert(collection_name=collection, points=[point])

