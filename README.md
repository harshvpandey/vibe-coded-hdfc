# HDFC AI MailRoom - Intelligent Email Processing & Supervisor Console

Welcome to the HDFC AI MailRoom Admin Hub. This is a production-ready, AI-powered multi-agent customer automation platform designed to fetch, validate, query, draft, and dispatch responses to customer banking queries automatically using the **Google Gemini API**, **Gmail (IMAP/SMTP)**, and **FastAPI**.

---

## 1. System Ingestion & Supervision Workflow

The system synchronizes with your Gmail inbox over **IMAP**, ingests unread customer emails, processes them through our batch-optimized Multi-Agent pipeline, and applies an automated confidence routing rule to either dispatch a response instantly or escalate to a human supervisor for review:

```
                            [ Gmail Inbox (IMAP) ]
                                      │
                                      ▼ (Fetch Unseen Emails)
                          [ FastAPI Sync Endpoints ]
                                      │
                                      ▼
                        [ Multi-Agent AI Pipeline ]
                                      │
       ┌──────────────────────────────┴──────────────────────────────┐
       │                                                             │
       ▼ (LLM Call 1: Combined Analysis)                             ▼ (LLM Call 2: Response Gen)
 [Combined Analysis Agent]                                     [Response Generation Agent]
  - Cleans whitespace & summarizes                              - Empathetic template drafting
  - Classifies intent & sentiment                               - Formats tables dynamically
  - Extracts card/account numbers                               - Masks credentials (security)
       │                                                             │
       ├─────────────────────────────────────────────────────────────┘
       ▼
 [Deterministic Python Agent Checks]
  - Validation: Account/Card validation against Core Database
  - Routing: Blocks API execution if credentials fail validation
  - API execution: Get Account Balance, Transactions, Statements
       │
       ▼
 [Supervisor Confidence Routing Gate]
       │
       ├──────────────────────────────────────────────┐
       │ (Confidence Score > 95%)                     │ (Confidence Score <= 95% or Out-of-Scope)
       ▼                                              ▼
 [Automatic Send (SMTP)]                     [Escalate to Supervisor Console Queue]
  - Dispatched via Gmail SMTP                 - Human inspects draft & extracted entities
  - Saved as status: AUTO_SENT                 - Direct manual editing of body allowed
                                              - Action: [Dismiss/Archive] (REJECTED status)
                                              - Action: [Approve & Send] (MANUALLY_SENT status)
```

---

## 1.1 Purpose and Specifications of LLM Calls

To ensure high performance and minimize rate limit impact (5 Requests Per Minute limit in the free Gemini tier), our orchestration is optimized into exactly **two sequential LLM calls**:

### Call 1: Batched Combined Analysis Engine (`CombinedAnalysisAgent`)
*   **Prompt Template**: `prompts/templates.py:COMBINED_ANALYSIS_SYSTEM`
*   **Input**: Raw customer email sender, subject, and message body.
*   **Role & Purpose**:
    *   **Email Understanding**: Cleans spaces, normalizes layouts, detects language, and compiles a concise 1-sentence request summary.
    *   **Intent Classification**: Identifies if requests represent `ACCOUNT_BALANCE` (savings account balances), `CARD_TRANSACTIONS` (recent card histories), `STATEMENT_REQUEST` (e-statement downloads), or `UNKNOWN`.
    *   **Sentiment Analysis**: Evaluates customer frustration level (`NEUTRAL`, `POSITIVE`, `NEGATIVE/URGENT`) along with reasoning to prioritize urgent workflows.
    *   **Entity Extraction**: Structurally parses banking tokens (10-digit savings account numbers, full or masked credit card numbers, statement month/year, transaction limit counts, and sender signatures).
*   **Format**: Raw, schema-enforced JSON.

### Call 2: Contextual Response Generation Engine (`ResponseGenerationAgent`)
*   **Prompt Template**: `prompts/templates.py:RESPONSE_SYSTEM`
*   **Input**: Extracted entities, detected intents, original email subject/body, deterministic core system validation results, and retrieved mock banking balance/transaction database payloads.
*   **Role & Purpose**:
    *   **Secure Drafting**: Enforces strict security compliance. Automatically masks sensitive numbers (e.g. Account endings `XXXX7890`, Card endings `XXXX8901`) before writing responses, preventing credential leak.
    *   **Dynamic Data Formatting**: Converts credit card transaction histories into highly readable Markdown data tables within the body.
    *   **Empathy Tailoring**: Adapts wording based on sentiment (e.g., placing immediate attention indicators on urgent complaints).
    *   **Supervision Metric**: Computes a precise `confidence_score` (between `0.0` and `1.0`). If the score is above `0.95` (95%), the email is approved for direct dispatch. Else, it flags it for supervisor review.
*   **Format**: Raw, schema-enforced JSON containing `draft_response` and `confidence_score`.

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
│   ├── base.py               # Generates structured JSON responses from Gemini 2.5 using response_mime_type.
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

## 2.5 Secure Relational Database & SQL Policy Guardrails Engine

To handle complex database requests safely, the platform operates on an advanced SQLAlchemy relational model featuring Curated Read-Only Semantic Views and a programmatic SQL Policy Guardrails engine in Python.

### The Security Flow Architecture

