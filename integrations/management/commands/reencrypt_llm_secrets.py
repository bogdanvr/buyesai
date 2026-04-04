from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from integrations.models import LlmProviderAccount
from integrations.services.secrets import decrypt_secret_with_key, encrypt_secret_with_key


class Command(BaseCommand):
    help = "Перешифровывает сохранённые API-ключи LLM-провайдеров с одного мастер-ключа на другой."

    def add_arguments(self, parser):
        parser.add_argument("--old-key", dest="old_key", required=True, help="Старый INTEGRATIONS_SECRET_KEY.")
        parser.add_argument("--new-key", dest="new_key", required=True, help="Новый INTEGRATIONS_SECRET_KEY.")
        parser.add_argument("--dry-run", action="store_true", help="Только проверить, сколько ключей будет перешифровано.")

    @transaction.atomic
    def handle(self, *args, **options):
        old_key = str(options["old_key"] or "").strip()
        new_key = str(options["new_key"] or "").strip()
        dry_run = bool(options.get("dry_run"))

        if not old_key:
            raise CommandError("Нужно передать --old-key.")
        if not new_key:
            raise CommandError("Нужно передать --new-key.")
        if old_key == new_key:
            raise CommandError("Старый и новый ключи совпадают. Ротация не нужна.")

        providers = list(
            LlmProviderAccount.objects
            .filter(api_key_encrypted__gt="")
            .order_by("id")
        )
        reencrypted = 0
        for provider in providers:
            plaintext = decrypt_secret_with_key(provider.api_key_encrypted, old_key)
            if dry_run:
                reencrypted += 1
                continue
            provider.api_key_encrypted = encrypt_secret_with_key(plaintext, new_key)
            provider.api_key_last4 = plaintext[-4:] if plaintext else ""
            provider.save(update_fields=["api_key_encrypted", "api_key_last4", "updated_at"])
            reencrypted += 1

        if dry_run:
            transaction.set_rollback(True)
            self.stdout.write(self.style.WARNING(f"Dry run: будет перешифровано ключей: {reencrypted}"))
            return

        self.stdout.write(self.style.SUCCESS(f"Перешифровано ключей: {reencrypted}"))
