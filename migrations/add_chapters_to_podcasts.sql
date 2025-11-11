-- Migration: Add chapters column to podcasts table
-- Date: 2025-11-10
-- Issue: #602
-- Description: Add chapters JSON column to store dynamic chapter markers with timestamps

-- Add chapters column (nullable, defaults to empty array)
ALTER TABLE podcasts
ADD COLUMN IF NOT EXISTS chapters JSONB DEFAULT '[]'::jsonb;

-- Add comment
COMMENT ON COLUMN podcasts.chapters IS 'Dynamic chapter markers with timestamps (title, start_time, end_time, word_count)';

-- Verify the column was added
SELECT column_name, data_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_name = 'podcasts' AND column_name = 'chapters';
