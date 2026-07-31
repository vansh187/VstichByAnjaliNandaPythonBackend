"""Production catalog reset + seed script (REVIEW BEFORE RUNNING).

Wipes all rows from the four catalog tables (categories, products, variants,
product images) - including their uploaded files in the Supabase Storage
bucket - and inserts one real category ("Cord Set") and one real product (a
black floral-embroidered co-ord set) with images uploaded to Storage.

This targets a PRODUCTION Supabase project. It is split into four parts and
will not delete anything without an interactive, exact-text confirmation:

    Part A - print live schema (columns/constraints) for the four tables and
              verify the configured Storage bucket actually exists.
    Part B - print current row counts + sample rows, then require you to
              type "confirmed, proceed" before deleting anything.
    Part C - upload the new images to Storage and insert the real category,
              product, one variant, and 3 product images.
    Part D - re-query everything and confirm every uploaded image URL
              actually returns HTTP 200.

Usage:
    python scripts/reset_and_seed_catalog.py

Requires in .env: DATABASE_URL, SUPABASE_SERVICE_ROLE_KEY.
Requires installed: Pillow (pip install Pillow) - requests/psycopg2 already
in requirements.txt.

The Supabase project's REST/Storage base URL is derived from DATABASE_URL's
own embedded project ref (the "postgres.<ref>" pooler username), not read
from a separate SUPABASE_URL variable - .env has previously drifted out of
sync with DATABASE_URL (pointed at a different project entirely), which
silently broke every Storage API call while DB queries kept working fine.
Deriving it from DATABASE_URL means the two can never disagree.
"""

import os
import re
import sys

import psycopg2
import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vstitchServices.supabaseStorageService import compress_to_webp  # noqa: E402

load_dotenv()


def derive_supabase_url(database_url):
    match = re.search(r"//postgres\.([a-z0-9]+):", database_url)
    if not match:
        print(
            "Could not find a 'postgres.<project-ref>' username in DATABASE_URL - "
            "expected Supabase's pooler connection string format."
        )
        sys.exit(1)
    return f"https://{match.group(1)}.supabase.co"

CREATED_BY = "catalog_reset_script"
BUCKET_NAME = "VStitch-catalogue-images"

CATEGORY_IMAGE_LOCAL_PATH = r"E:\VstitchImages\Cord set\CategoryImage.jpeg"
CATEGORY_IMAGE_STORAGE_PATH = "categories/cord-set/category-image.webp"
CATEGORY_NAME = "Cord Set"

PRODUCT_IMAGES_LOCAL_DIR = r"E:\VstitchImages\Cord set\Black DesignWhite"
PRODUCT_IMAGE_FILES = ["Full.png", "Design.png", "Bottom.jpg"]
PRODUCT_IMAGE_STORAGE_PREFIX = "products/cord-set/black-design-white"

PRODUCT_NAME = "Black Floral Embroidered Co-ord Set"
PRODUCT_DESCRIPTION = (
    "A relaxed-fit black co-ord set featuring an oversized cotton shirt with a "
    "classic collar and long balloon sleeves, finished with delicate white "
    "floral vine embroidery along the placket. The matching tailored shorts "
    "have a self-fabric tie-waist belt and contrast white piping for an "
    "adjustable, cinched fit - perfect for easy day-to-evening styling."
)
PRODUCT_BASE_PRICE = 1999.00  # Placeholder - update to the real selling price.

VARIANT_SKU = "CORDSET-BLKWHT-STD"
VARIANT_SIZE = "Standard"
VARIANT_COLOR = "Black"
VARIANT_PRICE = PRODUCT_BASE_PRICE
VARIANT_STOCK_QUANTITY = 10  # Placeholder - update to the real stock on hand.

CATALOG_TABLES_IN_DELETE_ORDER = [
    "VStitch_ProductImages",
    "VStitch_ProductVariants",
    "VStitch_Products",
    "VStitch_Categories",
]
# (table, id_column) pairs, lowercase to match Postgres's folded identifiers -
# used as literal string arguments to pg_get_serial_sequence, not as SQL
# identifiers, so they must match the catalog's actual stored names exactly.
CATALOG_SEQUENCES = [
    ("vstitch_productimages", "vstitchproductimageid"),
    ("vstitch_productvariants", "vstitchproductvariantid"),
    ("vstitch_products", "vstitchproductid"),
    ("vstitch_categories", "vstitchcategoryid"),
]

