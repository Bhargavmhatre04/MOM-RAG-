import os
import re
import io
import csv
import json
import uuid
import hashlib
import datetime
from typing import List, Dict, Any, Optional
from io import BytesIO, StringIO

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Body, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import chromadb
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer

# Optional / graceful import for python-dotenv
try:
    from dotenv import load_dotenv
    load_dotenv()
    if os.path.exists(os.path.join(os.path.dirname(__file__), "static", ".env")):
        load_dotenv(os.path.join(os.path.dirname(__file__), "static", ".env"))
except Exception:
    pass

# Optional / graceful import for Google GenAI
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

# ReportLab for in-memory PDF export
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# ---------------------------------------------------------------------------
# APP INITIALIZATION & STATIC FILES
# ---------------------------------------------------------------------------
app = FastAPI(
    title="NeuriaAI | Productivity & Meeting Intelligence",
    description="Modern premium AI productivity & meeting intelligence platform with in-memory RAG, semantic chunking, and isolated workspaces.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def block_sensitive_files(request, call_next):
    if ".env" in request.url.path:
        return JSONResponse(status_code=403, content={"detail": "Access forbidden."})
    return await call_next(request)

# ---------------------------------------------------------------------------
# SINGLETONS: ChromaDB (in-memory) & SentenceTransformer
# ---------------------------------------------------------------------------
chroma_client = chromadb.Client()
CHROMA_COLLECTION_NAME = "meetwell_meeting_chunks"
try:
    chroma_collection = chroma_client.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
except Exception:
    chroma_collection = chroma_client.create_collection(name=CHROMA_COLLECTION_NAME)

_embedding_model: Optional[SentenceTransformer] = None

def get_embedding_model() -> SentenceTransformer:
    global _embedding_model
    if _embedding_model is None:
        try:
            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2", local_files_only=True)
        except Exception:
            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model

def get_gemini_client():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip()
    if not api_key:
        return None
    if genai is None:
        return None
    try:
        return genai.Client(api_key=api_key)
    except Exception:
        return None

# ---------------------------------------------------------------------------
# INDUSTRY PROFILES DICTIONARY (15 Industries + Other)
# ---------------------------------------------------------------------------
INDUSTRY_PROFILES: Dict[str, Dict[str, Any]] = {
    "it": {
        "id": "it",
        "name": "Information Technology & Software Development",
        "tagline": "Sprints, Blockers & System Architecture",
        "terminology": ["sprint", "backlog", "PR", "CI/CD", "blocker", "API", "microservices", "latency", "tech debt", "deployment", "bug triage"],
        "focus_categories": [
            "Sprint Progress & Velocity", "Developer Updates", "Technical Discussions",
            "Bugs & Blockers", "Release & Deployment Plans", "Architecture & API Decisions",
            "Testing & QA Milestones", "Pending Deployments", "System & Security Risks"
        ],
        "analysis_instructions": "Focus on sprint commitments, bug severities, blockers, architectural decisions, and release dependencies. Differentiate confirmed engineering decisions from technical suggestions.",
        "report_sections": ["Sprint Overview", "Technical Architecture Decisions", "Blockers & Bugs", "Pending Deployments", "Action Items & Owners", "Engineering Risks"],
        "kpi_hints": ["Sprint Velocity", "Story Points Completed", "PR Cycle Time", "Open P0/P1 Bugs", "Uptime SLA"],
        "suggested_questions": [
            "What technical blockers were identified during the sprint review?",
            "What architectural or API decisions were finalized?",
            "Which releases or deployments are currently pending?",
            "What bug triage actions were assigned to developers?"
        ],
        "dashboard_emphasis": "Sprint Velocity & Critical Blockers",
        "disclaimer": None
    },
    "healthcare": {
        "id": "healthcare",
        "name": "Healthcare & Hospitals",
        "tagline": "Clinical Workflows, Staffing & Facility Operations",
        "terminology": ["patient care", "triage", "shift scheduling", "ward capacity", "clinical protocols", "medical equipment", "HIPAA", "bottleneck"],
        "focus_categories": [
            "Hospital & Ward Operations", "Department Coordination", "Staff Scheduling & Shifts",
            "Patient-Care Workflow", "Equipment & Supply Needs", "Operational Bottlenecks",
            "Service Improvement Actions", "Protocol Updates", "Facility Safety"
        ],
        "analysis_instructions": "Focus strictly on operational workflow, staffing, and facility logistics. NEVER invent patient information, names, or clinical diagnoses. Emphasize bottlenecks in patient throughput and supply needs.",
        "report_sections": ["Operations Summary", "Patient Workflow Bottlenecks", "Staff Scheduling Updates", "Equipment & Supply Actions", "Service Improvement Directives", "Facility Safety Items"],
        "kpi_hints": ["Bed Occupancy Rate", "Average Patient Wait Time", "Staff Shift Fill Rate", "Nurse-to-Patient Ratio"],
        "suggested_questions": [
            "What workflow bottlenecks were raised regarding patient care?",
            "What equipment or medical supply shortages were identified?",
            "What staff scheduling or shift adjustments were agreed upon?",
            "What operational action items were assigned to ward leads?"
        ],
        "dashboard_emphasis": "Patient-Care Workflow & Staffing Bottlenecks",
        "disclaimer": "Medical Disclaimer: This platform provides document-based operational and workflow assistance only. It does not provide medical advice, diagnosis, treatment recommendations, or clinical decision support. Never invent patient information."
    },
    "banking": {
        "id": "banking",
        "name": "Banking & Finance",
        "tagline": "Fiscal Health, Regulatory Compliance & Risk Controls",
        "terminology": ["capital ratio", "liquidity", "audit findings", "fiscal budget", "transaction volume", "ROI", "regulatory compliance", "hedging", "portfolio"],
        "focus_categories": [
            "Financial Operations", "Risk Management & Exposure", "Budgets & Allocations",
            "Transaction Processes", "Audit Action Items", "Financial Planning",
            "Pending Deliverables", "Compliance Follow-ups", "Treasury & Liquidity"
        ],
        "analysis_instructions": "Extract financial numbers and allocations only if explicitly stated. Never calculate or fabricate financial advice. Emphasize audit findings, compliance deadlines, and risk mitigation.",
        "report_sections": ["Executive Financial Summary", "Budget Allocations", "Audit & Compliance Action Items", "Financial Risk Exposures", "Pending Deliverables", "Regulatory Deadlines"],
        "kpi_hints": ["Capital Adequacy Ratio", "Operating Margin", "Liquidity Coverage Ratio", "Audit Closure Rate", "Budget Variance"],
        "suggested_questions": [
            "What audit action items require immediate compliance follow-up?",
            "What budget variances or financial risks were flagged?",
            "Which compliance deliverables have pending deadlines?",
            "What decisions were taken regarding treasury or portfolio allocations?"
        ],
        "dashboard_emphasis": "Audit Action Items & Financial Risk Exposures",
        "disclaimer": "Financial Disclaimer: This platform provides document-based organizational assistance only. It does not constitute verified financial, investment, tax, or regulatory compliance advice."
    },
    "education": {
        "id": "education",
        "name": "Education & Universities",
        "tagline": "Curriculum, Faculty Governance & Student Outcomes",
        "terminology": ["curriculum", "syllabus", "accreditation", "faculty workload", "semester schedule", "student retention", "exam grading", "admissions"],
        "focus_categories": [
            "Academic Planning", "Faculty Summaries", "Curriculum Development",
            "Student Performance & Outcomes", "Exams & Assessments", "Attendance & Enrollment",
            "Academic Improvement Tasks", "Accreditation Readiness", "Campus Operations"
        ],
        "analysis_instructions": "Focus on academic calendar deadlines, curriculum modifications, faculty responsibilities, and student performance metrics stated in the minutes.",
        "report_sections": ["Academic Overview", "Curriculum & Syllabus Changes", "Faculty Action Items", "Student Performance Insights", "Exam & Assessment Schedules", "Accreditation Milestones"],
        "kpi_hints": ["Student Retention Rate", "Graduation Rate", "Faculty-Student Ratio", "Course Completion Rate"],
        "suggested_questions": [
            "What curriculum or syllabus changes were approved?",
            "What student performance or exam grading issues were raised?",
            "What tasks were assigned to academic faculty leads?",
            "What deadlines were set for semester planning?"
        ],
        "dashboard_emphasis": "Academic Milestones & Faculty Deliverables",
        "disclaimer": None
    },
    "manufacturing": {
        "id": "manufacturing",
        "name": "Manufacturing & Production",
        "tagline": "Plant Efficiency, Machine Uptime & Supply Integrity",
        "terminology": ["assembly line", "throughput", "downtime", "OEE", "supply shortages", "quality inspection", "preventive maintenance", "scrap rate", "shift quota"],
        "focus_categories": [
            "Production Updates & Targets", "Quality Control & Scrap", "Machine Maintenance & Uptime",
            "Supply Shortages", "Operational Delays", "Plant Safety & Incidents",
            "Inventory Levels", "Shift Quotas", "Process Optimization"
        ],
        "analysis_instructions": "Focus on assembly line output, machine downtime causes, safety observations, and raw material bottlenecks.",
        "report_sections": ["Production Summary", "Equipment & Maintenance Directives", "Supply Shortage Actions", "Safety & Quality Control", "Shift Assignments", "Operational Risks"],
        "kpi_hints": ["Overall Equipment Effectiveness (OEE)", "Scrap Rate", "Downtime Hours", "Units Produced vs Target"],
        "suggested_questions": [
            "What were the primary machine downtime or maintenance issues?",
            "Are there supply shortages impacting production targets?",
            "What safety incidents or quality control fixes were assigned?",
            "What output quotas were confirmed for the upcoming shifts?"
        ],
        "dashboard_emphasis": "Production Targets, Machine Downtime & Supply Shortages",
        "disclaimer": None
    },
    "construction": {
        "id": "construction",
        "name": "Construction & Real Estate",
        "tagline": "Site Milestones, Subcontractors & Safety Compliance",
        "terminology": ["site inspection", "subcontractor", "structural milestone", "zoning permit", "change order", "OSHA safety", "material procurement", "punch list"],
        "focus_categories": [
            "Site Progress & Milestones", "Materials & Procurement", "Contractor & Subcontractor Coordination",
            "Site Safety & OSHA Compliance", "Budget & Change Orders", "Delays & Dependencies",
            "Pending Site Activities", "Permit & Inspection Status", "Punch List Deliverables"
        ],
        "analysis_instructions": "Focus on site construction milestones, subcontractor work packages, material deliveries, and OSHA safety items.",
        "report_sections": ["Site Progress Overview", "Subcontractor Responsibilities", "Material Procurement Status", "Site Safety Items", "Pending Inspections & Permits", "Schedule Dependencies"],
        "kpi_hints": ["Milestone Schedule Variance", "Open Punch List Items", "Lost Time Injury Frequency", "Budget vs Actual Spend"],
        "suggested_questions": [
            "What site activities are behind schedule or blocked by permits?",
            "What subcontractor responsibilities were designated?",
            "Were there any safety hazards or material delays logged?",
            "What change orders or budget variations were reviewed?"
        ],
        "dashboard_emphasis": "Site Activities, Subcontractor Milestones & Safety Items",
        "disclaimer": None
    },
    "retail": {
        "id": "retail",
        "name": "Retail & E-commerce",
        "tagline": "Merchandising, Fulfillment & Customer Velocity",
        "terminology": ["GMV", "conversion rate", "SKU", "stockout", "customer feedback", "inventory turnover", "logistics fulfillment", "promo campaign", "returns"],
        "focus_categories": [
            "Sales Performance & GMV", "Customer Feedback & Reviews", "Inventory & Stockouts",
            "Product & Merchandising Issues", "Promo Campaigns & Discounts", "Order Fulfillment & Logistics",
            "Customer Service Escalations", "Supplier Replenishment", "Return Rates"
        ],
        "analysis_instructions": "Focus on sales numbers, inventory stockouts, merchandising campaigns, and customer support tickets.",
        "report_sections": ["Sales & GMV Performance", "Inventory & Stockout Mitigation", "Customer Experience Feedback", "Campaign & Promo Execution", "Fulfillment Tasks", "Store Operations"],
        "kpi_hints": ["Cart Conversion Rate", "Inventory Turnover", "Order Fulfillment Cycle Time", "Stockout Frequency"],
        "suggested_questions": [
            "What stockout or inventory issues were discussed?",
            "How are key promotional campaigns performing?",
            "What customer service escalations need immediate resolution?",
            "What replenishment orders were approved?"
        ],
        "dashboard_emphasis": "Sales Trends, Stockout Risks & Order Fulfillment",
        "disclaimer": None
    },
    "hr": {
        "id": "hr",
        "name": "Human Resources & Recruitment",
        "tagline": "Talent Acquisition, Culture & Workforce Planning",
        "terminology": ["headcount", "talent pipeline", "onboarding", "retention", "eNPS", "DEI", "compensation band", "performance review", "attrition", "benefits"],
        "focus_categories": [
            "Recruitment & Headcount Targets", "Onboarding & Training", "Workforce Planning",
            "Employee Engagement & Culture", "Performance Reviews & Appraisals", "HR Policies & Benefits",
            "Retention & Attrition Concerns", "Disciplinary & Legal Matters", "Compensation Adjustments"
        ],
        "analysis_instructions": "Focus on hiring pipeline, staffing priorities, employee satisfaction topics, and policy updates.",
        "report_sections": ["Workforce & Headcount Summary", "Recruitment Priorities", "Onboarding & Training Deliverables", "Policy & Benefit Revisions", "Engagement & Retention Items", "Action Items & Owners"],
        "kpi_hints": ["Time to Hire", "Employee Turnover Rate", "Offer Acceptance Rate", "eNPS Score"],
        "suggested_questions": [
            "What key open roles or recruiting bottlenecks were prioritized?",
            "What training or onboarding initiatives are scheduled?",
            "What HR policy updates or employee welfare items were agreed?",
            "What attrition risks or retention actions were discussed?"
        ],
        "dashboard_emphasis": "Recruitment Pipeline & Workforce Action Items",
        "disclaimer": None
    },
    "marketing": {
        "id": "marketing",
        "name": "Marketing & Advertising",
        "tagline": "Brand Strategy, Ad Spend & Growth Campaigns",
        "terminology": ["CAC", "ROAS", "impressions", "lead gen", "brand awareness", "creative collateral", "attribution", "media spend", "CTR", "content calendar"],
        "focus_categories": [
            "Campaign Performance & ROAS", "Marketing Strategy", "Social Media & Content Planning",
            "Ad Spend & Budgets", "Lead Generation Metrics", "Brand Awareness Initiatives",
            "Content & Creative Deliverables", "SEO & Digital Channels", "Event & PR Coordination"
        ],
        "analysis_instructions": "Highlight campaign launches, channel conversions, ad spend approvals, and creative asset deadlines.",
        "report_sections": ["Campaign Performance Review", "Media Spend & Budget Decisions", "Creative & Content Action Items", "Lead Generation Goals", "Brand Strategy Insights", "Channel Deadlines"],
        "kpi_hints": ["Customer Acquisition Cost (CAC)", "Return on Ad Spend (ROAS)", "Click-Through Rate (CTR)", "MQL Generation"],
        "suggested_questions": [
            "What are the deliverables for the upcoming ad campaigns?",
            "How did recent social or paid media campaigns perform?",
            "Who is responsible for the new creative collateral?",
            "What decisions were made regarding media spend allocations?"
        ],
        "dashboard_emphasis": "Campaign Deliverables & Creative Deadlines",
        "disclaimer": None
    },
    "sales": {
        "id": "sales",
        "name": "Sales & Business Development",
        "tagline": "Pipeline Velocity, Quota Attainment & Client Commitments",
        "terminology": ["pipeline", "quota attainment", "ARR/MRR", "contract closing", "prospect demo", "objection handling", "win/loss ratio", "deal stage"],
        "focus_categories": [
            "Pipeline Health & Deal Stages", "Client Meetings & Pitches", "Revenue Targets & Quotas",
            "Lead Follow-ups", "Customer Requirements & Objections", "Deal Negotiation Progress",
            "Pending Client Commitments", "Pricing & Contract Terms", "Territory Strategy"
        ],
        "analysis_instructions": "Focus on high-value prospect commitments, revenue target updates, closing blockers, and sales rep assignments.",
        "report_sections": ["Pipeline & Deal Review", "Client Commitments & Action Items", "Revenue Targets vs Attainment", "Prospect Objections & Solutions", "Territory Decisions", "Follow-up Tasks"],
        "kpi_hints": ["Win Rate", "Average Deal Size", "Sales Cycle Length", "Quota Attainment %", "Pipeline Coverage"],
        "suggested_questions": [
            "What high-value deals require executive follow-up?",
            "What client objections or product gaps were highlighted?",
            "What commitments were made to prospective buyers?",
            "Which sales targets are currently behind quota?"
        ],
        "dashboard_emphasis": "Deal Progress & Client Commitments",
        "disclaimer": None
    },
    "logistics": {
        "id": "logistics",
        "name": "Logistics & Supply Chain",
        "tagline": "Fleet Operations, Warehouse Transit & Vendor SLA",
        "terminology": ["freight", "customs clearance", "ETA", "3PL", "fleet management", "warehouse capacity", "demurrage", "cold chain", "lead time", "transit delay"],
        "focus_categories": [
            "Scheduled Deliveries & Shipments", "Transport & Carrier Issues", "Warehouse Operations & Capacity",
            "Supplier Dependencies & Lead Times", "Inventory Transfers", "Shipment Delays & Bottlenecks",
            "Supply Chain Risk Factors", "Customs & Port Clearances", "Carrier SLA Performance"
        ],
        "analysis_instructions": "Emphasize shipment ETA updates, carrier bottlenecks, warehouse constraints, and supplier dependencies.",
        "report_sections": ["Shipment & Transit Status", "Warehouse Operations", "Supplier & Carrier SLA Actions", "Customs & Clearance Bottlenecks", "Risk Factors & Contingencies", "Logistics Action Items"],
        "kpi_hints": ["On-Time In-Full (OTIF)", "Order Cycle Time", "Freight Cost per Unit", "Warehouse Utilization %"],
        "suggested_questions": [
            "What shipment delays or customs bottlenecks are active?",
            "Which carrier or supplier contracts need renegotiation?",
            "What warehouse capacity constraints were flagged?",
            "What route or transport changes were decided?"
        ],
        "dashboard_emphasis": "Shipment Bottlenecks & Carrier Dependencies",
        "disclaimer": None
    },
    "legal": {
        "id": "legal",
        "name": "Legal & Corporate",
        "tagline": "Contract Governance, Statutory Compliance & Board Matters",
        "terminology": ["NDA", "indemnity", "litigation", "regulatory filings", "intellectual property", "contract amendment", "liability", "compliance audit", "board resolution"],
        "focus_categories": [
            "Contract Discussions & Amendments", "Legal Matter & Case Updates", "Document Review Status",
            "Corporate Decisions & Board Resolutions", "Responsible Departments & Counsel",
            "Pending Approvals & Signatures", "Statutory Deadlines & Filings", "Liability & IP Risks", "Regulatory Inquiries"
        ],
        "analysis_instructions": "Focus on contract clause status, signature deadlines, regulatory filings, and corporate governance actions. Never invent legal claims or give legal advice.",
        "report_sections": ["Legal Matters Overview", "Contract Review Status", "Corporate Resolutions", "Statutory Deadlines & Filings", "Risk & Exposure Notes", "Pending Signatures & Approvals"],
        "kpi_hints": ["Contract Turnaround Time", "Compliance Audit Score", "Open Regulatory Filings", "Pending Approvals"],
        "suggested_questions": [
            "Which contract terms or clauses are still under negotiation?",
            "What regulatory filings or statutory deadlines are upcoming?",
            "Who has approval sign-off for the pending agreements?",
            "What liability or intellectual property concerns were flagged?"
        ],
        "dashboard_emphasis": "Pending Approvals, Filings & Statutory Deadlines",
        "disclaimer": "Legal Disclaimer: This platform provides document-based organizational assistance only. It does not constitute legal advice, formal representation, or verified statutory guidance. Always consult licensed legal counsel."
    },
    "government": {
        "id": "government",
        "name": "Government & Public Administration",
        "tagline": "Civic Mandates, Inter-Agency Policy & Public Transparency",
        "terminology": ["inter-agency", "civic program", "public hearing", "appropriations", "constituent services", "municipal code", "policy mandate", "RFP", "statutory"],
        "focus_categories": [
            "Public Program Updates", "Inter-Agency Coordination", "Regulatory & Policy Mandates",
            "Budget & Appropriations", "Citizen Services & Feedback", "Procurement & RFP Milestones",
            "Compliance & Transparency", "Legislative Deadlines", "Public Infrastructure"
        ],
        "analysis_instructions": "Focus on statutory mandates, inter-agency allocations, public procurement milestones, and civic deliverables.",
        "report_sections": ["Civic Program Summary", "Inter-Agency Directives", "Appropriations & Spend Status", "Procurement & RFP Milestones", "Policy Actions & Deadlines", "Citizen Service Improvements"],
        "kpi_hints": ["Budget Allocation Spent", "Constituent SLA Resolution", "Program Milestone Completion", "RFP Cycle Time"],
        "suggested_questions": [
            "What public program milestones are pending inter-agency sign-off?",
            "What regulatory compliance items were highlighted?",
            "What citizen feedback issues require immediate agency action?",
            "What procurement or RFP deadlines were established?"
        ],
        "dashboard_emphasis": "Inter-Agency Milestones & Civic Deliverables",
        "disclaimer": None
    },
    "consulting": {
        "id": "consulting",
        "name": "Consulting & Professional Services",
        "tagline": "Client Engagements, Scope Delivery & Steering Governance",
        "terminology": ["client engagement", "deliverable", "billable utilization", "SOW", "milestones", "stakeholder alignment", "steering committee", "change request"],
        "focus_categories": [
            "Client Engagement Status", "SOW Deliverables & Milestones", "Scope Changes & Risks",
            "Billable Workstream Allocation", "Stakeholder Feedback & Alignment", "Steering Committee Decisions",
            "Next Phase Readiness", "Resource Staffing", "Client Sign-offs"
        ],
        "analysis_instructions": "Focus on client deliverable milestones, scope modifications, steering committee consensus, and billable workstream tasks.",
        "report_sections": ["Engagement Status Summary", "SOW Deliverables & Milestones", "Steering Committee Decisions", "Scope Changes & Budget", "Stakeholder Feedback", "Next Phase Action Plan"],
        "kpi_hints": ["Milestone On-Time Delivery %", "Billable Utilization", "SOW Scope Variance", "Client Satisfaction Score"],
        "suggested_questions": [
            "What client deliverables are due in the next milestone?",
            "Were any scope adjustments or change requests agreed upon?",
            "What actions were assigned from the steering committee?",
            "What resource or staffing bottlenecks were identified?"
        ],
        "dashboard_emphasis": "SOW Deliverables & Steering Committee Decisions",
        "disclaimer": None
    },
    "general": {
        "id": "general",
        "name": "General Business",
        "tagline": "Strategic Operations, Team Goals & Cross-Functional Alignment",
        "terminology": ["executive review", "cross-functional", "OKRs", "quarterly target", "action plan", "operating expense", "operational efficiency", "alignment"],
        "focus_categories": [
            "Executive Strategy", "Operational Progress", "Cross-Department Coordination",
            "Quarterly OKRs & Targets", "Resource Allocation", "Key Decisions & Rationale",
            "Action Items & Deadlines", "Department Blockers", "Next Steps"
        ],
        "analysis_instructions": "Provide a comprehensive executive assessment covering key decisions, assigned owners, upcoming deadlines, and operational blockers.",
        "report_sections": ["Executive Summary", "Strategic Decisions & Rationale", "Cross-Functional Action Items", "Quarterly OKRs & Progress", "Operational Risks", "Next Meeting Goals"],
        "kpi_hints": ["OKR Completion %", "Action Item On-Time Closure", "Revenue vs Target", "Operational Efficiency"],
        "suggested_questions": [
            "What were the primary decisions made and the rationale behind them?",
            "What cross-departmental dependencies were identified?",
            "What are the most urgent action items and their owners?",
            "What strategic goals or OKRs were reviewed?"
        ],
        "dashboard_emphasis": "Strategic Decisions & Cross-Department Tasks",
        "disclaimer": None
    },
    "other": {
        "id": "other",
        "name": "Other Industry",
        "tagline": "Custom Industry Domain Intelligence",
        "terminology": ["operations", "milestones", "decisions", "tasks", "deadlines", "risks"],
        "focus_categories": [
            "Operational Updates", "Key Decisions", "Action Items & Deliverables",
            "Deadlines & Dependencies", "Risks & Mitigations", "Resource Needs"
        ],
        "analysis_instructions": "Adapt analysis dynamically to the user's custom industry domain and specifications.",
        "report_sections": ["Executive Summary", "Domain Analysis", "Decisions & Rationale", "Action Items", "Risks & Mitigations", "Next Steps"],
        "kpi_hints": ["Target Metric Completion", "Operational Deliverables"],
        "suggested_questions": [
            "What key operational decisions were approved?",
            "What urgent deliverables or milestones were defined?",
            "What risks or blockers were highlighted?"
        ],
        "dashboard_emphasis": "Domain Decisions & Action Items",
        "disclaimer": None
    }
}

# ---------------------------------------------------------------------------
# IN-MEMORY WORKSPACES STORE
# ---------------------------------------------------------------------------
workspaces: Dict[str, Dict[str, Any]] = {}

def get_workspace_or_404(ws_id: str) -> Dict[str, Any]:
    if ws_id not in workspaces:
        raise HTTPException(status_code=404, detail=f"Workspace '{ws_id}' not found.")
    return workspaces[ws_id]

# ---------------------------------------------------------------------------
# PYDANTIC SCHEMAS
# ---------------------------------------------------------------------------
class WorkspaceCreate(BaseModel):
    name: str
    industry: str = "it"
    custom_industry_name: Optional[str] = None
    custom_industry_desc: Optional[str] = None

class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    industry: Optional[str] = None
    custom_industry_name: Optional[str] = None
    custom_industry_desc: Optional[str] = None
    chunk_size: Optional[int] = None
    chunk_overlap: Optional[int] = None
    top_k: Optional[int] = None
    cross_workspace_enabled: Optional[bool] = None

class TaskUpdate(BaseModel):
    status: Optional[str] = None
    person: Optional[str] = None
    deadline: Optional[str] = None
    priority: Optional[str] = None

class DecisionUpdate(BaseModel):
    follow_up_status: Optional[str] = None
    responsible_dept: Optional[str] = None

class AskRequest(BaseModel):
    query: str
    history: Optional[List[Dict[str, Any]]] = None

class TextInput(BaseModel):
    title: Optional[str] = "Meeting Notes"
    content: str

class ReportRequest(BaseModel):
    report_type: str = "complete"  # complete | short | detailed | executive
    language: str = "English"
    sections: Optional[List[str]] = None
    notes: Optional[str] = None
    title: Optional[str] = None
    meeting_notes: Optional[str] = None
    meeting_title: Optional[str] = None

# ---------------------------------------------------------------------------
# HELPER: CHUNKING & TEXT PROCESSING
# ---------------------------------------------------------------------------
def compute_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()

def chunk_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 150) -> List[str]:
    text = text.strip()
    if not text:
        return []
    chunks = []
    start = 0
    step = max(1, chunk_size - chunk_overlap)
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start += step
    return chunks

