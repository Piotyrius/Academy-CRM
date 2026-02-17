"""
Global safety wrapper for django-fernet-fields.

This ensures that InvalidToken from cryptography.fernet never crashes
queries (e.g. when generating OpenAPI schema or listing enrollments).
"""

try:  # pragma: no cover - defensive, depends on optional package
    from fernet_fields import EncryptedTextField  # type: ignore[import]
    from cryptography.fernet import InvalidToken  # type: ignore[import]

    _original_from_db_value = getattr(EncryptedTextField, "from_db_value", None)

    if callable(_original_from_db_value):

        def safe_from_db_value(self, value, expression, connection, *args):
            """
            Wrap original EncryptedField.from_db_value to swallow InvalidToken.

            If decryption fails (e.g. after SECRET_KEY rotation or data
            corruption), return None instead of raising so queries don't 500.
            """
            if value in (None, b"", ""):
                return value
            try:
                return _original_from_db_value(self, value, expression, connection, *args)
            except InvalidToken:
                # Let callers treat undecryptable values as missing; callers will see None.
                return None

        EncryptedTextField.from_db_value = safe_from_db_value  # type: ignore[assignment]
except Exception:
    # If anything goes wrong, fail silently; core app should still run.
    pass


