"""External integration adapters, kept separate from business logic (FRD recommendation 6).

Swap implementations here when a real ERP/HIS or payment gateway becomes available.
"""

from app.core.config import settings
from app.integrations.erp.base import ErpAdapter
from app.integrations.payment.base import PaymentGateway


def build_erp_adapter() -> ErpAdapter:
    if settings.erp_adapter == "memory":
        from app.integrations.erp.mock import InMemoryErpAdapter

        return InMemoryErpAdapter()
    from app.integrations.erp.http import HttpErpAdapter

    return HttpErpAdapter(settings.erp_base_url, settings.erp_timeout_seconds)


def build_payment_gateway() -> PaymentGateway:
    from app.integrations.payment.mock import MockPaymentGateway

    return MockPaymentGateway(
        settings.payment_base_url, settings.payment_webhook_secret, settings.payment_timeout_seconds
    )