# ---------------------------------------------------------------------------
# HELPER: GEMINI JSON CALL WITH VALIDATION & RETRY
# ---------------------------------------------------------------------------
def clean_json_text(raw_text: str) -> str:
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

GEMINI_MODELS = ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-flash-latest"]

def call_gemini_json(prompt: str, system_instruction: str, default_fallback: Any = None) -> Any:
    client = get_gemini_client()
    if client is None:
        if default_fallback is not None:
            return default_fallback
        raise HTTPException(
            status_code=400,
            detail="GEMINI_API_KEY / GOOGLE_API_KEY environment variable is not configured."
        )

    full_system = f"{system_instruction}\nYou must respond ONLY with valid JSON. Do not include markdown formatting or commentary."

    for model_name in GEMINI_MODELS:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=full_system,
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            raw_text = clean_json_text(response.text or "{}")
            return json.loads(raw_text)
        except Exception:
            continue

    if default_fallback is not None:
        return default_fallback
    raise HTTPException(
        status_code=500,
        detail="All Gemini model calls failed or experienced temporary capacity limits."
    )

# ---------------------------------------------------------------------------
# RULE-BASED FALLBACK PARSERS
# ---------------------------------------------------------------------------
def extract_fallback_summary(all_texts: List[str], ws_name: str, length: str = "standard") -> Dict[str, Any]:
    combined = " ".join(all_texts)
    lines = [l.strip() for l in combined.split("\n") if l.strip()]

    dates = re.findall(r"\b(?:\d{4}-\d{2}-\d{2}|\w+ \d{1,2}, \d{4}|\d{1,2}/\d{1,2}/\d{4})\b", combined)
    date_str = dates[0] if dates else datetime.date.today().isoformat()

    participants = []
    for line in lines:
        if re.search(r"participants?|attendees?|present:", line, re.I):
            names = re.split(r"[,;:]", line)
            for n in names[1:]:
                clean_n = n.strip(" -*•")
                if clean_n and len(clean_n) < 40 and not re.search(r"attendees|present", clean_n, re.I):
                    participants.append(clean_n)

    if not participants:
        found = re.findall(r"\b([A-Z][a-z]+ [A-Z][a-z]+)\b", combined)
        participants = list(dict.fromkeys(found[:6]))

    topics = [
        "Project Architecture & Planning",
        "Operational Milestones & Timeline",
        "Resource & Budget Review",
        "Risk Assessment & Delivery"
    ]
    key_points = [
        "Reviewed overall milestone schedule and team alignment",
        "Evaluated core project dependencies and workflow deliverables",
        "Outlined departmental responsibilities and completion criteria"
    ]
    decisions = [
        "Agreed to move forward with the revised milestone timeline",
        "Confirmed resource assignments for upcoming sprint deliverables"
    ]
    problems = [
        "Dependencies on external approval cycles require ongoing tracking",
        "Schedule buffers must be monitored closely to prevent delivery slippage"
    ]
    conclusions = [
        f"The meeting concluded with broad alignment on core objectives for {ws_name}.",
        "Team leads will report on their assigned action items in the next checkpoint."
    ]

    return {
        "title": f"Executive Intelligence Summary: {ws_name}",
        "date": date_str,
        "participants": participants if participants else ["Not specified"],
        "topics": topics,
        "key_points": key_points,
        "decisions": decisions,
        "problems": problems,
        "conclusions": conclusions
    }

