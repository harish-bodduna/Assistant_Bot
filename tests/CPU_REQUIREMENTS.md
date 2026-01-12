# CPU Requirements for 1440 Bot on Azure VM

## CPU Usage Analysis

### Workload Characteristics

#### 1. **Document Ingestion** (CPU-Intensive)
- PDF parsing with Docling: **High CPU** (layout analysis, OCR)
- Image processing: **Moderate CPU** (resizing, format conversion)
- OCR operations (RapidOCR): **High CPU** (when OCR is needed)
- Embedding generation: **Moderate CPU** (Sentence Transformers)
- **Peak CPU Usage**: 70-90% of available cores during ingestion
- **Duration**: 1-2 minutes per PDF

#### 2. **QA/Querying** (Moderate CPU)
- Vector search in Qdrant: **Low CPU** (mostly memory/I/O)
- Embedding generation: **Moderate CPU** (single query embedding)
- OpenAI API calls: **No CPU** (external API)
- **Typical CPU Usage**: 10-30% during queries
- **Duration**: Seconds per query

#### 3. **Streamlit UI** (Low CPU)
- Web server: **Low CPU** (mostly I/O)
- Rendering: **Minimal CPU**
- **Typical CPU Usage**: 5-10%
- **Duration**: Continuous but low

#### 4. **Qdrant** (Low CPU)
- Vector database: **Low CPU** (mostly memory operations)
- Search operations: **Low CPU** (indexed lookups)
- **Typical CPU Usage**: 5-15%
- **Duration**: Continuous but low

---

## CPU Requirements by Scenario

### Single Document Ingestion
- **CPU Usage**: ~2-3 cores at peak
- **Recommended**: 2-4 cores
- **Duration**: 1-2 minutes per document

### Concurrent Operations
- **Ingestion + QA + Streamlit**: ~3-4 cores at peak
- **Recommended**: 4 cores minimum
- **Occurrence**: Rare (usually sequential)

### Normal Operation (QA/Querying)
- **CPU Usage**: ~0.5-1 core
- **Recommended**: 2 cores sufficient
- **Pattern**: Continuous but low

---

## Azure VM CPU Options

### ✅ **Recommended: Standard_D4s_v3 (4 vCPU)**
- **vCPUs**: 4 cores
- **RAM**: 16 GB
- **Cost**: ~$150/month
- **CPU Performance**: Excellent (D-series = dedicated CPU, no overcommit)
- **Suitable For**:
  - ✅ Single document ingestion (2-3 cores used)
  - ✅ Concurrent QA queries (plenty of headroom)
  - ✅ Running ingestion + QA simultaneously
  - ✅ Production workloads

### ✅ **Alternative: Standard_D2s_v3 (2 vCPU)**
- **vCPUs**: 2 cores
- **RAM**: 8 GB
- **Cost**: ~$75/month
- **CPU Performance**: Good
- **Suitable For**:
  - ⚠️ Single operations only (ingestion OR QA, not both)
  - ⚠️ 8 GB RAM may be tight for peak usage
  - ⚠️ Slower ingestion (less CPU headroom)
  - ✅ Development/testing

### ✅ **High Performance: Standard_D8s_v3 (8 vCPU)**
- **vCPUs**: 8 cores
- **RAM**: 32 GB
- **Cost**: ~$300/month
- **CPU Performance**: Excellent
- **Suitable For**:
  - ✅ Multiple concurrent document processing
  - ✅ Batch processing many PDFs
  - ✅ Multiple concurrent QA queries
  - ⚠️ Overkill for single-threaded workloads

---

## CPU vs Memory Trade-off

### Scenario: Limited Budget

| VM Size | vCPU | RAM | Cost | Verdict |
|---------|------|-----|------|---------|
| Standard_D2s_v3 | 2 | 8 GB | ~$75 | ❌ RAM too tight (8 GB) |
| Standard_B4ms | 4 (burst) | 16 GB | ~$70 | ⚠️ Burstable CPU (may throttle) |
| Standard_D4s_v3 | 4 | 16 GB | ~$150 | ✅ **BEST BALANCE** |

### Key Insight
- **CPU**: 4 cores is optimal (2 cores is limiting, 8 cores is overkill)
- **Memory**: 16 GB is necessary (8 GB is too tight)
- **Cost**: $150/month for D4s_v3 is the sweet spot

---

## CPU Performance Characteristics

### D-Series (Recommended)
- **D = Dedicated CPU**: No overcommit, guaranteed performance
- **Best for**: Consistent performance, production workloads
- **Examples**: Standard_D2s_v3, Standard_D4s_v3, Standard_D8s_v3

### B-Series (Budget Option)
- **B = Burstable CPU**: Credits-based, can throttle
- **Best for**: Development, intermittent workloads
- **Risk**: CPU throttling during heavy ingestion
- **Examples**: Standard_B4ms (4 vCPU, 16 GB RAM, ~$70/month)

### F-Series (Compute Optimized)
- **F = Fast CPU**: Higher clock speed
- **Best for**: CPU-intensive workloads
- **Not needed here**: Your workload isn't purely CPU-bound

---

## Recommended Configuration

### **Primary Recommendation: Standard_D4s_v3**

