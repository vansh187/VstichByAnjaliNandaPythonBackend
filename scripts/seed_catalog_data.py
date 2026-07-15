"""Seed script: inserts 5 categories, 5 products, 6 size/color variants per
product (30 total), and one image per variant, so the frontend team has real
catalog data - covering multiple sizes/colors per product - to integrate
against before the catalog API itself is built.

Idempotent - re-running it does not duplicate categories, products, variants
(matched by SKU), or images (one per variant, skipped if already present).

Usage:
    python scripts/seed_catalog_data.py
"""

import os
import sys

import psycopg2
from dotenv import load_dotenv

load_dotenv()

SEEDED_BY = "seed-script"

CATEGORIES = ["Sarees", "Kurtis", "Lehengas", "Salwar Suits", "Dupattas"]

# category_name -> (product_name, description, base_price)
PRODUCTS = {
    "Sarees": (
        "Banarasi Silk Saree",
        "Handwoven Banarasi silk saree with a gold zari border.",
        2999.00,
    ),
    "Kurtis": (
        "Anarkali Kurti",
        "Floor-length Anarkali kurti in flowing rayon fabric.",
        1499.00,
    ),
    "Lehengas": (
        "Bridal Lehenga Choli",
        "Heavily embroidered bridal lehenga choli with dupatta.",
        8999.00,
    ),
    "Salwar Suits": (
        "Cotton Salwar Suit",
        "Everyday cotton salwar suit set, pre-stitched.",
        1999.00,
    ),
    "Dupattas": (
        "Embroidered Dupatta",
        "Chiffon dupatta with delicate thread embroidery.",
        799.00,
    ),
}

# product_name -> list of (sku, size, color, price, stock_quantity, image_seed)
# Sarees/Dupattas are one-size-fits-all in this catalog, so their 6 variants
# vary by color only; Kurtis/Lehengas/Salwar Suits vary by both size and color.
VARIANTS = {
    "Banarasi Silk Saree": [
        ("SAREE-BANARASI-RED-STD", "Standard", "Red", 2999.00, 20, "banarasi-silk-saree-red"),
        ("SAREE-BANARASI-BLUE-STD", "Standard", "Blue", 2999.00, 15, "banarasi-silk-saree-blue"),
        ("SAREE-BANARASI-GREEN-STD", "Standard", "Green", 2999.00, 18, "banarasi-silk-saree-green"),
        ("SAREE-BANARASI-MAROON-STD", "Standard", "Maroon", 2999.00, 12, "banarasi-silk-saree-maroon"),
        ("SAREE-BANARASI-GOLDEN-STD", "Standard", "Golden", 2999.00, 10, "banarasi-silk-saree-golden"),
        ("SAREE-BANARASI-BLACK-STD", "Standard", "Black", 2999.00, 22, "banarasi-silk-saree-black"),
    ],
    "Anarkali Kurti": [
        ("KURTI-ANARKALI-BLUE-S", "S", "Blue", 1499.00, 20, "anarkali-kurti-blue-s"),
        ("KURTI-ANARKALI-BLUE-M", "M", "Blue", 1499.00, 30, "anarkali-kurti-blue-m"),
        ("KURTI-ANARKALI-BLUE-L", "L", "Blue", 1499.00, 25, "anarkali-kurti-blue-l"),
        ("KURTI-ANARKALI-BLUE-XL", "XL", "Blue", 1499.00, 15, "anarkali-kurti-blue-xl"),
        ("KURTI-ANARKALI-PINK-M", "M", "Pink", 1499.00, 28, "anarkali-kurti-pink-m"),
        ("KURTI-ANARKALI-PINK-L", "L", "Pink", 1499.00, 18, "anarkali-kurti-pink-l"),
    ],
    "Bridal Lehenga Choli": [
        ("LEHENGA-BRIDAL-MAROON-S", "S", "Maroon", 8999.00, 6, "bridal-lehenga-maroon-s"),
        ("LEHENGA-BRIDAL-MAROON-M", "M", "Maroon", 8999.00, 10, "bridal-lehenga-maroon-m"),
        ("LEHENGA-BRIDAL-MAROON-L", "L", "Maroon", 8999.00, 8, "bridal-lehenga-maroon-l"),
        ("LEHENGA-BRIDAL-RED-S", "S", "Red", 8999.00, 5, "bridal-lehenga-red-s"),
        ("LEHENGA-BRIDAL-RED-M", "M", "Red", 8999.00, 9, "bridal-lehenga-red-m"),
        ("LEHENGA-BRIDAL-RED-L", "L", "Red", 8999.00, 7, "bridal-lehenga-red-l"),
    ],
    "Cotton Salwar Suit": [
        ("SUIT-COTTON-GREEN-S", "S", "Green", 1999.00, 20, "cotton-salwar-suit-green-s"),
        ("SUIT-COTTON-GREEN-M", "M", "Green", 1999.00, 22, "cotton-salwar-suit-green-m"),
        ("SUIT-COTTON-GREEN-L", "L", "Green", 1999.00, 25, "cotton-salwar-suit-green-l"),
        ("SUIT-COTTON-GREEN-XL", "XL", "Green", 1999.00, 14, "cotton-salwar-suit-green-xl"),
        ("SUIT-COTTON-YELLOW-M", "M", "Yellow", 1999.00, 18, "cotton-salwar-suit-yellow-m"),
        ("SUIT-COTTON-YELLOW-L", "L", "Yellow", 1999.00, 16, "cotton-salwar-suit-yellow-l"),
    ],
    "Embroidered Dupatta": [
        ("DUPATTA-EMBROIDERED-PINK-STD", "Standard", "Pink", 799.00, 40, "embroidered-dupatta-pink"),
        ("DUPATTA-EMBROIDERED-BLUE-STD", "Standard", "Blue", 799.00, 35, "embroidered-dupatta-blue"),
        ("DUPATTA-EMBROIDERED-YELLOW-STD", "Standard", "Yellow", 799.00, 30, "embroidered-dupatta-yellow"),
        ("DUPATTA-EMBROIDERED-GREEN-STD", "Standard", "Green", 799.00, 25, "embroidered-dupatta-green"),
        ("DUPATTA-EMBROIDERED-MAROON-STD", "Standard", "Maroon", 799.00, 20, "embroidered-dupatta-maroon"),
        ("DUPATTA-EMBROIDERED-BLACK-STD", "Standard", "Black", 799.00, 28, "embroidered-dupatta-black"),
    ],
}