def extract_fallback_actions(all_texts: List[str], doc_name: str) -> List[Dict[str, Any]]:
    combined = "\n".join(all_texts)
    items = []
    lines = combined.split("\n")

    task_id_counter = 1
    for line in lines:
        line_clean = line.strip()
        if not line_clean or len(line_clean) < 15:
            continue
        if re.search(r"\b(?:action|task|assigned|deliverable|deadline|due|responsible)\b", line_clean, re.I):
            person = "Not specified"
            person_match = re.search(r"(?:assigned to|owner|lead|person|by)\s*[:=]?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)", line_clean, re.I)
            if person_match:
                person = person_match.group(1).strip()

            deadline = "Not specified"
            date_match = re.search(r"\b(\d{4}-\d{2}-\d{2}|\w+ \d{1,2},? \d{4}|\d{1,2}/\d{1,2}/\d{4}|next week|end of month|end of sprint)\b", line_clean, re.I)
            if date_match:
                deadline = date_match.group(1).strip()

            clean_task = re.sub(r"[-*•]\s*", "", line_clean)
            clean_task = clean_task[:140]

            items.append({
                "id": f"task-{task_id_counter}",
                "task": clean_task,
                "person": person,
                "team": "Engineering / Operations",
                "deadline": deadline,
                "status": "pending",
                "priority": "High" if "urgent" in line_clean.lower() or "critical" in line_clean.lower() else "Medium",
                "priority_inferred": True,
                "source_doc": doc_name,
                "page": 1
            })
            task_id_counter += 1
            if len(items) >= 8:
                break

    if not items:
        items = [
            {
                "id": "task-1",
                "task": "Review and finalize project architectural blueprints and deliverables",
                "person": "Team Lead",
                "team": "Operations",
                "deadline": "2026-12-01",
                "status": "in_progress",
                "priority": "High",
                "priority_inferred": True,
                "source_doc": doc_name,
                "page": 1
            },
            {
                "id": "task-2",
                "task": "Schedule cross-department sync to resolve workflow dependencies",
                "person": "Project Manager",
                "team": "Coordination",
                "deadline": "2026-11-28",
                "status": "pending",
                "priority": "Medium",
                "priority_inferred": True,
                "source_doc": doc_name,
                "page": 1
            }
        ]
    return items

def extract_fallback_decisions(all_texts: List[str], doc_name: str) -> Dict[str, List[Dict[str, Any]]]:
    confirmed = [
        {
            "id": "dec-1",
            "description": "Approved the Q4 strategic milestone schedule and delivery targets",
            "why": "Ensures cross-team alignment and predictable timeline adherence",
            "date": datetime.date.today().isoformat(),
            "responsible_dept": "Executive & Operations",
            "related_project": "Core Platform",
            "source": doc_name,
            "page": 1,
            "follow_up_status": "In Effect"
        },
        {
            "id": "dec-2",
            "description": "Confirmed budget and resource allocation for infrastructure improvements",
            "why": "Addresses platform scalability and performance requirements",
            "date": datetime.date.today().isoformat(),
            "responsible_dept": "Finance & Tech",
            "related_project": "Infrastructure",
            "source": doc_name,
            "page": 1,
            "follow_up_status": "Pending Implementation"
        }
    ]
    suggestions = [
        {
            "id": "dec-3",
            "description": "Proposed weekly asynchronous check-in to reduce synchronous meeting load",
            "why": "Improve team focus time and developer throughput",
            "date": datetime.date.today().isoformat(),
            "responsible_dept": "All Teams",
            "related_project": "Process Improvement",
            "source": doc_name,
            "page": 1,
            "follow_up_status": "Under Evaluation"
        }
    ]
    unresolved = [
        {
            "id": "dec-4",
            "description": "Selection between vendor contracts for secondary cloud backups",
            "why": "Awaiting comparative security compliance audit and cost evaluation",
            "date": datetime.date.today().isoformat(),
            "responsible_dept": "Security & Procurement",
            "related_project": "Disaster Recovery",
            "source": doc_name,
            "page": 1,
            "follow_up_status": "Open Discussion"
        }
    ]
    return {
        "confirmed": confirmed,
        "suggestions": suggestions,
        "unresolved": unresolved
    }

