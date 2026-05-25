from fastapi import APIRouter, HTTPException
from models.schemas import (
    ValidateAccountRequest, ValidateAccountResponse,
    ValidateCardRequest, ValidateCardResponse,
    GetAccountBalanceRequest, GetAccountBalanceResponse,
    GetCardTransactionsRequest, GetCardTransactionsResponse,
    GetStatementRequest, GetStatementResponse
)
from utils import database
from utils.logger import log_api_call

router = APIRouter(prefix="/api/bank", tags=["Mock Banking APIs"])

@router.post("/validate-account", response_model=ValidateAccountResponse)
def validate_account(req: ValidateAccountRequest):
    acc = database.get_account(req.account_number)
    if acc:
        res = ValidateAccountResponse(status="VALID", customer_name=acc["customer_name"])
        log_api_call("ValidateAccountAPI", "/validate-account", req.dict(), res.dict(), 200)
        return res
    else:
        res = ValidateAccountResponse(status="INVALID", error="Account number not found in core system")
        log_api_call("ValidateAccountAPI", "/validate-account", req.dict(), res.dict(), 200)
        return res

@router.post("/validate-card", response_model=ValidateCardResponse)
def validate_card(req: ValidateCardRequest):
    card = database.get_card(req.card_number)
    if card:
        res = ValidateCardResponse(status="VALID", cardholder_name=card["cardholder_name"])
        log_api_call("ValidateCardAPI", "/validate-card", req.dict(), res.dict(), 200)
        return res
    else:
        res = ValidateCardResponse(status="INVALID", error="Credit card details are invalid or card not found")
        log_api_call("ValidateCardAPI", "/validate-card", req.dict(), res.dict(), 200)
        return res

@router.post("/account-balance", response_model=GetAccountBalanceResponse)
def get_account_balance(req: GetAccountBalanceRequest):
    acc = database.get_account(req.account_number)
    if acc:
        if acc["status"] != "ACTIVE":
            res = GetAccountBalanceResponse(
                status="FAILURE",
                account_number=req.account_number,
                customer_name=acc["customer_name"],
                balance=0.0,
                error=f"Account is suspended (Status: {acc['status']})"
            )
            log_api_call("GetAccountBalanceAPI", "/account-balance", req.dict(), res.dict(), 200)
            return res
            
        res = GetAccountBalanceResponse(
            status="SUCCESS",
            account_number=acc["account_number"],
            customer_name=acc["customer_name"],
            balance=acc["balance"],
            currency=acc["currency"]
        )
        log_api_call("GetAccountBalanceAPI", "/account-balance", req.dict(), res.dict(), 200)
        return res
    else:
        res = GetAccountBalanceResponse(
            status="FAILURE",
            account_number=req.account_number,
            customer_name="Unknown",
            balance=0.0,
            error="Account not found"
        )
        log_api_call("GetAccountBalanceAPI", "/account-balance", req.dict(), res.dict(), 404)
        raise HTTPException(status_code=404, detail="Account not found")

@router.post("/card-transactions", response_model=GetCardTransactionsResponse)
def get_card_transactions(req: GetCardTransactionsRequest):
    card = database.get_card(req.card_number)
    if card:
        if card["status"] != "ACTIVE":
            res = GetCardTransactionsResponse(
                status="FAILURE",
                card_number=req.card_number,
                cardholder_name=card["cardholder_name"],
                available_limit=0.0,
                credit_limit=0.0,
                transactions=[],
                error=f"Credit card is inactive or suspended (Status: {card['status']})"
            )
            log_api_call("GetCardTransactionsAPI", "/card-transactions", req.dict(), res.dict(), 200)
            return res
            
        # Limit the number of transactions returned based on limit parameter
        txs = card["transactions"][:req.limit]
        res = GetCardTransactionsResponse(
            status="SUCCESS",
            card_number=card["card_number"],
            cardholder_name=card["cardholder_name"],
            available_limit=card["available_limit"],
            credit_limit=card["credit_limit"],
            transactions=txs
        )
        log_api_call("GetCardTransactionsAPI", "/card-transactions", req.dict(), res.dict(), 200)
        return res
    else:
        res = GetCardTransactionsResponse(
            status="FAILURE",
            card_number=req.card_number,
            cardholder_name="Unknown",
            available_limit=0.0,
            credit_limit=0.0,
            transactions=[],
            error="Credit card not found"
        )
        log_api_call("GetCardTransactionsAPI", "/card-transactions", req.dict(), res.dict(), 404)
        raise HTTPException(status_code=404, detail="Credit card not found")

@router.post("/statement", response_model=GetStatementResponse)
def get_statement(req: GetStatementRequest):
    acc = database.get_account(req.account_number)
    if not acc:
        res = GetStatementResponse(
            status="FAILURE",
            account_number=req.account_number,
            period=req.period,
            error="Account not found"
        )
        log_api_call("GetStatementAPI", "/statement", req.dict(), res.dict(), 404)
        raise HTTPException(status_code=404, detail="Account not found")
        
    stmt = database.get_statement(req.account_number, req.period)
    if stmt:
        res = GetStatementResponse(
            status="SUCCESS",
            account_number=req.account_number,
            period=stmt["period"],
            filename=stmt["filename"],
            size=stmt["size"],
            download_url=stmt["download_url"]
        )
        log_api_call("GetStatementAPI", "/statement", req.dict(), res.dict(), 200)
        return res
    else:
        res = GetStatementResponse(
            status="FAILURE",
            account_number=req.account_number,
            period=req.period,
            error=f"No statement available for period '{req.period}'"
        )
        log_api_call("GetStatementAPI", "/statement", req.dict(), res.dict(), 200)
        return res
