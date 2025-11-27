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
        import logging
        logger = logging.getLogger(__name__)
        
        # Store the original method
        original_from_db_value = fernet_fields.fields.FernetField.from_db_value
        
        def patched_from_db_value(self, value, expression, connection):
            """
            Patched version that handles string-to-bytes conversion with encoding.
            
            The original fernet_fields code tries bytes(value) which fails in Python 3
            when value is a string. This patch intercepts that and handles it properly.
            
            We convert strings to bytes BEFORE calling the original method to prevent the error.
            """
            if value is None:
                return None
            
            # If value is already bytes, use original method directly
            if isinstance(value, bytes):
                return original_from_db_value(self, value, expression, connection)
            
            # If value is a string, convert to bytes BEFORE calling original method
            # This prevents the TypeError: string argument without an encoding
            if isinstance(value, str):
                # Encrypted data from database is typically stored as base64-encoded strings
                # Try base64 decode first (most common case)
                import base64
                try:
                    # Try to decode as base64
                    value_bytes = base64.b64decode(value, validate=True)
                    return original_from_db_value(self, value_bytes, expression, connection)
                except Exception:
                    # If base64 decode fails, try encoding as latin-1 (preserves byte values 1:1)
                    # This is safer for binary/encrypted data than UTF-8
                    try:
                        value_bytes = value.encode('latin-1')
                        return original_from_db_value(self, value_bytes, expression, connection)
                    except Exception:
                        # Last resort: UTF-8 encoding
                        try:
                            value_bytes = value.encode('utf-8')
                            return original_from_db_value(self, value_bytes, expression, connection)
                        except Exception as e:
                            # If all else fails, log and try original method (might fail, but at least we tried)
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.warning(f"Failed to convert string to bytes in fernet_fields patch: {e}")
                            # Try original method - it will fail, but at least we tried our best
                            return original_from_db_value(self, value, expression, connection)
            
            # For other types, use original method
            return original_from_db_value(self, value, expression, connection)
        
        # Apply the patch to FernetField base class
        fernet_fields.fields.FernetField.from_db_value = patched_from_db_value
        logger.info("✅ Patched fernet_fields.fields.FernetField.from_db_value")
        
        # Also patch EncryptedTextField - check both locations
        # EncryptedTextField might be in fernet_fields.fields or fernet_fields directly
        if hasattr(fernet_fields, 'EncryptedTextField'):
            # EncryptedTextField at module level
            if fernet_fields.EncryptedTextField != fernet_fields.fields.FernetField:
                fernet_fields.EncryptedTextField.from_db_value = patched_from_db_value
                logger.info("✅ Patched fernet_fields.EncryptedTextField.from_db_value")
        
        if hasattr(fernet_fields.fields, 'EncryptedTextField'):
            # EncryptedTextField in fields submodule
            if fernet_fields.fields.EncryptedTextField != fernet_fields.fields.FernetField:
                fernet_fields.fields.EncryptedTextField.from_db_value = patched_from_db_value
                logger.info("✅ Patched fernet_fields.fields.EncryptedTextField.from_db_value")
        
        # Patch all field classes in the module that inherit from FernetField
        patched_count = 0
        for attr_name in dir(fernet_fields.fields):
            attr = getattr(fernet_fields.fields, attr_name, None)
            if (attr and 
                isinstance(attr, type) and 
                issubclass(attr, fernet_fields.fields.FernetField) and 
                attr != fernet_fields.fields.FernetField):
                try:
                    attr.from_db_value = patched_from_db_value
                    patched_count += 1
                except Exception:
                    pass  # Skip if we can't patch it
        
        # Also check fernet_fields module level
        for attr_name in dir(fernet_fields):
            if attr_name.startswith('_'):
                continue
            attr = getattr(fernet_fields, attr_name, None)
            if (attr and 
                isinstance(attr, type) and 
                hasattr(attr, 'from_db_value') and
                attr != fernet_fields.fields.FernetField):
                try:
                    # Check if it's a field class
                    if hasattr(attr, '__bases__') and any('Field' in str(base) for base in attr.__bases__):
                        attr.from_db_value = patched_from_db_value
                        patched_count += 1
                except Exception:
                    pass  # Skip if we can't patch it
        
        if patched_count > 0:
            logger.info(f"✅ Patched {patched_count} additional fernet_fields subclasses")
        
        logger.info("✅ fernet_fields encoding patch applied successfully")
        
    except ImportError:
        # fernet_fields not available, nothing to patch
        import logging
        logger = logging.getLogger(__name__)
        logger.warning("⚠️ fernet_fields not available - patch not applied")
    except Exception as e:
        # If patching fails, log it but continue
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"❌ Failed to patch fernet_fields: {e}", exc_info=True)


# Apply the patch when this module is imported
_patch_fernet_fields()


