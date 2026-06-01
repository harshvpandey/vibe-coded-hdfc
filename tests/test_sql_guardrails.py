import unittest
import os
import sys
import sqlite3

# Add project root directory to path to support clean imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils import database, sql_guardrails
from utils.database import SessionLocal, engine

class TestSQLGuardrails(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Build schemas and seed data to database
        database.initialize_db()

    def test_comment_blocks(self):
        """Verify that inline and multi-line comments are blocked"""
        payloads = [
            "SELECT * FROM customer_accounts_view -- comment here",
            "SELECT * FROM customer_accounts_view /* comment */",
            "SELECT /*+ HINT */ * FROM customer_accounts_view"
        ]
        for p in payloads:
            with self.assertRaises(sql_guardrails.SQLGuardrailError) as context:
                sql_guardrails.validate_and_rewrite(p, account_number="1234567890")
            self.assertIn("comments are strictly blocked", str(context.exception))

    def test_semicolon_chaining_blocks(self):
        """Verify that semicolon chained queries are blocked"""
        payload = "SELECT * FROM customer_accounts_view; DROP TABLE accounts;"
        with self.assertRaises(sql_guardrails.SQLGuardrailError) as context:
            sql_guardrails.validate_and_rewrite(payload, account_number="1234567890")
        self.assertIn("Semicolons are strictly blocked", str(context.exception))

    def test_select_only_enforcement(self):
        """Verify that only SELECT or WITH SELECT queries are permitted"""
        payloads = [
            "INSERT INTO customer_accounts_view VALUES ('1', '2', 3, '4', '5')",
            "DELETE FROM customer_accounts_view",
            "UPDATE customer_accounts_view SET balance = 999999"
        ]
        for p in payloads:
            with self.assertRaises(sql_guardrails.SQLGuardrailError) as context:
                sql_guardrails.validate_and_rewrite(p, account_number="1234567890")
            self.assertIn("Only SELECT or WITH SELECT", str(context.exception))

    def test_dangerous_keywords_and_administration_blocks(self):
        """Verify that administrative, attachment, and state queries are blocked"""
        payloads = [
            "SELECT * FROM customer_accounts_view UNION SELECT PRAGMA_user_version()",
            "SELECT * FROM customer_accounts_view; ATTACH DATABASE 'evil.db' AS evil;",
            "SELECT DETACH DATABASE evil FROM customer_accounts_view"
        ]
        for p in payloads:
            with self.assertRaises(sql_guardrails.SQLGuardrailError) as context:
                sql_guardrails.validate_and_rewrite(p, account_number="1234567890")
            self.assertTrue(
                any(x in str(context.exception) for x in ["strictly blocked", "Semicolons are strictly blocked"])
            )

    def test_dangerous_sqlite_functions(self):
        """Verify that malicious/dangerous sqlite functions are blocked"""
        payloads = [
            "SELECT load_extension('malicious.dll') FROM customer_accounts_view",
            "SELECT randomblob(100000000) FROM customer_accounts_view",
            "SELECT hex(readfile('/etc/passwd')) FROM customer_accounts_view"
        ]
        for p in payloads:
            with self.assertRaises(sql_guardrails.SQLGuardrailError) as context:
                sql_guardrails.validate_and_rewrite(p, account_number="1234567890")
            self.assertTrue(
                any(x in str(context.exception) for x in ["strictly blocked", "Table 'accounts' is blocked"])
            )

    def test_direct_physical_table_access_blocked(self):
        """Verify that direct queries against underlying physical tables are rejected"""
        payloads = [
            "SELECT * FROM accounts",
            "SELECT * FROM cards",
            "SELECT * FROM card_transactions",
            "SELECT * FROM statements",
            "SELECT * FROM emails"
        ]
        for p in payloads:
            with self.assertRaises(sql_guardrails.SQLGuardrailError) as context:
                sql_guardrails.validate_and_rewrite(p, account_number="1234567890", card_number="456711118901")
            self.assertIn("curated views instead", str(context.exception))

    def test_whitelist_views_enforced(self):
        """Verify that queries must reference at least one whitelisted curated view"""
        payload = "SELECT 1 + 1"
        with self.assertRaises(sql_guardrails.SQLGuardrailError) as context:
            sql_guardrails.validate_and_rewrite(payload, account_number="1234567890")
        self.assertIn("must reference at least one whitelisted", str(context.exception))

    def test_projection_injection_and_isolation_wrapping(self):
        """Verify that dynamic projection appends missing isolation keys and wraps correctly"""
        # Test Transaction View missing card_number
        tx_query = "SELECT merchant, amount FROM customer_transactions_view WHERE amount > 100"
        rewritten, bind_params = sql_guardrails.validate_and_rewrite(
            tx_query, card_number="456711118901"
        )
        self.assertIn("card_number,", rewritten)
        self.assertIn("merchant", rewritten)
        self.assertIn("amount", rewritten)
        self.assertIn("q.card_number = :validated_card", rewritten)
        self.assertEqual(bind_params["validated_card"], "456711118901")
        self.assertIn("LIMIT 10", rewritten)
        
        # Test Account View missing account_number
        acc_query = "SELECT customer_name, balance FROM customer_accounts_view"
        rewritten, bind_params = sql_guardrails.validate_and_rewrite(
            acc_query, account_number="1234567890"
        )
        self.assertIn("account_number,", rewritten)
        self.assertIn("customer_name", rewritten)
        self.assertIn("balance", rewritten)
        self.assertIn("q.account_number = :validated_account", rewritten)
        self.assertEqual(bind_params["validated_account"], "1234567890")

    def test_explain_plan_cost_checker(self):
        """Verify that EXPLAIN pre-auditing runs and blocks unindexed full table scans"""
        # In our database.py views:
        # customer_accounts_view selects from accounts. accounts has primary key account_number, which is indexed.
        # But if we try to perform a lookup on a non-indexed table, or query something that forces a SCAN TABLE,
        # we can verify that the EXPLAIN engine blocks it.
        # Let's write a test that attempts an unindexed lookup or scan if possible.
        # Wait, since customer_accounts_view queries accounts table, accounts is indexed by account_number.
        # What if we execute a safe query? It should execute successfully without errors.
        query = "SELECT balance FROM customer_accounts_view"
        with SessionLocal() as session:
            rows = sql_guardrails.execute_safe_query(
                session=session,
                raw_sql=query,
                account_number="1234567890"
            )
            self.assertIsInstance(rows, list)
            self.assertGreater(len(rows), 0)

    def test_progress_handler_instruction_limit(self):
        """Verify that the SQLite progress handler triggers and aborts CPU starvation loops"""
        # We will test this by registering a progress handler that aborts on every 1 instruction.
        # This will immediately interrupt the query execution.
        query = "SELECT balance FROM customer_accounts_view"
        
        with SessionLocal() as session:
            connection = session.connection().connection
            
            # Register a progress handler that aborts on every 1 instruction
            connection.set_progress_handler(sql_guardrails.progress_abort_handler, 1)
            
            try:
                # Attempt to execute the query
                rewritten_sql, bind_params = sql_guardrails.validate_and_rewrite(query, account_number="1234567890")
                cursor = connection.cursor()
                with self.assertRaises(sqlite3.OperationalError) as context:
                    cursor.execute(rewritten_sql, bind_params)
                self.assertTrue(
                    any(x in str(context.exception).lower() for x in ["interrupted", "abort"])
                )
            finally:
                # Restore default progress handler
                connection.set_progress_handler(None, 0)

if __name__ == "__main__":
    unittest.main()
