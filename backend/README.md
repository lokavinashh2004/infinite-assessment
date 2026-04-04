# ClaimCopilot — AI-Powered Medical Insurance Claim Processor

A production-ready FastAPI service that processes medical insurance claims using
a **5-tool MCP (Model Context Protocol) pipeline** powered by **Groq AI**
and **RAG (Retrieval-Augmented Generation)**.

---

## Architecture

```
Upload PDF/Image
       │
       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     MCP Pipeline (tool_router.py)               │
│                                                                 │
│  Tool 1              Tool 2                Tool 3 ┐ (parallel)  │
│  File Reader  ──▶  Data Extractor  ──▶   RAG      │             │
│  (pdfplumber       (Groq AI)             Retriever│             │
│   + OCR)                                 (ChromaDB)             │
│                                                   │             │
│                                         Tool 4  ──┘             │
│                                         Structured              │
│                                         Retriever               │
│                                         (CSV/JSON)              │
│                                                 │               │
│                                                 ▼               │
│                                         Tool 5                  │
│                                         Validation              │
│                                         Engine                  │
└─────────────────────────────────────────────────────────────────┘
       │
       ▼
  JSON Response: Approved | Partially Approved | Rejected
```

---

## Project Structure

```
claim_copilot/
├── main.py                          # FastAPI app entry point
├── config.py                        # Env vars + path constants
├── requirements.txt
├── pytest.ini
├── .env.example
├── routers/
│   └── claims.py                    # POST /claims/process
├── mcp/
│   └── tool_router.py               # Pipeline orchestrator
├── tools/
│   ├── tool1_file_reader.py         # PDF + image text extraction
│   ├── tool2_data_extractor.py      # Groq AI structured extraction
│   ├── tool3_rag_retriever.py       # ChromaDB RAG retrieval
│   ├── tool4_structured_retriever.py# CSV/JSON policy lookup
│   └── tool5_validation_engine.py   # Adjudication decision engine
├── models/
│   └── schemas.py                   # Pydantic v2 data models
├── data/
│   ├── policies.csv                 # 5 sample policy records
│   ├── coverage_rules.json          # 8 coverage clauses
│   └── policy_pdfs/                 # ← Place your policy PDFs here
├── scripts/
│   └── build_vectorstore.py         # Index policy PDFs into ChromaDB
└── tests/
    ├── conftest.py
    ├── test_tool1.py
    ├── test_tool2.py
    ├── test_tool3.py
    ├── test_tool4.py
    └── test_tool5.py
```

---

## Prerequisites

- **Python 3.11+**
- **Tesseract OCR** installed on the system:
  - Windows: Download from [UB Mannheim builds](https://github.com/UB-Mannheim/tesseract/wiki)
    and add to `PATH` (default: `C:\Program Files\Tesseract-OCR`)
  - Linux/macOS: `sudo apt install tesseract-ocr` / `brew install tesseract`
- **Groq API key** (get one at https://console.groq.com/)

---

## Setup

### 1. Clone / navigate to the project

```bash
cd "claim_copilot"
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
copy .env.example .env      # Windows
# or
cp .env.example .env        # Linux/macOS
```

Edit `.env` and set your real Groq API key:
```
GROQ_API_KEY=gsk_...
```

### 5. (Optional) Build the RAG vector store

Place any policy PDF documents in `data/policy_pdfs/`, then run:

```bash
python scripts/build_vectorstore.py
```

> If no PDFs are present, Tool 3 will return an empty result set (non-fatal).

---

## Running the Server

```bash
uvicorn main:app --reload
```

The API will be available at: **http://localhost:8000**

Interactive docs: **http://localhost:8000/docs**

---

## API Endpoints

### `GET /health`
Liveness check.

**Response:**
```json
{ "status": "ok" }
```

---

### `POST /claims/process`
Process a medical insurance claim document.

**Request:** `multipart/form-data` with field `file` (PDF, PNG, JPG, or TIFF)

**Example (curl):**
```bash
curl -X POST http://localhost:8000/claims/process \
  -F "file=@/path/to/claim.pdf"
```

**Response:**
```json
{
  "decision": "Approved",
  "approved_amount": 125000.0,
  "reason": "All eligibility checks passed. Claim fully approved.",
  "clauses_cited": ["CL-001", "CL-002"],
  "checks_passed": ["policy_exists", "policy_active", "date_in_range",
                    "waiting_period_met", "treatments_covered", "amount_within_limit"],
  "policy_id": "POL-2024-GOLD-001",
  "patient_name": "Rahul Sharma",
  "total_claimed": 125000.0,
  "execution_log": ["[12:00:01] STEP 1: Reading document …", "..."],
  "rag_rules_used": ["Surgery is covered up to ₹3,00,000 under Gold and Silver plan..."],
  "timestamp": "2024-06-07T12:00:05.123456+00:00"
}
```

---

## Decision Logic

| Scenario | Decision | Approved Amount |
|---|---|---|
| All 6 checks pass | **Approved** | Full claimed amount |
| Only amount exceeds limit | **Partially Approved** | Effective limit (min of sub-limits / coverage cap) |
| Policy not found | **Rejected** | ₹0 |
| Policy not active (lapsed/expired) | **Rejected** | ₹0 |
| Any treatment not covered | **Rejected** | ₹0 |

---

## Running Tests

```bash
# From inside the claim_copilot/ directory
pytest
```

Or with verbose output:
```bash
pytest -v --tb=long
```

---

## Sample Data

### `data/policies.csv` — 5 policies

| Policy ID | Holder | Status | Plan | Limit |
|---|---|---|---|---|
| POL-2024-GOLD-001 | Rahul Sharma | **active** | gold | ₹5,00,000 |
| POL-2024-GOLD-002 | Priya Mehta | **active** | gold | ₹5,00,000 |
| POL-2024-SILV-003 | Anita Verma | **active** | silver | ₹2,50,000 |
| POL-2023-SILV-004 | Deepak Nair | **lapsed** | silver | ₹2,50,000 |
| POL-2022-GOLD-005 | Sunita Patel | **expired** | gold | ₹5,00,000 |

### `data/coverage_rules.json` — 8 clauses

| Clause | Coverage | Eligible Plans | Sub-limit |
|---|---|---|---|
| CL-001 | Surgery | gold, silver | ₹3,00,000 |
| CL-002 | ICU | gold, silver | ₹10,000/day |
| CL-003 | Room & Board | gold, silver, bronze | ₹5,000/day |
| CL-004 | Medicines | gold, silver | ₹50,000 |
| CL-005 | OPD/Diagnostics | gold only | ₹25,000 |
| CL-006 | Daycare | gold, silver | ₹75,000 |
| CL-007 | Maternity | gold only | ₹1,00,000 |
| CL-008 | Dental | **none** | ₹0 (excluded) |

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `GROQ_API_KEY` | ✅ | Your Groq API key |
