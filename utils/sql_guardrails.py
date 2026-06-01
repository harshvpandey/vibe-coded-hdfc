# Programmatic SQL Policy Guardrails Engine
import re
import sqlite3
from sqlalchemy import text
from utils.logger import log_api_call

# Whitelisted views that the LLM is allowed to query
ALLOWED_VIEWS = {
    "customer_accounts_view",
    "customer_transactions_view",
    "customer_statements_view"
}

# Blocked physical database tables to prevent bypass of curated views
BLOCKED_TABLES = {
    "accounts",
    "cards",
    "card_transactions",
    "statements",
    "emails"
}

# Blocked modify and admin operations
BLOCKED_OPERATIONS = [
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", 
    "REPLACE", "TRUNCATE", "PRAGMA", "ATTACH", "DETACH"
]

# Dangerous SQLite functions that could compromise system integrity
BLOCKED_FUNCTIONS = [
    "load_extension", "randomblob", "hex", "readfile", "writefile"
]

class SQLGuardrailError(Exception):
    """Custom exception raised for database policy violations"""
    pass

def validate_and_rewrite(sql_query: str, card_number: str = None, account_number: str = None) -> tuple:
    """
    Validates the incoming query against standard guardrails and rewrites it as an outer
    subquery to enforce absolute tenant isolation and prevent horizontal privilege escalation.
    
    Returns:
        (rewritten_sql_str, bind_parameters_dict)
    """
    if not sql_query:
        raise SQLGuardrailError("Empty SQL query provided")
        
    cleaned_query = sql_query.strip()
    query_upper = cleaned_query.upper()
    
    # 1. Block comments to prevent parser escaping/bypasses
    if "--" in cleaned_query or "/*" in cleaned_query or "*/" in cleaned_query:
        raise SQLGuardrailError("SQL comments are strictly blocked to prevent query evasion")
        
    # 2. Block semicolon chaining to prevent multi-statement execution
    if ";" in cleaned_query:
        raise SQLGuardrailError("Semicolons are strictly blocked to prevent query stacking")
        
    # 3. Only allow SELECT or WITH SELECT queries
    if not (query_upper.startswith("SELECT") or query_upper.startswith("WITH")):
        raise SQLGuardrailError("Only SELECT or WITH SELECT queries are permitted")
        
    # 4. Check for modify and administration keywords
    for keyword in BLOCKED_OPERATIONS:
        # We perform a direct substring check to block all variants (e.g. PRAGMA_user_version)
        if keyword in query_upper:
            raise SQLGuardrailError(f"Database operation '{keyword}' is strictly blocked")
            
    # 5. Check for dangerous SQLite functions
    for func in BLOCKED_FUNCTIONS:
        if func.upper() in query_upper:
            raise SQLGuardrailError(f"SQLite function '{func}' is strictly blocked")
            
    # 6. Check for direct physical table names to force semantic view usage
    for table in BLOCKED_TABLES:
        pattern = r"\b" + re.escape(table.upper()) + r"\b"
        if re.search(pattern, query_upper):
            raise SQLGuardrailError(f"Direct access to table '{table}' is blocked. Use curated views instead")
            
    # 7. Identify which curated views are queried
    referenced_views = set()
    for view in ALLOWED_VIEWS:
        pattern = r"\b" + re.escape(view.upper()) + r"\b"
        if re.search(pattern, query_upper):
            referenced_views.add(view)
            
    if not referenced_views:
        raise SQLGuardrailError("Query must reference at least one whitelisted curated view")
        
    # 8. Check that no other non-whitelisted tables are accessed
    from_join_patterns = re.findall(r"\b(?:FROM|JOIN)\s+([a-zA-Z0-9_]+)", query_upper)
    for table_name in from_join_patterns:
        name_lower = table_name.lower()
        if name_lower in BLOCKED_TABLES:
            raise SQLGuardrailError(f"Direct access to table '{table_name}' is blocked")
            
    # 9. Dynamic SELECT projection injection and Tenant Isolation Clause setup
    inner_sql = cleaned_query
    filters = []
    bind_params = {}
    
    # Check for card transactions view
    if "customer_transactions_view" in referenced_views:
        if not card_number:
            raise SQLGuardrailError("Card validation required to query transaction history")
        # Ensure card_number is projected in the select clause
        if "CARD_NUMBER" not in query_upper and "*" not in query_upper:
            # Inject card_number to the first SELECT keyword
            select_match = re.search(r"\bSELECT\b", inner_sql, re.IGNORECASE)
            if select_match:
                idx = select_match.end()
                inner_sql = inner_sql[:idx] + " card_number, " + inner_sql[idx:]
                query_upper = inner_sql.upper()
        filters.append("q.card_number = :validated_card")
        bind_params["validated_card"] = str(card_number).replace(" ", "").replace("-", "").strip()
        
    # Check for account balance or statement views
    if "customer_accounts_view" in referenced_views or "customer_statements_view" in referenced_views:
        if not account_number:
            raise SQLGuardrailError("Account validation required to query account details or statements")
        # Ensure account_number is projected in the select clause
        if "ACCOUNT_NUMBER" not in query_upper and "*" not in query_upper:
            # Inject account_number to the first SELECT keyword
            select_match = re.search(r"\bSELECT\b", inner_sql, re.IGNORECASE)
            if select_match:
                idx = select_match.end()
                inner_sql = inner_sql[:idx] + " account_number, " + inner_sql[idx:]
                query_upper = inner_sql.upper()
        filters.append("q.account_number = :validated_account")
        bind_params["validated_account"] = str(account_number).strip()
        
    # 10. Wrap inner query as outer subquery and apply filters
    if not filters:
        raise SQLGuardrailError("Could not determine tenant isolation boundaries for query")
        
    isolation_clause = " AND ".join(filters)
    rewritten_sql = f"SELECT * FROM (\n  {inner_sql}\n) AS q\nWHERE {isolation_clause}\nLIMIT 10"
    
    return rewritten_sql, bind_params