```
Specifications:
- vCPUs: 4 cores (dedicated)
- RAM: 16 GB
- Disk: Premium SSD
- Cost: ~$150/month (VM only)

Why 4 vCPU?
✅ Handles peak ingestion (2-3 cores used)
✅ Allows concurrent operations (ingestion + QA)
✅ Provides headroom for spikes
✅ Dedicated CPU (no throttling)
✅ Good balance of cost/performance
```

### **Budget Alternative: Standard_B4ms**

```
Specifications:
- vCPUs: 4 cores (burstable)
- RAM: 16 GB
- Disk: Standard SSD
- Cost: ~$70/month (VM only)

Trade-offs:
✅ Lower cost ($80/month savings)
⚠️ Burstable CPU (may throttle during heavy ingestion)
⚠️ Standard SSD (slower than Premium)
⚠️ Less predictable performance

Suitable for: Development, low-traffic production
```

---

## CPU Usage During Typical Operations

### Document Ingestion (1 PDF)
```
Time: 0:00 - Starting ingestion
CPU: ████████░░ 80% (3-4 cores active)
     - PDF parsing: 2 cores
     - OCR (if needed): 1 core
     - Image processing: 0.5 core
     - Embeddings: 0.5 core

Time: 1:30 - Processing complete
CPU: ██░░░░░░░░ 20% (1 core active)
     - Final processing: 1 core
```

### QA Query
```
Time: 0:00 - Query received
CPU: ████░░░░░░ 40% (1-2 cores active)
     - Embedding generation: 1 core
     - Vector search: 0.5 core (mostly memory)

Time: 0:05 - Response generated
CPU: █░░░░░░░░░ 10% (minimal)
```

### Concurrent (Ingestion + QA)
```
CPU: ████████░░ 80-90% (3-4 cores active)
     - Ingestion: 2-3 cores
     - QA: 1 core
```

---

## Performance Comparison

### 2 vCPU (D2s_v3)
- **Ingestion Time**: ~2-3 minutes per PDF (slower)
- **Concurrent Operations**: Not recommended
- **Cost**: ~$75/month
- **Verdict**: ⚠️ CPU-limited, slower processing

### 4 vCPU (D4s_v3) - Recommended
- **Ingestion Time**: ~1-2 minutes per PDF (optimal)
- **Concurrent Operations**: ✅ Supported
- **Cost**: ~$150/month
- **Verdict**: ✅ **Perfect balance**

### 8 vCPU (D8s_v3)
- **Ingestion Time**: ~1-2 minutes per PDF (same - not CPU-bound)
- **Concurrent Operations**: ✅ Excellent
- **Cost**: ~$300/month
- **Verdict**: ⚠️ Overkill (your workload doesn't scale beyond 4 cores)

---

## Real-World Performance

Based on your current setup and workload:

### Single Document Ingestion
- **Observed**: ~1-2 minutes per PDF
- **CPU Usage**: 2-3 cores active
- **Bottleneck**: Memory/I/O, not CPU

### QA Query
- **Observed**: ~5-30 seconds per query (OpenAI API is the bottleneck)
- **CPU Usage**: <1 core active
- **Bottleneck**: Network/OpenAI API latency, not CPU

### Key Insight
**Your workload is not CPU-bound**. The bottlenecks are:
1. **Network latency** (OpenAI API, SharePoint, Azure Blob)
2. **Memory operations** (model loading, embeddings)
3. **I/O operations** (disk, network)

More CPU won't significantly speed things up.

---

## Final Recommendation

### **Standard_D4s_v3 (4 vCPU, 16 GB RAM)**

**Why 4 vCPU is Optimal:**
1. ✅ Handles peak ingestion (uses 2-3 cores)
2. ✅ Allows concurrent operations
3. ✅ Provides headroom without waste
4. ✅ Dedicated CPU (consistent performance)
5. ✅ Best cost/performance ratio

**Why NOT 2 vCPU:**
- ❌ Slower ingestion (CPU-limited)
- ❌ Can't run concurrent operations
- ❌ Less headroom for spikes

**Why NOT 8 vCPU:**
- ❌ Overkill (workload doesn't use more than 4 cores)
- ❌ 2x cost with no performance benefit
- ❌ Your bottlenecks are network/I/O, not CPU

---

## Cost Summary

| VM Size | vCPU | RAM | VM Cost | Total Cost* | Recommendation |
|---------|------|-----|---------|-------------|----------------|
| Standard_D2s_v3 | 2 | 8 GB | ~$75 | ~$145/month | ❌ RAM too tight |
| Standard_B4ms | 4 (burst) | 16 GB | ~$70 | ~$140/month | ⚠️ Burstable CPU |
| **Standard_D4s_v3** | **4** | **16 GB** | **~$150** | **~$220/month** | ✅ **BEST** |
| Standard_D8s_v3 | 8 | 32 GB | ~$300 | ~$370/month | ⚠️ Overkill |

*Total includes VM + OS disk (128 GB) + Data disk (256 GB) + networking

---

## Conclusion

**You need 4 vCPU, not 2 or 8.**

- **Minimum**: 4 vCPU for comfortable operation
- **Recommended**: 4 vCPU (Standard_D4s_v3)
- **Overkill**: 8 vCPU (no performance gain for your workload)

**The optimal configuration is:**
- **4 vCPU + 16 GB RAM** (Standard_D4s_v3)
- Cost: ~$220/month total
- Perfect balance of CPU, memory, and cost
