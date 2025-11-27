"""
Compatibility helpers for third-party packages expecting older Django APIs.

Currently provides a `force_text` alias for Django 4+ where it was removed,
so libraries like `django-fernet-fields` that still import `force_text`
continue to work when running on Django 5.1.
"""

from django.utils import encoding as django_encoding

try:
    # Django < 4: `force_text` exists and we do nothing.
    getattr(django_encoding, "force_text")
except AttributeError:
    # Django 4+: `force_text` was removed; alias it to `force_str`.
    from django.utils.encoding import force_str

    django_encoding.force_text = force_str  # type: ignore[attr-defined]


