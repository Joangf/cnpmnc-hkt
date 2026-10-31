from fastapi import FastAPI
from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

# Fine-grained buckets (5 ms -> 5 s) so p95/p99 are meaningful; the defaults are too coarse.
LATENCY_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.075,
    0.1,
    0.15,
    0.2,
    0.3,
    0.5,
    0.75,
    1.0,
    1.5,
    2.0,
    3.0,
    5.0,
)

BOOKINGS = Counter(
    "bookings_total",
    "Booking attempts by result",
    ["result"],  # confirmed | pending | rejected | conflict | unavailable | erp_unavailable
)
PAYMENTS = Counter("payments_total", "Payment status transitions", ["status"])
ERP_CALLS = Histogram(
    "erp_call_duration_seconds",
    "Latency of calls to the ERP/HIS adapter",
    ["operation", "outcome"],
    buckets=LATENCY_BUCKETS,
)
RECOMMENDATIONS = Counter(
    "specialty_recommendations_total", "Specialties suggested by the symptom checker", ["specialty"]
)


def setup_metrics(app: FastAPI) -> None:
    Instrumentator(excluded_handlers=["/metrics", "/healthz", "/readyz"]).instrument(
        app, latency_lowr_buckets=LATENCY_BUCKETS
    ).expose(app, endpoint="/metrics", include_in_schema=False)
