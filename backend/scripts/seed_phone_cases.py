import argparse
import json
import sys
from decimal import Decimal
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import get_connection  # noqa: E402


DATA_FILE = BACKEND_DIR / "data" / "phone_cases.json"
DEFAULT_STORE_NAME = "CaseMarket Test Magazasi"


def load_products() -> list[dict]:
    with DATA_FILE.open(encoding="utf-8") as file:
        products = json.load(file)

    if not isinstance(products, list) or not products:
        raise ValueError("phone_cases.json dolu bir JSON listesi olmali.")
    return products


def find_seller(cursor, store_name: str) -> tuple[int, str]:
    cursor.execute(
        "SELECT id, store_name FROM sellers WHERE store_name = %s ORDER BY id",
        (store_name,),
    )
    sellers = cursor.fetchall()
    if not sellers:
        raise RuntimeError(
            f"'{store_name}' adli test magazasi bulunamadi. "
            "Once mevcut bir satici magazasi olusturun veya --store-name kullanin."
        )
    if len(sellers) > 1:
        raise RuntimeError(
            f"'{store_name}' adinda birden fazla magaza var; benzersiz bir --store-name kullanin."
        )
    return sellers[0]


def validate_category(cursor, category_id: int | None) -> None:
    if category_id is None:
        return
    cursor.execute("SELECT 1 FROM categories WHERE id = %s", (category_id,))
    if cursor.fetchone() is None:
        raise RuntimeError(f"Kategori bulunamadi: {category_id}")


def seed(store_name: str) -> tuple[int, int, int]:
    products = load_products()
    added = updated = skipped = 0

    with get_connection() as connection:
        with connection.cursor() as cursor:
            seller_id, resolved_store_name = find_seller(cursor, store_name)
            checked_categories: set[int | None] = set()

            for product in products:
                category_id = product.get("category_id")
                if category_id not in checked_categories:
                    validate_category(cursor, category_id)
                    checked_categories.add(category_id)

                values = (
                    category_id,
                    product["name"].strip(),
                    product["description"].strip(),
                    Decimal(str(product["price"])),
                    int(product["stock"]),
                    product["image_url"],
                    bool(product["is_active"]),
                )
                cursor.execute(
                    """
                    SELECT id, category_id, name, description, price, stock, image_url, is_active
                    FROM products
                    WHERE seller_id = %s AND image_url = %s
                    ORDER BY id
                    """,
                    (seller_id, product["image_url"]),
                )
                existing = cursor.fetchall()
                if len(existing) > 1:
                    raise RuntimeError(
                        f"Birden fazla mevcut urun ayni gorsel yolunu kullaniyor: {product['image_url']}"
                    )

                if not existing:
                    cursor.execute(
                        """
                        INSERT INTO products
                            (seller_id, category_id, name, description, price, stock, image_url, is_active)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (seller_id, *values),
                    )
                    added += 1
                    continue

                row = existing[0]
                current = (row[1], row[2], row[3], row[4], row[5], row[6], row[7])
                if current == values:
                    skipped += 1
                    continue

                cursor.execute(
                    """
                    UPDATE products
                    SET category_id = %s,
                        name = %s,
                        description = %s,
                        price = %s,
                        stock = %s,
                        image_url = %s,
                        is_active = %s
                    WHERE id = %s AND seller_id = %s
                    """,
                    (*values, row[0], seller_id),
                )
                updated += 1

    print(f"Magaza: {resolved_store_name} (ID: {seller_id})")
    print(f"Eklendi: {added} | Guncellendi: {updated} | Atlandi: {skipped}")
    return added, updated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="ABO telefon kilifi katalog verilerini yukler.")
    parser.add_argument("--store-name", default=DEFAULT_STORE_NAME)
    args = parser.parse_args()
    seed(args.store_name)


if __name__ == "__main__":
    main()
