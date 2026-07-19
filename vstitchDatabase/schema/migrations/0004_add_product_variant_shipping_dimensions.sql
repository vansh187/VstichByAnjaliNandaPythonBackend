-- Migration: adds package weight/dimensions to VStitch_ProductVariants so a
-- Shiprocket shipment can be created after payment capture. Shiprocket's
-- create-order API requires weight/length/breadth/height per shipment
-- (min 0.5cm per side, weight > 0) and nothing in the schema captured this
-- before now. Nullable rather than NOT NULL, since existing rows have no
-- value yet and backfilling one is a catalog-data task, not a schema one -
-- shipment creation itself rejects (ValueError) any order whose items are
-- missing a value rather than silently sending Shiprocket a 0.

ALTER TABLE VStitch_ProductVariants
    ADD COLUMN IF NOT EXISTS WeightKg   NUMERIC(6,3),
    ADD COLUMN IF NOT EXISTS LengthCm   NUMERIC(6,2),
    ADD COLUMN IF NOT EXISTS BreadthCm  NUMERIC(6,2),
    ADD COLUMN IF NOT EXISTS HeightCm   NUMERIC(6,2);

ALTER TABLE VStitch_ProductVariants
    DROP CONSTRAINT IF EXISTS chk_variants_weight_kg;
ALTER TABLE VStitch_ProductVariants
    ADD CONSTRAINT chk_variants_weight_kg CHECK (WeightKg IS NULL OR WeightKg > 0);

ALTER TABLE VStitch_ProductVariants
    DROP CONSTRAINT IF EXISTS chk_variants_length_cm;
ALTER TABLE VStitch_ProductVariants
    ADD CONSTRAINT chk_variants_length_cm CHECK (LengthCm IS NULL OR LengthCm >= 0.5);

ALTER TABLE VStitch_ProductVariants
    DROP CONSTRAINT IF EXISTS chk_variants_breadth_cm;
ALTER TABLE VStitch_ProductVariants
    ADD CONSTRAINT chk_variants_breadth_cm CHECK (BreadthCm IS NULL OR BreadthCm >= 0.5);

ALTER TABLE VStitch_ProductVariants
    DROP CONSTRAINT IF EXISTS chk_variants_height_cm;
ALTER TABLE VStitch_ProductVariants
    ADD CONSTRAINT chk_variants_height_cm CHECK (HeightCm IS NULL OR HeightCm >= 0.5);
