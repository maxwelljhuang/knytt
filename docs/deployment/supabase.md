# Deploying to Supabase Cloud

This guide walks you through deploying the Knytt database and authentication to Supabase Cloud.

## Overview

Supabase provides:
- **PostgreSQL Database** with pgvector extension for embeddings
- **Authentication** with JWT tokens
- **Storage** for product images (optional)
- **Real-time** subscriptions (optional)
- **Auto-generated REST API** (not used - we use custom FastAPI backend)

## Prerequisites

- Supabase account (free tier available at [supabase.com](https://supabase.com))
- Supabase CLI installed locally
- Local development environment working

## Step 1: Create Supabase Project

### 1.1 Create New Project

1. Go to [https://app.supabase.com](https://app.supabase.com)
2. Click "New Project"
3. Fill in project details:
   - **Name**: `knytt-production` (or your preferred name)
   - **Database Password**: Generate a strong password (save it securely!)
   - **Region**: Choose closest to your users (e.g., `us-east-1`, `eu-west-1`)
   - **Pricing Plan**: Free tier for development, Pro for production

4. Click "Create new project" and wait ~2 minutes for provisioning

### 1.2 Get Project Credentials

Once created, go to **Project Settings > API**:

```bash
# You'll need these values:
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

Go to **Project Settings > Database** for the connection string:

```bash
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

## Step 2: Link Local Project to Supabase Cloud

### 2.1 Login to Supabase CLI

```bash
supabase login
```

This opens a browser window to authenticate.

### 2.2 Link Project

```bash
cd /Users/jin.huang/claude/knytt/knytt

# Link to your Supabase Cloud project
supabase link --project-ref your-project-ref

# Get your project ref from the Supabase dashboard URL:
# https://app.supabase.com/project/YOUR-PROJECT-REF
```

### 2.3 Verify Connection

```bash
supabase status
```

You should see your cloud project details.

## Step 3: Create Database Schema

Since we're using SQLAlchemy models, we'll create the schema directly using our Python script.

### 3.1 Update Environment Variables

Create a `.env.production` file:

```bash
# Supabase Cloud
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# Database (use connection pooler for production)
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# API
API_HOST=0.0.0.0
API_PORT=8001

# ML Configuration
CLIP_MODEL=ViT-B/32
EMBEDDING_DIMENSION=512
```

### 3.2 Create Schema on Cloud Database

```bash
# Activate virtual environment
source venv/bin/activate

# Run database creation script with production environment
DATABASE_URL="postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres" python create_db.py
```

This creates all 6 tables:
- `users`
- `user_embeddings`
- `user_interactions`
- `products`
- `product_embeddings`
- `task_executions`

### 3.3 Verify Schema

Login to Supabase Studio and check the Table Editor:
```
https://app.supabase.com/project/YOUR-PROJECT-REF/editor
```

You should see all 6 tables listed.

## Step 4: Configure Authentication

Supabase Auth is automatically enabled. Configure settings in **Authentication > Providers**.

### 4.1 Email Authentication

1. Go to **Authentication > Providers > Email**
2. Enable "Email provider"
3. **Confirm email**: Disable for development, enable for production
4. **Secure email change**: Enable
5. **Secure password change**: Enable

### 4.2 Configure Email Templates (Production)

Go to **Authentication > Email Templates** to customize:
- Confirmation email
- Password recovery email
- Email change confirmation

### 4.3 Configure Site URL

Go to **Authentication > URL Configuration**:

```
Site URL: https://your-frontend-domain.com
Redirect URLs:
  - http://localhost:3000/*
  - https://your-frontend-domain.com/*
```

## Step 5: Set Up Row Level Security (RLS)

Supabase automatically creates RLS policies. For our custom backend, we handle authorization in FastAPI, but it's good practice to enable RLS as a safety layer.

### 5.1 Enable RLS on All Tables

```sql
-- Run in Supabase SQL Editor
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_interactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE products ENABLE ROW LEVEL SECURITY;
ALTER TABLE product_embeddings ENABLE ROW LEVEL SECURITY;
ALTER TABLE task_executions ENABLE ROW LEVEL SECURITY;
```

### 5.2 Create Policies for Service Role

Since our backend uses the service role key, it bypasses RLS. For the anon key (if used directly from frontend):

```sql
-- Allow service role full access (already default)
-- Anon users can only read products
CREATE POLICY "Allow anon read products"
ON products FOR SELECT
TO anon
USING (true);

CREATE POLICY "Allow anon read product_embeddings"
ON product_embeddings FOR SELECT
TO anon
USING (true);

-- Authenticated users can read their own data
CREATE POLICY "Users can read own data"
ON users FOR SELECT
TO authenticated
USING (auth.uid()::text = id::text);

CREATE POLICY "Users can update own data"
ON users FOR UPDATE
TO authenticated
USING (auth.uid()::text = id::text);

-- Users can read/write their own interactions
CREATE POLICY "Users can read own interactions"
ON user_interactions FOR SELECT
TO authenticated
USING (auth.uid()::text = user_id::text);

CREATE POLICY "Users can create own interactions"
ON user_interactions FOR INSERT
TO authenticated
WITH CHECK (auth.uid()::text = user_id::text);
```

## Step 6: Optional - Set Up Storage for Product Images

If you want to store product images in Supabase Storage:

### 6.1 Create Storage Bucket

```sql
-- Run in Supabase SQL Editor
INSERT INTO storage.buckets (id, name, public)
VALUES ('product-images', 'product-images', true);
```

### 6.2 Set Storage Policies

```sql
-- Allow public read access to product images
CREATE POLICY "Public read access"
ON storage.objects FOR SELECT
TO public
USING (bucket_id = 'product-images');

-- Allow authenticated users to upload
CREATE POLICY "Authenticated users can upload"
ON storage.objects FOR INSERT
TO authenticated
WITH CHECK (bucket_id = 'product-images');
```

### 6.3 Update Backend to Use Supabase Storage

Update your backend code to upload images to Supabase Storage instead of local filesystem.

## Step 7: Test Connection from Backend

### 7.1 Test Database Connection

```bash
# Test connection with production database
python -c "from backend.db.session import engine; print(engine.connect())"
```

### 7.2 Test Backend API

```bash
# Start backend with production env
source venv/bin/activate
uvicorn backend.api.main:app --host 0.0.0.0 --port 8001 --env-file .env.production
```

Test endpoints:
```bash
# Health check
curl http://localhost:8001/health

# Test user registration
curl -X POST http://localhost:8001/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123","name":"Test User"}'

# Test login
curl -X POST http://localhost:8001/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'
```

## Step 8: Configure Frontend

Update `frontend/.env.local` with production credentials:

```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=https://your-backend-api.com  # This will be your Cloud Run URL
```

## Step 9: Monitoring and Maintenance

### 9.1 Database Usage

Monitor database usage in **Project Settings > Database**:
- Connection count
- Database size
- CPU usage

### 9.2 Set Up Backups

Supabase Pro includes:
- Daily backups (retained 7 days)
- Point-in-time recovery (PITR)

For Free tier, export your database regularly:

```bash
# Export database schema and data
supabase db dump -f backup.sql

# Or use pg_dump directly
pg_dump "postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres" > backup.sql
```

### 9.3 Monitor Logs

View logs in Supabase Dashboard:
- **Logs > Postgres Logs**: Database queries and errors
- **Logs > Auth Logs**: Authentication events
- **Logs > API Logs**: REST API calls (if using)

## Step 10: Connection Pooling

Supabase provides two connection methods:

### Direct Connection (for migrations, admin tasks)
```
postgresql://postgres:[PASSWORD]@db.your-project-ref.supabase.co:5432/postgres
```

### Pooled Connection (for applications) - RECOMMENDED
```
postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres
```

**Always use the pooled connection for your backend API in production.**

## Troubleshooting

### Connection Timeout

If you get connection timeouts:
1. Check that your IP is not blocked
2. Use connection pooler URL (port 6543)
3. Check firewall settings

### Too Many Connections

Free tier: 60 connections max
Pro tier: 200+ connections

Solutions:
- Use connection pooling (PgBouncer is built-in)
- Adjust SQLAlchemy pool size in `backend/db/session.py`:
  ```python
  engine = create_engine(
      DATABASE_URL,
      pool_size=5,  # Reduce for cloud
      max_overflow=10,
      pool_pre_ping=True,
  )
  ```

### Extension Not Found

If pgvector is not available:
```sql
-- Run in SQL Editor
CREATE EXTENSION IF NOT EXISTS vector;
```

### RLS Blocking Queries

If queries fail with permission errors, check RLS policies or temporarily disable:
```sql
ALTER TABLE table_name DISABLE ROW LEVEL SECURITY;
```

## Cost Estimation

### Free Tier (Development)
- 500 MB database
- 1 GB file storage
- 2 GB bandwidth
- 50,000 monthly active users
- 7-day log retention

**Cost**: $0/month

### Pro Tier (Production)
- 8 GB database (+ $0.125/GB extra)
- 100 GB file storage (+ $0.021/GB extra)
- 250 GB bandwidth (+ $0.09/GB extra)
- Daily backups + PITR
- 90-day log retention

**Cost**: $25/month base + usage

## Next Steps

1. Deploy backend API to **GCP Cloud Run** - see [gcp-cloud-run.md](./gcp-cloud-run.md)
2. Deploy frontend to **Cloudflare Pages** - see [cloudflare-pages.md](./cloudflare-pages.md)
3. Configure custom domains
4. Set up monitoring and alerts

## Resources

- [Supabase Documentation](https://supabase.com/docs)
- [Supabase CLI Reference](https://supabase.com/docs/guides/cli)
- [Database Connection Pooling](https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler)
- [PostgreSQL Best Practices](https://supabase.com/docs/guides/database/postgres)
