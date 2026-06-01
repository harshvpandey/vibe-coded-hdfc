# Handoff Report: HDFC AI MailRoom System Integration

Welcome to the official technical handoff guide for the HDFC AI MailRoom Admin and Supervision Hub. This document contains comprehensive architecture overviews, directory layouts, configuration specifications, and running guidelines for the newly deployed systems.

---

## 1. System Overview & Architecture

The HDFC AI MailRoom System is an automated email ingestion and customer service response platform. The system operates on a **Human-in-the-Loop AI Supervision** model:

```
                            [ Gmail Inbox (IMAP) ]
                                      │
                                      ▼ (Server-Side Ingestion Filter)
                          [ FastAPI Ingestion Sync ]
                                      │
                                      ▼
                        [ Multi-Agent AI Pipeline ]
                                      │
       ┌──────────────────────────────┴──────────────────────────────┐
       │                                                             │
       ▼ (LLM Call 1: Combined Analysis)                             ▼ (LLM Call 2: Response Gen)
 [Combined Analysis Agent]                                     [Response Generation Agent]
  - Batched 4 agents (Understanding, Intent,                    - Safe drafting with regex-enforced
    Sentiment, Entities) into one request                         credential masking (e.g. XXXX7890)
  - Enforces raw JSON schema output                             - Computes confidence score
       │                                                             │
       ├─────────────────────────────────────────────────────────────┘
       ▼
 [Deterministic Python Validations]
  - Checks extracted card/account validations against Core Database
  - API execution: Retrieves savings account balances, card histories, statements
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

## 2. LLM Call Architecture Specifications

To ensure high processing speeds and bypass Gemini API free tier rate-limiting (5 RPM / 20 Requests Per Day for some models), the multi-agent pipeline is optimized into **exactly two sequential LLM calls**:

### Call 1: Batched Combined Analysis Engine (`CombinedAnalysisAgent`)
*   **Prompt Instructions**: `prompts/templates.py:COMBINED_ANALYSIS_SYSTEM`
*   **Model**: `gemini-2.5-flash`
*   **Role & Sub-agents**:
    *   *Email Understanding*: standardizes whitespace and compiles a 1-sentence request summary.
    *   *Intent Classification*: maps customer request to core tasks (`ACCOUNT_BALANCE`, `CARD_TRANSACTIONS`, `STATEMENT_REQUEST`, or `UNKNOWN`).
    *   *Sentiment Analysis*: analyzes emotional status (`POSITIVE`, `NEUTRAL`, `NEGATIVE/URGENT`) with textual reasoning.
    *   *Entity Extraction*: extracts banking details (10-digit savings account, full/masked card, statement period, transaction limit count).
*   **Output Format**: Schema-enforced JSON.

### Call 2: Contextual Response Generation Engine (`ResponseGenerationAgent`)
*   **Prompt Instructions**: `prompts/templates.py:RESPONSE_SYSTEM`
*   **Model**: `gemini-2.5-flash`
*   **Role & Purpose**:
    *   *Empathetic Drafting*: Compiles a professional corporate banking response.
    *   *Security Compliance*: Automatically masks sensitive data ending in `XXXX7890` or `XXXX8901` before writing replies.
    *   *Data Formatting*: Converts transaction histories into HTML-rendered Markdown data tables.
    *   *Supervision Metric*: Generates a `confidence_score` (between `0.0` and `1.0`). If above `0.95`, the email dispatches automatically. Else, it queues for review.
*   **Output Format**: Schema-enforced JSON (`draft_response`, `confidence_score`).

---

## 3. Configuration & `.env` Setup

All authentication keys and network connection variables are managed in the local `.env` configuration file in the project root:

```ini
# Gemini API Key (Enables Multi-Agent AI Pipelines)
GOOGLE_API_KEY=AIzaSyCCPTHYb8wawYgF4_EXo3RwFbEqSltRf7Y

# Supervisor Gmail Account Credentials (IMAP/SMTP Ingestion & Dispatch)
GMAIL_EMAIL=harshvardhan.pandey.y@gmail.com
GMAIL_APP_PASSWORD=pffgwsvuwqillrru