CONFIRMATION_PHRASE = "confirmed, proceed"


def verify_local_images_exist():
    """Fails fast, before touching production at all, if any source image is
    missing/unreadable - otherwise that failure would only surface after the
    production delete had already been committed (see the commit-ordering
    comment in main()), with nothing to replace the deleted data.
    """
    local_paths = [CATEGORY_IMAGE_LOCAL_PATH] + [
        os.path.join(PRODUCT_IMAGES_LOCAL_DIR, filename) for filename in PRODUCT_IMAGE_FILES
    ]
    missing_paths = [path for path in local_paths if not os.path.isfile(path)]
    if missing_paths:
        print("ERROR: the following source image(s) are missing - aborting before touching production:")
        for path in missing_paths:
            print(f"  {path}")
        sys.exit(1)
    print(f"Confirmed all {len(local_paths)} source image file(s) exist and are readable.")


def require_env(name):
    value = os.getenv(name)
    if not value:
        print(f"Missing required environment variable: {name}")
        sys.exit(1)
    return value


def banner(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


# --------------------------------------------------------------------------
# Part A - schema + bucket inspection
# --------------------------------------------------------------------------


def print_schema(cursor):
    banner("PART A - Live schema for catalog tables")
    tables = ["vstitch_categories", "vstitch_products", "vstitch_productvariants", "vstitch_productimages"]
    for table in tables:
        print(f"\n--- {table} ---")
        cursor.execute(
            """
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = %s
            ORDER BY ordinal_position;
            """,
            (table,),
        )
        for column_name, data_type, is_nullable, column_default in cursor.fetchall():
            print(f"  {column_name:30} {data_type:20} nullable={is_nullable:3} default={column_default}")

        cursor.execute(
            """
            SELECT tc.constraint_type, tc.constraint_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name AND tc.table_name = kcu.table_name
            WHERE tc.table_name = %s
            ORDER BY tc.constraint_type, tc.constraint_name;
            """,
            (table,),
        )
        for constraint_type, constraint_name, column_name in cursor.fetchall():
            print(f"  constraint: {constraint_type:12} {constraint_name:40} ({column_name})")


def verify_bucket_exists(cursor):
    cursor.execute("select id, name, public from storage.buckets;")
    rows = cursor.fetchall()
    print(f"\nAvailable Storage buckets: {rows}")

    matching = [row for row in rows if row[0] == BUCKET_NAME]
    if not matching:
        print(
            f"\nERROR: bucket id '{BUCKET_NAME}' not found. "
            f"Available bucket ids: {[row[0] for row in rows]}. "
            "Update BUCKET_NAME in this script to match exactly, then re-run."
        )
        sys.exit(1)

    _, _, is_public = matching[0]
    print(f"Confirmed bucket '{BUCKET_NAME}' exists (public={is_public}).")
    return is_public


# --------------------------------------------------------------------------
# Part B - inspect + delete existing test data
# --------------------------------------------------------------------------


def print_counts_and_samples(cursor, label):
    banner(f"PART B - Row counts ({label})")
    for table in CATALOG_TABLES_IN_DELETE_ORDER:
        cursor.execute(f"SELECT COUNT(*) FROM {table};")
        count = cursor.fetchone()[0]
        print(f"\n{table}: {count} rows")
        if count:
            cursor.execute(f"SELECT * FROM {table} LIMIT 5;")
            column_names = [desc[0] for desc in cursor.description]
            print(f"  columns: {column_names}")
            for row in cursor.fetchall():
                print(f"  {row}")


def delete_all_catalog_data(cursor):
    for table in CATALOG_TABLES_IN_DELETE_ORDER:
        cursor.execute(f"DELETE FROM {table};")
        print(f"Deleted all rows from {table}.")

    for table, id_column in CATALOG_SEQUENCES:
        cursor.execute(
            "SELECT setval(pg_get_serial_sequence(%s, %s), 1, false);",
            (table, id_column),
        )
        print(f"Reset identity sequence for {table}.{id_column} to start at 1.")


def list_storage_objects(prefix, headers, supabase_url):
    response = requests.post(
        f"{supabase_url}/storage/v1/object/list/{BUCKET_NAME}",
        headers=headers,
        json={"prefix": prefix, "limit": 1000},
        timeout=30,
    )
    response.raise_for_status()
    return [f"{prefix}{item['name']}" for item in response.json()]


def delete_storage_objects(paths, headers, supabase_url):
    if not paths:
        return
    response = requests.delete(
        f"{supabase_url}/storage/v1/object/{BUCKET_NAME}",
        headers=headers,
        json={"prefixes": paths},
        timeout=30,
    )
    response.raise_for_status()
    print(f"Deleted {len(paths)} storage object(s): {paths}")


def wipe_storage_bucket(headers, supabase_url):
    for prefix in ("categories/", "products/"):
        paths = list_storage_objects(prefix, headers, supabase_url)
        delete_storage_objects(paths, headers, supabase_url)


# --------------------------------------------------------------------------
# Part C - insert real category + product
# --------------------------------------------------------------------------


def read_and_compress_to_webp(local_path):
    with open(local_path, "rb") as local_file:
        return compress_to_webp(local_file.read())


def upload_image(storage_path, image_bytes, headers, supabase_url):
    upload_headers = dict(headers)
    upload_headers["Content-Type"] = "image/webp"
    response = requests.post(
        f"{supabase_url}/storage/v1/object/{BUCKET_NAME}/{storage_path}",
        headers=upload_headers,
        data=image_bytes,
        timeout=60,
    )
    response.raise_for_status()
    print(f"Uploaded {storage_path} ({len(image_bytes)} bytes).")


def build_image_url(storage_path, is_public, headers, supabase_url):
    if is_public:
        return f"{supabase_url}/storage/v1/object/public/{BUCKET_NAME}/{storage_path}"

    response = requests.post(
        f"{supabase_url}/storage/v1/object/sign/{BUCKET_NAME}/{storage_path}",
        headers=headers,
        json={"expiresIn": 60 * 60 * 24 * 365 * 10},  # 10 years - bucket is private long-term
        timeout=30,
    )
    response.raise_for_status()
    signed_path = response.json()["signedURL"]
    return f"{supabase_url}/storage/v1{signed_path}"


def insert_category(cursor, image_url):
    cursor.execute(
        """
        INSERT INTO VStitch_Categories (CategoryName, ImageUrl, IsActive, created_by, created_date)
        VALUES (%s, %s, TRUE, %s, CURRENT_TIMESTAMP)
        RETURNING VstitchCategoryId;
        """,
        (CATEGORY_NAME, image_url, CREATED_BY),
    )
    return cursor.fetchone()[0]


def insert_product(cursor, category_id):
    cursor.execute(
        """
        INSERT INTO VStitch_Products
            (ProductName, Description, VstitchCategoryId, BasePrice, IsActive, created_by, created_date)
        VALUES (%s, %s, %s, %s, TRUE, %s, CURRENT_TIMESTAMP)
        RETURNING VstitchProductId;
        """,
        (PRODUCT_NAME, PRODUCT_DESCRIPTION, category_id, PRODUCT_BASE_PRICE, CREATED_BY),
    )
    return cursor.fetchone()[0]


def insert_variant(cursor, product_id):
    cursor.execute(
        """
        INSERT INTO VStitch_ProductVariants
            (VstitchProductId, Sku, Size, Color, Price, StockQuantity, IsActive, created_by, created_date)
        VALUES (%s, %s, %s, %s, %s, %s, TRUE, %s, CURRENT_TIMESTAMP)
        RETURNING VstitchProductVariantId;
        """,
        (product_id, VARIANT_SKU, VARIANT_SIZE, VARIANT_COLOR, VARIANT_PRICE, VARIANT_STOCK_QUANTITY, CREATED_BY),
    )
    return cursor.fetchone()[0]


def insert_product_image(cursor, product_id, variant_id, image_url, is_primary, display_order):
    cursor.execute(
        """
        INSERT INTO VStitch_ProductImages
            (VstitchProductId, VstitchProductVariantId, ImageUrl, IsPrimary, DisplayOrder, created_by, created_date)
        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP);
        """,
        (product_id, variant_id, image_url, is_primary, display_order, CREATED_BY),
    )


def seed_real_catalog_data(cursor, is_public, headers, supabase_url):
    banner("PART C - Uploading images and inserting real catalog data")

    category_image_bytes = read_and_compress_to_webp(CATEGORY_IMAGE_LOCAL_PATH)
    upload_image(CATEGORY_IMAGE_STORAGE_PATH, category_image_bytes, headers, supabase_url)
    category_image_url = build_image_url(CATEGORY_IMAGE_STORAGE_PATH, is_public, headers, supabase_url)

    category_id = insert_category(cursor, category_image_url)
    print(f"Inserted category '{CATEGORY_NAME}' -> id={category_id}")

    product_id = insert_product(cursor, category_id)
    print(f"Inserted product '{PRODUCT_NAME}' -> id={product_id}")

    variant_id = insert_variant(cursor, product_id)
    print(f"Inserted variant '{VARIANT_SKU}' -> id={variant_id}")

    image_urls = []
    for index, filename in enumerate(PRODUCT_IMAGE_FILES):
        local_path = os.path.join(PRODUCT_IMAGES_LOCAL_DIR, filename)
        storage_path = f"{PRODUCT_IMAGE_STORAGE_PREFIX}/{index + 1:02d}.webp"
        image_bytes = read_and_compress_to_webp(local_path)
        upload_image(storage_path, image_bytes, headers, supabase_url)
        image_url = build_image_url(storage_path, is_public, headers, supabase_url)
        image_urls.append(image_url)
        insert_product_image(
            cursor,
            product_id,
            variant_id,
            image_url,
            is_primary=(index == 0),
            display_order=index,
        )
        print(f"Inserted product image #{index + 1}: {image_url}")

    return category_id, product_id, variant_id, image_urls


# --------------------------------------------------------------------------
# Part D - verify
# --------------------------------------------------------------------------


def verify_final_state(cursor, image_urls):
    banner("PART D - Verifying inserted rows and image URLs")
    print_counts_and_samples(cursor, "after insert")

    print("\nChecking uploaded image URLs return HTTP 200:")
    for url in image_urls:
        try:
            response = requests.get(url, timeout=30)
            status = "OK" if response.status_code == 200 else "FAIL"
            print(f"  [{status}] {response.status_code} {url}")
        except requests.RequestException as error:
            print(f"  [FAIL] {url} -> {error}")


def main():
    database_url = require_env("DATABASE_URL")
    supabase_url = derive_supabase_url(database_url)
    service_role_key = require_env("SUPABASE_SERVICE_ROLE_KEY")
    headers = {
        "apikey": service_role_key,
        "Authorization": f"Bearer {service_role_key}",
    }
    print(f"Derived Supabase project URL from DATABASE_URL: {supabase_url}")

    verify_local_images_exist()

    connection = psycopg2.connect(database_url)
    cursor = connection.cursor()
    try:
        print_schema(cursor)
        is_public = verify_bucket_exists(cursor)

        print_counts_and_samples(cursor, "current, before any deletion")

        banner("PART B - Confirmation required before deletion")
        print(
            "This will permanently delete ALL rows from VStitch_Categories, "
            "VStitch_Products, VStitch_ProductVariants, VStitch_ProductImages "
            "AND all files under categories/ and products/ in the "
            f"'{BUCKET_NAME}' Storage bucket on a PRODUCTION project."
        )
        answer = input(f"Type '{CONFIRMATION_PHRASE}' to continue, anything else aborts: ")
        if answer.strip() != CONFIRMATION_PHRASE:
            print("Confirmation phrase did not match. Aborting - no changes made.")
            connection.rollback()
            sys.exit(1)

        # Deletion and the reseed below share ONE transaction, committed only
        # once both succeed - if seeding fails partway (bad image, a Storage
        # upload error, whatever), rolling back must undo the delete too, or
        # production is left permanently empty with nothing to replace it.
        # (The Storage-bucket wipe/re-upload calls just below are still their
        # own irreversible side effects outside this DB transaction - the
        # pre-flight file check above and this single-commit ordering are
        # what keep the DB side safe, not a guarantee across both systems.)
        delete_all_catalog_data(cursor)
        wipe_storage_bucket(headers, supabase_url)
        print("\nDeletion staged (not yet committed).")

        print_counts_and_samples(cursor, "after deletion, before commit - expect all 0")

        _, _, _, image_urls = seed_real_catalog_data(cursor, is_public, headers, supabase_url)
        connection.commit()
        print("\nDeletion + insert committed together.")

        verify_final_state(cursor, image_urls)

    except Exception:
        connection.rollback()
        raise
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    main()
