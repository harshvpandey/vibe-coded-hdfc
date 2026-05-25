import os
import json
import logging
from datetime import datetime
from config import settings

# Configure standard logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(settings.AUDIT_LOG_FILE, encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("MailRoomAudit")

def mask_sensitive_data(text: str) -> str:
    """Masks credit card numbers and account numbers in logs to protect confidentiality"""
    if not text:
        return text
        
    import re
    # Mask credit cards (e.g. 13-16 digit numbers)
    # Match strings of 12-16 digits with potential spaces/dashes
    card_pattern = r'\b(?:\d[ -]*?){13,16}\b'
    def card_replacer(match):
        digits = match.group(0).replace(" ", "").replace("-", "")
        return f"{digits[:4]}XXXX{digits[-4:]}"
    
    # Mask account numbers (e.g. 10 digits)
    account_pattern = r'\b\d{10}\b'
    def account_replacer(match):
        digits = match.group(0)
        return f"XXXX{digits[-4:]}"
        
    text = re.sub(card_pattern, card_replacer, text)
    text = re.sub(account_pattern, account_replacer, text)
    return text

def log_agent_execution(agent_name: str, status: str, inputs: dict, outputs: dict):
    """Logs the input and output parameters of an agent run, with security masking"""
    timestamp = datetime.now().isoformat()
    
    masked_inputs = json.loads(mask_sensitive_data(json.dumps(inputs)))
    masked_outputs = json.loads(mask_sensitive_data(json.dumps(outputs)))
    
    log_entry = {
        "timestamp": timestamp,
        "type": "AGENT_EXECUTION",
        "agent": agent_name,
        "status": status,
        "inputs": masked_inputs,
        "outputs": masked_outputs
    }
    
    logger.info(f"Agent {agent_name} executed with status: {status}")
    # Write detailed JSON to audit log file in append mode
    try:
        with open(settings.AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to write to audit log: {str(e)}")

def log_api_call(api_name: str, endpoint: str, request_data: dict, response_data: dict, status_code: int):
    """Logs custom core banking API calls and decisions"""
    timestamp = datetime.now().isoformat()
    
    masked_req = json.loads(mask_sensitive_data(json.dumps(request_data)))
    masked_res = json.loads(mask_sensitive_data(json.dumps(response_data)))
    
    log_entry = {
        "timestamp": timestamp,
        "type": "API_CALL",
        "api": api_name,
        "endpoint": endpoint,
        "status_code": status_code,
        "request": masked_req,
        "response": masked_res
    }
    
    logger.info(f"API Call {api_name} ({endpoint}) status: {status_code}")
    try:
        with open(settings.AUDIT_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry) + "\n")
    except Exception as e:
        logger.error(f"Failed to write to audit log: {str(e)}")

def get_recent_audit_logs(limit: int = 50):
    """Reads recent logs from settings.AUDIT_LOG_FILE and returns them as a list of dicts"""
    logs = []
    if not os.path.exists(settings.AUDIT_LOG_FILE):
        return logs
        
    try:
        with open(settings.AUDIT_LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
            for line in lines[-limit:]:
                try:
                    logs.append(json.loads(line.strip()))
                except:
                    # Non-JSON line (standard logger output)
                    logs.append({"timestamp": datetime.now().isoformat(), "type": "SYSTEM", "message": line.strip()})
    except Exception as e:
        logger.error(f"Failed to read audit logs: {str(e)}")
        
    return logs
