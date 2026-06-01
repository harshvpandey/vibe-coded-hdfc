# SQLAlchemy Relational Database Backend representing Core Banking Systems
import json
import datetime
from sqlalchemy import create_engine, Column, String, Float, Integer, ForeignKey, Text, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from config import settings

# Create local SQLite engine
engine = create_engine(
    settings.DATABASE_URL, 
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# --- SQL DATABASE TABLES DEFINITIONS ---

class DbAccount(Base):
    __tablename__ = 'accounts'
    account_number = Column(String, primary_key=True)
    customer_name = Column(String, nullable=False)
    balance = Column(Float, default=0.0)
    currency = Column(String, default='INR')
    status = Column(String, default='ACTIVE')

class DbCard(Base):
    __tablename__ = 'cards'
    card_number = Column(String, primary_key=True)
    cardholder_name = Column(String, nullable=False)
    status = Column(String, default='ACTIVE')
    credit_limit = Column(Float, default=100000.0)
    available_limit = Column(Float, default=80000.0)

class DbCardTransaction(Base):
    __tablename__ = 'card_transactions'
    id = Column(Integer, primary_key=True, autoincrement=True)
    card_number = Column(String, ForeignKey('cards.card_number'), index=True)
    date = Column(String, nullable=False)
    merchant = Column(String, nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String, default='DEBIT')

class DbStatement(Base):
    __tablename__ = 'statements'
    id = Column(Integer, primary_key=True, autoincrement=True)
    account_number = Column(String, ForeignKey('accounts.account_number'), index=True)
    period = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    size = Column(String, nullable=False)
    download_url = Column(String, nullable=False)

class DbEmail(Base):
    __tablename__ = 'emails'
    id = Column(String, primary_key=True)
    sender = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    status = Column(String, default='PENDING_REVIEW')
    confidence_score = Column(Float, default=0.0)
    draft_response = Column(Text)
    received_at = Column(String)
    intents_json = Column(Text) # JSON string list
    sentiment = Column(String, default='NEUTRAL')
    entities_json = Column(Text) # JSON string dict
    validation_results_json = Column(Text) # JSON string dict
    api_responses_json = Column(Text) # JSON string dict
    agent_logs_json = Column(Text) # JSON string list

# --- CONVERTER UTILITIES ---

def db_account_to_dict(acc):
    if not acc: return None
    return {
        "account_number": acc.account_number,
        "customer_name": acc.customer_name,
        "balance": acc.balance,
        "currency": acc.currency,
        "status": acc.status
    }

def db_card_to_dict(card, txs=None):
    if not card: return None
    transactions_list = []
    if txs:
        for tx in txs:
            transactions_list.append({
                "date": tx.date,
                "merchant": tx.merchant,
                "amount": tx.amount,
                "type": tx.type
            })
    return {
        "card_number": card.card_number,
        "cardholder_name": card.cardholder_name,
        "status": card.status,
        "credit_limit": card.credit_limit,
        "available_limit": card.available_limit,
        "transactions": transactions_list
    }

def db_email_to_dict(mail):
    if not mail: return None
    return {
        "id": mail.id,
        "sender": mail.sender,
        "subject": mail.subject,
        "body": mail.body,
        "status": mail.status,
        "confidence_score": mail.confidence_score,
        "draft_response": mail.draft_response,
        "received_at": mail.received_at,
        "intents": json.loads(mail.intents_json or "[]"),
        "sentiment": mail.sentiment,
        "entities": json.loads(mail.entities_json or "{}"),
        "validation_results": json.loads(mail.validation_results_json or "{}"),
        "api_responses": json.loads(mail.api_responses_json or "{}"),
        "agent_logs": json.loads(mail.agent_logs_json or "[]")
    }

# --- BACKWARD COMPATIBLE DICT PROXIES ---

class AccountsDbProxy(dict):
    def items(self):
        with SessionLocal() as session:
            accounts = session.query(DbAccount).all()
            return [(a.account_number, db_account_to_dict(a)) for a in accounts]
            
    def keys(self):
        with SessionLocal() as session:
            accounts = session.query(DbAccount).all()
            return [a.account_number for a in accounts]
            
    def __getitem__(self, key):
        with SessionLocal() as session:
            a = session.query(DbAccount).filter(DbAccount.account_number == str(key)).first()
            if a: return db_account_to_dict(a)
            raise KeyError(key)

    def values(self):
        with SessionLocal() as session:
            accounts = session.query(DbAccount).all()
            return [db_account_to_dict(a) for a in accounts]
            
    def __len__(self):
        with SessionLocal() as session:
            return session.query(DbAccount).count()

class CardsDbProxy(dict):
    def items(self):
        with SessionLocal() as session:
            cards = session.query(DbCard).all()
            return [(c.card_number, db_card_to_dict(c, session.query(DbCardTransaction).filter(DbCardTransaction.card_number == c.card_number).all())) for c in cards]
            
    def keys(self):
        with SessionLocal() as session:
            cards = session.query(DbCard).all()
            return [c.card_number for c in cards]
            
    def __getitem__(self, key):
        with SessionLocal() as session:
            c = session.query(DbCard).filter(DbCard.card_number == str(key)).first()
            if c:
                txs = session.query(DbCardTransaction).filter(DbCardTransaction.card_number == c.card_number).all()
                return db_card_to_dict(c, txs)
            raise KeyError(key)

    def values(self):
        with SessionLocal() as session:
            cards = session.query(DbCard).all()
            result = []
            for c in cards:
                txs = session.query(DbCardTransaction).filter(DbCardTransaction.card_number == c.card_number).all()
                result.append(db_card_to_dict(c, txs))
            return result
            
    def __len__(self):
        with SessionLocal() as session:
            return session.query(DbCard).count()

# Instantiate global proxies to maintain full API contract compatibility
accounts_db = AccountsDbProxy()
cards_db = CardsDbProxy()

# --- DATABASE HELPER FUNCTIONS ---

def get_account(account_number: str):
    """Retrieves account if exists, cleans up spaces"""
    if not account_number:
        return None
    cleaned = str(account_number).strip()
    with SessionLocal() as session:
        acc = session.query(DbAccount).filter(DbAccount.account_number == cleaned).first()
        return db_account_to_dict(acc)

def get_card(card_number: str):
    """Retrieves credit card if exists, handles card matching by ending digits"""
    if not card_number:
        return None
    cleaned = str(card_number).replace(" ", "").replace("-", "").strip()
    
    with SessionLocal() as session:
        # Try exact match first
        card = session.query(DbCard).filter(DbCard.card_number == cleaned).first()
        if card:
            txs = session.query(DbCardTransaction).filter(DbCardTransaction.card_number == card.card_number).all()
            return db_card_to_dict(card, txs)
        
        # Try ending match (suffix matching)
        all_cards = session.query(DbCard).all()
        for c in all_cards:
            if len(cleaned) >= 4 and c.card_number.endswith(cleaned[-4:]):
                txs = session.query(DbCardTransaction).filter(DbCardTransaction.card_number == c.card_number).all()
                return db_card_to_dict(c, txs)
            if len(cleaned) >= 9 and c.card_number.endswith(cleaned):
                txs = session.query(DbCardTransaction).filter(DbCardTransaction.card_number == c.card_number).all()
                return db_card_to_dict(c, txs)
                
    return None

def get_statement(account_number: str, period: str):
    """Retrieves statement for a period"""
    if not account_number or not period:
        return None
    
    with SessionLocal() as session:
        statements = session.query(DbStatement).filter(DbStatement.account_number == str(account_number)).all()
        if not statements:
            return None
            
        period_lower = period.lower()
        for stmt in statements:
            if stmt.period.lower() in period_lower or period_lower in stmt.period.lower():
                return {
                    "period": stmt.period,
                    "filename": stmt.filename,
                    "size": stmt.size,
                    "download_url": stmt.download_url
                }
                
        # Default fallback
        if "apr" in period_lower:
            apr_stmt = session.query(DbStatement).filter(DbStatement.account_number == str(account_number), DbStatement.period == "April 2026").first()
            if apr_stmt:
                return {
                    "period": apr_stmt.period,
                    "filename": apr_stmt.filename,
                    "size": apr_stmt.size,
                    "download_url": apr_stmt.download_url
                }
                
    return None

def update_account_balance(account_number: str, new_balance: float):
    """Updates account balance (for testing and dashboard edits)"""
    with SessionLocal() as session:
        acc = session.query(DbAccount).filter(DbAccount.account_number == str(account_number)).first()
        if acc:
            acc.balance = new_balance
            session.commit()
            return True
    return False

def add_mock_account(account_number: str, customer_name: str, balance: float, status: str = "ACTIVE"):
    """Inserts a new mock account or updates existing"""
    with SessionLocal() as session:
        acc = session.query(DbAccount).filter(DbAccount.account_number == str(account_number)).first()
        if acc:
            acc.customer_name = customer_name
            acc.balance = balance
            acc.status = status
        else:
            acc = DbAccount(
                account_number=str(account_number),
                customer_name=customer_name,
                balance=balance,
                status=status
            )
            session.add(acc)
        session.commit()
    return True

def add_mock_card(card_number: str, cardholder_name: str, status: str = "ACTIVE", credit_limit: float = 100000.0, available_limit: float = 80000.0):
    """Inserts a new mock card"""
    with SessionLocal() as session:
        card = session.query(DbCard).filter(DbCard.card_number == str(card_number)).first()
        if card:
            card.cardholder_name = cardholder_name
            card.status = status
            card.credit_limit = credit_limit
            card.available_limit = available_limit
        else:
            card = DbCard(
                card_number=str(card_number),
                cardholder_name=cardholder_name,
                status=status,
                credit_limit=credit_limit,
                available_limit=available_limit
            )
            session.add(card)
            
            # Seed default transactions for new cards
            tx1 = DbCardTransaction(card_number=card.card_number, date="2026-05-24", merchant="Fuel Outlet", amount=2000.0, type="DEBIT")
            tx2 = DbCardTransaction(card_number=card.card_number, date="2026-05-21", merchant="Supermarket", amount=1450.0, type="DEBIT")
            session.add_all([tx1, tx2])
            
        session.commit()
    return True

# --- EMAIL QUEUE MANAGEMENT ---

def get_all_emails():
    """Retrieve all queued emails sorted by received_at descending"""
    with SessionLocal() as session:
        emails = session.query(DbEmail).all()
        result = [db_email_to_dict(e) for e in emails]
        return sorted(result, key=lambda x: x.get("received_at", ""), reverse=True)

def get_email(email_id: str):
    """Retrieve an email from the queue by ID"""
    with SessionLocal() as session:
        email_item = session.query(DbEmail).filter(DbEmail.id == email_id).first()
        return db_email_to_dict(email_item)

def add_email_to_db(email_id: str, sender: str, subject: str, body: str, status: str, 
                    confidence_score: float, draft_response: str, intents: list, sentiment: str,
                    entities: dict = None, validation_results: dict = None, api_responses: dict = None, agent_logs: list = None):
    """Adds a new processed email to our queue database"""
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    with SessionLocal() as session:
        email_item = session.query(DbEmail).filter(DbEmail.id == email_id).first()
        if email_item:
            # Update in place if exists
            email_item.sender = sender
            email_item.subject = subject
            email_item.body = body
            email_item.status = status
            email_item.confidence_score = confidence_score
            email_item.draft_response = draft_response
            email_item.intents_json = json.dumps(intents or ["UNKNOWN"])
            email_item.sentiment = sentiment or "NEUTRAL"
            email_item.entities_json = json.dumps(entities or {})
            email_item.validation_results_json = json.dumps(validation_results or {})
            email_item.api_responses_json = json.dumps(api_responses or {})
            email_item.agent_logs_json = json.dumps(agent_logs or [])
        else:
            email_item = DbEmail(
                id=email_id,
                sender=sender,
                subject=subject,
                body=body,
                status=status,
                confidence_score=confidence_score,
                draft_response=draft_response,
                received_at=now_str,
                intents_json=json.dumps(intents or ["UNKNOWN"]),
                sentiment=sentiment or "NEUTRAL",
                entities_json=json.dumps(entities or {}),
                validation_results_json=json.dumps(validation_results or {}),
                api_responses_json=json.dumps(api_responses or {}),
                agent_logs_json=json.dumps(agent_logs or [])
            )
            session.add(email_item)
        session.commit()
        return db_email_to_dict(email_item)

def update_email_status(email_id: str, status: str, response_body: str = None):
    """Updates an email status and optionally updates the response draft"""
    with SessionLocal() as session:
        email_item = session.query(DbEmail).filter(DbEmail.id == email_id).first()
        if email_item:
            email_item.status = status
            if response_body is not None:
                email_item.draft_response = response_body
            session.commit()
            return True
    return False

# --- SEEDING & SEMANTIC VIEW INITIALIZATION ---

def initialize_db():
    """Builds schemas, constructs SQLite read-only semantic views, and seeds historical datasets"""
    # 1. Create table tables
    Base.metadata.create_all(bind=engine)
    
    # 2. Build semantic view definitions
    with engine.connect() as conn:
        conn.execute(text("CREATE VIEW IF NOT EXISTS customer_accounts_view AS SELECT account_number, customer_name, balance, currency, status FROM accounts;"))
        conn.execute(text("CREATE VIEW IF NOT EXISTS customer_transactions_view AS SELECT card_number, date, merchant, amount, type FROM card_transactions;"))
        conn.execute(text("CREATE VIEW IF NOT EXISTS customer_statements_view AS SELECT account_number, period, filename, size, download_url FROM statements;"))
        conn.commit()
        
    # 3. Seed baseline datasets if empty
    with SessionLocal() as session:
        if session.query(DbAccount).count() == 0:
            # Seed Accounts
            a1 = DbAccount(account_number="1234567890", customer_name="John Doe", balance=125000.0, currency="INR", status="ACTIVE")
            a2 = DbAccount(account_number="9876543210", customer_name="Jane Smith", balance=450000.0, currency="INR", status="ACTIVE")
            a3 = DbAccount(account_number="5555555555", customer_name="Robert Miller", balance=12500.5, currency="INR", status="SUSPENDED")
            session.add_all([a1, a2, a3])
            
            # Seed Cards
            c1 = DbCard(card_number="456711118901", cardholder_name="John Doe", status="ACTIVE", credit_limit=200000.0, available_limit=142051.0)
            c2 = DbCard(card_number="987654321000", cardholder_name="Jane Smith", status="ACTIVE", credit_limit=500000.0, available_limit=493871.0)
            c3 = DbCard(card_number="987654321", cardholder_name="John Doe", status="ACTIVE", credit_limit=100000.0, available_limit=82000.0)
            session.add_all([c1, c2, c3])
            
            # Seed Card Transactions
            txs = [
                DbCardTransaction(card_number="456711118901", date="2026-05-22", merchant="HDFC Auto Pay", amount=15000.0, type="DEBIT"),
                DbCardTransaction(card_number="456711118901", date="2026-05-20", merchant="Uber India", amount=350.0, type="DEBIT"),
                DbCardTransaction(card_number="456711118901", date="2026-05-15", merchant="Netflix India", amount=649.0, type="DEBIT"),
                DbCardTransaction(card_number="456711118901", date="2026-05-12", merchant="Swiggy", amount=450.0, type="DEBIT"),
                DbCardTransaction(card_number="456711118901", date="2026-05-10", merchant="Amazon India", amount=1500.0, type="DEBIT"),
                
                DbCardTransaction(card_number="987654321000", date="2026-05-14", merchant="Zara Mumbai", amount=4999.0, type="DEBIT"),
                DbCardTransaction(card_number="987654321000", date="2026-05-11", merchant="Zomato", amount=850.0, type="DEBIT"),
                DbCardTransaction(card_number="987654321000", date="2026-05-08", merchant="Starbucks Coffee", amount=280.0, type="DEBIT"),
                
                DbCardTransaction(card_number="987654321", date="2026-05-23", merchant="Croma Digital", amount=12000.0, type="DEBIT"),
                DbCardTransaction(card_number="987654321", date="2026-05-18", merchant="Flipkart", amount=3500.0, type="DEBIT"),
                DbCardTransaction(card_number="987654321", date="2026-05-15", merchant="MakeMyTrip", amount=2500.0, type="DEBIT")
            ]
            session.add_all(txs)
            
            # Seed Statements
            s1 = DbStatement(account_number="1234567890", period="April 2026", filename="Statement_1234567890_Apr26.pdf", size="142 KB", download_url="https://api.hdfc.com/statements/download/1234567890_Apr26.pdf")
            s2 = DbStatement(account_number="1234567890", period="March 2026", filename="Statement_1234567890_Mar26.pdf", size="138 KB", download_url="https://api.hdfc.com/statements/download/1234567890_Mar26.pdf")
            s3 = DbStatement(account_number="9876543210", period="April 2026", filename="Statement_9876543210_Apr26.pdf", size="212 KB", download_url="https://api.hdfc.com/statements/download/9876543210_Apr26.pdf")
            s4 = DbStatement(account_number="9876543210", period="May 2026", filename="Statement_9876543210_May26.pdf", size="225 KB", download_url="https://api.hdfc.com/statements/download/9876543210_May26.pdf")
            session.add_all([s1, s2, s3, s4])
            
            # Seed simulated inbox queue items
            e1 = DbEmail(
                id="sim_01",
                sender="aman.singh@gmail.com",
                subject="Urgent check savings balance",
                body="Please provide my savings account balance for account number 1234567890. I need to make an immediate transfer.",
                status="AUTO_SENT",
                confidence_score=0.98,
                draft_response="Dear Aman Singh,\n\nThank you for writing to HDFC Bank.\n\nRegarding your request, the available balance for your savings account ending in XXXX7890 is INR 125,000.00.\n\nIf you have any further questions, please do not hesitate to contact us.\n\nWarm regards,\nCustomer Support Team, HDFC Bank",
                received_at="2026-05-30 11:45",
                intents_json=json.dumps(["ACCOUNT_BALANCE"]),
                sentiment="NEGATIVE/URGENT",
                entities_json=json.dumps({"account_number": "1234567890", "customer_name": "Aman Singh"}),
                validation_results_json=json.dumps({"account_validated": True, "customer_name": "John Doe"}),
                api_responses_json=json.dumps({"GetAccountBalanceAPI": {"status": "SUCCESS", "account_number": "1234567890", "customer_name": "John Doe", "balance": 125000.00, "currency": "INR"}}),
                agent_logs_json=json.dumps([])
            )
            
            e2 = DbEmail(
                id="sim_02",
                sender="robert.miller@gmail.com",
                subject="Statement and Card history",
                body="Please send me statement for April 2026 and also share transactions for card 999999999.",
                status="PENDING_REVIEW",
                confidence_score=0.78,
                draft_response="Dear Robert Miller,\n\nThank you for writing to HDFC Bank.\n\nRegarding your credit card query, the credit card ending in 999999999 could not be validated in our systems. Please double check the card number.\n\nFor your account statement, our records indicate account validation failed. Please check your account number.\n\nIf you have further questions, please let us know.\n\nWarm regards,\nCustomer Support Team, HDFC Bank",
                received_at="2026-05-30 12:05",
                intents_json=json.dumps(["STATEMENT_REQUEST", "CARD_TRANSACTIONS"]),
                sentiment="NEUTRAL",
                entities_json=json.dumps({"card_number": "999999999", "statement_period": "April 2026"}),
                validation_results_json=json.dumps({"account_validated": False, "card_validated": False}),
                api_responses_json=json.dumps({}),
                agent_logs_json=json.dumps([])
            )
            
            e3 = DbEmail(
                id="sim_03",
                sender="priya.sharma@yahoo.com",
                subject="HDFC Home Loan Query",
                body="I want to apply for a home loan of 50 Lakhs. Can someone call me or share the latest interest rates? My contact is +91-9876543210.",
                status="PENDING_REVIEW",
                confidence_score=0.45,
                draft_response="Dear Priya Sharma,\n\nThank you for writing to HDFC Bank.\n\nWe have received your query regarding HDFC Home Loan applications. Please note that this automated mailbox currently only supports queries regarding Account Balance, Card Transactions, and E-Statement requests. We have queued your loan query for our human relationship managers to contact you on +91-9876543210 shortly.\n\nWarm regards,\nCustomer Support Team, HDFC Bank",
                received_at="2026-05-30 12:15",
                intents_json=json.dumps(["UNKNOWN"]),
                sentiment="NEUTRAL",
                entities_json=json.dumps({}),
                validation_results_json=json.dumps({}),
                api_responses_json=json.dumps({}),
                agent_logs_json=json.dumps([])
            )
            session.add_all([e1, e2, e3])
            
        session.commit()
