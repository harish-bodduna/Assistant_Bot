# Memory Requirements for 1440 Bot

## Overview
This document provides memory requirements for running the complete 1440 Bot stack.

---

## Component Breakdown

### 1. **Qdrant (Vector Database) - Docker Container**
- **Base Memory**: ~200-300 MB (idle)
- **With Data**: 
  - ~50-100 MB per 1000 documents
  - ~10-20 MB per 10,000 vectors (384-dim embeddings)
  - Current (5 documents): ~300-400 MB
- **Peak (during ingestion)**: ~500 MB
- **Recommended**: 512 MB - 1 GB allocation

### 2. **Python Environment & Core Libraries**
- **Base Python + Dependencies**: ~100-150 MB
- **PyTorch (CPU)**: ~200-300 MB
- **Transformers Library**: ~50-100 MB (loaded)
- **LlamaIndex**: ~50-100 MB
- **Azure SDK**: ~30-50 MB
- **OpenAI SDK**: ~10-20 MB
- **Total Base**: ~450-720 MB

### 3. **Embedding Models** (Loaded in Memory)

#### Sentence Transformers (`all-MiniLM-L6-v2`)
- **Model Size**: ~80 MB (on disk)
- **In Memory**: ~120-150 MB (loaded)
- **Status**: Always loaded for text embeddings

#### Docling Layout Model (`docling-layout-heron`)
- **Model Size**: ~500-700 MB (on disk, cached)
- **In Memory**: ~800 MB - 1.2 GB (loaded during PDF processing)
- **Status**: Loaded only during ingestion/parsing
- **Note**: Largest memory consumer during ingestion

### 4. **OCR Models (RapidOCR)**
- **Models**: ~40-50 MB (cached on disk)
- **In Memory**: ~100-150 MB (loaded during OCR operations)
- **Status**: Loaded during PDF processing with OCR

### 5. **PDF Processing (Per Document)**
- **PDF Loading**: ~10-50 MB per document (temporary)
- **Image Extraction**: ~50-200 MB per document (depending on image count)
- **Markdown Generation**: ~10-30 MB per document (temporary)
- **Peak per Document**: ~300-500 MB (brief, during processing)

### 6. **Streamlit UI** (When Running)
- **Base Memory**: ~100-150 MB
- **With Active Session**: ~150-250 MB

### 7. **Operating System & Other Processes**
- **Windows Base**: ~2-4 GB
- **Docker Desktop**: ~400-600 MB
- **Other System Processes**: ~500 MB - 1 GB

---

## Memory Requirements by Scenario

### **Scenario 1: Minimal Setup (Idle - No Processing)**
- Qdrant: 300 MB
- Python Environment: 500 MB
- Sentence Transformers: 150 MB
- Docker Desktop: 500 MB
- OS Base: 3 GB
- **Total**: ~4.5 GB minimum

### **Scenario 2: Document Ingestion (Active Processing)**
- All of Scenario 1: 4.5 GB
- Docling Layout Model: +1.2 GB
- RapidOCR Models: +150 MB
- PDF Processing Buffer: +500 MB (per document, temporary)
- **Total Peak**: ~6.5 GB
- **Recommended**: **8 GB** to handle multiple documents safely

### **Scenario 3: QA/Querying (With Streamlit)**
- All of Scenario 1: 4.5 GB
- Streamlit: +200 MB
- Query Processing: +100-200 MB (temporary)
- **Total**: ~5 GB
- **Recommended**: **6 GB** for comfortable operation

### **Scenario 4: Full Stack (Ingestion + QA + Streamlit)**
- All components active
- **Total Peak**: ~7-8 GB
- **Recommended**: **10-12 GB** for production use

---

## Recommendations

### **Minimum Requirements**
- **8 GB RAM** - Can run ingestion and QA separately
- Suitable for development/testing
- May need to close other applications during ingestion

### **Recommended Requirements**
- **16 GB RAM** - Comfortable for all operations
- Can run ingestion, QA, and Streamlit simultaneously
- Leaves headroom for other applications
- Suitable for production use with moderate document volumes

### **Production/Large Scale**
- **32 GB RAM** - For processing many documents or large PDFs
- Better performance with multiple concurrent operations
- Can handle batch processing of many documents

---

## Memory Optimization Tips

1. **Process documents sequentially** (not in parallel) to reduce peak memory
2. **Close other applications** during heavy ingestion
3. **Use smaller batch sizes** if memory is constrained
4. **Clear Python caches** periodically if processing many documents
5. **Restart Docker/Qdrant** if memory usage grows over time

---

## Current System Status
Based on your current setup:
- **5 documents ingested**: ~4-5 GB total usage expected
- **Qdrant**: ~400 MB
- **Python processes**: ~700 MB
- **Docker**: ~750 MB
- **Total observed**: ~2 GB (not all models loaded)

### **Peak during ingestion observed**: ~3-4 GB
### **With all models loaded**: ~5-6 GB

---

## Notes

- **Disk Space**: 
  - Python packages: ~5-10 GB
  - Model cache: ~2-3 GB (HuggingFace cache)
  - Qdrant data: ~100 MB per 1000 documents
  - Markdown exports: Varies by document count/size

- **GPU Memory** (if using GPU):
  - Not currently used (CPU-only mode)
  - Would require additional 2-4 GB VRAM if enabled

- **Swap/Virtual Memory**: 
  - Windows virtual memory helps, but performance degrades
  - Ensure at least 8 GB swap space available