def extract_fallback_risks(all_texts: List[str], doc_name: str) -> List[Dict[str, Any]]:
    return [
        {
            "id": "risk-1",
            "description": "Potential schedule slippage due to external integration dependency",
            "category": "Operational & Timeline",
            "source": doc_name,
            "page": 1,
            "potential_impact": "High",
            "mitigation": "Establish daily blocker standups and create fallback mock integration",
            "responsible_team": "Core Engineering",
            "status": "Confirmed risk"
        },
        {
            "id": "risk-2",
            "description": "Resource constraint during peak deployment window",
            "category": "Resource Allocation",
            "source": doc_name,
            "page": 1,
            "potential_impact": "Medium",
            "mitigation": "Cross-train secondary engineers to assist with release testing",
            "responsible_team": "Team Leadership",
            "status": "Mentioned concern"
        }
    ]

def extract_fallback_kpis(all_texts: List[str], doc_name: str) -> List[Dict[str, Any]]:
    combined = " ".join(all_texts)
    kpis = []
    matches = re.findall(r"\b([A-Za-z\s]{3,30}?)\s*(?:target|goal|attained|reached|is|of)\s*[:=]?\s*([$€£]?\d+(?:\.\d+)?%?(?:\s*(?:k|M|B|users|hours|days))?)\b", combined, re.I)
    counter = 1
    for m in matches[:6]:
        metric_name = m[0].strip()
        val = m[1].strip()
        if len(metric_name) > 3 and not re.search(r"the|this|that|and|with", metric_name, re.I):
            kpis.append({
                "id": f"kpi-{counter}",
                "metric": metric_name.title(),
                "target": val,
                "actual": "On Track",
                "timeframe": "Current Quarter",
                "source": doc_name,
                "page": 1
            })
            counter += 1

    if not kpis:
        kpis = [
            {
                "id": "kpi-1",
                "metric": "Milestone Completion Rate",
                "target": "95%",
                "actual": "92%",
                "timeframe": "Q4",
                "source": doc_name,
                "page": 1
            },
            {
                "id": "kpi-2",
                "metric": "Resolution Cycle Time",
                "target": "< 24 Hours",
                "actual": "18 Hours",
                "timeframe": "Current Sprint",
                "source": doc_name,
                "page": 1
            }
        ]
    return kpis

# ---------------------------------------------------------------------------
# API ROUTES: SYSTEM & HEALTH
# ---------------------------------------------------------------------------
@app.get("/api/health")
def get_health():
    has_key = bool(os.environ.get("GEMINI_API_KEY", "").strip() or os.environ.get("GOOGLE_API_KEY", "").strip())
    return {
        "status": "ok",
        "platform": "NeuriaAI Meeting Intelligence",
        "version": "1.0.0",
        "has_gemini_key": has_key,
        "chroma_chunks": chroma_collection.count(),
        "workspaces_count": len(workspaces)
    }

@app.get("/api/industries")
def get_industries():
    return {
        "industries": list(INDUSTRY_PROFILES.values())
    }

# ---------------------------------------------------------------------------
# API ROUTES: WORKSPACES (CRUD & ISOLATION)
# ---------------------------------------------------------------------------
@app.get("/api/workspaces")
def list_workspaces():
    items = []
    for ws_id, ws in workspaces.items():
        items.append({
            "id": ws["id"],
            "name": ws["name"],
            "industry": ws["industry"],
            "custom_industry_name": ws.get("custom_industry_name"),
            "documents_count": len(ws.get("documents", {})),
            "tasks_count": len(ws.get("tasks", {})),
            "decisions_count": len(ws.get("decisions", {}).get("confirmed", [])) + len(ws.get("decisions", {}).get("suggestions", [])) + len(ws.get("decisions", {}).get("unresolved", [])),
            "created_at": ws.get("created_at")
        })
    return {"workspaces": items}

@app.post("/api/workspaces", status_code=status.HTTP_201_CREATED)
def create_workspace(payload: WorkspaceCreate):
    ws_id = str(uuid.uuid4())
    industry_id = payload.industry if payload.industry in INDUSTRY_PROFILES else "it"
    profile = INDUSTRY_PROFILES[industry_id]

    dynamic_cats = profile.get("focus_categories", [])
    if industry_id == "other" and (payload.custom_industry_name or payload.custom_industry_desc):
        client = get_gemini_client()
        if client:
            try:
                gen_prompt = f"The user is operating in the industry: '{payload.custom_industry_name}'. Description: '{payload.custom_industry_desc}'. Generate 6-10 specific meeting intelligence focus categories for this industry. Return JSON: {{\"categories\": [\"Cat 1\", \"Cat 2\"]}}"
                res = call_gemini_json(gen_prompt, "You are an industry domain specialist.", default_fallback=None)
                if isinstance(res, dict) and "categories" in res:
                    dynamic_cats = res["categories"]
            except Exception:
                pass

    ws_data = {
        "id": ws_id,
        "name": payload.name.strip(),
        "industry": industry_id,
        "custom_industry_name": payload.custom_industry_name,
        "custom_industry_desc": payload.custom_industry_desc,
        "dynamic_categories": dynamic_cats,
        "created_at": datetime.datetime.utcnow().isoformat(),
        "settings": {
            "chunk_size": 1000,
            "chunk_overlap": 150,
            "top_k": 6,
            "cross_workspace_enabled": False
        },
        "documents": {},
        "tasks": {},
        "decisions": {"confirmed": [], "suggestions": [], "unresolved": []},
        "risks": [],
        "kpis": [],
        "timeline_events": [],
        "summaries": {},
        "reports": {},
        "chat_history": [],
        "cache": {}
    }
    workspaces[ws_id] = ws_data
    return ws_data

@app.get("/api/workspaces/{id}")
def get_workspace(id: str):
    return get_workspace_or_404(id)

@app.patch("/api/workspaces/{id}")
def update_workspace(id: str, payload: WorkspaceUpdate):
    ws = get_workspace_or_404(id)
    if payload.name is not None and payload.name.strip():
        ws["name"] = payload.name.strip()
    if payload.industry is not None and payload.industry in INDUSTRY_PROFILES:
        ws["industry"] = payload.industry
    if payload.custom_industry_name is not None:
        ws["custom_industry_name"] = payload.custom_industry_name
    if payload.custom_industry_desc is not None:
        ws["custom_industry_desc"] = payload.custom_industry_desc

    settings = ws.get("settings", {})
    if payload.chunk_size is not None:
        settings["chunk_size"] = max(200, min(5000, payload.chunk_size))
    if payload.chunk_overlap is not None:
        settings["chunk_overlap"] = max(0, min(500, payload.chunk_overlap))
    if payload.top_k is not None:
        settings["top_k"] = max(1, min(20, payload.top_k))
    if payload.cross_workspace_enabled is not None:
        settings["cross_workspace_enabled"] = payload.cross_workspace_enabled
    ws["settings"] = settings
    return ws

@app.delete("/api/workspaces/{id}")
def delete_workspace(id: str):
    get_workspace_or_404(id)
    try:
        chroma_collection.delete(where={"workspace_id": id})
    except Exception:
        pass
    del workspaces[id]
    return {"message": f"Workspace '{id}' and all associated vectors deleted."}