def get_or_create_category(cursor, category_name):
    cursor.execute(
        "SELECT VstitchCategoryId FROM VStitch_Categories WHERE CategoryName = %s AND ParentCategoryId IS NULL;",
        (category_name,),
    )
    existing_row = cursor.fetchone()
    if existing_row is not None:
        return existing_row[0]

    cursor.execute(
        """
        INSERT INTO VStitch_Categories (CategoryName, created_by, created_date)
        VALUES (%s, %s, CURRENT_TIMESTAMP)
        RETURNING VstitchCategoryId;
        """,
        (category_name, SEEDED_BY),
    )
    return cursor.fetchone()[0]


def get_or_create_product(cursor, product_name, description, category_id, base_price):
    cursor.execute("SELECT VstitchProductId FROM VStitch_Products WHERE ProductName = %s;", (product_name,))
    existing_row = cursor.fetchone()
    if existing_row is not None:
        return existing_row[0]

    cursor.execute(
        """
        INSERT INTO VStitch_Products
            (ProductName, Description, VstitchCategoryId, BasePrice, IsActive, created_by, created_date)
        VALUES (%s, %s, %s, %s, TRUE, %s, CURRENT_TIMESTAMP)
        RETURNING VstitchProductId;
        """,
        (product_name, description, category_id, base_price, SEEDED_BY),
    )
    return cursor.fetchone()[0]


def upsert_variant(cursor, product_id, sku, size, color, price, stock_quantity):
    cursor.execute(
        """
        INSERT INTO VStitch_ProductVariants
            (VstitchProductId, Sku, Size, Color, Price, StockQuantity, IsActive, created_by, created_date)
        VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (Sku) DO UPDATE SET Sku = EXCLUDED.Sku
        RETURNING VstitchProductVariantId;
        """,
        (product_id, sku, size, color, price, stock_quantity, SEEDED_BY),
    )
    return cursor.fetchone()[0]


def ensure_variant_image(cursor, product_id, variant_id, image_url):
    cursor.execute(
        "SELECT 1 FROM VStitch_ProductImages WHERE VstitchProductVariantId = %s;",
        (variant_id,),
    )
    if cursor.fetchone() is not None:
        return

    cursor.execute(
        """
        INSERT INTO VStitch_ProductImages
            (VstitchProductId, VstitchProductVariantId, ImageUrl, IsPrimary, DisplayOrder, created_by, created_date)
        VALUES (%s, %s, %s, TRUE, 1, %s, CURRENT_TIMESTAMP);
        """,
        (product_id, variant_id, image_url, SEEDED_BY),
    )


def seed():
    connection = psycopg2.connect(os.getenv("DATABASE_URL"))
    cursor = connection.cursor()
    variant_count = 0
    image_count = 0
    try:
        for category_name in CATEGORIES:
            category_id = get_or_create_category(cursor, category_name)
            product_name, description, base_price = PRODUCTS[category_name]
            product_id = get_or_create_product(cursor, product_name, description, category_id, base_price)

            for sku, size, color, price, stock_quantity, image_seed in VARIANTS[product_name]:
                variant_id = upsert_variant(cursor, product_id, sku, size, color, price, stock_quantity)
                variant_count += 1
                ensure_variant_image(
                    cursor, product_id, variant_id, f"https://picsum.photos/seed/{image_seed}/600/800"
                )
                image_count += 1

        connection.commit()
        print(
            f"Seeded {len(CATEGORIES)} categories, {len(PRODUCTS)} products, "
            f"{variant_count} variants, {image_count} product images."
        )
    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    sys.exit(seed())
