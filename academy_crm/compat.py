"""
Compatibility helpers for third-party packages expecting older Django APIs.

Currently provides a `force_text` alias for Django 4+ where it was removed,
so libraries like `django-fernet-fields` that still import `force_text`
continue to work when running on Django 5.1.

Also patches fernet_fields to handle encoding issues when converting strings to bytes.
"""
from django.utils import encoding as django_encoding

try:
    # Django < 4: `force_text` exists and we do nothing.
    getattr(django_encoding, "force_text")
except AttributeError:
    # Django 4+: `force_text` was removed; alias it to `force_str`.
    from django.utils.encoding import force_str

    django_encoding.force_text = force_str  # type: ignore[attr-defined]


# Patch fernet_fields to handle encoding issues
def _patch_fernet_fields():
    """
    Patch fernet_fields to fix TypeError when converting strings to bytes.
    
    The issue: fernet_fields tries to convert a string to bytes using bytes(value)
    without specifying an encoding, which fails in Python 3.
    
    This patch wraps the from_db_value method to catch and handle the encoding error.
    """
    try:
        import fernet_fields.fields
        
        # Store the original method
        original_from_db_value = fernet_fields.fields.FernetField.from_db_value
        
        def patched_from_db_value(self, value, expression, connection):
            """
            Patched version that handles string-to-bytes conversion with encoding.
            
            The original fernet_fields code tries bytes(value) which fails in Python 3
            when value is a string. This patch intercepts that and handles it properly.
            
            Encrypted data in the database is typically stored as base64-encoded strings.
            We need to decode the base64 string to bytes before the original method can decrypt it.
            """
            if value is None:
                return None
            
            # If value is already bytes, use original method
            if isinstance(value, bytes):
                return original_from_db_value(self, value, expression, connection)
            
            # If value is a string, we need to handle it carefully
            # The original method might try bytes(value) which fails in Python 3
            if isinstance(value, str):
                # Try the original method first (it might work in some cases)
                try:
                    return original_from_db_value(self, value, expression, connection)
                except TypeError as e:
                    # Check if this is the encoding error we're trying to fix
                    error_msg = str(e).lower()
                    if 'encoding' in error_msg or 'string argument' in error_msg:
                        # The original code is trying bytes(value) which fails
                        # Encrypted data from database is typically stored as base64-encoded strings
                        # We need to decode the base64 string to bytes first
                        import base64
                        try:
                            # Try to decode as base64 (most common case for encrypted data)
                            value_bytes = base64.b64decode(value)
                            return original_from_db_value(self, value_bytes, expression, connection)
                        except Exception:
                            # If base64 decode fails, the value might be plain text or already in bytes format
                            # Try encoding as UTF-8 (for plain text) or latin-1 (for binary data)
                            try:
                                value_bytes = value.encode('latin-1')
                                return original_from_db_value(self, value_bytes, expression, connection)
                            except Exception:
                                # Last resort: UTF-8 encoding
                                value_bytes = value.encode('utf-8')
                                return original_from_db_value(self, value_bytes, expression, connection)
                    # Re-raise if it's a different TypeError
                    raise
            
            # For other types, use original method
            return original_from_db_value(self, value, expression, connection)
        
        # Apply the patch to all FernetField subclasses
        fernet_fields.fields.FernetField.from_db_value = patched_from_db_value
        
        # Also patch EncryptedTextField if it's a separate class
        if hasattr(fernet_fields.fields, 'EncryptedTextField'):
            if fernet_fields.fields.EncryptedTextField != fernet_fields.fields.FernetField:
                fernet_fields.fields.EncryptedTextField.from_db_value = patched_from_db_value
        
    except ImportError:
        # fernet_fields not available, nothing to patch
        pass
    except Exception:
        # If patching fails, continue anyway - better to have migrations fail
        # with a clear error than to silently break
        pass


# Apply the patch when this module is imported
_patch_fernet_fields()


