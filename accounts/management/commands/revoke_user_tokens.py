"""
Revoke (blacklist) all outstanding refresh tokens for a given user.

Usage:

    python manage.py revoke_user_tokens --email user@example.com
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

from rest_framework_simplejwt.token_blacklist.models import (
    BlacklistedToken,
    OutstandingToken,
)


User = get_user_model()


class Command(BaseCommand):
    help = "Revoke all outstanding refresh tokens for a user (by email)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            required=True,
            help="Email of the user whose tokens should be revoked.",
        )

    def handle(self, *args, **options):
        email = options["email"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist as exc:
            raise CommandError(f"User with email '{email}' does not exist.") from exc

        tokens = OutstandingToken.objects.filter(user=user)
        count = 0
        for token in tokens:
            BlacklistedToken.objects.get_or_create(token=token)
            count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Blacklisted {count} outstanding refresh token(s) for {user.email}."
            )
        )


