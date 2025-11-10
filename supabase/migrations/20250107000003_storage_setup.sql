-- Storage Buckets Configuration for Knytt
-- Setup for product images, user avatars, and data files

-- =====================================================
-- STORAGE BUCKETS
-- =====================================================

-- Product images bucket (public)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'product-images',
    'product-images',
    true,
    52428800, -- 50MB limit
    ARRAY['image/jpeg', 'image/png', 'image/webp', 'image/gif']::text[]
)
ON CONFLICT (id) DO NOTHING;

-- User avatars bucket (public)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'avatars',
    'avatars',
    true,
    5242880, -- 5MB limit
    ARRAY['image/jpeg', 'image/png', 'image/webp']::text[]
)
ON CONFLICT (id) DO NOTHING;

-- CSV data uploads bucket (private - for ingestion)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'data-uploads',
    'data-uploads',
    false,
    524288000, -- 500MB limit
    ARRAY['text/csv', 'application/csv', 'text/plain']::text[]
)
ON CONFLICT (id) DO NOTHING;

-- FAISS indices bucket (private - for ML models)
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
VALUES (
    'ml-models',
    'ml-models',
    false,
    5242880000, -- 5GB limit
    ARRAY['application/octet-stream']::text[]
)
ON CONFLICT (id) DO NOTHING;

-- =====================================================
-- STORAGE POLICIES
-- =====================================================

-- Product Images: Anyone can read, only service role can upload
DROP POLICY IF EXISTS "Product images are publicly accessible" ON storage.objects;
CREATE POLICY "Product images are publicly accessible"
ON storage.objects FOR SELECT
USING (bucket_id = 'product-images');

DROP POLICY IF EXISTS "Only service role can upload product images" ON storage.objects;
CREATE POLICY "Only service role can upload product images"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'product-images'
    AND auth.role() = 'service_role'
);

DROP POLICY IF EXISTS "Only service role can update product images" ON storage.objects;
CREATE POLICY "Only service role can update product images"
ON storage.objects FOR UPDATE
USING (
    bucket_id = 'product-images'
    AND auth.role() = 'service_role'
);

DROP POLICY IF EXISTS "Only service role can delete product images" ON storage.objects;
CREATE POLICY "Only service role can delete product images"
ON storage.objects FOR DELETE
USING (
    bucket_id = 'product-images'
    AND auth.role() = 'service_role'
);

-- User Avatars: Anyone can read, users can manage their own
DROP POLICY IF EXISTS "Avatars are publicly accessible" ON storage.objects;
CREATE POLICY "Avatars are publicly accessible"
ON storage.objects FOR SELECT
USING (bucket_id = 'avatars');

DROP POLICY IF EXISTS "Users can upload their own avatar" ON storage.objects;
CREATE POLICY "Users can upload their own avatar"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'avatars'
    AND (storage.foldername(name))[1] = auth.uid()::text
);

DROP POLICY IF EXISTS "Users can update their own avatar" ON storage.objects;
CREATE POLICY "Users can update their own avatar"
ON storage.objects FOR UPDATE
USING (
    bucket_id = 'avatars'
    AND (storage.foldername(name))[1] = auth.uid()::text
);

DROP POLICY IF EXISTS "Users can delete their own avatar" ON storage.objects;
CREATE POLICY "Users can delete their own avatar"
ON storage.objects FOR DELETE
USING (
    bucket_id = 'avatars'
    AND (storage.foldername(name))[1] = auth.uid()::text
);

-- Data Uploads: Only service role can access
DROP POLICY IF EXISTS "Only service role can read data uploads" ON storage.objects;
CREATE POLICY "Only service role can read data uploads"
ON storage.objects FOR SELECT
USING (
    bucket_id = 'data-uploads'
    AND auth.role() = 'service_role'
);

DROP POLICY IF EXISTS "Only service role can upload data files" ON storage.objects;
CREATE POLICY "Only service role can upload data files"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'data-uploads'
    AND auth.role() = 'service_role'
);

DROP POLICY IF EXISTS "Only service role can delete data files" ON storage.objects;
CREATE POLICY "Only service role can delete data files"
ON storage.objects FOR DELETE
USING (
    bucket_id = 'data-uploads'
    AND auth.role() = 'service_role'
);

-- ML Models: Only service role can access
DROP POLICY IF EXISTS "Only service role can read ML models" ON storage.objects;
CREATE POLICY "Only service role can read ML models"
ON storage.objects FOR SELECT
USING (
    bucket_id = 'ml-models'
    AND auth.role() = 'service_role'
);

DROP POLICY IF EXISTS "Only service role can upload ML models" ON storage.objects;
CREATE POLICY "Only service role can upload ML models"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'ml-models'
    AND auth.role() = 'service_role'
);

DROP POLICY IF EXISTS "Only service role can delete ML models" ON storage.objects;
CREATE POLICY "Only service role can delete ML models"
ON storage.objects FOR DELETE
USING (
    bucket_id = 'ml-models'
    AND auth.role() = 'service_role'
);

-- =====================================================
-- HELPER FUNCTION: Generate storage URL
-- =====================================================
CREATE OR REPLACE FUNCTION get_product_image_url(bucket text, path text)
RETURNS text
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN format('%s/storage/v1/object/public/%s/%s',
        current_setting('app.settings.supabase_url', true),
        bucket,
        path
    );
END;
$$;

COMMENT ON FUNCTION get_product_image_url IS 'Generate full URL for product images';
