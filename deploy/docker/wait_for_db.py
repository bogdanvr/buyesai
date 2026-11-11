"""Wait for the external database before running migrations."""

import os
import time

import django
from django.db import OperationalError, connections


def main():
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")
    django.setup()
    timeout = int(os.environ.get("DB_WAIT_TIMEOUT_SECONDS", "60"))
    if timeout <= 0:
        raise SystemExit("DB_WAIT_TIMEOUT_SECONDS must be greater than zero.")

    deadline = time.monotonic() + timeout
    connection = connections["default"]
    while True:
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            connection.close()
            print("Database is ready.", flush=True)
            return
        except OperationalError as exc:
            connection.close()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise SystemExit(f"Database was not ready after {timeout}s: {exc}") from exc
            print("Waiting for database...", flush=True)
            time.sleep(min(2, remaining))


if __name__ == "__main__":
    main()
