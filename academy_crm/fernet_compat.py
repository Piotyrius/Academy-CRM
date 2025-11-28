"""
Global safety wrapper for django-fernet-fields.

This ensures that InvalidToken from cryptography.fernet never crashes
queries (e.g. when generating OpenAPI schema or listing enrollments).
"""

try:  # pragma: no cover - defensive, depends on optional package
    from fernet_fields.fields import FernetField  # type: ignore[import]
    from cryptography.fernet import InvalidToken  # type: ignore[import]

    _original_from_db_value = getattr(FernetField, "from_db_value", None)

    if callable(_original_from_db_value):

        def safe_from_db_value(self, value, expression, connection):
            """
            Wrap original FernetField.from_db_value to swallow InvalidToken.

            If decryption fails (e.g. after SECRET_KEY rotation or data
            corruption), return None instead of raising so queries don't 500.
            """
            if value in (None, b"", ""):
                return value
            try:
                return _original_from_db_value(self, value, expression, connection)
            except InvalidToken:
                # Let callers treat missing/invalid secrets as None.
                return None

        FernetField.from_db_value = safe_from_db_value  # type: ignore[assignment]
except Exception:
    # If anything goes wrong, fail silently; core app should still run.
    pass


