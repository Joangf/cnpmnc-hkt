"""External integration adapters, kept separate from business logic (FRD recommendation 6).

Swap implementations here when a real ERP/HIS becomes available. Payments: services/sepay.py.
"""

from app.core.config import settings
from app.integrations.erp.base import ErpAdapter


def build_erp_adapter() -> ErpAdapter:
    if settings.erp_adapter == "memory":
        from app.integrations.erp.mock import InMemoryErpAdapter

        return InMemoryErpAdapter()
    from app.integrations.erp.http import HttpErpAdapter

    return HttpErpAdapter(settings.erp_base_url, settings.erp_timeout_seconds)
