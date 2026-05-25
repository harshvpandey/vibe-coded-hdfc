import time
import httpx
from config import settings
from utils import database
from utils.logger import log_agent_execution

class ValidationAgent:
    def __init__(self):
        self.name = "ValidationAgent"

    def process(self, entities: dict) -> dict:
        """Validates extracted account and card entities against Core Banking mock database or APIs"""
        start_time = time.time()
        inputs = {"entities": entities}
        
        account_number = entities.get("account_number")
        card_number = entities.get("card_number")
        
        results = {
            "account_validated": False,
            "account_status": "NOT_PROVIDED",
            "account_owner": None,
            "card_validated": False,
            "card_status": "NOT_PROVIDED",
            "card_owner": None,
            "errors": []
        }
        
        # Determine whether to use HTTP API calls or direct in-process database imports
        # If the server is running, we call it via HTTP. Otherwise, we query database module directly.
        use_http = False
        try:
            # Quick check if server is active (though normally we'll fall back to direct DB inside orchestration)
            with httpx.Client(timeout=0.5) as client:
                r = client.get(f"{settings.API_URL}/docs")
                if r.status_code == 200:
                    use_http = True
        except Exception:
            use_http = False

        # 1. Validate Account Number
        if account_number:
            if use_http:
                try:
                    with httpx.Client(timeout=2.0) as client:
                        response = client.post(
                            f"{settings.API_URL}/api/bank/validate-account",
                            json={"account_number": str(account_number)}
                        )
                        if response.status_code == 200:
                            data = response.json()
                            if data.get("status") == "VALID":
                                results["account_validated"] = True
                                results["account_status"] = "VALID"
                                results["account_owner"] = data.get("customer_name")
                            else:
                                results["account_status"] = "INVALID"
                                results["errors"].append("Account number not found in core system.")
                        else:
                            results["account_status"] = "API_ERROR"
                            results["errors"].append("Account validation API returned an error.")
                except Exception as e:
                    results["account_status"] = "API_CONNECT_FAIL"
                    results["errors"].append(f"HTTP Account validation failed: {str(e)}")
            
            # Fallback to direct module check (robust & fast)
            if not results["account_validated"] and results["account_status"] in ["NOT_PROVIDED", "API_CONNECT_FAIL", "INVALID"]:
                acc = database.get_account(account_number)
                if acc:
                    results["account_validated"] = True
                    results["account_status"] = "VALID"
                    results["account_owner"] = acc["customer_name"]
                else:
                    results["account_status"] = "INVALID"
                    results["errors"].append("Account number not found in core database.")

        # 2. Validate Credit Card
        if card_number:
            if use_http:
                try:
                    with httpx.Client(timeout=2.0) as client:
                        response = client.post(
                            f"{settings.API_URL}/api/bank/validate-card",
                            json={"card_number": str(card_number)}
                        )
                        if response.status_code == 200:
                            data = response.json()
                            if data.get("status") == "VALID":
                                results["card_validated"] = True
                                results["card_status"] = "VALID"
                                results["card_owner"] = data.get("cardholder_name")
                            else:
                                results["card_status"] = "INVALID"
                                results["errors"].append("Credit card number not found in core system.")
                        else:
                            results["card_status"] = "API_ERROR"
                            results["errors"].append("Credit card validation API returned an error.")
                except Exception as e:
                    results["card_status"] = "API_CONNECT_FAIL"
                    results["errors"].append(f"HTTP Card validation failed: {str(e)}")
            
            # Fallback to direct database check
            if not results["card_validated"] and results["card_status"] in ["NOT_PROVIDED", "API_CONNECT_FAIL", "INVALID"]:
                card = database.get_card(card_number)
                if card:
                    results["card_validated"] = True
                    results["card_status"] = "VALID"
                    results["card_owner"] = card["cardholder_name"]
                else:
                    results["card_status"] = "INVALID"
                    results["errors"].append("Credit card details invalid or not found in core database.")

        duration = int((time.time() - start_time) * 1000)
        results["agent_duration_ms"] = duration
        
        # Log agent execution
        log_agent_execution(self.name, "SUCCESS", inputs, results)
        return results