# Server Ingestion Search Filter Keyword
GMAIL_SYNC_FILTER_KEYWORD=HDFC
```

> [!IMPORTANT]
> **Google App Password Requirement**
> Standard Google account passwords are blocked by default on IMAP/SMTP connections. You must generate a **16-character Google App Password** (using your account settings at *myaccount.google.com/apppasswords*) to allow programmatic fetching and dispatching. The provided App Password `pffgwsvuwqillrru` has been successfully tested and configured!

---

## 4. Key Directory & Code Modifications

Here is what was created/modified during deployment:

*   **`config/settings.py`**: Added Gmail credentials, network connection hostnames, confidence thresholds, and `GMAIL_SYNC_FILTER_KEYWORD` defaults.
*   **`utils/database.py` [UPDATED]**: Fully migrated mock dictionary storage to **SQLAlchemy 2.0 ORM** using SQLite. 
    *   Defines structured tables for `accounts`, `cards`, `card_transactions`, `statements`, and `emails`.
    *   Exposes three curated read-only semantic views: `customer_accounts_view`, `customer_transactions_view`, and `customer_statements_view`.
    *   Maintains thread-safe dictionary proxies (`AccountsDbProxy`, `CardsDbProxy`) to support 100% backward compatibility with legacy APIs and dashboard endpoints.
    *   Indexes foreign keys (`card_transactions.card_number` and `statements.account_number`) to support rapid index lookups.
*   **`utils/sql_guardrails.py` [NEW]**: Programmatic Python-level SQL policy engine implementing AST lexical checks, whitelisting, subquery isolation, instruction timeouts, and execution plan auditing.
*   **`utils/email_service.py`**: Coordinates Gmail connectivity. Uses secure IMAP to fetch unseen emails, parses MIME structures, and SMTP STARTTLS to dispatch responses. **Features a built-in simulation fallback mode**: if connection fails or credentials are unset, it mock-generates queries and saves SMTP replies to local log streams to ensure out-of-the-box offline execution.
*   **`workflows/orchestrator.py` [UPDATED]**: Modified `execute_api_call` to check for LLM-generated SQL queries, validate and rewrite them using the SQL Guardrails engine, execute them parameterized, and fall back gracefully to standard deterministic lookup methods if any policy or cost check fails.
*   **`prompts/templates.py` [UPDATED]**: Extended `COMBINED_ANALYSIS_SYSTEM` system prompt schema to support dynamic, parameter-less SQL query generation against the semantic views schema, instructing the LLM to never include raw credential identifiers in the generated SQL.
*   **`apis/app.py`**: Exposed endpoints to sync inbox queues, fetch filtered list structures, manually approve and edit drafts, and archive rejected transactions.
*   **`agents/base.py`**: Migrated active LLM model from `gemini-2.5-flash-lite` to `gemini-2.5-flash` to resolve 429 daily rate-limiting blocks and optimize processing speeds.
*   **`static/`**: Serve a stunning supervisor console featuring search bars, sidebar tab filters, circular animated confidence gauges, Markdown draft editors, mock DB monitor drawers, and live terminal audit consoles.
*   **`tests/test_sql_guardrails.py` [NEW]**: Comprehensive testing suite asserting comment blockers, semicolon blocks, whitelisted views, physical table access rejections, outer subquery tenant isolation wrapping, dynamic projection injection, SQLite progress handler instruction aborts, and EXPLAIN full-table scan query plan blocks.
*   **`tests/test_scenarios.py` [UPDATED]**: Modified to trigger automated database table and view initialization before integration testing begins.

---

## 5. Technical Specifications of the SQL Policy Guardrails Engine

To protect our SQLite banking database from malicious activity or unintended heavy operations, `utils/sql_guardrails.py` enforces a 6-stage security pipeline:

1.  **Lexical Token Check**: Completely rejects any incoming SQL query text containing comment delimiters (`--`, `/*`, `*/`) or semicolon chained multi-statements (`;`).
2.  **SELECT-only Enforcement**: Verifies the query starts strictly with `SELECT` or `WITH`, and contains no write keywords (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `REPLACE`, `TRUNCATE`).
3.  **Physical Table Access Block**: Strictly blocks any direct access to underlying database tables (`accounts`, `cards`, `card_transactions`, etc.). Queries are whitelisted strictly against curated read-only semantic views (`customer_accounts_view`, `customer_transactions_view`, `customer_statements_view`).
4.  **Dynamic SELECT Projection Injector**: If the LLM generates a valid query but fails to project the necessary grouping key (`card_number` or `account_number`) in the SELECT list, the engine automatically injects it to avoid SQLite outer reference errors.
5.  **Outer Subquery Tenant Isolation Wrapping**: To prevent database logic bypasses or horizontal privilege escalations (especially for queries utilizing `GROUP BY`, `ORDER BY`, `LIMIT`, subqueries, or CTEs), the dynamic SQL is programmatically wrapped inside a clean outer subquery applying validated parameters from the session context:
    ```sql
    SELECT * FROM (
      -- LLM generated safe query goes here
    ) AS q
    WHERE q.card_number = :validated_card
    LIMIT 10;
    ```
6.  **SQLite Connection Sandbox Limits**:
    *   *SQLite Progress Handler*: Registers `connection.set_progress_handler` on the SQLite connection. If query execution consumes more than 1,000 instructions, the progress handler instantly interrupts and terminates execution (CPU starvation protection).
    *   *EXPLAIN Query Plan Auditing*: Pre-runs `EXPLAIN QUERY PLAN` on SQLite before execution. If the planner is performing an unindexed full table scan (`SCAN TABLE`) instead of using indexes (`SEARCH TABLE`), execution is instantly aborted.

---

## 6. Verification Results

### 6.1 Programmatic SQL Guardrail Tests
All 10 custom unit tests in [test_sql_guardrails.py](file:///c:/Users/techn/Documents/projects/vibe_coded_hdfc/tests/test_sql_guardrails.py) pass successfully:
*   Comment Blocks: Verified comments trigger security exceptions. (**Passed**)
*   Semicolons: Verified chained queries are rejected. (**Passed**)
*   SELECT-only: Verified write operations are blocked. (**Passed**)
*   Dangerous commands: Verified `PRAGMA`/`ATTACH`/`DETACH` are blocked. (**Passed**)
*   Physical Tables: Direct physical table queries are rejected. (**Passed**)
*   Dynamic Projection: Correct injection of `card_number` or `account_number`. (**Passed**)
*   Subquery Wrapping: Correct isolation boundaries constructed. (**Passed**)
*   EXPLAIN Query Plan: Unindexed scans abort successfully. (**Passed**)
*   Progress Handler: High-instruction queries abort successfully at 1,000 instructions. (**Passed**)

### 6.2 Business Integration Scenario Tests
All 5 core customer query scenarios in [test_scenarios.py](file:///c:/Users/techn/Documents/projects/vibe_coded_hdfc/tests/test_scenarios.py) pass successfully against our SQLAlchemy database:
1.  **Scenario 1: Account Balance**: Correctly resolves balance information for active accounts. (**Passed**)
2.  **Scenario 2: Card Transactions**: Correctly fetches recent credit card history. (**Passed**)
3.  **Scenario 3: Statement Request**: Successfully fetches and resolves download URLs for statements. (**Passed**)
4.  **Scenario 4: Multi-intent Request**: Combines account balance and credit card historical queries. (**Passed**)
5.  **Scenario 5: Partial Failure**: Emits recheck warnings for invalid card credentials while resolving account balance. (**Passed**)

---

## 7. How to Run & Ingest Mail

### 7.1 Start local server:
Initialize the FastAPI server in your workspace:
```bash
venv\Scripts\python main.py
```
*Access the interactive supervision console by opening **`http://localhost:8000`** in your browser.*

### 7.2 Run Automated Tests:
*   **Run SQL Guardrail Tests**:
    ```bash
    venv\Scripts\python -m unittest tests/test_sql_guardrails.py
    ```
*   **Run Integration Scenario Tests**:
    ```bash
    venv\Scripts\python tests/test_scenarios.py
    ```
