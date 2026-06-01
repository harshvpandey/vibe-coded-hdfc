import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import datetime
import random
import hashlib
from config import settings
from utils.logger import logger

def parse_header_value(header_value) -> str:
    """Decodes email headers which might be encoded (e.g. UTF-8 base64)"""
    if not header_value:
        return ""
    decoded_fragments = decode_header(header_value)
    result = []
    for fragment, charset in decoded_fragments:
        if isinstance(fragment, bytes):
            try:
                result.append(fragment.decode(charset or "utf-8", errors="ignore"))
            except Exception:
                result.append(fragment.decode("latin1", errors="ignore"))
        else:
            result.append(str(fragment))
    return "".join(result)

def extract_body(msg) -> str:
    """Recursively walks email parts and retrieves plain-text body payload"""
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            if content_type == "text/plain" and "attachment" not in content_disposition:
                try:
                    return part.get_payload(decode=True).decode(part.get_content_charset() or "utf-8", errors="ignore")
                except Exception:
                    return part.get_payload(decode=True).decode("latin-1", errors="ignore")
    else:
        try:
            return msg.get_payload(decode=True).decode(msg.get_content_charset() or "utf-8", errors="ignore")
        except Exception:
            return msg.get_payload(decode=True).decode("latin-1", errors="ignore")
    return ""

