from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from typing import Dict, Any

from models.schemas import EmailProcessRequest, AgentState
from apis import mock_banking
from workflows.orchestrator import EmailOrchestrator
from utils import database
from utils.logger import get_recent_audit_logs, logger

app = FastAPI(
    title="HDFC AI MailRoom System",
    description="Intelligent Email Processing and Automated Response System with Multi-Agent Orchestration",
    version="1.0.0"
)

# Enable CORS for local cross-origin development if needed
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Mock Banking Core APIs
app.include_router(mock_banking.router)

# Instantiate Orchestrator
orchestrator = EmailOrchestrator()

# --- Orchestrator Processing Endpoint ---

@app.post("/api/process-email", response_model=AgentState)
def process_customer_email(req: EmailProcessRequest):
    """Triggers the full multi-agent workflow to process the customer email"""
    logger.info(f"Received email process request from sender: {req.sender}")
    try:
        result_state = orchestrator.process_email(
            sender=req.sender,
            subject=req.subject,
            body=req.body
        )
        return result_state
    except Exception as e:
        logger.error(f"Failed to process email: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Orchestrator error: {str(e)}")


# --- Database Editor Endpoints (for Dashboard UI) ---

@app.get("/api/db/accounts")
def get_db_accounts():
    """Retrieve all mock accounts"""
    return database.accounts_db

@app.get("/api/db/cards")
def get_db_cards():
    """Retrieve all mock credit cards"""
    return database.cards_db

class DbAccountCreate(BaseModel):
    account_number: str
    customer_name: str
    balance: float
    status: str = "ACTIVE"

@app.post("/api/db/accounts")
def add_db_account(data: DbAccountCreate):
    """Add or update a mock bank account"""
    database.add_mock_account(
        account_number=data.account_number,
        customer_name=data.customer_name,
        balance=data.balance,
        status=data.status
    )
    return {"status": "SUCCESS", "message": f"Account {data.account_number} updated"}

class DbCardCreate(BaseModel):
    card_number: str
    cardholder_name: str
    status: str = "ACTIVE"
    credit_limit: float = 100000.0
    available_limit: float = 80000.0

@app.post("/api/db/cards")
def add_db_card(data: DbCardCreate):
    """Add or update a mock credit card"""
    database.add_mock_card(
        card_number=data.card_number,
        cardholder_name=data.cardholder_name,
        status=data.status,
        credit_limit=data.credit_limit,
        available_limit=data.available_limit
    )
    return {"status": "SUCCESS", "message": f"Card {data.card_number} updated"}


# --- Audit Logs Endpoint ---

@app.get("/api/logs")
def get_audit_logs():
    """Fetches recently recorded audit logs of agent execution and decisions"""
    return get_recent_audit_logs(limit=100)


# --- Static Files & Dashboard serving ---

# We mount static directories at the end, so standard API routes take precedence
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
os.makedirs(static_dir, exist_ok=True)

app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
