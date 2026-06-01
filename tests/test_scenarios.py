# Automated Integration Test Suite for HDFC AI MailRoom System
import os
import sys

# Add project root directory to path to support clean imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from workflows.orchestrator import EmailOrchestrator
from utils import database

# Define the 5 core business scenarios to test
TEST_SCENARIOS = [
    {
        "id": 1,
        "name": "Scenario 1: Account Balance Enquiry",
        "sender": "hvpandey2000@gmail.com",
        "subject": "Balance inquiry",
        "body": "Please provide my savings account balance for account number 1234567890."
    },
    {
        "id": 2,
        "name": "Scenario 2: Credit Card Usage Enquiry",
        "sender": "hvpandey2000@gmail.com",
        "subject": "Credit card transactions",
        "body": "Please share my last 5 credit card transactions for card 4567XXXX8901."
    },
    {
        "id": 3,
        "name": "Scenario 3: Statement Request",
        "sender": "hvpandey2000@gmail.com",
        "subject": "E-statement required",
        "body": "Kindly send my bank statement for April 2026."
    },
    {
        "id": 4,
        "name": "Scenario 4: Multiple Requests in One Email",
        "sender": "hvpandey2000@gmail.com",
        "subject": "Account balance and card history",
        "body": "Please share my account balance for account 1234567890 and also send last 3 transactions of my credit card 987654321."
    },
    {
        "id": 5,
        "name": "Scenario 5: Partial Validation Failure",
        "sender": "hvpandey2000@gmail.com",
        "subject": "Account details and CC check",
        "body": "Please provide balance for account 1234567890 and card transactions for card 999999999."
    }
]

def run_tests():
    print("=" * 70)
    print("            HDFC AI MAILROOM - INTEGRATION TEST RUNNER")
    print("=" * 70)
    
    # Initialize the relational database and seed mock records
    database.initialize_db()
    
    orchestrator = EmailOrchestrator()
    passed_counts = 0
    
    for idx, tc in enumerate(TEST_SCENARIOS):
        if idx > 0:
            print("\n[RATE_LIMIT_PACING] Waiting 15s between scenarios to respect Gemini Free Tier limits...")
            import time
            time.sleep(15)
            
        print(f"\n[RUNNING] {tc['name']}")
        print("-" * 50)
        print(f"From: {tc['sender']}")
        print(f"Subject: {tc['subject']}")
        print(f"Body: {tc['body']}")
        print("Processing...")
        
        try:
            state = orchestrator.process_email(
                sender=tc["sender"],
                subject=tc["subject"],
                body=tc["body"]
            )
            
            # --- EVALUATE SUCCESS METRICS ---
            print("\n[RESULT] Success!")
            print(f"Execution Time: {state.execution_time_ms} ms")
            print(f"Sentiment: {state.sentiment}")
            print(f"Intents Identified: {state.intents}")
            print(f"Extracted Entities: {state.entities}")
            print(f"Validation Outcomes: {state.validation_results}")
            print(f"APIs Executed: {[c.get('api') for c in state.selected_apis]}")
            
            print("\nDraft Response preview:")
            print('"' * 40)
            print(state.draft_response[:250] + "...")
            print('"' * 40)
            
            # Scenario specific assertions
            success = True
            if tc["id"] == 1:
                if "ACCOUNT_BALANCE" not in state.intents:
                    print("[FAIL] ACCOUNT_BALANCE intent not identified.")
                    success = False
                if "125,000" not in state.draft_response and "1,25,000" not in state.draft_response:
                    print("[FAIL] Correct balance amount missing from email draft.")
                    success = False
            elif tc["id"] == 2:
                if "CARD_TRANSACTIONS" not in state.intents:
                    print("[FAIL] CARD_TRANSACTIONS intent not identified.")
                    success = False
            elif tc["id"] == 3:
                if "STATEMENT_REQUEST" not in state.intents:
                    print("[FAIL] STATEMENT_REQUEST intent not identified.")
                    success = False
            elif tc["id"] == 4:
                if len(state.intents) < 2:
                    print("[FAIL] Fails to detect multiple intents.")
                    success = False
            elif tc["id"] == 5:
                # Succeeded balance fetch, card failed
                if not state.validation_results.get("account_validated"):
                    print("[FAIL] Account was not validated.")
                    success = False
                if state.validation_results.get("card_validated"):
                    print("[FAIL] Invalid card was incorrectly validated.")
                    success = False
                lower_draft = state.draft_response.lower()
                has_warning = any(x in lower_draft for x in ["could not", "invalid", "error", "fail", "issue", "unable"])
                if not has_warning:
                    print("[FAIL] No rejection warning in drafted response for card.")
                    success = False
                    
            if success:
                print(f"[PASS] {tc['name']} fully verified.")
                passed_counts += 1
            else:
                print(f"[FAIL] {tc['name']} verification check failed.")
                
        except Exception as e:
            print(f"[ERROR] Exception during processing: {str(e)}")
            
        print("-" * 50)
        
    print("\n" + "=" * 70)
    print(f"TEST RUN SUMMARY: {passed_counts} / {len(TEST_SCENARIOS)} SCENARIOS PASSED")
    print("=" * 70)
    
    if passed_counts == len(TEST_SCENARIOS):
        print("ALL SCENARIOS VERIFIED SUCCESSFULLY!")
        return 0
    else:
        print("SOME VERIFICATION CHECKS FAILED.")
        return 1

if __name__ == "__main__":
    sys.exit(run_tests())

#failure <95% set it up for review for human review