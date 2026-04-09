# ClaimCopilot: AI-Powered Medical Claim Processing
**Project Report**

---

## 1. Project Overview

**ClaimCopilot** is an end-to-end medical insurance claim adjudication system designed to automate the traditionally manual and error-prone process of evaluating insurance claims. 

The immediate problem it solves is the vast paperwork processing bottleneck in healthcare—replacing manual data entry, manual cross-referencing of policy guidelines, and subjective review processes. By leveraging optical character recognition (OCR), Retrieval-Augmented Generation (RAG), and advanced Large Language Models (LLMs), ClaimCopilot reliably extracts information from medical bills, compares the treatments against structured databases and unstructured policy documents, and produces an automated, explainable adjudication decision (Approve/Reject/Flag).

**Key value propositions:**
- Drastically reduces turnaround time for claims processing.
- Enhances accuracy and consistency in decision-making through rule-based validation.
- Allows healthcare administrators to seamlessly track histories, explore policies, and batch process files.

---

## 2. File-by-File Breakdown

### 📂 Root Level
- **`.env`**: Stores sensitive credentials (like `OPENROUTER_API_KEY`).
- **`README.md` & `DEPLOYMENT_GUIDE.md`**: Core project documentation on setup, tools, and execution strategies.
- **`mcp_server.py` & `claude_desktop_config.json`**: Wraps the backend into an official Model Context Protocol (MCP) server, allowing Claude desktop integration.
- **`generate_mcp_report.py`**: A utility script to generate evaluation or usage reports based on processed data.

### 🔌 Backend (Python)
- **`main.py`**: The entry point for the Flask application. It defines the middleware, routers, and pre-loads the machine learning resources for quicker responses.
- **`config.py`**: Central configuration registry. Loads and exports environment variables, absolute directory paths, and settings such as vector store configurations and default LLM models.
- **`requirements.txt`**: Standard Python package dependencies file outlining required libraries (Flask, pdfplumber, langchain, openai, pandas, etc.).

**`backend/routers/`**
- **`claims.py`**: Handles inbound `/process` API requests mapping to the claims pipeline.
- **`chat.py`**: Exposes the logic required to query policies and interact with the policy rules engine.

**`backend/tools/` (Agentic Toolkit / The Brain)**
- **`tool1_file_reader.py`**: Serves as the OCR component using `pdfplumber` and `pytesseract` to turn physical medical bills/documents into workable text.
- **`tool2_data_extractor.py`**: Uses language models (via OpenRouter) to extract structured insights (Patient name, diagnosis, amount) from raw text.
- **`tool3_rag_retriever.py`**: Executes semantic searches (using a ChromaDB VectorStore and generating embeddings) against unstructured policy PDFs. 
- **`tool4_structured_retriever.py`**: Pulls and matches exact policy coverage clauses using `pandas` and a centralized CSV/JSON source of truth.
- **`tool5_validation_engine.py`**: The adjudicator module—utilizes Pydantic to ensure all prior extractions hit requirements and finalizes the "Approve/Reject" outcome based on logic.

**`backend/pipeline/`**
- **`tool_router.py`**: The master orchestration logic mapping the sequence of executing Tool 1 through Tool 5 to yield a final decision. 

**`backend/models/`**
- **`db.py`**: Handles initialization and interaction with the local SQLite archive database, tracking successful jobs.

### 🌌 Frontend (React + Vite)
- **`package.json` & `vite.config.js`**: React workspace configuration.
- **`src/main.jsx` & `src/App.jsx`**: Core component rendering tree building the primary interaction views.
- **`src/Chatbot.jsx`**: Houses the direct AI assistant widget the admins use on the frontend.
- **`src/App.css` & `src/index.css`**: Styling sheets managing the app’s look and feel.

---

## 3. Tech Stack & Tools

### Frontend
- **Framework**: React 19 / Vite
- **Styling**: Vanilla CSS Modules (`App.css`, `index.css`)
- **HTTP Client**: Axios

### Backend
- **Framework**: Flask / Gunicorn (Python 3.10+)
- **ORM / Storage**: SQLite3 / Pandas
- **Vector Database**: ChromaDB (Open-source vector store)
- **LLM Orchestration**: LangChain (Core, Chroma, Text Splitters)

### Machine Learning Context
- **OCR Engine**: Tesseract (`pytesseract`), `pdfplumber`, `Pillow`
- **Embeddings**: `openai/text-embedding-3-small` (Proxy via LangChain)
- **Inference Server**: `google/gemini-2.0-flash-001` (Called via OpenRouter SDK)
- **Validation**: Pydantic v2

### Tools
- **Claude Desktop MCP**: Integrates via FastMCP (`mcp[cli]`).

---

## 4. APIs & Integrations

