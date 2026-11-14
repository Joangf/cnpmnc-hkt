from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    env: str = "dev"
    service_name: str = "backend"
    log_level: str = "INFO"

    database_url: str = "postgresql+asyncpg://healthcare:healthcare@postgres:5432/healthcare"
    redis_url: str = "redis://redis:6379/0"

    # Auth (NFR-01, NFR-02)
    jwt_secret: str = "change-me-in-any-shared-environment"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    refresh_cookie_name: str = "refresh_token"
    cookie_secure: bool = False
    login_rate_limit: int = 10
    login_rate_window_seconds: int = 300
    password_reset_ttl_seconds: int = 900

    # Registration email verification (OTP) delivered through Resend
    resend_api_key: str = ""
    # Resend's shared sender only delivers to the Resend account owner's address; set a sender
    # on a verified domain to email arbitrary customers.
    email_from: str = "CareBook Hospital Booking <onboarding@resend.dev>"
    email_timeout_seconds: float = 10.0
    otp_ttl_seconds: int = 600
    otp_max_attempts: int = 5
    otp_resend_cooldown_seconds: int = 60

    # Scheduling (FRD 4.4.1, BR-05) - durations/buffers live on AppointmentType
    clinic_timezone: str = "Asia/Ho_Chi_Minh"
    slot_increment_minutes: int = 10
    booking_min_lead_minutes: int = 60
    booking_horizon_days: int = 14
    cancellation_cutoff_hours: int = 24
    availability_cache_seconds: int = 30
    pending_booking_expiry_minutes: int = 15

    # ERP/HIS integration (FRD 3.2, OQ-01/02)
    erp_adapter: str = "http"  # http | memory
    erp_base_url: str = "http://mock-erp:8100"
    erp_timeout_seconds: float = 5.0
    erp_webhook_secret: str = "erp-webhook-secret"
    schedule_sync_interval_seconds: int = 600
    reconcile_interval_seconds: int = 60
    run_background_jobs: bool = True

    # Payments: VietQR bank transfer to a SePay-monitored account (FRD 4.10, OQ-03/05/09).
    # Account values come from the environment (docker-compose / .env), never from code.
    sepay_account: str = ""  # receiving account / VA number shown on the QR
    sepay_bank: str = ""  # bank short name accepted by vietqr.app, e.g. "OCB"
    sepay_account_name: str = ""
    sepay_webhook_api_key: str = ""  # SePay webhook "API Key" auth; empty rejects every call
    sepay_api_token: str = ""  # SePay User API token; empty disables transaction polling
    sepay_api_base: str = "https://my.sepay.vn/userapi"
    sepay_poll_seconds: int = 15
    sepay_timeout_seconds: float = 10.0
    payment_code_prefix: str = "CB"
    payment_hold_minutes: int = 15  # unpaid confirmed appointments are released after this
    currency: str = "VND"

    webhook_tolerance_seconds: int = 300
    review_requires_approval: bool = False
    # Reasons a patient can pick when reporting a review (SCRUM-50); configurable per hospital.
    review_report_reasons: list[str] = [
        "Offensive or abusive language",
        "Personal or private information",
        "Spam or advertising",
        "Not about this doctor or visit",
        "False or misleading",
        "Other",
    ]
    emergency_number: str = "115"

    # AI symptom search and review summaries, through an OpenAI-compatible gateway (LiteLLM).
    # Empty base URL = AI off; every AI step then falls back to the rule-only behaviour.
    llm_base_url: str = ""
    llm_api_key: str = ""
    llm_model: str = "deepseek-v4-flash"
    llm_disable_thinking: bool = True  # reasoning tokens are paid for and not needed here
    llm_timeout_seconds: float = 30.0
    llm_daily_token_budget: int = 200_000  # chat tokens per clinic day; 0 = unlimited
    embedding_model: str = "embedding"  # dense, 1024 dims (bge-m3)
    rerank_model: str = "embedding-colbert"  # one vector per token, scored by MaxSim
    embedding_dims: int = 1024
    search_index_interval_seconds: int = 60
    # Retrieval: candidates per leg, RRF constant, relevance gate on the ColBERT score (0..1).
    # Calibrated on the seed catalog with bge-m3 ColBERT phrase coverage: symptoms the
    # user actually wrote score >= ~0.71, unrelated sentences <= ~0.61.
    ai_candidates_per_leg: int = 30
    ai_rrf_k: int = 60
    # A phrase passes the gate if every word of it is written in the text, or - for a
    # paraphrase - its average token match reaches ai_gate_min_score AND its weakest token
    # reaches ai_token_floor_score (one strong word is not enough: "child fever" vs "fever").
    ai_gate_min_score: float = 0.74
    ai_token_floor_score: float = 0.76
    # Best candidate under this = the text has nothing symptom-like; skip the paid rephrase.
    ai_rephrase_min_best_score: float = 0.45
    # A symptom found only through an LLM rephrasing must still relate to the user's own
    # words at least this much - the check that the rephrasing did not change the meaning.
    ai_rephrase_floor_score: float = 0.62
    ai_rephrase_variants: int = 3
    ai_max_symptoms: int = 6
    ai_requests_per_minute: int = 20  # per client IP, for each AI endpoint
    # Doctor ranking inside a recommended specialty (weights are relative).
    ai_doctors_per_specialty: int = 3
    ai_weight_relevance: float = 0.5
    ai_weight_rating: float = 0.3
    ai_weight_availability: float = 0.2
    ai_explanation_cache_seconds: int = 7 * 24 * 3600
    # Review summaries (SCRUM-46): minimum commented, published reviews before summarising.
    review_summary_min_reviews: int = 3
    review_summary_max_reviews: int = 40

    # Seed accounts (app/seed.py)
    admin_email: str = "admin@example.com"
    admin_password: str = "Admin12345!"
    demo_patient_email: str = "patient@example.com"
    demo_patient_password: str = "Patient12345!"
    loadtest_password: str = "LoadTest123!"

    @property
    def is_dev(self) -> bool:
        return self.env == "dev"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
