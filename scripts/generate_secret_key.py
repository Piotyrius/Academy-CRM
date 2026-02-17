"""
Generate a secure Django SECRET_KEY.
Run: python scripts/generate_secret_key.py
"""
import secrets
import string

def generate_secret_key():
    """Generate a Django-compatible SECRET_KEY."""
    chars = string.ascii_letters + string.digits + '!@#$%^&*(-_=+)'
    return ''.join(secrets.choice(chars) for _ in range(50))

if __name__ == '__main__':
    secret_key = generate_secret_key()
    print("=" * 80)
    print("GENERATED SECRET_KEY")
    print("=" * 80)
    print()
    print(secret_key)
    print()
    print("=" * 80)
    print("Copy this value and use it as SECRET_KEY in Render environment variables")
    print("=" * 80)