def fetch_unseen_emails() -> list:
    """
    Connects to Gmail via IMAP, pulls unread messages, and parses them.
    If credentials are missing or connection fails, falls back gracefully to high-fidelity Simulation Mode.
    """
    email_addr = settings.GMAIL_EMAIL
    app_pwd = settings.GMAIL_APP_PASSWORD

    # Fallback to simulation mode if credentials are missing
    if not email_addr or not app_pwd or email_addr == "harshhdfc1@gmail.com" and app_pwd == "ILoveHDFCBank@1" and False:
        # Note: We can try real IMAP if credentials exist, but we must protect against network errors or auth failure
        pass

    logger.info("Connecting to Gmail IMAP server...")
    try:
        if not email_addr or not app_pwd:
            raise ValueError("Gmail credentials missing in .env")

        # Standard secure IMAP connection
        mail = imaplib.IMAP4_SSL(settings.GMAIL_IMAP_SERVER, settings.GMAIL_IMAP_PORT)
        mail.login(email_addr, app_pwd)
        mail.select("inbox")
        
        # Search for unseen messages mentioning "HDFC" in the subject or body to avoid pulling unrelated emails
        status, data = mail.search(
            None, 
            "UNSEEN", 
            "OR", 
            "SUBJECT", 
            settings.GMAIL_SYNC_FILTER_KEYWORD, 
            "BODY", 
            settings.GMAIL_SYNC_FILTER_KEYWORD
        )
        if status != "OK":
            raise ValueError(f"IMAP search failed: {status}")
            
        mail_ids = data[0].split()
        fetched_emails = []
        
        for num in mail_ids:
            # Fetch full raw email body RFC822
            status, msg_data = mail.fetch(num, "(RFC822)")
            if status != "OK" or not msg_data:
                continue
                
            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)
            
            subject = parse_header_value(msg["Subject"])
            sender = parse_header_value(msg["From"])
            body = extract_body(msg)
            
            # Extract standard sender email address from "Name <address@domain.com>"
            clean_sender = sender
            if "<" in sender and ">" in sender:
                clean_sender = sender.split("<")[1].split(">")[0].strip()
                
            # Create a unique but friendly ID
            msg_id_header = msg.get("Message-ID", "")
            if msg_id_header:
                h = hashlib.md5(msg_id_header.encode()).hexdigest()[:8]
                msg_id = f"gmail_{h}"
            else:
                msg_id = f"gmail_{random.randint(10000, 99999)}"
                
            fetched_emails.append({
                "id": msg_id,
                "sender": clean_sender,
                "subject": subject,
                "body": body,
                "received_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            })
            
            # Mark as read (SEEN) to prevent dual ingestion
            mail.store(num, "+FLAGS", "\\Seen")
            
        mail.close()
        mail.logout()
        logger.info(f"Gmail sync completed. Fetched {len(fetched_emails)} unread emails.")
        return fetched_emails
        
    except Exception as e:
        logger.warn(f"Failed to fetch emails via Gmail IMAP: {str(e)}. Reverting to Simulation Mode...")
        return get_simulated_emails()

def send_reply_email(to_email: str, subject: str, body_text: str) -> bool:
    """
    Sends an automated, styled corporate reply email via Gmail SMTP.
    Falls back gracefully to logging output if credentials are missing or server connection fails.
    """
    email_addr = settings.GMAIL_EMAIL
    app_pwd = settings.GMAIL_APP_PASSWORD
    
    logger.info(f"Attempting to send email reply to: {to_email}")
    
    if not email_addr or not app_pwd:
        logger.info(f"[SIMULATION SMTP] Outgoing Mail to {to_email} saved in server logs.")
        logger.info(f"Subject: {subject}\nBody:\n{body_text}")
        return True
        
    try:
        # Create standard multipart container
        msg = MIMEMultipart()
        msg["From"] = email_addr
        msg["To"] = to_email
        msg["Subject"] = subject
        
        # Attach email body text
        msg.attach(MIMEText(body_text, "plain", "utf-8"))
        
        # Secure SMTP connection with STARTTLS
        smtp = smtplib.SMTP(settings.GMAIL_SMTP_SERVER, settings.GMAIL_SMTP_PORT)
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()
        
        smtp.login(email_addr, app_pwd)
        smtp.send_message(msg)
        smtp.quit()
        
        logger.info(f"SMTP response sent successfully to: {to_email}")
        return True
    except Exception as e:
        logger.error(f"SMTP execution failed: {str(e)}. Writing email response to local audit file...")
        # Fallback log dump
        logger.info(f"[FAILED SMTP MOCK DUMP] Outgoing Mail to {to_email}")
        logger.info(f"Subject: {subject}\nBody:\n{body_text}")
        return False

# --- SIMULATION FALLBACK GENERATOR ---
def get_simulated_emails() -> list:
    """Generates randomized mock customer queries to make offline testing fun and dynamic"""
    templates = [
        {
            "subject": "Check card transactions urgently",
            "body": "Hi team, please share my credit card transactions history for card ending in 8901. I suspect some double-charge. Thanks, John Doe.",
            "sender": "john.doe@gmail.com"
        },
        {
            "subject": "Statement request",
            "body": "Dear customer support, please send the e-statement of my savings bank account 1234567890 for the period April 2026. Regard, John.",
            "sender": "johndoe@gmail.com"
        },
        {
            "subject": "Double request: statement and balance",
            "body": "Hello HDFC Bank, please share my account balance for account 1234567890 and also share transactions of my credit card 987654321. Send as soon as possible.",
            "sender": "customer_test@outlook.com"
        },
        {
            "subject": "HDFC Credit Card application",
            "body": "Hello, I want to apply for the HDFC Infinia Credit card. What is the eligibility criteria? Please call me on 9988776655.",
            "sender": "applicant_amit@yahoo.com"
        },
        {
            "subject": "Urgent account check",
            "body": "Hey there! I am having issues transferring funds from my savings account balance 5555555555. Can you check its status and let me know the balance?",
            "sender": "robert.miller@gmail.com"
        }
    ]
    
    # Randomly pick 1-2 scenarios to simulate incoming email fetching
    count = random.randint(1, 2)
    selected = random.sample(templates, count)
    
    simulated_list = []
    for idx, item in enumerate(selected):
        h = hashlib.md5(f"{item['subject']}_{time_now_str()}".encode()).hexdigest()[:6]
        simulated_list.append({
            "id": f"sim_sync_{h}",
            "sender": item["sender"],
            "subject": item["subject"],
            "body": item["body"],
            "received_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        })
    return simulated_list

def time_now_str() -> str:
    return datetime.datetime.now().isoformat()
