-- SQL script to add cloudinary_public_id column if it doesn't exist
-- Run this on your production database if the migration hasn't been applied

-- Check if column exists and add it if missing
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'storage_files' 
        AND column_name = 'cloudinary_public_id'
    ) THEN
        ALTER TABLE storage_files 
        ADD COLUMN cloudinary_public_id VARCHAR(512);
        
        CREATE INDEX IF NOT EXISTS storage_files_cloudinary_public_id_idx 
        ON storage_files(cloudinary_public_id);
        
        RAISE NOTICE 'Column cloudinary_public_id added successfully';
    ELSE
        RAISE NOTICE 'Column cloudinary_public_id already exists';
    END IF;
END $$;

-- Also add other cloudinary columns if they don't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'storage_files' 
        AND column_name = 'cloudinary_folder'
    ) THEN
        ALTER TABLE storage_files 
        ADD COLUMN cloudinary_folder VARCHAR(512);
        RAISE NOTICE 'Column cloudinary_folder added successfully';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'storage_files' 
        AND column_name = 'cloudinary_url'
    ) THEN
        ALTER TABLE storage_files 
        ADD COLUMN cloudinary_url VARCHAR(1024);
        RAISE NOTICE 'Column cloudinary_url added successfully';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'storage_files' 
        AND column_name = 'cloudinary_resource_type'
    ) THEN
        ALTER TABLE storage_files 
        ADD COLUMN cloudinary_resource_type VARCHAR(20) DEFAULT 'image';
        RAISE NOTICE 'Column cloudinary_resource_type added successfully';
    END IF;
END $$;




