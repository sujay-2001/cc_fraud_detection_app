# otp_utils.py
import os, secrets, smtplib, redis, ssl, logging, traceback
from email.message import EmailMessage
from datetime import datetime, timezone
from pydantic import EmailStr

# ---------------- Redis ----------------
OTP_TTL        = int(os.getenv("OTP_TTL_SECONDS",      300))
VERIFY_WINDOW  = int(os.getenv("OTP_VERIFY_WINDOW",    900))
MAX_PER_HOUR   = int(os.getenv("OTP_MAX_PER_HOUR",       5))

r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                         decode_responses=True)
log = logging.getLogger(__name__)

# ---------------- SMTP -----------------
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "465"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)

# --------------------------------------------------------------------------
def generate_code() -> str:
    """Return a 6-digit zero-padded code as string."""
    return f"{secrets.randbelow(1_000_000):06}"

def send_code_email(to_addr: EmailStr, code: str) -> None:
    """Send a 6-digit OTP e-mail and log any SMTP failures with traceback."""

    msg = EmailMessage()
    msg["Subject"] = "Your verification code"
    msg["From"]    = SMTP_FROM
    msg["To"]      = to_addr
    msg.set_content(
        f"Hi!\n\nYour verification code is: {code}\n"
        f"It expires in {OTP_TTL // 60} minutes.\n\n"
        "If you didn't request this, just ignore this e-mail."
    )

    try:
        # ── choose SSL (port 465) or STARTTLS (port 587) ────────────────
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10, context=context) as s:
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)

    except Exception as exc:
        # 1️⃣  structured log (shows with log-level INFO if you keep default handler)
        log.exception("SMTP failure sending OTP to %s", to_addr)

        # 2️⃣  raw traceback to stderr (guaranteed to appear in container logs)
        traceback.print_exc()

        # 3️⃣  re-raise so FastAPI turns it into 500 or your caller can handle it
        raise

def send_welcome_email(to_addr: EmailStr, name: str) -> None:
    """Send a 6-digit OTP e-mail and log any SMTP failures with traceback."""

    msg = EmailMessage()
    msg["Subject"] = "Welcome to Fraud Lens!"
    msg["From"]    = SMTP_FROM
    msg["To"]      = to_addr
    plain = (
        f"Hi {name},\n\n"
        "🎉 Welcome aboard! Your account is now active and you can sign in right away.\n\n"
        "If you have any questions, just hit reply.\n\n"
        "Cheers,\nThe Fraud Lens Team"
    )
    msg.set_content(plain)

    try:
        # ── choose SSL (port 465) or STARTTLS (port 587) ────────────────
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=10, context=context) as s:
            s.login(SMTP_USER, SMTP_PASS)
            s.send_message(msg)

    except Exception as exc:
        # 1️⃣  structured log (shows with log-level INFO if you keep default handler)
        log.exception("SMTP failure sending OTP to %s", to_addr)

        # 2️⃣  raw traceback to stderr (guaranteed to appear in container logs)
        traceback.print_exc()

        # 3️⃣  re-raise so FastAPI turns it into 500 or your caller can handle it
        raise
# --------------------------------------------------------------------------
def hour_bucket() -> str:
    now = datetime.now(timezone.utc)
    return now.strftime("%Y%m%d%H")        # e.g. 2025043013

def can_request(email: str) -> bool:
    count_key = f"otp-req:{email}:{hour_bucket()}"
    req = r.incr(count_key)
    if req == 1:
        r.expire(count_key, 3600)
    return req <= MAX_PER_HOUR

def remember_code(email: str, code: str) -> None:
    r.setex(f"otp:{email}", OTP_TTL, code)

def consume_code(email: str, code: str) -> bool:
    key = f"otp:{email}"
    stored = r.get(key)
    if stored and stored == code:
        r.delete(key)
        r.setex(f"otp-ok:{email}", VERIFY_WINDOW, 1)   # mark verified
        return True
    return False

def is_verified(email: str) -> bool:
    return bool(r.get(f"otp-ok:{email}"))
