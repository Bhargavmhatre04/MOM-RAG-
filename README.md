# NeuriaAI — Multi-Industry AI Meeting Intelligence Platform

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)](https://python.org)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-In--Memory-FF6F00?style=flat)](https://www.trychroma.com/)
[![Google Gemini](https://img.shields.io/badge/Google%20Gemini-AI-4285F4?style=flat&logo=google)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **NeuriaAI** is a production-grade, multi-industry AI meeting intelligence and productivity platform. It ingests meeting transcripts, notes, and PDF documents, indexes them into an in-memory vector database, and leverages retrieval-augmented generation (RAG) powered by Google Gemini to extract actionable decisions, tasks, risk matrices, KPIs, and multi-format reports across 16 specialized industries.

---

## 🌟 Key Features

### 🏢 16 Domain-Specialized Industry Profiles
Tailors extraction rubrics, compliance guardrails, KPI tracking, and risk analysis for:
- **Software Engineering & Tech**: Sprints, architecture, tech debt, PR reviews, CI/CD blockers.
- **Healthcare & Clinical**: HIPAA compliance, patient safety, diagnostic protocols, clinical audits.
- **Finance & Banking**: Regulatory audits (SOX, Basel III), capital allocation, fiduciary risks.
- **Legal & Compliance**: Privilege markers, litigation exposure, contractual liabilities.
- **HR & People Operations**: Talent retention, compensation, DEI, policy enforcement.
- **Sales & Business Development**: Pipeline velocity, ARR/MRR quotas, competitive displacement.
- **Marketing & Growth**: CAC, LTV, conversion funnels, campaign attribution.
- **Education & Academia**: Curriculum standards, accreditation, student outcomes.
- **Construction & Real Estate**: OSHA safety, zoning, contractor milestones, punch lists.
- **Manufacturing & Supply Chain**: Lean/Six Sigma, OEE, supply bottlenecks, QA tolerance.
- **Consulting & Professional Services**: Utilization rates, client deliverables, scope control.
- **Media, Creative & Entertainment**: IP rights, production deadlines, asset approvals.
- **Government & Public Sector**: Public accountability, FOIA compliance, civic stakeholder impact.
- **General Corporate**: Cross-functional alignment, strategic roadmaps, resource allocation.

### 🧠 End-to-End RAG Architecture
- **In-Memory Vector Search**: ChromaDB Ephemeral Client with semantic embeddings via `sentence-transformers/all-MiniLM-L6-v2`.
- **Intelligent Chunking**: Recursive character chunking (500 tokens with 80-token overlap) respecting transcript speaker boundaries and section breaks.
- **Google Gemini Integration**: Uses Google's latest `gemini-2.5-flash` model with fallback awareness for high-speed, cost-effective inference.
- **Strict Grounding & Citation**: Extracted answers and summaries cite direct source chunks with similarity scores.

### 📊 17 Interactive Intelligence Panes
1. **Executive Dashboard**: High-level telemetry, meeting scores, action item progress, and distribution charts.
2. **Documents & Transcripts**: Multi-file upload (PDF, TXT, MD) and raw text input with real-time status.
3. **Structured Summary**: Executive summary, key discussion points, and sentiment breakdown.
4. **Decisions Matrix**: Categorized decisions with rationale, stakeholder consensus, and impact ratings.
5. **Action Items & Kanban Board**: Interactive task board with inline status updating (Todo, In Progress, Blocked, Done).
6. **Deadlines & Milestones**: Chronological agenda and delivery tracker.
7. **Risk Register**: Categorized risk matrix with severity ratings (High, Medium, Low) and mitigation strategies.
8. **Decision Tracker**: Historical log of finalized, pending, and disputed consensus points.
9. **Meeting Timeline**: Interactive visual flow of meeting milestones and discussion threads.
10. **Meeting Comparison**: Cross-compare transcripts to track unresolved items and team progress over time.
11. **Follow-Up Prep**: Auto-generated post-meeting email drafts and attendee agenda briefs.
12. **KPI & Metrics Hub**: Industry-specific quantifiable performance metrics.
13. **Reports & Exports**: On-the-fly streaming exports in **PDF** (custom styled ReportLab), **CSV**, **Markdown**, **TXT**, and **JSON**.
14. **Ask Meetings (RAG Q&A)**: Conversational chat interface grounded in meeting transcripts with similarity citations.
15. **Settings & Environment**: API key configuration, active model selection, and memory diagnostics.

### 🎨 Editorial Luxury Aesthetic
- Bespoke black (`#000000`) and warm gold/amber (`#D4954A` - `#F0B86E`) design system.
- Responsive layout with desktop/tablet/mobile optimization.
- Zero heavyweight frontend dependencies — pure vanilla HTML5, CSS3, and ES6 JavaScript.

---

## 🛠️ Technology Stack

| Layer | Technology |
| :--- | :--- |
| **Backend Framework** | [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) |
| **Data Validation** | [Pydantic v2](https://docs.pydantic.dev/) |
| **Vector Database** | [ChromaDB](https://www.trychroma.com/) (In-Memory Client) |
| **Embeddings** | [Sentence-Transformers](https://www.sbert.net/) (`all-MiniLM-L6-v2`) |
| **LLM Inference** | [Google GenAI SDK](https://github.com/google-gemini/generative-ai-python) (`gemini-2.5-flash`) |
| **Document Parsing** | [PyPDF](https://pypdf.readthedocs.io/) (PDF extraction) |
| **PDF Generation** | [ReportLab](https://www.reportlab.com/) (In-memory buffer streaming) |
| **Frontend UI** | Vanilla HTML5 / Modern CSS (Variables, Grid, Flexbox) / Vanilla JS |
| **Visualizations** | [Chart.js](https://www.chartjs.org/) via CDN |

---

## 🚀 Getting Started

### 1. Prerequisites
- **Python 3.10+**
- **Google Gemini API Key** (Get one free at [Google AI Studio](https://aistudio.google.com/))

### 2. Clone the Repository
```bash
git clone https://github.com/Bhargavmhatre04/MOM-RAG-.git
cd "MOM-RAG-"
```

### 3. Set Up Virtual Environment
```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure Your API Key
Set your Gemini API key in your environment:
```bash
export GEMINI_API_KEY="your-gemini-api-key"
```
*(Alternatively, you can provide the API key directly in the web UI under the **Settings** tab or via a `.env` file.)*

### 6. Run the Application
```bash
uvicorn app:app --reload --port 8000
```

Open your browser and navigate to:
```
http://localhost:8000
```

---

## 📂 Project Structure

```text
.
├── .gitignore              # Ignores .venv, __pycache__, and all .env credential files
├── README.md               # Documentation and project manual
├── app.py                  # FastAPI backend: RAG pipeline, ChromaDB, Gemini, & export engines
├── requirements.txt        # Pinned production dependencies
└── static/
    ├── app.js              # Vanilla JS frontend state, DOM handlers, and API client
    ├── index.html          # NeuriaAI single-page application markup & dashboard views
    └── style.css           # Luxury dark & gold design system, layout, and animations
```

---

## 🔌 API Endpoints Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Service health, ChromaDB status, and Gemini key validation |
| `GET` | `/api/industries` | List of all 16 supported industry profiles and configurations |
| `POST` | `/api/documents/upload` | Upload PDF, TXT, or MD documents for ingestion & chunking |
| `POST` | `/api/documents/text` | Ingest raw meeting transcripts or minutes directly |
| `GET` | `/api/documents` | Retrieve all ingested document summaries and chunk counts |
| `DELETE` | `/api/documents/{id}` | Delete a document and purge its vectors from ChromaDB |
| `POST` | `/api/process` | Run full AI extraction (summary, decisions, tasks, risks, KPIs) |
| `POST` | `/api/ask` | Grounded RAG question-answering with citation matching |
| `PATCH` | `/api/tasks/{task_id}` | Update action item status or assignee |
| `PATCH` | `/api/decisions/{dec_id}` | Update decision consensus state |
| `POST` | `/api/compare` | Multi-transcript comparative delta analysis |
| `GET` | `/api/export/{format}` | Stream export reports (`pdf`, `csv`, `md`, `txt`, `json`) |

---

## 🛡️ Security & Privacy
- **Zero Local Disk Footprint**: ChromaDB runs entirely in memory; exports are streamed from in-memory byte buffers.
- **Credential Protection**: API keys are read securely from environment variables and never logged or committed to version control.
- **Mathematical Isolation**: Vector collections are partitioned by session to prevent cross-document contamination.

---

## 📄 License
This project is open-source under the [MIT License](LICENSE).
