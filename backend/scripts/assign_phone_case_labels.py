"""Apply the reviewed ABO phone labels to the demo catalog products."""

import argparse
import json
import re
import sys
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
PROJECT_DIR = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from database import get_connection  # noqa: E402


DATA_DIR = BACKEND_DIR / "data"
DEFAULT_STORE_NAME = "CaseMarket Test Magazasi"


def load_labels():
    labels = json.loads((DATA_DIR / "phone_case_labels.json").read_text(encoding="utf-8"))
    products = json.loads((DATA_DIR / "phone_cases.json").read_text(encoding="utf-8"))
    source_text = (DATA_DIR / "IMAGE_SOURCES.md").read_text(encoding="utf-8")
    source_asins = {
        f"/products/{image}": asin
        for image, asin in re.findall(r"\| (case-\d{3}\.(?:webp|jpg)) \| (B[A-Z0-9]{9}) \|", source_text)
    }
    product_urls = {product["image_url"] for product in products}
    label_urls = [label["image_url"] for label in labels]

    if not labels or len(set(label_urls)) != len(labels) or set(label_urls) != product_urls:
        raise ValueError("Etiketler mevcut demo urunleriyle bire bir eslesmeli.")

    for label in labels:
        image_url = label["image_url"]
        if source_asins.get(image_url) != label["source_asin"]:
            raise ValueError(f"ABO ilan kimligi kaynak dosyasiyla uyusmuyor: {image_url}")
        if not (PROJECT_DIR / "frontend/public" / image_url.lstrip("/")).is_file():
            raise ValueError(f"Yerel gorsel eksik: {image_url}")
        if not label["category"] or not label["phones"]:
            raise ValueError(f"Kategori veya uyumlu model eksik: {image_url}")
        phones = [tuple(phone) for phone in label["phones"]]
        if any(len(phone) != 2 or not all(phone) for phone in phones) or len(set(phones)) != len(phones):
            raise ValueError(f"Gecersiz veya yinelenen telefon modeli: {image_url}")

    return labels


def assign_labels(store_name: str, verify_only: bool = False):
    labels = load_labels()
    with get_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id FROM sellers WHERE store_name = %s", (store_name,))
            sellers = cursor.fetchall()
            if len(sellers) != 1:
                raise RuntimeError(f"Tek bir demo magazasi bulunmali: {store_name}")
            seller_id = sellers[0][0]

            # Check every target before writing. A conflict must not alter another seller's work.
            targets = []
            for label in labels:
                cursor.execute(
                    "SELECT id, category_id FROM products WHERE seller_id = %s AND image_url = %s",
                    (seller_id, label["image_url"]),
                )
                rows = cursor.fetchall()
                if len(rows) != 1:
                    raise RuntimeError(f"Tam bir urun bulunmali: {label['image_url']}")
                product_id, category_id = rows[0]
                cursor.execute(
                    """
                    SELECT b.name, m.name
                    FROM product_compatible_models AS pcm
                    JOIN phone_models AS m ON m.id = pcm.phone_model_id
                    JOIN phone_brands AS b ON b.id = m.brand_id
                    WHERE pcm.product_id = %s
                    """,
                    (product_id,),
                )
                existing_phones = set(cursor.fetchall())
                expected_phones = {tuple(phone) for phone in label["phones"]}
                if existing_phones - expected_phones:
                    raise RuntimeError(f"Urunun farkli bir uyumluluk atamasi var: {product_id}")
                if category_id is not None:
                    cursor.execute("SELECT name FROM categories WHERE id = %s", (category_id,))
                    if cursor.fetchone()[0] != label["category"]:
                        raise RuntimeError(f"Urunun farkli bir kilif turu var: {product_id}")
                targets.append((product_id, category_id, existing_phones, expected_phones, label))

            if verify_only:
                incomplete = [
                    product_id for product_id, category_id, existing, expected, _ in targets
                    if category_id is None or existing != expected
                ]
                if incomplete:
                    raise RuntimeError(f"Eksik etiketli urunler: {incomplete}")
                print(f"Dogrulandi: {len(targets)} urun, {len({phone for _, _, _, phones, _ in targets for phone in phones})} telefon modeli")
                return

            for product_id, category_id, _, expected_phones, label in targets:
                cursor.execute(
                    "INSERT INTO categories (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                    (label["category"],),
                )
                cursor.execute("SELECT id FROM categories WHERE name = %s", (label["category"],))
                target_category_id = cursor.fetchone()[0]
                if category_id is None:
                    cursor.execute(
                        "UPDATE products SET category_id = %s WHERE id = %s",
                        (target_category_id, product_id),
                    )

                for brand_name, model_name in sorted(expected_phones):
                    cursor.execute(
                        "INSERT INTO phone_brands (name) VALUES (%s) ON CONFLICT (name) DO NOTHING",
                        (brand_name,),
                    )
                    cursor.execute("SELECT id FROM phone_brands WHERE name = %s", (brand_name,))
                    brand_id = cursor.fetchone()[0]
                    cursor.execute(
                        "INSERT INTO phone_models (brand_id, name) VALUES (%s, %s) ON CONFLICT (brand_id, name) DO NOTHING",
                        (brand_id, model_name),
                    )
                    cursor.execute(
                        "SELECT id FROM phone_models WHERE brand_id = %s AND name = %s",
                        (brand_id, model_name),
                    )
                    model_id = cursor.fetchone()[0]
                    cursor.execute(
                        "INSERT INTO product_compatible_models (product_id, phone_model_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                        (product_id, model_id),
                    )

    print(f"Etiketlendi: {len(targets)} mevcut urun")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store-name", default=DEFAULT_STORE_NAME)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    assign_labels(args.store_name, args.verify_only)


if __name__ == "__main__":
    main()
