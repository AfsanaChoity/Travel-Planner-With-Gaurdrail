import hashlib
import hmac
import time
from typing import Tuple


def generate_signature(payload: str, timestamp: float, secret_key: str) -> str:
    """
    Generates an HMAC-SHA256 signature for a given payload and timestamp.
    
    Format: payload + ":" + timestamp
    """
    message = f"{payload}:{timestamp}".encode("utf-8")
    return hmac.new(secret_key.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_signature(
    payload: str,
    signature: str,
    timestamp: float,
    secret_key: str,
    max_age_seconds: int = 300,
) -> Tuple[bool, str]:
    """
    Verifies the HMAC-SHA256 signature and checks for replay attacks.

    Returns:
        (is_valid: bool, reason: str)
    """
    if not signature:
        return False, "Missing request signature."

    if not timestamp:
        return False, "Missing request timestamp."

    if not secret_key:
        return False, "Server HMAC secret key is not configured."

    # 1. Replay attack check: verify timestamp freshness
    current_time = time.time()
    time_diff = abs(current_time - timestamp)

    if time_diff > max_age_seconds:
        return False, f"Request expired (timestamp skew: {int(time_diff)}s, allowed: {max_age_seconds}s). Possible replay attack."

    # 2. Cryptographic signature check
    expected_signature = generate_signature(payload, timestamp, secret_key)

    # Use constant-time comparison to prevent timing attacks
    if not hmac.compare_digest(expected_signature, signature):
        return False, "Invalid HMAC signature: payload has been tampered with or key is invalid."

    return True, "Signature verified successfully."
