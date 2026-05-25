# Mock In-Memory Database representing Core Banking Systems

# Mock Account Database
accounts_db = {
    "1234567890": {
        "account_number": "1234567890",
        "customer_name": "John Doe",
        "balance": 125000.00,
        "currency": "INR",
        "status": "ACTIVE"
    },
    "9876543210": {
        "account_number": "9876543210",
        "customer_name": "Jane Smith",
        "balance": 450000.00,
        "currency": "INR",
        "status": "ACTIVE"
    },
    "5555555555": {
        "account_number": "5555555555",
        "customer_name": "Robert Miller",
        "balance": 12500.50,
        "currency": "INR",
        "status": "SUSPENDED"
    }
}

# Mock Credit Card Database
# Maps last 4 digits or card number to card information
# We'll support both full card matches and matches ending with digits for ease of mock testing
cards_db = {
    "456711118901": {
        "card_number": "456711118901",
        "cardholder_name": "John Doe",
        "status": "ACTIVE",
        "credit_limit": 200000.00,
        "available_limit": 142051.00,
        "transactions": [
            {"date": "2026-05-22", "merchant": "HDFC Auto Pay", "amount": 15000.00, "type": "DEBIT"},
            {"date": "2026-05-20", "merchant": "Uber India", "amount": 350.00, "type": "DEBIT"},
            {"date": "2026-05-15", "merchant": "Netflix India", "amount": 649.00, "type": "DEBIT"},
            {"date": "2026-05-12", "merchant": "Swiggy", "amount": 450.00, "type": "DEBIT"},
            {"date": "2026-05-10", "merchant": "Amazon India", "amount": 1500.00, "type": "DEBIT"}
        ]
    },
    "987654321000": {
        "card_number": "987654321000",
        "cardholder_name": "Jane Smith",
        "status": "ACTIVE",
        "credit_limit": 500000.00,
        "available_limit": 493871.00,
        "transactions": [
            {"date": "2026-05-14", "merchant": "Zara Mumbai", "amount": 4999.00, "type": "DEBIT"},
            {"date": "2026-05-11", "merchant": "Zomato", "amount": 850.00, "type": "DEBIT"},
            {"date": "2026-05-08", "merchant": "Starbucks Coffee", "amount": 280.00, "type": "DEBIT"}
        ]
    },
    "987654321": { # Adding a entry for scenario 4 (987654321)
        "card_number": "987654321",
        "cardholder_name": "John Doe",
        "status": "ACTIVE",
        "credit_limit": 100000.00,
        "available_limit": 82000.00,
        "transactions": [
            {"date": "2026-05-23", "merchant": "Croma Digital", "amount": 12000.00, "type": "DEBIT"},
            {"date": "2026-05-18", "merchant": "Flipkart", "amount": 3500.00, "type": "DEBIT"},
            {"date": "2026-05-15", "merchant": "MakeMyTrip", "amount": 2500.00, "type": "DEBIT"}
        ]
    }
}

# Mock Statements Database
# Maps account_number -> period -> statement info/download URL
statements_db = {
    "1234567890": {
        "April 2026": {"filename": "Statement_1234567890_Apr26.pdf", "size": "142 KB", "download_url": "https://api.hdfc.com/statements/download/1234567890_Apr26.pdf"},
        "March 2026": {"filename": "Statement_1234567890_Mar26.pdf", "size": "138 KB", "download_url": "https://api.hdfc.com/statements/download/1234567890_Mar26.pdf"}
    },
    "9876543210": {
        "April 2026": {"filename": "Statement_9876543210_Apr26.pdf", "size": "212 KB", "download_url": "https://api.hdfc.com/statements/download/9876543210_Apr26.pdf"},
        "May 2026": {"filename": "Statement_9876543210_May26.pdf", "size": "225 KB", "download_url": "https://api.hdfc.com/statements/download/9876543210_May26.pdf"}
    }
}


# --- DATABASE HELPER FUNCTIONS ---

def get_account(account_number: str):
    """Retrieves account if exists, cleans up spaces"""
    if not account_number:
        return None
    cleaned = str(account_number).strip()
    return accounts_db.get(cleaned)

def get_card(card_number: str):
    """Retrieves credit card if exists, handles card matching by ending digits"""
    if not card_number:
        return None
    cleaned = str(card_number).replace(" ", "").replace("-", "").strip()
    
    # Try exact match first
    if cleaned in cards_db:
        return cards_db[cleaned]
    
    # Try ending match (for cards masked like 4567XXXX8901 or 987654321)
    # Check if the extracted card number is a suffix of any card in our DB
    for key, val in cards_db.items():
        # Mask matching: e.g. "4567XXXX8901" -> matches key "456711118901"
        # We can do this by matching the last 4 digits
        if len(cleaned) >= 4 and key.endswith(cleaned[-4:]):
            return val
        if len(cleaned) >= 9 and key.endswith(cleaned):
            return val
            
    return None

def get_statement(account_number: str, period: str):
    """Retrieves statement for a period"""
    account_period_db = statements_db.get(account_number)
    if not account_period_db:
        return None
        
    # Attempt fuzzy matching for period (e.g. "April 2026" or "Apr 2026" or "April")
    period_lower = period.lower()
    for key, val in account_period_db.items():
        if key.lower() in period_lower or period_lower in key.lower():
            return {"period": key, **val}
            
    # Default fallback to return April 2026 if period is roughly matching April
    if "apr" in period_lower:
        return {"period": "April 2026", **account_period_db.get("April 2026")}
        
    return None

def update_account_balance(account_number: str, new_balance: float):
    """Updates account balance (for testing and dashboard edits)"""
    account = get_account(account_number)
    if account:
        account["balance"] = new_balance
        return True
    return False

def add_mock_account(account_number: str, customer_name: str, balance: float, status: str = "ACTIVE"):
    """Inserts a new mock account or updates existing"""
    accounts_db[account_number] = {
        "account_number": account_number,
        "customer_name": customer_name,
        "balance": balance,
        "currency": "INR",
        "status": status
    }
    return True

def add_mock_card(card_number: str, cardholder_name: str, status: str = "ACTIVE", credit_limit: float = 100000.0, available_limit: float = 80000.0):
    """Inserts a new mock card"""
    cards_db[card_number] = {
        "card_number": card_number,
        "cardholder_name": cardholder_name,
        "status": status,
        "credit_limit": credit_limit,
        "available_limit": available_limit,
        "transactions": [
            {"date": "2026-05-24", "merchant": "Fuel Outlet", "amount": 2000.0, "type": "DEBIT"},
            {"date": "2026-05-21", "merchant": "Supermarket", "amount": 1450.0, "type": "DEBIT"}
        ]
    }
    return True
