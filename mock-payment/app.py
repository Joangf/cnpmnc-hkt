"""Mock payment gateway - SANDBOX ONLY, no real money moves.

Flow: the platform creates a checkout -> the browser opens checkout_url -> the payer clicks
Pay / Decline -> a signed callback is POSTed to the platform -> the browser is redirected to
return_url. k6 can skip the browser step via POST /api/checkouts/{ref}/simulate.
"""

import asyncio
import hashlib
import hmac
import html
import json
import os
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

import httpx
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

PUBLIC_URL = os.getenv("MOCK_PAYMENT_PUBLIC_URL", "http://localhost:8080/mock-payment").rstrip("/")
SECRET = os.getenv("PAYMENT_WEBHOOK_SECRET", "payment-webhook-secret")

app = FastAPI(title="Mock Payment Gateway (sandbox)", version="0.1.0")

Outcome = Literal["success", "fail"]


class CheckoutIn(BaseModel):
    merchant_payment_id: str
    amount: Decimal
    currency: str
    description: str
    return_url: str
    callback_url: str


class Checkout(CheckoutIn):
    provider_reference: str
    status: Literal["OPEN", "SUCCEEDED", "FAILED", "REFUNDED"] = "OPEN"
    callback_status: int | None = None


class SimulateIn(BaseModel):
    outcome: Outcome = "success"


class RefundIn(BaseModel):
    provider_reference: str
    amount: Decimal


_checkouts: dict[str, Checkout] = {}
_lock = asyncio.Lock()


async def _send_callback(checkout: Checkout) -> int | None:
    payload = {
        "event_id": uuid.uuid4().hex,
        "provider_reference": checkout.provider_reference,
        "merchant_payment_id": checkout.merchant_payment_id,
        "status": checkout.status,
        "amount": str(checkout.amount),
        "currency": checkout.currency,
        "occurred_at": datetime.now(UTC).isoformat(),
        "failure_reason": "Card declined (sandbox)" if checkout.status == "FAILED" else None,
    }
    body = json.dumps(payload).encode()
    ts = str(int(time.time()))
    signature = hmac.new(SECRET.encode(), ts.encode() + b"." + body, hashlib.sha256).hexdigest()
    headers = {"content-type": "application/json", "x-mock-timestamp": ts, "x-mock-signature": signature}
    async with httpx.AsyncClient(timeout=5) as client:
        for attempt in range(3):
            try:
                response = await client.post(checkout.callback_url, content=body, headers=headers)
                return response.status_code
            except httpx.HTTPError:
                await asyncio.sleep(1 + attempt)
    return None


async def _complete(reference: str, outcome: Outcome) -> Checkout:
    async with _lock:
        checkout = _checkouts.get(reference)
        if checkout is None:
            raise HTTPException(404, "Checkout not found")
        if checkout.status != "OPEN":
            return checkout  # idempotent
        checkout.status = "SUCCEEDED" if outcome == "success" else "FAILED"
    checkout.callback_status = await _send_callback(checkout)
    return checkout


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@app.post("/api/checkouts", status_code=201)
async def create_checkout(data: CheckoutIn) -> dict:
    reference = f"MP-{uuid.uuid4().hex[:12].upper()}"
    _checkouts[reference] = Checkout(**data.model_dump(), provider_reference=reference)
    return {"provider_reference": reference, "checkout_url": f"{PUBLIC_URL}/checkout/{reference}"}


@app.post("/api/checkouts/{reference}/simulate")
async def simulate(reference: str, data: SimulateIn) -> dict:
    checkout = await _complete(reference, data.outcome)
    return {"status": checkout.status, "callback_status": checkout.callback_status}


@app.post("/api/refunds", status_code=201)
async def refund(data: RefundIn) -> dict:
    checkout = _checkouts.get(data.provider_reference)
    if checkout is None or checkout.status != "SUCCEEDED":
        raise HTTPException(409, "Payment cannot be refunded")
    if data.amount != checkout.amount:
        raise HTTPException(422, "Partial refunds are not supported in the sandbox")
    checkout.status = "REFUNDED"
    return {"refund_reference": f"RF-{uuid.uuid4().hex[:12].upper()}", "status": "REFUNDED"}


@app.get("/checkout/{reference}", response_class=HTMLResponse)
async def checkout_page(reference: str) -> str:
    checkout = _checkouts.get(reference)
    if checkout is None:
        raise HTTPException(404, "Checkout not found")
    amount = f"{checkout.amount:,.0f} {html.escape(checkout.currency)}"
    disabled = "" if checkout.status == "OPEN" else "disabled"
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sandbox checkout</title>
<style>
  body {{ font-family: system-ui, sans-serif; background: #f1f5f9; margin: 0; padding: 16px; }}
  .card {{ max-width: 420px; margin: 40px auto; background: #fff; border-radius: 12px; padding: 24px;
           box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
  .badge {{ display: inline-block; background: #fef3c7; color: #92400e; padding: 2px 8px; border-radius: 999px; font-size: 12px; }}
  .amount {{ font-size: 28px; font-weight: 700; margin: 12px 0; }}
  button {{ width: 100%; padding: 12px; border: 0; border-radius: 8px; font-size: 16px; margin-top: 8px; cursor: pointer; }}
  .pay {{ background: #0d9488; color: #fff; }} .fail {{ background: #e2e8f0; color: #0f172a; }}
  button:disabled {{ opacity: .5; cursor: not-allowed; }}
</style></head>
<body><div class="card">
  <span class="badge">SANDBOX - no real payment</span>
  <p>{html.escape(checkout.description)}</p>
  <div class="amount">{amount}</div>
  <p>Status: <strong>{checkout.status}</strong></p>
  <form method="post" action="./{reference}/complete">
    <button class="pay" name="outcome" value="success" {disabled}>Pay now</button>
    <button class="fail" name="outcome" value="fail" {disabled}>Simulate decline</button>
  </form>
</div></body></html>"""


@app.post("/checkout/{reference}/complete")
async def complete_from_page(reference: str, outcome: Outcome = Form(...)) -> RedirectResponse:
    checkout = await _complete(reference, outcome)
    return RedirectResponse(checkout.return_url, status_code=303)
