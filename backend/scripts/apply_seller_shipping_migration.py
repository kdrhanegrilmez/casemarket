from pathlib import Path
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import get_connection  # noqa: E402


def main():
    sql = (BACKEND_DIR / "migrations" / "003_seller_shipping.sql").read_text(encoding="utf-8")
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(sql)
    print("Satıcı kargo durumu şeması hazır.")


if __name__ == "__main__":
    main()
