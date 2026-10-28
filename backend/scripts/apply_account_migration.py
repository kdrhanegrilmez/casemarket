"""Apply the additive account and checkout migration to a running local database."""

from pathlib import Path

from database import get_connection


def main():
    migration = Path(__file__).resolve().parents[1] / "migrations" / "001_account_checkout.sql"
    statements = migration.read_text(encoding="utf-8").split(";")
    with get_connection() as connection:
        with connection.cursor() as cursor:
            for statement in statements:
                if statement.strip():
                    cursor.execute(statement)
    print("Account checkout migration applied.")


if __name__ == "__main__":
    main()