```
User Email
   │
   ▼ (Gemini extracts parameter-less SQL)
LLM SQL Generation (No raw card/account numbers in prompt or SQL)
   │
   ▼
Parser Validation (Token Check: blocks comments, semicolons, admin commands)
   │
   ▼
Whitelist Verification (Sources verified against Allowed Views)
   │
   ▼
Dynamic Projection Injector (Ensures card_number or account_number is projected)
   │
   ▼
Subquery Tenant Wrapping (Outer wrapper applies session-level validated parameter)
   │
   ▼
EXPLAIN Cost Checker (Pre-run EXPLAIN QUERY PLAN; abort if full table scan)
   │
   ▼
SQLite Connection Sandbox (Progress handler halts execution if instructions > 1,000)
   │
   ▼
Safe Parameterized Execution
```

### 1. Curated Read-Only Semantic Views
Direct access to underlying physical tables (`accounts`, `cards`, `card_transactions`, `statements`, `emails`) is strictly blocked. Instead, queries are whitelisted only against the following semantic views:
*   `customer_accounts_view` (Exposes: `account_number`, `customer_name`, `balance`, `currency`, `status`)
*   `customer_transactions_view` (Exposes: `card_number`, `date`, `merchant`, `amount`, `type`)
*   `customer_statements_view` (Exposes: `account_number`, `period`, `filename`, `size`, `download_url`)

### 2. Lexical & AST Guardrails
All dynamic queries are inspected programmatically at the Python engine level using strict security filters:
*   **Lexical Token Blocks**: Semicolon-chaining (`;`), database comments (`--`, `/*`), administrative commands (`PRAGMA`), database attachment (`ATTACH`, `DETACH`), and dangerous SQLite functions (`load_extension`, `randomblob`, `hex`, `readfile`, `writefile`) are strictly blocked.
*   **Write Prevention**: Rejects any non-SELECT keyword operations (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `REPLACE`, `TRUNCATE`).

### 3. Outer Subquery Tenant Isolation (Unbreakable Boundaries)
Rather than appending raw filters (which corrupts logic when `GROUP BY`, `ORDER BY`, `LIMIT`, subqueries, or CTEs are used), the LLM generates parameter-less SQL. The Python engine wraps it as an inner query:
```sql
SELECT * FROM (
  -- LLM generated safe query here
) AS q
WHERE q.card_number = :validated_card
LIMIT 10;
```
*   **Dynamic SELECT Injector**: If the LLM does not project the grouping column (`card_number` or `account_number`) in the SELECT clause, the Python parser automatically injects it into the inner SELECT projection to prevent SQLite reference errors.
*   **Authenticated Session Binding**: Validated card/account strings are retrieved strictly from the customer's authenticated context—never from the LLM or raw email prompts—and bound using parameterized SQL (`:validated_card`, `:validated_account`).

### 4. Connection Sandboxing & Performance Guards
*   **SQLite Progress Handler**: The connection is registered with `sqlite3.set_progress_handler` to abort query execution if it consumes more than 1,000 SQLite VM instructions, preventing CPU starvation.
*   **EXPLAIN Query Plan Cost Checks**: Pre-runs `EXPLAIN QUERY PLAN` on SQLite. If the plan reveals an unindexed full table scan (`SCAN TABLE`), execution is instantly aborted. Index structures are built on the physical tables' foreign keys to guarantee high-performance, indexed execution plans.

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
- **IMAP Server-Side Sync Filter**: Implements server-side keywords filtering in Gmail IMAP using `UNSEEN OR SUBJECT "HDFC" BODY "HDFC"` which instructs the mail server to filter your inbox *before* transferring data, completely ignoring unrelated personal unread emails.
- **API Model Migration**: Migrated the core multi-agent orchestration model from `gemini-2.5-flash-lite` to `gemini-2.5-flash` to resolve rate-limiting blocks and deliver faster response generation.
- **Human-in-the-Loop Supervision Dashboard**: A full supervisor queue console with status filters, search controls, radial confidence gauges, direct response text editors, mock database monitors, and live terminal logs.

---

## 6. Assumptions & Limitations

### Assumptions
- Core banking APIs are mocked/simulated using an in-process SQLite database. No real banking backend is connected.
- Authentication and authorization are simplified. No user login or session management is implemented.
- Email server integration is simulated when Gmail credentials are not configured. The system falls back to high-fidelity mock email scenarios.
- No real customer banking data is used. All account numbers, card numbers, balances, and transactions are fictional seed data.
- The Ollama LLM server is expected to be running locally at `http://localhost:11434` with the `llama3` model loaded.

### Limitations
- **Database**: Uses SQLite instead of PostgreSQL/MongoDB. SQLite is single-writer and not suitable for high-concurrency production deployments.
- **Rate Limiting**: The 2-call LLM optimization is designed around free-tier rate limits. Production deployments with higher quotas could leverage individual agent calls for finer granularity.
- **No Docker Deployment**: A Dockerfile is provided but no Docker Compose or Kubernetes manifests are included.
- **No OCR/Attachment Processing**: Email attachments are not parsed. Only plain-text email bodies are processed.
- **Single Language Model**: The system currently uses a single LLM model. No model fallback or ensemble strategy is implemented.
- **No Voice Channel**: Only email channel is supported; no voice or chat omnichannel integration.
