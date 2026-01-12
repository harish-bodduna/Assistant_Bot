from qdrant_client import QdrantClient
import os

client = QdrantClient(
    url=os.getenv('QDRANT_URL', 'http://localhost:6333'),
    timeout=10,
    check_compatibility=False
)

coll = client.get_collection('manuals_text')
print(f'Total documents in Qdrant: {coll.points_count}')

scroll_result = client.scroll(collection_name='manuals_text', limit=20)
print(f'\nDocuments:')
for point in scroll_result[0]:
    file_name = point.payload.get('file_name', 'unknown') if hasattr(point, 'payload') and point.payload else 'N/A'
    print(f'  - {file_name}')
