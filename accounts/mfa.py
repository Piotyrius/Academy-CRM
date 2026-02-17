"""
Helpers for Time-based One-Time Password (TOTP) MFA.

We keep this small and dependency-light; `pyotp` handles the core math.
"""
import pyotp


def generate_mfa_secret() -> str:
    """Generate a new base32 TOTP secret."""
    return pyotp.random_base32()


def get_totp(secret: str) -> pyotp.TOTP:
    """Return a TOTP object for the given secret."""
    return pyotp.TOTP(secret)


def verify_totp(secret: str, code: str, valid_window: int = 1) -> bool:
    """
    Verify a TOTP code for the given secret.

    `valid_window` allows a small clock-skew tolerance (number of steps).
    """
    try:
        totp = get_totp(secret)
        return totp.verify(code, valid_window=valid_window)
    except Exception:
        return False



