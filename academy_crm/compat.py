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
        import fernet_fields
        import logging
        logger = logging.getLogger(__name__)
        
        # Find the actual field class - EncryptedTextField is imported from fernet_fields directly
        # Check what's available in fernet_fields
        EncryptedTextField = getattr(fernet_fields, 'EncryptedTextField', None)
        
        if not EncryptedTextField:
            # Try fernet_fields.fields
            try:
                import fernet_fields.fields as fields_module
                EncryptedTextField = getattr(fields_module, 'EncryptedTextField', None)
            except ImportError:
                pass
        
        if not EncryptedTextField:
            logger.warning("⚠️ Could not find EncryptedTextField in fernet_fields")
            return
        
        # Get the base class - EncryptedTextField might inherit from something
        # Find the actual class that has from_db_value
        field_class = EncryptedTextField
        base_class = None
        
        # Try to find the base class by checking MRO (Method Resolution Order)
        for cls in EncryptedTextField.__mro__:
            if hasattr(cls, 'from_db_value') and cls != object:
                base_class = cls
                break
        
        if not base_class:
            # If we can't find it in MRO, use EncryptedTextField itself
            base_class = EncryptedTextField
        
        # Store the original method
        original_from_db_value = base_class.from_db_value
        
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
        
        # Apply the patch to the base class
        base_class.from_db_value = patched_from_db_value
        logger.info(f"✅ Patched base class: {base_class.__name__}")
        
        # Patch EncryptedTextField directly
        EncryptedTextField.from_db_value = patched_from_db_value
        logger.info("✅ Patched EncryptedTextField.from_db_value")
        
        # Patch all classes in the MRO of EncryptedTextField that have from_db_value
        patched_count = 0
        for cls in EncryptedTextField.__mro__:
            if (cls != object and 
                cls != base_class and 
                hasattr(cls, 'from_db_value') and
                cls.from_db_value != patched_from_db_value):
                try:
                    cls.from_db_value = patched_from_db_value
                    patched_count += 1
                    logger.info(f"✅ Patched {cls.__name__}.from_db_value")
                except Exception:
                    pass  # Skip if we can't patch it
        
        # Also check fernet_fields module for other field classes
        for attr_name in dir(fernet_fields):
            if attr_name.startswith('_'):
                continue
            attr = getattr(fernet_fields, attr_name, None)
            if (attr and 
                isinstance(attr, type) and 
                hasattr(attr, 'from_db_value') and
                attr != EncryptedTextField and
                attr != base_class):
                try:
                    # Check if it's a field class (inherits from models.Field or similar)
                    if hasattr(attr, '__bases__'):
                        # Check if it's a Django field
                        from django.db import models
                        if any(issubclass(base, models.Field) if isinstance(base, type) else False 
                               for base in attr.__bases__):
                            attr.from_db_value = patched_from_db_value
                            patched_count += 1
                            logger.info(f"✅ Patched {attr_name}.from_db_value")
                except Exception:
                    pass  # Skip if we can't patch it
        
        if patched_count > 0:
            logger.info(f"✅ Patched {patched_count} additional field classes")
        
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