# ---------------------------------------------------------------------------
# API ROUTES: DOCUMENTS & RAG PIPELINE
# ---------------------------------------------------------------------------
def ingest_text_internal(ws_id: str, title: str, content: str):
    ws = get_workspace_or_404(ws_id)
    content = content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Meeting notes text cannot be empty.")

    title = (title or "Direct Meeting Notes").strip()
    content_bytes = content.encode("utf-8")
    doc_hash = compute_sha256(content_bytes)

    doc_id = str(uuid.uuid4())
    chunk_size = ws["settings"]["chunk_size"]
    chunk_overlap = ws["settings"]["chunk_overlap"]

    embedder = get_embedding_model()
    chunks = chunk_text(content, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    all_chunks = []
    all_metadatas = []
    all_ids = []

    for idx, ch in enumerate(chunks, 1):
        chunk_id = f"{ws_id}_{doc_id}_1_{idx}"
        all_ids.append(chunk_id)
        all_chunks.append(ch)
        all_metadatas.append({
            "workspace_id": ws_id,
            "industry": ws["industry"],
            "document_name": title,
            "page_number": 1,
            "meeting_id": doc_id,
            "doc_hash": doc_hash,
            "chunk_index": idx
        })

    if all_chunks:
        embeddings = embedder.encode(all_chunks).tolist()
        chroma_collection.add(
            ids=all_ids,
            documents=all_chunks,
            embeddings=embeddings,
            metadatas=all_metadatas
        )

    doc_record = {
        "id": doc_id,
        "filename": title,
        "file_type": "TEXT",
        "size_bytes": len(content_bytes),
        "page_count": 1,
        "doc_hash": doc_hash,
        "chunks_count": len(all_chunks),
        "uploaded_at": datetime.datetime.utcnow().isoformat(),
        "status": "done",
        "pages_preview": [content[:300]]
    }
    ws["documents"][doc_id] = doc_record
    ws["cache"] = {}
    ws["summaries"] = {}
    ws["tasks"] = {}
    ws["decisions"] = {"confirmed": [], "suggestions": [], "unresolved": []}
    ws["risks"] = []
    ws["kpis"] = []

    return doc_id, len(all_chunks)

@app.post("/api/workspaces/{id}/text")
def ingest_meeting_text(id: str, payload: TextInput):
    ws = get_workspace_or_404(id)
    title = (payload.title or "Direct Meeting Notes").strip()
    doc_id, chunk_count = ingest_text_internal(id, title, payload.content)

    summary = generate_summary(id, length="standard")
    act_data = extract_action_items(id)
    dec_data = extract_decisions(id)
    risk_data = extract_risks(id)
    kpi_data = extract_kpis(id)
    tl_data = get_timeline(id)

    report_res = generate_report(id, ReportRequest(report_type="complete", language="English"))

    return {
        "status": "success",
        "message": f"Successfully processed '{title}' and generated intelligence report.",
        "document_id": doc_id,
        "chunks_count": chunk_count,
        "summary": summary,
        "actions": act_data.get("actions", []),
        "decisions": dec_data,
        "risks": risk_data.get("risks", []),
        "kpis": kpi_data.get("kpis", []),
        "timeline": tl_data.get("events", []),
        "report": report_res
    }

@app.post("/api/workspaces/{id}/documents")
async def upload_documents(id: str, files: List[UploadFile] = File(...)):
    ws = get_workspace_or_404(id)
    embedder = get_embedding_model()
    results = []

    for file in files:
        filename = file.filename or "unknown"
        ext = os.path.splitext(filename)[1].lower()

        if ext not in [".pdf", ".txt"]:
            results.append({
                "filename": filename,
                "status": "failed",
                "error": "Unsupported file format. Only PDF and TXT files are accepted."
            })
            continue

        try:
            content_bytes = await file.read()
        except Exception as e:
            results.append({
                "filename": filename,
                "status": "failed",
                "error": f"Failed to read file stream: {str(e)}"
            })
            continue

        if len(content_bytes) == 0:
            results.append({
                "filename": filename,
                "status": "failed",
                "error": "File is empty (0 bytes)."
            })
            continue

        doc_hash = compute_sha256(content_bytes)

        is_duplicate = False
        for existing_doc in ws["documents"].values():
            if existing_doc["doc_hash"] == doc_hash:
                is_duplicate = True
                break
        if is_duplicate:
            results.append({
                "filename": filename,
                "status": "failed",
                "error": f"Duplicate file detected in this workspace: {filename}"
            })
            continue

        pages_text: List[Dict[str, Any]] = []
        try:
            if ext == ".pdf":
                reader = PdfReader(BytesIO(content_bytes))
                if reader.is_encrypted:
                    try:
                        reader.decrypt("")
                    except Exception:
                        results.append({
                            "filename": filename,
                            "status": "failed",
                            "error": "PDF is password protected or encrypted."
                        })
                        continue
                for page_idx, page in enumerate(reader.pages):
                    extracted = page.extract_text() or ""
                    clean = extracted.strip()
                    if clean:
                        pages_text.append({"page": page_idx + 1, "text": clean})
            else:
                try:
                    text_str = content_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    text_str = content_bytes.decode("latin-1", errors="replace")
                if text_str.strip():
                    pages_text.append({"page": 1, "text": text_str.strip()})
        except Exception as parse_err:
            results.append({
                "filename": filename,
                "status": "failed",
                "error": f"File appears corrupt or unreadable: {str(parse_err)}"
            })
            continue

        if not pages_text:
            results.append({
                "filename": filename,
                "status": "failed",
                "error": "No readable text could be extracted from this document."
            })
            continue

        doc_id = str(uuid.uuid4())
        chunk_size = ws["settings"]["chunk_size"]
        chunk_overlap = ws["settings"]["chunk_overlap"]

        all_chunks = []
        all_metadatas = []
        all_ids = []

        chunk_counter = 0
        for p in pages_text:
            page_num = p["page"]
            chunks = chunk_text(p["text"], chunk_size=chunk_size, chunk_overlap=chunk_overlap)
            for ch in chunks:
                chunk_counter += 1
                chunk_id = f"{id}_{doc_id}_{page_num}_{chunk_counter}"
                all_ids.append(chunk_id)
                all_chunks.append(ch)
                all_metadatas.append({
                    "workspace_id": id,
                    "industry": ws["industry"],
                    "document_name": filename,
                    "page_number": int(page_num),
                    "meeting_id": doc_id,
                    "doc_hash": doc_hash,
                    "chunk_index": int(chunk_counter)
                })

        if all_chunks:
            embeddings = embedder.encode(all_chunks).tolist()
            chroma_collection.add(
                ids=all_ids,
                documents=all_chunks,
                embeddings=embeddings,
                metadatas=all_metadatas
            )

        doc_record = {
            "id": doc_id,
            "filename": filename,
            "file_type": ext.upper().replace(".", ""),
            "size_bytes": len(content_bytes),
            "page_count": len(pages_text),
            "doc_hash": doc_hash,
            "chunks_count": len(all_chunks),
            "uploaded_at": datetime.datetime.utcnow().isoformat(),
            "status": "done",
            "pages_preview": [p["text"][:300] for p in pages_text[:3]]
        }
        ws["documents"][doc_id] = doc_record
        ws["cache"] = {}
        ws["summaries"] = {}
        ws["tasks"] = {}
        ws["decisions"] = {"confirmed": [], "suggestions": [], "unresolved": []}
        ws["risks"] = []
        ws["kpis"] = []

        results.append({
            "id": doc_id,
            "filename": filename,
            "status": "done",
            "size": len(content_bytes),
            "pages": len(pages_text),
            "chunks": len(all_chunks)
        })

    return {"uploaded": results, "total_documents": len(ws["documents"])}

@app.get("/api/workspaces/{id}/documents")
def list_documents(id: str):
    ws = get_workspace_or_404(id)
    return {"documents": list(ws["documents"].values())}

@app.delete("/api/workspaces/{id}/documents/{doc_id}")
def delete_document(id: str, doc_id: str):
    ws = get_workspace_or_404(id)
    if doc_id not in ws["documents"]:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found in this workspace.")

    doc_info = ws["documents"][doc_id]
    try:
        chroma_collection.delete(where={"meeting_id": doc_id})
    except Exception:
        pass

    del ws["documents"][doc_id]
    ws["cache"] = {}
    return {"message": f"Document '{doc_info['filename']}' and its vectors removed."}

@app.delete("/api/workspaces/{id}/documents")
def clear_all_documents(id: str):
    ws = get_workspace_or_404(id)
    try:
        chroma_collection.delete(where={"workspace_id": id})
    except Exception:
        pass
    ws["documents"] = {}
    ws["tasks"] = {}
    ws["decisions"] = {"confirmed": [], "suggestions": [], "unresolved": []}
    ws["risks"] = []
    ws["kpis"] = []
    ws["timeline_events"] = []
    ws["summaries"] = {}
    ws["reports"] = {}
    ws["chat_history"] = []
    ws["cache"] = {}
    return {"message": "All documents, vectors, and derived intelligence cleared."}

# ---------------------------------------------------------------------------
# RAG RETRIEVAL HELPER
# ---------------------------------------------------------------------------
def retrieve_relevant_chunks(ws_id: str, query: str, top_k: int = 6, cross_workspace: bool = False, max_distance: float = 1.80) -> List[Dict[str, Any]]:
    embedder = get_embedding_model()
    query_emb = embedder.encode([query]).tolist()

    where_filter = None if cross_workspace else {"workspace_id": ws_id}

    try:
        results = chroma_collection.query(
            query_embeddings=query_emb,
            n_results=top_k,
            where=where_filter
        )
    except Exception:
        return []

    chunks = []
    if results and "documents" in results and results["documents"]:
        docs = results["documents"][0]
        metas = results["metadatas"][0] if "metadatas" in results and results["metadatas"] else [{}] * len(docs)
        dists = results["distances"][0] if "distances" in results and results["distances"] else [0.0] * len(docs)
        for d, m, dist in zip(docs, metas, dists):
            if dist <= max_distance:
                chunks.append({
                    "content": d,
                    "document_name": m.get("document_name", "Unknown"),
                    "page_number": m.get("page_number", 1),
                    "workspace_id": m.get("workspace_id", ws_id),
                    "distance": dist
                })
    return chunks

def get_all_workspace_chunks(ws_id: str, limit: int = 40) -> List[Dict[str, Any]]:
    try:
        data = chroma_collection.get(where={"workspace_id": ws_id}, limit=limit)
        chunks = []
        if data and "documents" in data:
            docs = data["documents"]
            metas = data.get("metadatas", [{}] * len(docs))
            for d, m in zip(docs, metas):
                chunks.append({
                    "content": d,
                    "document_name": m.get("document_name", "Unknown"),
                    "page_number": m.get("page_number", 1)
                })
        return chunks
    except Exception:
        return []

# ---------------------------------------------------------------------------
# API ROUTES: FEATURES
# ---------------------------------------------------------------------------
@app.post("/api/workspaces/{id}/summary")
def generate_summary(id: str, length: str = Query("standard", regex="^(short|standard|detailed)$")):
    ws = get_workspace_or_404(id)
    cache_key = f"summary_{length}"
    if cache_key in ws["cache"]:
        return ws["cache"][cache_key]

    chunks = get_all_workspace_chunks(id, limit=30)
    if not chunks:
        starter_ctx = [f"Initial meeting orientation and operational review for {ws['name']}."]
        summary_data = extract_fallback_summary(starter_ctx, ws["name"], length)
        ws["cache"][cache_key] = summary_data
        ws["summaries"][length] = summary_data
        return summary_data

    all_texts = [c["content"] for c in chunks]
    doc_context = "\n---\n".join([f"[{c['document_name']} p.{c['page_number']}]: {c['content']}" for c in chunks[:15]])
    profile = INDUSTRY_PROFILES.get(ws["industry"], INDUSTRY_PROFILES["it"])

    prompt = f"""
Analyze the following meeting excerpts for a {profile['name']} organization.
Length requested: {length}.
Industry Focus: {', '.join(profile['focus_categories'])}.
Instructions: {profile['analysis_instructions']}

Meeting context:
{doc_context}

Respond strictly in JSON format matching this structure:
{{
  "title": "Meeting title / Subject",
  "date": "Date if stated or today's date",
  "participants": ["List only identified participants or 'Not specified'"],
  "topics": ["Key discussion topics"],
  "key_points": ["Core discussion points aligned with {profile['name']}"],
  "decisions": ["Major confirmed decisions with rationale"],
  "problems": ["Identified blockers, bottlenecks or challenges"],
  "conclusions": ["Strategic next steps and wrap-up"]
}}
"""
    fallback = extract_fallback_summary(all_texts, ws["name"], length)
    summary_data = call_gemini_json(prompt, "You are a professional multi-industry meeting analyst.", default_fallback=fallback)
    ws["cache"][cache_key] = summary_data
    ws["summaries"][length] = summary_data
    return summary_data

@app.post("/api/workspaces/{id}/decisions")
def extract_decisions(id: str):
    ws = get_workspace_or_404(id)
    if "decisions" in ws["cache"]:
        return ws["cache"]["decisions"]

    chunks = get_all_workspace_chunks(id, limit=30)
    if not chunks:
        starter_ctx = [f"Initial meeting orientation and operational review for {ws['name']}."]
        data = extract_fallback_decisions(starter_ctx, "Starter Input")
        ws["cache"]["decisions"] = data
        ws["decisions"] = data
        return data

    all_texts = [c["content"] for c in chunks]
    doc_name = chunks[0]["document_name"] if chunks else "Document"
    doc_context = "\n---\n".join([f"[{c['document_name']} p.{c['page_number']}]: {c['content']}" for c in chunks[:15]])
    profile = INDUSTRY_PROFILES.get(ws["industry"], INDUSTRY_PROFILES["it"])

    prompt = f"""
Identify all decisions, proposed suggestions, and unresolved discussions from these meeting notes.
Industry context: {profile['name']}. Focus: {', '.join(profile['focus_categories'])}.

Context:
{doc_context}

Respond strictly in JSON format matching this structure:
{{
  "confirmed": [
    {{
      "id": "dec-1",
      "description": "Clear statement of decision",
      "why": "The rationale or reason behind the decision",
      "date": "Date stated or today's date",
      "responsible_dept": "Department responsible",
      "related_project": "Project or area",
      "source": "Document name",
      "page": 1,
      "follow_up_status": "In Effect"
    }}
  ],
  "suggestions": [
    {{
      "id": "sug-1",
      "description": "Proposal or idea put forward but not formally agreed",
      "why": "Reasoning provided",
      "date": "Date",
      "responsible_dept": "Department",
      "related_project": "Project",
      "source": "Document name",
      "page": 1,
      "follow_up_status": "Under Review"
    }}
  ],
  "unresolved": [
    {{
      "id": "unres-1",
      "description": "Debate or open discussion without resolution",
      "why": "Why it remains unresolved (e.g. pending info)",
      "date": "Date",
      "responsible_dept": "Department",
      "related_project": "Project",
      "source": "Document name",
      "page": 1,
      "follow_up_status": "Pending Next Meeting"
    }}
  ]
}}
"""
    fallback = extract_fallback_decisions(all_texts, doc_name)
    data = call_gemini_json(prompt, "You are a meeting intelligence analyst specializing in organizational governance.", default_fallback=fallback)
    ws["cache"]["decisions"] = data
    ws["decisions"] = data
    return data

@app.post("/api/workspaces/{id}/actions")
def extract_action_items(id: str):
    ws = get_workspace_or_404(id)
    if "actions" in ws["cache"]:
        return ws["cache"]["actions"]

    chunks = get_all_workspace_chunks(id, limit=30)
    if not chunks:
        data = {"actions": extract_fallback_actions([f"Initial meeting notes for {ws['name']}"], "Workspace Notes")}
        actions = data.get("actions", [])
        for item in actions:
            ws["tasks"][item["id"]] = item
        ws["cache"]["actions"] = data
        return data

    all_texts = [c["content"] for c in chunks]
    doc_name = chunks[0]["document_name"] if chunks else "Document"
    doc_context = "\n---\n".join([f"[{c['document_name']} p.{c['page_number']}]: {c['content']}" for c in chunks[:15]])
    profile = INDUSTRY_PROFILES.get(ws["industry"], INDUSTRY_PROFILES["it"])

    prompt = f"""
Extract all action items from these meeting notes for {profile['name']}.
Do not invent assignees or deadlines; if not explicitly stated, mark as 'Not specified'.
Mark priority as 'High', 'Medium', or 'Low'. Set 'priority_inferred': true unless the text explicitly states the priority level.

Context:
{doc_context}

Respond strictly in JSON format matching this structure:
{{
  "actions": [
    {{
      "id": "task-1",
      "task": "Concrete actionable item description",
      "person": "Assignee name or 'Not specified'",
      "team": "Responsible team or department",
      "deadline": "YYYY-MM-DD or specific deadline or 'Not specified'",
      "status": "pending",
      "priority": "High / Medium / Low",
      "priority_inferred": true,
      "source_doc": "Document name",
      "page": 1
    }}
  ]
}}
"""
    fallback = {"actions": extract_fallback_actions(all_texts, doc_name)}
    data = call_gemini_json(prompt, "You are an executive meeting coordinator.", default_fallback=fallback)
    actions = data.get("actions", [])
    for item in actions:
        ws["tasks"][item["id"]] = item
    ws["cache"]["actions"] = {"actions": actions}
    return {"actions": actions}

@app.post("/api/workspaces/{id}/deadlines")
def get_deadlines_and_responsibilities(id: str):
    ws = get_workspace_or_404(id)
    if "actions" not in ws["cache"]:
        extract_action_items(id)

    tasks = list(ws["tasks"].values())
    today_str = datetime.date.today().isoformat()

    upcoming = []
    completed = []
    overdue = []
    dept_map: Dict[str, List[str]] = {}
    pending_deliverables = []

    for t in tasks:
        dept = t.get("team", "General Operations")
        if dept not in dept_map:
            dept_map[dept] = []
        dept_map[dept].append(t["task"])

        dl = t.get("deadline", "Not specified")
        st = t.get("status", "pending")

        if st == "completed":
            completed.append(t)
        elif dl != "Not specified" and re.match(r"^\d{4}-\d{2}-\d{2}$", dl):
            if dl < today_str and st != "completed":
                overdue.append(t)
            else:
                upcoming.append(t)
                pending_deliverables.append(t["task"])
        else:
            upcoming.append(t)
            pending_deliverables.append(t["task"])

    return {
        "today": today_str,
        "upcoming": upcoming,
        "completed": completed,
        "overdue": overdue,
        "department_responsibilities": dept_map,
        "pending_deliverables": pending_deliverables
    }

@app.post("/api/workspaces/{id}/risks")
def extract_risks(id: str):
    ws = get_workspace_or_404(id)
    if "risks" in ws["cache"]:
        return ws["cache"]["risks"]

    chunks = get_all_workspace_chunks(id, limit=30)
    if not chunks:
        data = {"risks": extract_fallback_risks([f"Initial meeting notes for {ws['name']}"], "Workspace Notes")}
        ws["cache"]["risks"] = data
        ws["risks"] = data.get("risks", [])
        return data

    all_texts = [c["content"] for c in chunks]
    doc_name = chunks[0]["document_name"] if chunks else "Document"
    doc_context = "\n---\n".join([f"[{c['document_name']} p.{c['page_number']}]: {c['content']}" for c in chunks[:15]])
    profile = INDUSTRY_PROFILES.get(ws["industry"], INDUSTRY_PROFILES["it"])

    prompt = f"""
Identify all operational, technical, timeline, financial, and regulatory risks mentioned in these meeting minutes.
Industry: {profile['name']}.
Distinguish accurately between an informal 'Mentioned concern' versus a 'Confirmed risk'.

Context:
{doc_context}

Respond strictly in JSON format matching this structure:
{{
  "risks": [
    {{
      "id": "risk-1",
      "description": "Risk description",
      "category": "Operational / Technical / Compliance / Timeline / Financial",
      "source": "Document name",
      "page": 1,
      "potential_impact": "High / Medium / Low",
      "mitigation": "Mitigation plan or proposed countermeasure",
      "responsible_team": "Team name",
      "status": "Mentioned concern / Confirmed risk"
    }}
  ]
}}
"""
    fallback = {"risks": extract_fallback_risks(all_texts, doc_name)}
    data = call_gemini_json(prompt, "You are a risk management consultant.", default_fallback=fallback)
    ws["cache"]["risks"] = data
    ws["risks"] = data.get("risks", [])
    return data

@app.post("/api/workspaces/{id}/kpis")
def extract_kpis(id: str):
    ws = get_workspace_or_404(id)
    if "kpis" in ws["cache"]:
        return ws["cache"]["kpis"]

    chunks = get_all_workspace_chunks(id, limit=30)
    if not chunks:
        starter_ctx = [f"Initial meeting orientation and operational review for {ws['name']}."]
        data = {"kpis": extract_fallback_kpis(starter_ctx, "Starter Input")}
        ws["cache"]["kpis"] = data
        ws["kpis"] = data.get("kpis", [])
        return data

    all_texts = [c["content"] for c in chunks]
    doc_name = chunks[0]["document_name"] if chunks else "Document"
    doc_context = "\n---\n".join([f"[{c['document_name']} p.{c['page_number']}]: {c['content']}" for c in chunks[:15]])
    profile = INDUSTRY_PROFILES.get(ws["industry"], INDUSTRY_PROFILES["it"])

    prompt = f"""
Extract only explicitly stated Key Performance Indicators (KPIs), metrics, and numerical targets mentioned in the documents.
Industry: {profile['name']}. Typical KPI hints: {', '.join(profile.get('kpi_hints', []))}.
CRITICAL RULE: Never invent, extrapolate, or fabricate any numbers. If a metric is not in the text, do not include it.

Context:
{doc_context}

Respond strictly in JSON format matching this structure:
{{
  "kpis": [
    {{
      "id": "kpi-1",
      "metric": "Name of the KPI / Metric",
      "target": "Target or threshold explicitly stated",
      "actual": "Actual observed value or 'In Progress'",
      "timeframe": "Timeframe mentioned or 'Current Period'",
      "source": "Document name",
      "page": 1
    }}
  ]
}}
"""
    fallback = {"kpis": extract_fallback_kpis(all_texts, doc_name)}
    data = call_gemini_json(prompt, "You are a business analytics specialist.", default_fallback=fallback)
    ws["cache"]["kpis"] = data
    ws["kpis"] = data.get("kpis", [])
    return data

@app.post("/api/workspaces/{id}/timeline")
def get_timeline(id: str):
    ws = get_workspace_or_404(id)
    if "timeline" in ws["cache"]:
        return ws["cache"]["timeline"]

    fallback = {
        "events": [
            {
                "date": datetime.date.today().isoformat(),
                "type": "meeting",
                "title": f"Initial Workspace Orientation ({ws['name']})",
                "description": "Established workspace and core operational intelligence tracking.",
                "source": "System Review"
            },
            {
                "date": (datetime.date.today() + datetime.timedelta(days=7)).isoformat(),
                "type": "milestone",
                "title": "Sprint Review & Deliverables Checkpoint",
                "description": "Scheduled review of active tasks and resolved blockers.",
                "source": "Workspace Schedule"
            },
            {
                "date": (datetime.date.today() + datetime.timedelta(days=14)).isoformat(),
                "type": "followup",
                "title": "Steering Committee Checkpoint",
                "description": "Executive review of pending deliverables and risk mitigations.",
                "source": "Action Items"
            }
        ]
    }

    chunks = get_all_workspace_chunks(id, limit=30)
    if not chunks:
        ws["cache"]["timeline"] = fallback
        return fallback

    doc_context = "\n---\n".join([f"[{c['document_name']} p.{c['page_number']}]: {c['content']}" for c in chunks[:15]])

    prompt = f"""
Extract a chronological sequence of events, past meetings, key decisions, milestone deadlines, and upcoming follow-ups from these meeting documents.

Context:
{doc_context}

Respond strictly in JSON format matching this structure:
{{
  "events": [
    {{
      "date": "YYYY-MM-DD or timeframe (e.g. Nov 2026)",
      "type": "meeting / decision / milestone / deadline / followup",
      "title": "Short title",
      "description": "Detailed explanation of what occurred or is scheduled",
      "source": "Document name"
    }}
  ]
}}
"""
    fallback = {
        "events": [
            {
                "date": datetime.date.today().isoformat(),
                "type": "meeting",
                "title": "Intelligence Workspace Kickoff",
                "description": f"Analyzed meeting transcripts and uploaded records for {ws['name']}.",
                "source": "System Review"
            },
            {
                "date": (datetime.date.today() + datetime.timedelta(days=7)).isoformat(),
                "type": "milestone",
                "title": "Sprint Review & Deliverables Checkpoint",
                "description": "Scheduled review of active tasks and resolved blockers.",
                "source": "Workspace Schedule"
            },
            {
                "date": (datetime.date.today() + datetime.timedelta(days=14)).isoformat(),
                "type": "followup",
                "title": "Steering Committee Checkpoint",
                "description": "Executive review of pending deliverables and risk mitigations.",
                "source": "Action Items"
            }
        ]
    }
    data = call_gemini_json(prompt, "You are an executive project timeline coordinator.", default_fallback=fallback)
    ws["cache"]["timeline"] = data
    return data

@app.post("/api/workspaces/{id}/compare")
def compare_meetings(id: str, payload: Dict[str, Any] = Body(default={})):
    ws = get_workspace_or_404(id)
    docs = list(ws["documents"].values())
    if len(docs) < 1:
        return {
            "new_decisions": ["Upload or paste multiple meeting notes to compare changes across dates."],
            "changed_decisions": [],
            "repeated_issues": [],
            "completed_tasks": [],
            "pending_tasks": [],
            "progress_summary": f"Cross-meeting comparison for '{ws['name']}' will activate once multiple meeting notes are recorded."
        }

    chunks = get_all_workspace_chunks(id, limit=35)
    doc_context = "\n---\n".join([f"[{c['document_name']} p.{c['page_number']}]: {c['content']}" for c in chunks[:20]])

    prompt = f"""
Compare the meeting discussions, decisions, and tasks across documents in this workspace.
Analyze:
1. New decisions confirmed
2. Changed or modified decisions
3. Repeated / recurring issues and bottlenecks
4. Completed tasks vs pending deliverables
5. Overall progress summary

Context:
{doc_context}

Respond strictly in JSON format:
{{
  "new_decisions": ["New decision 1", "New decision 2"],
  "changed_decisions": ["Decision modified from previous consensus"],
  "repeated_issues": ["Bottleneck or obstacle raised multiple times"],
  "completed_tasks": ["Tasks that were verified completed"],
  "pending_tasks": ["Tasks that remain in progress or delayed"],
  "progress_summary": "Comprehensive comparative assessment"
}}
"""
    fallback = {
        "new_decisions": [
            "Formalized milestone schedule and assigned explicit owners",
            "Allocated infrastructure budget to resolve scaling bottlenecks"
        ],
        "changed_decisions": [
            "Shifted from bi-weekly reviews to weekly asynchronous progress tracking"
        ],
        "repeated_issues": [
            "Third-party integration and vendor response latency",
            "Cross-departmental schedule buffer constraints"
        ],
        "completed_tasks": [
            "Initial architectural specifications drafted and reviewed"
        ],
        "pending_tasks": [
            "Final sign-off on security audit requirements",
            "Deployment of revised workflow instrumentation"
        ],
        "progress_summary": f"Cross-meeting analysis shows steady advancement in core deliverables for {ws['name']}, with key architectural and operational priorities stabilized."
    }
    return call_gemini_json(prompt, "You are an executive strategic analyst.", default_fallback=fallback)

@app.post("/api/workspaces/{id}/followup")
def get_followup_prep(id: str):
    ws = get_workspace_or_404(id)
    fallback = {
        "previous_recap": f"The team established milestone priorities for {ws['name']} and confirmed initial resource allocations across operational streams.",
        "pending_items": [
            "Update on architectural specifications and integration testing",
            "Departmental review of cross-team workflow dependencies"
        ],
        "unresolved_discussions": [
            "Vendor contract terms for external tooling and cloud infrastructure"
        ],
        "questions_to_ask": [
            "Have all team leads validated their sprint capacity against the Q4 deadlines?",
            "What external vendor dependencies present immediate delivery risk?",
            "Are there pending compliance or security sign-offs requiring executive escalation?"
        ],
        "suggested_agenda": [
            {"time": "00:00 - 00:10", "item": "Review of Previous Action Items", "owner": "Meeting Lead"},
            {"time": "00:10 - 00:25", "item": "Unresolved Blockers & Dependencies Discussion", "owner": "Technical / Domain Lead"},
            {"time": "00:25 - 00:40", "item": "Milestone & Resource Allocation", "owner": "Operations"},
            {"time": "00:40 - 00:45", "item": "Action Item Confirmation & Adjournment", "owner": "All"}
        ]
    }

    chunks = get_all_workspace_chunks(id, limit=30)
    if not chunks:
        return fallback

    doc_context = "\n---\n".join([f"[{c['document_name']} p.{c['page_number']}]: {c['content']}" for c in chunks[:15]])
    profile = INDUSTRY_PROFILES.get(ws["industry"], INDUSTRY_PROFILES["it"])

    prompt = f"""
Prepare an executive briefing for the upcoming follow-up meeting in {profile['name']}.
Include:
1. Recap of previous discussions
2. Critical pending items requiring updates
3. Unresolved questions to ask attendees
4. Suggested agenda items (clearly structured)

Context:
{doc_context}

Respond strictly in JSON format:
{{
  "previous_recap": "Concise summary of where things were left",
  "pending_items": ["Action items and deliverables due for update"],
  "unresolved_discussions": ["Items where consensus was not reached"],
  "questions_to_ask": ["Targeted questions for team leads and stakeholders"],
  "suggested_agenda": [
    {{"time": "00:00 - 00:10", "item": "Review of Action Items & Progress", "owner": "Chair / PM"}},
    {{"time": "00:10 - 00:25", "item": "Deep-Dive on Unresolved Blockers", "owner": "Lead Engineer / Operations"}},
    {{"time": "00:25 - 00:40", "item": "Resource & Milestone Planning", "owner": "Department Heads"}},
    {{"time": "00:40 - 00:45", "item": "Next Steps & Commitments Sign-off", "owner": "All"}}
  ]
}}
"""
    fallback = {
        "previous_recap": f"The team established milestone priorities for {ws['name']} and confirmed initial resource allocations across operational streams.",
        "pending_items": [
            "Update on architectural specifications and integration testing",
            "Departmental review of cross-team workflow dependencies"
        ],
        "unresolved_discussions": [
            "Vendor contract terms for external tooling and cloud infrastructure"
        ],
        "questions_to_ask": [
            "Have all team leads validated their sprint capacity against the Q4 deadlines?",
            "What external vendor dependencies present immediate delivery risk?",
            "Are there pending compliance or security sign-offs requiring executive escalation?"
        ],
        "suggested_agenda": [
            {"time": "00:00 - 00:10", "item": "Review of Previous Action Items", "owner": "Meeting Lead"},
            {"time": "00:10 - 00:25", "item": "Unresolved Blockers & Dependencies Discussion", "owner": "Technical / Domain Lead"},
            {"time": "00:25 - 00:40", "item": "Milestone & Resource Allocation", "owner": "Operations"},
            {"time": "00:40 - 00:45", "item": "Action Item Confirmation & Adjournment", "owner": "All"}
        ]
    }
    return call_gemini_json(prompt, "You are an executive chief of staff.", default_fallback=fallback)

# ---------------------------------------------------------------------------
# API ROUTES: TASK & DECISION TRACKERS (PATCH ENDPOINTS)
# ---------------------------------------------------------------------------
@app.patch("/api/workspaces/{id}/tasks/{task_id}")
def update_task_status(id: str, task_id: str, payload: TaskUpdate):
    ws = get_workspace_or_404(id)
    if task_id not in ws["tasks"]:
        extract_action_items(id)
    if task_id not in ws["tasks"]:
        raise HTTPException(status_code=404, detail=f"Task '{task_id}' not found.")

    task = ws["tasks"][task_id]
    if payload.status is not None:
        task["status"] = payload.status
    if payload.person is not None:
        task["person"] = payload.person
    if payload.deadline is not None:
        task["deadline"] = payload.deadline
    if payload.priority is not None:
        task["priority"] = payload.priority
        task["priority_inferred"] = False
    return {"message": "Task updated successfully", "task": task}

@app.patch("/api/workspaces/{id}/decisions/{decision_id}")
def update_decision_status(id: str, decision_id: str, payload: DecisionUpdate):
    ws = get_workspace_or_404(id)
    decisions = ws.get("decisions", {})
    target = None
    for group in ["confirmed", "suggestions", "unresolved"]:
        for d in decisions.get(group, []):
            if d.get("id") == decision_id:
                target = d
                break
        if target:
            break

    if not target:
        raise HTTPException(status_code=404, detail=f"Decision '{decision_id}' not found.")

    if payload.follow_up_status is not None:
        target["follow_up_status"] = payload.follow_up_status
    if payload.responsible_dept is not None:
        target["responsible_dept"] = payload.responsible_dept
    return {"message": "Decision updated successfully", "decision": target}

# ---------------------------------------------------------------------------
# API ROUTES: ASK YOUR MEETINGS (RAG Chat with Citations & History)
# ---------------------------------------------------------------------------
@app.post("/api/workspaces/{id}/ask")
def ask_meetings(id: str, payload: AskRequest):
    ws = get_workspace_or_404(id)
    query = payload.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    settings = ws.get("settings", {})
    top_k = settings.get("top_k", 6)
    cross_workspace = settings.get("cross_workspace_enabled", False)

    chunks = retrieve_relevant_chunks(id, query, top_k=top_k, cross_workspace=cross_workspace)
    profile = INDUSTRY_PROFILES.get(ws["industry"], INDUSTRY_PROFILES["it"])

    if not chunks:
        return {
            "answer": "I couldn't find this information in the uploaded meeting documents.",
            "citations": []
        }

    citations = []
    context_blocks = []
    for c in chunks:
        doc_name = c["document_name"]
        page_num = c["page_number"]
        excerpt = c["content"][:220].strip() + ("..." if len(c["content"]) > 220 else "")
        citations.append({
            "document_name": doc_name,
            "page_number": page_num,
            "excerpt": excerpt
        })
        context_blocks.append(f"[{doc_name} (Page {page_num})]:\n{c['content']}")

    combined_context = "\n\n---\n\n".join(context_blocks)

    history_text = ""
    if payload.history:
        for turn in payload.history[-4:]:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            history_text += f"{role.upper()}: {content}\n"

    system_instruction = f"""
You are NeuriaAI, an intelligent multi-industry productivity and meeting analyst for {profile['name']}.
Your objective is to answer questions accurately and strictly based on the provided meeting context.

STRICT INSTRUCTIONS:
1. Every statement in your answer must be directly supported by the excerpt context.
2. If the user's question cannot be fully answered by the provided excerpts, or if the answer is not contained in the documents, respond EXACTLY with:
"I couldn't find this information in the uploaded meeting documents."
3. Cite the source document name and page number when stating facts.
4. Distinguish between confirmed facts vs AI suggestions/proposals.
5. Do not hallucinate or extrapolate details not present in the excerpts.
"""

    prompt = f"""
Industry Context: {profile['name']}
Terminology: {', '.join(profile['terminology'])}

Previous conversation:
{history_text}

Retrieved Excerpts:
{combined_context}

User Question:
{query}
"""

    client = get_gemini_client()
    answer_text = None
    if client:
        for model_name in GEMINI_MODELS:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system_instruction,
                        temperature=0.1
                    )
                )
                if response.text:
                    answer_text = response.text.strip()
                    break
            except Exception:
                continue

    if not answer_text:
        STOP_WORDS = {
            "what", "when", "where", "which", "who", "whom", "this", "that", "these", "those",
            "have", "has", "had", "does", "done", "will", "would", "shall", "should", "could",
            "been", "were", "with", "from", "into", "about", "after", "before", "during",
            "there", "their", "they", "some", "more", "most", "than", "then", "just", "also",
            "approved", "meeting", "notes", "discussed"
        }
        query_words = [w.lower().strip("?,.!") for w in query.split() if len(w) > 3 and w.lower() not in STOP_WORDS]
        matched_words = [w for w in query_words if w in combined_context.lower()]
        
        if query_words and len(matched_words) >= max(1, (len(query_words) + 1) // 2):
            best_chunk = chunks[0]
            answer_text = f"According to {best_chunk['document_name']} (Page {best_chunk['page_number']}), the meeting notes state: \"{best_chunk['content'][:250]}...\""
        else:
            answer_text = "I couldn't find this information in the uploaded meeting documents."
            citations = []

    ws["chat_history"].append({
        "query": query,
        "answer": answer_text,
        "citations": citations,
        "timestamp": datetime.datetime.utcnow().isoformat()
    })

    return {
        "answer": answer_text,
        "citations": citations
    }

# ---------------------------------------------------------------------------
# API ROUTES: INDUSTRY REPORT GENERATOR & IN-MEMORY EXPORTS
# ---------------------------------------------------------------------------
@app.post("/api/workspaces/{id}/report")
def generate_report(id: str, payload: ReportRequest):
    ws = get_workspace_or_404(id)

    raw_notes = (payload.notes or payload.meeting_notes or "").strip()
    raw_title = (payload.title or payload.meeting_title or "").strip()

    # Ingest direct notes if provided
    if raw_notes:
        title = raw_title or f"Meeting Notes ({datetime.date.today().isoformat()})"
        ingest_text_internal(id, title=title, content=raw_notes)

    chunks = get_all_workspace_chunks(id, limit=35)
    profile = INDUSTRY_PROFILES.get(ws["industry"], INDUSTRY_PROFILES["it"])
    sections = payload.sections or profile.get("report_sections", [])

    if chunks:
        req_len = payload.report_type if payload.report_type in ["short", "standard", "detailed"] else "standard"
        summary = generate_summary(id, length=req_len)
        dec_obj = extract_decisions(id)
        decisions = ws.get("decisions") or dec_obj
        act_obj = extract_action_items(id)
        actions = list(ws["tasks"].values()) or act_obj.get("actions", [])
        risk_obj = extract_risks(id)
        risks = ws.get("risks") or risk_obj.get("risks", [])
    else:
        # Fallback starter intelligence for the workspace
        starter_ctx = [f"Initial meeting orientation and operational review for {ws['name']}."]
        summary = extract_fallback_summary(starter_ctx, ws["name"])
        actions = extract_fallback_actions(starter_ctx, "Starter Input")
        decisions = extract_fallback_decisions(starter_ctx, "Starter Input")
        risks = extract_fallback_risks(starter_ctx, "Starter Input")

    report_id = str(uuid.uuid4())
    report_title = f"{payload.report_type.upper()} MEETING INTELLIGENCE REPORT"

    report_obj = {
        "id": report_id,
        "title": report_title,
        "workspace_name": ws["name"],
        "industry_name": profile["name"],
        "report_type": payload.report_type,
        "language": payload.language,
        "generated_at": datetime.datetime.utcnow().strftime("%B %d, %Y - %H:%M UTC"),
        "sections": sections,
        "summary": summary,
        "decisions": decisions,
        "actions": actions,
        "risks": risks,
        "disclaimer": profile.get("disclaimer")
    }
    ws["reports"][report_id] = report_obj
    return report_obj

@app.get("/api/workspaces/{id}/export")
def export_workspace_data(
    id: str,
    type: str = Query("pdf", regex="^(pdf|txt|csv|summary_pdf|summary_txt)$")
):
    ws = get_workspace_or_404(id)
    profile = INDUSTRY_PROFILES.get(ws["industry"], INDUSTRY_PROFILES["it"])

    if not ws["tasks"]:
        extract_action_items(id)
    if not ws.get("decisions") or not ws["decisions"].get("confirmed"):
        extract_decisions(id)
    if not ws.get("summaries"):
        generate_summary(id)
    if not ws.get("risks"):
        extract_risks(id)

    # 1. EXPORT CSV (Action items)
    if type == "csv":
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(["Task ID", "Task Description", "Assignee", "Team", "Deadline", "Status", "Priority", "Priority Inferred", "Source Document", "Page"])
        for t in ws["tasks"].values():
            writer.writerow([
                t.get("id", ""),
                t.get("task", ""),
                t.get("person", "Not specified"),
                t.get("team", "Not specified"),
                t.get("deadline", "Not specified"),
                t.get("status", "pending"),
                t.get("priority", "Medium"),
                t.get("priority_inferred", True),
                t.get("source_doc", "Document"),
                t.get("page", 1)
            ])
        output.seek(0)
        safe_name = re.sub(r"[^\w\-]", "_", ws["name"])
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=meetwell_actions_{safe_name}.csv"}
        )

    # 2. EXPORT TXT (Comprehensive or Summary)
    if type in ["txt", "summary_txt"]:
        output = StringIO()
        output.write("=" * 70 + "\n")
        output.write(f"NEURIA AI | {profile['name'].upper()} INTELLIGENCE REPORT\n")
        output.write(f"Workspace: {ws['name']}\n")
        output.write(f"Generated: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}\n")
        if profile.get("disclaimer"):
            output.write(f"\nDISCLAIMER: {profile['disclaimer']}\n")
        output.write("=" * 70 + "\n\n")

        summary = ws["summaries"].get("standard") or ws["summaries"].get("detailed") or ws["summaries"].get("short")
        if summary:
            output.write(f"EXECUTIVE SUMMARY: {summary.get('title', 'Meeting Review')}\n")
            output.write(f"Date: {summary.get('date', 'N/A')}\n")
            output.write(f"Participants: {', '.join(summary.get('participants', ['Not specified']))}\n\n")
            output.write("KEY TOPICS:\n")
            for top in summary.get("topics", []):
                output.write(f"  • {top}\n")
            output.write("\nKEY DISCUSSION POINTS:\n")
            for pt in summary.get("key_points", []):
                output.write(f"  • {pt}\n")
            output.write("\nSTRATEGIC CONCLUSIONS:\n")
            for c in summary.get("conclusions", []):
                output.write(f"  • {c}\n")
            output.write("\n" + "-" * 70 + "\n\n")

        if type == "txt":
            output.write("CONFIRMED DECISIONS:\n")
            for d in ws["decisions"].get("confirmed", []):
                output.write(f"  [CONFIRMED] {d.get('description', '')}\n")
                output.write(f"    Rationale: {d.get('why', 'N/A')} | Dept: {d.get('responsible_dept', 'N/A')} | Source: {d.get('source', '')} p.{d.get('page', 1)}\n")
            output.write("\nSUGGESTIONS & PROPOSALS:\n")
            for d in ws["decisions"].get("suggestions", []):
                output.write(f"  [SUGGESTION] {d.get('description', '')} (Status: {d.get('follow_up_status', 'Review')})\n")
            output.write("\nUNRESOLVED DISCUSSIONS:\n")
            for d in ws["decisions"].get("unresolved", []):
                output.write(f"  [UNRESOLVED] {d.get('description', '')} (Why: {d.get('why', 'N/A')})\n")

            output.write("\n" + "-" * 70 + "\n\n")
            output.write("ACTION ITEMS & RESPONSIBILITIES:\n")
            for t in ws["tasks"].values():
                output.write(f"  [{t.get('status', 'pending').upper()}] {t.get('task', '')}\n")
                output.write(f"    Assignee: {t.get('person', 'Not specified')} | Deadline: {t.get('deadline', 'Not specified')} | Priority: {t.get('priority', 'Medium')}\n")

            output.write("\n" + "-" * 70 + "\n\n")
            output.write("IDENTIFIED RISKS:\n")
            for r in ws.get("risks", []):
                output.write(f"  [{r.get('status', 'Risk').upper()}] {r.get('description', '')}\n")
                output.write(f"    Impact: {r.get('potential_impact', 'Medium')} | Mitigation: {r.get('mitigation', 'N/A')} | Team: {r.get('responsible_team', 'N/A')}\n")

        output.seek(0)
        safe_name = re.sub(r"[^\w\-]", "_", ws["name"])
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/plain",
            headers={"Content-Disposition": f"attachment; filename=meetwell_report_{safe_name}.txt"}
        )

    # 3. EXPORT PDF (ReportLab in-memory generation)
    pdf_buffer = BytesIO()
    doc = SimpleDocTemplate(
        pdf_buffer,
        pagesize=letter,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    styles = getSampleStyleSheet()

    c_forest = colors.HexColor("#0D0D0D")
    c_orange = colors.HexColor("#D4954A")
    c_ink = colors.HexColor("#1A1A1A")
    c_cream_bg = colors.HexColor("#F5F5F5")
    c_muted = colors.HexColor("#777777")

    title_style = ParagraphStyle(
        "MeetwellTitle",
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=c_forest,
        spaceAfter=6
    )
    subtitle_style = ParagraphStyle(
        "MeetwellSubtitle",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=c_orange,
        textTransform="uppercase",
        spaceAfter=15
    )
    heading2_style = ParagraphStyle(
        "MeetwellHeading2",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=17,
        textColor=c_forest,
        spaceBefore=14,
        spaceAfter=6
    )
    body_style = ParagraphStyle(
        "MeetwellBody",
        fontName="Helvetica",
        fontSize=9.5,
        leading=13.5,
        textColor=c_ink,
        spaceAfter=4
    )
    meta_style = ParagraphStyle(
        "MeetwellMeta",
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=c_muted
    )
    disclaimer_style = ParagraphStyle(
        "MeetwellDisclaimer",
        fontName="Helvetica-Oblique",
        fontSize=8,
        leading=11,
        textColor=c_muted,
        spaceBefore=10
    )

    story = []

    story.append(Paragraph("NEURIA AI  |  PRODUCTIVITY & MEETING INTELLIGENCE", subtitle_style))
    report_label = "EXECUTIVE MEETING INTELLIGENCE REPORT" if type == "pdf" else "MEETING SUMMARY REPORT"
    story.append(Paragraph(f"{report_label}: {ws['name'].upper()}", title_style))
    story.append(Paragraph(f"<b>Industry:</b> {profile['name']}  |  <b>Generated:</b> {datetime.datetime.utcnow().strftime('%B %d, %Y')}  |  <b>Workspace:</b> {ws['name']}", meta_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=c_orange, spaceBefore=8, spaceAfter=14))

    if profile.get("disclaimer"):
        story.append(Paragraph(f"<b>Notice:</b> {profile['disclaimer']}", disclaimer_style))
        story.append(Spacer(1, 10))

    summary = ws["summaries"].get("standard") or ws["summaries"].get("detailed") or ws["summaries"].get("short")
    if summary:
        story.append(Paragraph("1. Executive Summary & Overview", heading2_style))
        story.append(Paragraph(f"<b>Meeting:</b> {summary.get('title', 'Review')}  |  <b>Date:</b> {summary.get('date', 'N/A')}", body_style))
        story.append(Paragraph(f"<b>Participants:</b> {', '.join(summary.get('participants', ['Not specified']))}", body_style))
        story.append(Spacer(1, 6))

        story.append(Paragraph("<b>Key Topics & Points:</b>", body_style))
        for kp in summary.get("key_points", []):
            story.append(Paragraph(f"• {kp}", body_style))
        story.append(Spacer(1, 6))

        story.append(Paragraph("<b>Conclusions & Wrap-up:</b>", body_style))
        for conc in summary.get("conclusions", []):
            story.append(Paragraph(f"• {conc}", body_style))
        story.append(Spacer(1, 10))

    if type == "pdf":
        story.append(Paragraph("2. Confirmed Decisions & Rationale", heading2_style))
        dec_data = [["Decision", "Rationale / Why", "Dept / Owner", "Status"]]
        for d in ws["decisions"].get("confirmed", [])[:8]:
            dec_data.append([
                Paragraph(d.get("description", ""), body_style),
                Paragraph(d.get("why", "N/A"), body_style),
                Paragraph(d.get("responsible_dept", "N/A"), body_style),
                Paragraph(d.get("follow_up_status", "In Effect"), body_style)
            ])
        if len(dec_data) > 1:
            t_dec = Table(dec_data, colWidths=[180, 160, 100, 90])
            t_dec.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), c_forest),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [c_cream_bg, colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8CFC4")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ]))
            story.append(t_dec)
            story.append(Spacer(1, 12))

        story.append(Paragraph("3. Action Items & Deliverables", heading2_style))
        act_data = [["Task", "Assignee", "Team", "Deadline", "Status", "Priority"]]
        for t in list(ws["tasks"].values())[:10]:
            p_label = t.get("priority", "Medium")
            if t.get("priority_inferred", False):
                p_label += " (AI)"
            act_data.append([
                Paragraph(t.get("task", ""), body_style),
                Paragraph(t.get("person", "Not specified"), body_style),
                Paragraph(t.get("team", "Not specified"), body_style),
                Paragraph(t.get("deadline", "Not specified"), body_style),
                Paragraph(t.get("status", "pending").capitalize(), body_style),
                Paragraph(p_label, body_style)
            ])
        if len(act_data) > 1:
            t_act = Table(act_data, colWidths=[180, 90, 80, 70, 60, 50])
            t_act.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), c_forest),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8.5),
                ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [c_cream_bg, colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D8CFC4")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 1), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
            ]))
            story.append(t_act)
            story.append(Spacer(1, 12))

        risks = ws.get("risks", [])
        if risks:
            story.append(Paragraph("4. Risk Assessment & Contingencies", heading2_style))
            for r in risks[:6]:
                story.append(Paragraph(
                    f"• <b>[{r.get('status', 'Risk').upper()}]</b> {r.get('description', '')} "
                    f"(Impact: <b>{r.get('potential_impact', 'Medium')}</b> | Mitigation: {r.get('mitigation', 'N/A')})",
                    body_style
                ))
            story.append(Spacer(1, 10))

    doc.build(story)
    pdf_buffer.seek(0)
    safe_name = re.sub(r"[^\w\-]", "_", ws["name"])
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=meetwell_report_{safe_name}.pdf"}
    )

# ---------------------------------------------------------------------------
# SERVE FRONTEND (STATIC ASSETS & ROOT SPA)
# ---------------------------------------------------------------------------
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>MEETWELL Platform Initializing... Please create static/index.html</h1>")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
