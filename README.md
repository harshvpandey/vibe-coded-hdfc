# Intelligent Email Processing & Automated Customer Response System

Welcome to the HDFC AI MailRoom Admin Hub. This is a production-ready, AI-powered multi-agent customer automation platform designed to process, validate, query, and draft responses to customer banking queries automatically using the **Google Gemini API** and **FastAPI**.

---

## 1. System Architecture Workflow

The system takes incoming emails, streams them through an intelligent **Multi-Agent pipeline (8 specialized agents)**, queries deterministic **Core Banking APIs**, handles errors and partial validation failures gracefully, and outputs a secure, formatted email response.

```
Incoming Customer Email
        │
        ▼
[Email Understanding Agent] ────► Cleans spaces, detects language, summarizes
        │
        ├───► [Intent Classification Agent] ──► Identifies banking intents
        ├───► [Sentiment Analysis Agent] ────► Identifies urgency & emotion
        └───► [Entity Extraction Agent] ─────► Extracts account/card numbers
        │
        ▼
[Deterministic Validation Agent] ──► Checks card/account status against Core database
        │
        ▼
[API Selection Agent] ──────────► Decides safe Core Banking API queries (blocks invalid resources)
        │
        ▼
[Core Banking Systems] ────────► Get Account Balance, Get Card Transactions, Get Statement
        │
        ▼
[Response Generation Agent] ────► Compiles empathetic, secure email (masks accounts/cards)
        │
        ▼
[Auditor/Logging Agent] ────────► Reviews execution trace, audits safety, redacts logs
        │
        ▼
Final Outgoing Response Email
```

---

## 2. Directory Structure & Code Layout

Following the required structure, here is what each specific file does:

```
vibe_coded_hdfc/
│
├── config/
│   └── settings.py           # Application config, reads environment, configures default Gemini API keys.
│
├── models/
│   └── schemas.py            # Pydantic schemas validating all Core API inputs/responses and agent states.
│
├── prompts/
│   └── templates.py          # Highly detailed system instructions and target JSON schemas for each Gemini agent.
│
├── utils/
│   ├── database.py           # Mock Core Banking database with mock records (accounts, credit cards, statements).
│   └── logger.py             # Masking logger that redacts sensitive digits (cards/accounts) from execution logs.
│
├── apis/
│   ├── mock_banking.py       # REST API implementation of the five core validation and data retrieval banking endpoints.
│   └── app.py                # Central FastAPI application: mounts routes, DB management endpoints, and serves dashboard.
│
├── agents/
│   ├── base.py               # Generates structured JSON responses from Gemini 1.5 using response_mime_type.
│   ├── understanding.py      # Standardizes layout, detects language, and compiles brief summaries.
│   ├── intent.py             # Multi-intent classification engine mapping requests to core services.
│   ├── sentiment.py          # Identifies customer mood, raising high priority indicators for urgent requests.
│   ├── extraction.py         # Parses credentials, dates, limits, and customer signatures.
│   ├── validation.py         # Secure Python validator calling mock APIs or database modules directly.
│   ├── api_selection.py      # Strategic routing engine that decides which banking data queries to run.
│   ├── response_gen.py       # Creates premium, empathetic customer emails with masked sensitive credentials.
│   └── auditor.py            # Performance scorer verifying safety compliance on final outputs.
│
├── workflows/
│   └── orchestrator.py       # State-machine engine coordinating agents sequentially, handling partial failures.
│
├── static/                   # Assets for the premium Single-Page Dashboard
│   ├── index.html            # Admin panel workspace (simulated inbox, DB monitor, live node visualizer).
│   ├── styles.css            # Sleek dark-mode aesthetics, custom node connector graphics, and pulsing transitions.
│   └── app.js                # Javascript engine animating pipeline steps, updating DBs, and populating panels.
│
├── tests/
│   └── test_scenarios.py     # CLI integration script executing the 5 business scenarios sequentially.
│
├── main.py                   # Single executable startup script launching FastAPI + static dashboard.
├── requirements.txt          # Python package requirements.
└── README.md                 # Complete documentation.
```

---

## 3. Mock Banking API Contract Specifications

### 3.1 Validate Account API
- **Endpoint**: `POST /api/bank/validate-account`
- **Request Body**:
  ```json
  {
    "account_number": "1234567890"
  }
  ```
- **Response (Valid)**:
  ```json
  {
    "status": "VALID",
    "customer_name": "John Doe"
  }
  ```

### 3.2 Validate Card API
- **Endpoint**: `POST /api/bank/validate-card`
- **Request Body**:
  ```json
  {
    "card_number": "4567XXXX8901"
  }
  ```
- **Response (Valid)**:
  ```json
  {
    "status": "VALID",
    "cardholder_name": "John Doe"
  }
  ```

### 3.3 Get Account Balance API
- **Endpoint**: `POST /api/bank/account-balance`
- **Request Body**:
  ```json
  {
    "account_number": "1234567890"
  }
  ```
- **Response**:
  ```json
  {
    "status": "SUCCESS",
    "account_number": "1234567890",
    "customer_name": "John Doe",
    "balance": 125000.00,
    "currency": "INR"
  }
  ```

### 3.4 Get Card Transactions API
- **Endpoint**: `POST /api/bank/card-transactions`
- **Request Body**:
  ```json
  {
    "card_number": "456711118901",
    "limit": 3
  }
  ```
- **Response**:
  ```json
  {
    "status": "SUCCESS",
    "card_number": "456711118901",
    "cardholder_name": "John Doe",
    "available_limit": 142051.00,
    "credit_limit": 200000.00,
    "transactions": [
      {
        "date": "2026-05-22",
        "merchant": "HDFC Auto Pay",
        "amount": 15000.00,
        "type": "DEBIT"
      }
    ]
  }
  ```

---

## 4. Run & Installation Setup

### 4.1 Prerequisites
Ensure Python `3.10` or higher is installed. 

### 4.2 Setup Local Environment
1. Initialize the virtual environment:
   ```bash
   python -m venv venv
   ```
2. Install dependencies:
   ```bash
   venv\Scripts\pip install -r requirements.txt
   ```

### 4.3 Start the Web Server
Launch the server using our virtual environment runner:
```bash
venv\Scripts\python main.py
```
*The terminal will initialize the services and bind to `http://127.0.0.1:8000`. Open this address in your browser to access the premium interactive admin dashboard.*

### 4.4 Run Integration Tests (Offline Verification)
To test all 5 core business scenarios via CLI:
```bash
venv\Scripts\python tests/test_scenarios.py
```

---

## 5. Key Design Features & Production Compliance

- **Masking Sensitives**: Log scripts (`utils/logger.py`) and response generation parameters (`prompts/templates.py`) enforce regex and system instructions to mask credit card numbers (`XXXX8901`) and account numbers (`XXXX7890`) before writing to audit files or drafting client emails.
- **Graceful Failure & Recovery**: If an email requests both account balances and credit card histories (Scenario 5), and the credit card is invalid, the orchestrator pulls the balance details successfully while warning the customer regarding the failed card lookup, providing a clean partial-success response draft.
- **Zero-Guess Validation**: Account and card number checks are handled programmatically through direct backend API endpoints or mock database functions, preventing the LLM from fabricating credit card states or customer accounts.
- **High-Fidelity UI**: The Single-Page Dashboard offers a live, interactive execution trace: click on any agent node in the visualizer graph during/after a run to inspect its precise JSON input and output.
