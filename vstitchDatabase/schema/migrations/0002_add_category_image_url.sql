-- Migration: adds VStitch_Categories.ImageUrl - one banner/thumbnail image per
-- category (nullable, Supabase Storage URL), for category nav/listing pages.
-- Run once, directly against Supabase (matches how the rest of the schema is
-- applied - see README "Database schema").

ALTER TABLE VStitch_Categories
    ADD COLUMN IF NOT EXISTS ImageUrl VARCHAR(500);
