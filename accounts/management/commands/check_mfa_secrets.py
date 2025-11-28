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

        qs = User.objects.filter(mfa_secret__isnull=False).exclude(mfa_secret="")

        total = qs.count()
        invalid_count = 0
        fixed_count = 0

        if total == 0:
            self.stdout.write(self.style.SUCCESS("No users with non-empty `mfa_secret` found."))
            return

        self.stdout.write(f"Scanning {total} users with non-empty `mfa_secret`...")

        for user in qs.iterator():
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
            f"Scan complete. Total with non-empty `mfa_secret`: {total}, "
            f"invalid: {invalid_count}"
        )

        if auto_fix:
            summary += f", cleared: {fixed_count}"

        if invalid_count == 0:
            self.stdout.write(self.style.SUCCESS(summary))
        else:
            self.stdout.write(self.style.WARNING(summary))


