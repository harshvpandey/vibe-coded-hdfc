from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

# --- API Request/Response Schemas ---

class ValidateAccountRequest(BaseModel):
    account_number: str = Field(..., description="10-digit savings account number to validate")

class ValidateAccountResponse(BaseModel):
    status: str = Field(..., description="VALID or INVALID status")
    customer_name: Optional[str] = Field(None, description="Name of the customer if valid")
    error: Optional[str] = Field(None, description="Detailed validation error if invalid")

class ValidateCardRequest(BaseModel):
    card_number: str = Field(..., description="Credit card number (e.g. 12-16 digits)")

class ValidateCardResponse(BaseModel):
    status: str = Field(..., description="VALID or INVALID status")
    cardholder_name: Optional[str] = Field(None, description="Name of the cardholder if valid")
    error: Optional[str] = Field(None, description="Detailed validation error if invalid")

class GetAccountBalanceRequest(BaseModel):
    account_number: str = Field(..., description="10-digit savings account number")

class GetAccountBalanceResponse(BaseModel):
    status: str = Field(..., description="SUCCESS or FAILURE status")
    account_number: str
    customer_name: str
    balance: float
    currency: str = "INR"
    error: Optional[str] = None

class GetCardTransactionsRequest(BaseModel):
    card_number: str = Field(..., description="Credit card number")
    limit: Optional[int] = Field(5, description="Number of recent transactions to fetch")

class TransactionItem(BaseModel):
    date: str
    merchant: str
    amount: float
    type: str

class GetCardTransactionsResponse(BaseModel):
    status: str = Field(..., description="SUCCESS or FAILURE status")
    card_number: str
    cardholder_name: str
    available_limit: float
    credit_limit: float
    transactions: List[TransactionItem]
    error: Optional[str] = None

class GetStatementRequest(BaseModel):
    account_number: str
    period: str = Field(..., description="Month and year, e.g., 'April 2026'")

class GetStatementResponse(BaseModel):
    status: str = Field(..., description="SUCCESS or FAILURE status")
    account_number: str
    period: str
    filename: Optional[str] = None
    size: Optional[str] = None
    download_url: Optional[str] = None
    error: Optional[str] = None


# --- Workflow Input/Output Schemas ---

class EmailProcessRequest(BaseModel):
    sender: str = Field(..., description="Sender email address")
    subject: str = Field(..., description="Email subject line")
    body: str = Field(..., description="Plain text body of the email")

class AgentState(BaseModel):
    """Pydantic model representing the overall state of the orchestrator workflow"""
    sender: str
    subject: str
    body: str
    
    # 1. Understanding output
    cleaned_body: Optional[str] = None
    language: Optional[str] = "English"
    summary: Optional[str] = None
    
    # 2. Intent output
    intents: List[str] = Field(default_factory=list) # e.g. ["ACCOUNT_BALANCE", "CARD_TRANSACTIONS"]
    
    # 3. Sentiment output
    sentiment: str = "NEUTRAL" # NEUTRAL, POSITIVE, NEGATIVE/URGENT
    urgency_reason: Optional[str] = None
    
    # 4. Entity output
    entities: Dict[str, Any] = Field(default_factory=dict) # e.g. {"account_number": "1234567890", "card_number": "987654321", "statement_period": "April 2026"}
    
    # 5. Validation output
    validation_results: Dict[str, Any] = Field(default_factory=dict) # e.g. {"account_valid": True, "card_valid": False, "customer_name": "John Doe"}
    
    # 6. Selected APIs
    selected_apis: List[Dict[str, Any]] = Field(default_factory=list) # List of API calls to execute
    
    # 7. Fetched data
    api_responses: Dict[str, Any] = Field(default_factory=dict) # Data fetched from backend APIs
    
    # 8. Generated Response
    draft_response: Optional[str] = None
    confidence_score: float = 0.0
    
    # Execution tracing
    agent_logs: List[Dict[str, Any]] = Field(default_factory=list) # Node logs for UI viz
    execution_time_ms: int = 0
