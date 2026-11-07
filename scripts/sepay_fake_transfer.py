#!/usr/bin/env python3
"""Send a fake SePay "money in" webhook, as if the patient had transferred the money.

    python scripts/sepay_fake_transfer.py <payment_code> <amount> [--base URL] [--id N]

Uses `Authorization: Apikey $SEPAY_WEBHOOK_API_KEY` (default `dev-sepay-key`, the compose dev
value). Re-sending with the same --id replays the same bank transaction (it is ignored).
Standard library only.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

VN = timezone(timedelta(hours=7))


def build_payload(code: str, amount: int, transaction_id: int) -> dict:
    return {
        "id": transaction_id,
        "gateway": "OCB",
        "transactionDate": datetime.now(VN).strftime("%Y-%m-%d %H:%M:%S"),
        "accountNumber": os.getenv("SEPAY_ACCOUNT", "SEPNK33418"),
        "subAccount": None,
        "code": None,
        "content": f"{code} chuyen tien",
        "transferType": "in",
        "transferAmount": amount,
        "accumulated": 0,
        "referenceCode": f"FAKE{transaction_id}",
        "description": f"Fake transfer {code}",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("payment_code")
    parser.add_argument("amount", type=int)
    parser.add_argument("--base", default=os.getenv("PUBLIC_BASE_URL", "http://localhost:8080"))
    parser.add_argument("--id", type=int, default=None, help="SePay transaction id (default: now)")
    parser.add_argument("--key", default=os.getenv("SEPAY_WEBHOOK_API_KEY", "dev-sepay-key"))
    args = parser.parse_args()

    payload = build_payload(args.payment_code, args.amount, args.id or int(time.time() * 1000))
    request = urllib.request.Request(
        f"{args.base.rstrip('/')}/api/v1/payments/sepay-webhook",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Apikey {args.key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            print(response.status, response.read().decode())
            return 0
    except urllib.error.HTTPError as exc:
        print(exc.code, exc.read().decode(), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
