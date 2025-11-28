"""
Management command to scan and optionally fix invalid `mfa_secret` values.

This helps detect situations where the Fernet key (usually derived from
`SECRET_KEY` or related settings) has changed or some `mfa_secret` values
are corrupted and cannot be decrypted anymore.

Usage examples:

    # Dry run – only report problems
    python manage.py check_mfa_secrets

    # Auto-fix – clear invalid secrets and disable MFA for affected users
    python manage.py check_mfa_secrets --auto-fix
"""
from django.core.management.base import BaseCommand

from accounts.models import User


class Command(BaseCommand):
    help = (
        "Scan users for invalid `mfa_secret` values that cannot be decrypted "
        "and optionally clear them."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--auto-fix",
            action="store_true",
            dest="auto_fix",
            help=(
                "Automatically clear invalid `mfa_secret` values and set "
                "`mfa_enabled = False` for affected users."
            ),
        )

    def handle(self, *args, **options):
        auto_fix: bool = options["auto_fix"]

        # EncryptedTextField does not support lookups like exact/contains,
        # so we cannot filter on `mfa_secret` directly. Instead, iterate over
        # all users (or those with MFA enabled) and try to access the field.
        qs = User.objects.all()

        total = qs.count()
        invalid_count = 0
        fixed_count = 0

        if total == 0:
            self.stdout.write(self.style.SUCCESS("No users found to scan."))
            return

        self.stdout.write(f"Scanning {total} users for invalid `mfa_secret` values...")

        for user in qs.iterator():
            # Skip users that clearly have MFA disabled and no secret set.
            if not getattr(user, "mfa_enabled", False):
                continue

            try:
                # Accessing the field forces decryption via fernet_fields.
                _ = user.mfa_secret  # noqa: F841
            except Exception as exc:  # noqa: BLE001
                invalid_count += 1
                self.stdout.write(
                    self.style.WARNING(
                        f"Invalid mfa_secret for user {user.id} ({user.email}): {exc}"
                    )
                )

                if auto_fix:
                    user.mfa_secret = None
                    user.mfa_enabled = False
                    user.save(update_fields=["mfa_secret", "mfa_enabled"])
                    fixed_count += 1

        summary = (
            f"Scan complete. Users with invalid `mfa_secret`: {invalid_count}"
        )

        if auto_fix:
            summary += f", cleared: {fixed_count}"

        if invalid_count == 0:
            self.stdout.write(self.style.SUCCESS(summary))
        else:
            self.stdout.write(self.style.WARNING(summary))