- **OpenRouter API (`openai` Client)**: Acts as the exclusive intelligence pipeline. Provides high-fidelity Large Language Model (Gemini 2.0 Flash) throughput for structured JSON parsing, text generation, and claim assessments.
- **OpenAI Embeddings API** (`text-embedding-3-small`): Transmits text patches to generate mathematical vector representation for storage inside ChromaDB. This acts as the backbone of the Retrieval-Augmented Generation retrieval mechanism.
- **Model Context Protocol (FastMCP)**: A custom system integration tool allowing direct interaction between a user's Claude OS Desktop Instance and the local codebase tools. 

---

## 5. Architecture Overview

ClaimCopilot is built on a loosely coupled **Micro-Tool Orchestration Architecture** utilizing an API-driven (Controller-Service) schema:

1. **Presentation Layer (Frontend/MCP)**: Exposes APIs for users to submit individual or batch claims as PDFs, text, or Base64 blobs.
2. **Controller Layer (Flask/FastMCP)**: Handles routing, parameter sanitization, and warm-ups. Captures input and relays it to the `tool_router.py`.
3. **Intelligence Layer (Pipeline/Tools)**: This is a linear directed acyclic graph (DAG) approach:
   `Optical Character Recognition -> Entity Extraction -> RAG/Policy Retrieval -> Adjudication Rules -> Decision`.
4. **Data Persistence Layer (SQLite/Chroma)**: Once an event completes, it updates a ChromaDB instance (if new policies were fed) or stamps a relational SQLite record of the final adjudication outcome.

---

## 6. Workflow Explanation

The typical lifecycle of processing a medical claim runs seamlessly in the background to limit latency:

1. **Ingestion**: The user uploads a medical bill PDF document on the React frontend or passes it to the Claude MCP server.
2. **OCR Parsing (`Tool 1`)**: The document is converted entirely to workable strings.
3. **Data Structuring (`Tool 2`)**: The OpenRouter model ingests the raw string and converts it to strict JSON fields like `{"patient": "John", "amount": 1000, "diagnosis": "Asthma"}`.
4. **Policy Fetching (`Tool 3` & `Tool 4`)**:
   - *Structured*: The tool verifies if "Asthma" is a recognized clause in the company's `policies.csv`.
   - *Unstructured*: RAG queries ChromaDB to read dense medical guidelines concerning "Asthma".
5. **Adjudication Engine (`Tool 5`)**: Compares the scraped document variables (Tool 2) against the policy parameters (Tool 3 & 4) applying business logic checks (e.g., *Is amount ≤ Coverage Limit?*).
6. **Persistence & Return**: The final decision is stored in an SQLite system for later auditing. The frontend renders a card indicating if the ticket was approved alongside an exact reason string (e.g., "Approved. Expense within limits.").

---

## 7. Key Features

- **Model Context Protocol (MCP)**: Run the tool dynamically through Anthropic Claude by using the native OS client. It essentially gives AI autonomous ability to act as the claims department.
- **Advanced OCR Recognition**: Hybrid fallback using standard logic (`pdfplumber`) and vision image extraction (`pytesseract`).
- **Retrieval-Augmented Generation**: Policy logic is not hard-coded; the app "reads" medical books dynamically to ascertain validity. 
- **Automated Batching**: Process folders filled with hundreds of records simultaneously with zero lag via API concurrency.

---

## 8. Challenges & Solutions

**Challenge**: *Handling dense unstructured PDF structures (like messy doctor scribbles or unpredictable pharmacy invoices).*
**Solution**: Transitioning from a single parsing function to a robust two-step pipeline. `pytesseract` handles visual anomalies while the OpenRouter foundational model is tasked with structuring the messy strings rather than relying on regex matchers.

**Challenge**: *Vector Engine Latency over Torch.*
**Solution**: Originally, `sentence-transformers` loaded ~2GB models straight to RAM during startup, creating brutal memory locks. The architecture was switched out to rely on OpenRouter's HTTP embeddings endpoint (`text-embedding-3-small`), decreasing container size and accelerating cold starts significantly.

**Challenge**: *LLM Hallucinations causing fake policy approvals.*
**Solution**: Enforced strict adherence via **Pydantic Validation Engines** (`Tool 5`). The LLMs do not make the final call dynamically, instead, they provide parameters that are passed into definitive Python arithmetic validation logic.

---

## 9. Conclusion

ClaimCopilot represents the paradigm shift in operational health-tech tasks. By isolating standard programmatic workflows into "Tools" acting together sequentially, the system attains a high level of determinism while keeping the flexibility characteristic of Large Language Models. 

**Future Improvements** could include:
- A Docker-compose configuration bridging Redis task queues (Celery) to allow for asynchronous message processing of claims that take longer than standard HTTP timeout periods.
- Full cloud migration of the persistent ChromaDB state over to a managed instance like Pinecone or AWS PostgreSQL `pgvector`.
- An advanced React dashboard utilizing `Chart.js` for temporal analytics tracking Approval/Rejection ratios.