def progress_abort_handler():
    """Returns 1 to signal SQLite to immediately terminate execution"""
    return 1

def execute_safe_query(session, raw_sql: str, card_number: str = None, account_number: str = None) -> list:
    """
    Validates, rewrites, and executes the SQL query inside the secure sandbox connection.
    Applies progress instruction limits and pre-audits the query plan for unindexed scans.
    """
    # 1. Guardrail validation and rewriting
    rewritten_sql, bind_params = validate_and_rewrite(raw_sql, card_number, account_number)
    
    # Get raw dbapi connection from SQLAlchemy connection
    dbapi_conn = session.connection().connection
    if not dbapi_conn:
        raise SQLGuardrailError("Database connection is unavailable")
        
    # 2. Configure Progress Handler (terminate query if instructions > 1,000)
    # The handler is called every 1,000 instructions. On call, we immediately abort.
    dbapi_conn.set_progress_handler(progress_abort_handler, 1000)
    
    try:
        # 3. EXPLAIN QUERY PLAN Auditing
        explain_query = f"EXPLAIN QUERY PLAN {rewritten_sql}"
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute(explain_query, bind_params)
            plan_rows = cursor.fetchall()
            # Check for unindexed table scan ('SCAN TABLE' in the plan)
            for row in plan_rows:
                # SQLite plan row layout: (id, parent, notused, detail)
                detail = str(row[3]).upper()
                if "SCAN TABLE" in detail:
                    raise SQLGuardrailError(f"Query plan cost violation: Full table scan detected ({row[3]}). Aborting query execution.")
        finally:
            cursor.close()
            
        # 4. Secure Parameterized Execution
        result = session.execute(text(rewritten_sql), bind_params)
        columns = result.keys()
        rows = [dict(zip(columns, row)) for row in result.fetchall()]
        return rows
        
    except sqlite3.OperationalError as oe:
        if "interrupted" in str(oe).lower() or "abort" in str(oe).lower():
            raise SQLGuardrailError("Query execution terminated: CPU execution limit (1,000 instructions) exceeded")
        raise SQLGuardrailError(f"Database query execution failure: {str(oe)}")
    finally:
        # Restore default progress handler (none)
        dbapi_conn.set_progress_handler(None, 0)
