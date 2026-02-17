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
from django.db import connection

from accounts.models import User


class Command(BaseCommand):
    help = (
        "Scan users for invalid `mfa_secret` values and optionally clear them.\n"
        "Note: Due to EncryptedTextField limitations, the safety option simply\n"
        "clears all non-empty `mfa_secret` values using raw SQL."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--auto-fix",
            action="store_true",
            dest="auto_fix",
            help=(
                "CLEAR ALL non-empty `mfa_secret` values and set "
                "`mfa_enabled = False` for affected users using raw SQL."
            ),
        )

    def handle(self, *args, **options):
        auto_fix: bool = options["auto_fix"]

        total_users = User.objects.count()
        self.stdout.write(f"Total users: {total_users}")

        if not auto_fix:
            self.stdout.write(
                self.style.WARNING(
                    "Dry run only. Due to EncryptedTextField limitations, this "
                    "command cannot reliably detect individual invalid tokens "
                    "without risking crashes.\n"
                    "Run again with --auto-fix to CLEAR ALL non-empty "
                    "`mfa_secret` values safely using raw SQL."
                )
            )
            return

        self.stdout.write(
            self.style.WARNING(
                "AUTO-FIX MODE: All non-empty `mfa_secret` values will be "
                "cleared and `mfa_enabled` will be set to FALSE.\n"
                "This is safe but will require users to re-enable MFA."
            )
        )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET mfa_secret = NULL, mfa_enabled = FALSE
                WHERE mfa_secret IS NOT NULL AND mfa_secret != '';
                """
            )
            affected = cursor.rowcount

        self.stdout.write(
            self.style.SUCCESS(
                f"Cleared mfa_secret and disabled MFA for {affected} user(s)."
            )
        )

