# Knytt Deployment Guide

Complete guide for deploying the Knytt e-commerce platform to production using Railway (backend) and Vercel (frontend).

## Table of Contents

- [Quick Start](#quick-start)
- [Prerequisites](#prerequisites)
- [Deployment Architecture](#deployment-architecture)
- [Step-by-Step Deployment](#step-by-step-deployment)
- [Post-Deployment](#post-deployment)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

---

## Quick Start

**Estimated Time**: 2-3 hours
**Estimated Cost**: $70-150/month

### Architecture Overview

```
┌─────────────────┐
│   Vercel        │  ← Frontend (Next.js)
│  $20/month      │
└────────┬────────┘
         │
         │ HTTPS
         │
┌────────▼────────┐
│   Railway       │  ← Backend Infrastructure
│  $50-130/month  │
├─────────────────┤
│  - API Service  │
│  - Celery Worker│
│  - Celery Beat  │
│  - PostgreSQL   │
│  - Redis        │
└─────────────────┘
```

---

## Prerequisites

### Required Accounts
- [ ] GitHub account (with Knytt repository)
- [ ] Railway account → [Sign up](https://railway.app)
- [ ] Vercel account → [Sign up](https://vercel.com)
- [ ] Credit card for Railway billing

### Required Tools
```bash
# Install Railway CLI (optional)
npm install -g @railway/cli

# Install Vercel CLI (optional)
npm install -g vercel
```

### Prepare Repository
```bash
# Generate production secrets
./scripts/generate_secrets.sh

# Verify local build works
docker-compose build
docker-compose up -d
```

---

## Deployment Architecture

### Railway Services

| Service | Description | Resources | Port |
|---------|-------------|-----------|------|
| **api** | FastAPI backend | 2GB RAM, 2 vCPU | 8000 |
| **celery-worker** | Background task processor | 1-2GB RAM | N/A |
| **celery-beat** | Task scheduler (singleton) | 512MB RAM | N/A |
| **postgres** | Database with pgvector | 1-2GB RAM | 5432 |
| **redis** | Cache & Celery broker | 256-512MB RAM | 6379 |

### Vercel Configuration

- **Framework**: Next.js 16
- **Build Command**: `npm run build`
- **Root Directory**: `frontend`
- **Node Version**: 18.x

---

## Step-by-Step Deployment

### Part 1: Backend Deployment (Railway)

#### 1.1 Create Railway Project

```bash
# Login to Railway
railway login

# Initialize project
railway init

# Link to your GitHub repo
railway link
```

Or use the Railway Dashboard:
1. Go to https://railway.app/new
2. Select "Deploy from GitHub repo"
3. Choose your `knytt` repository

#### 1.2 Add PostgreSQL Database

```bash
# Using CLI
railway add --database postgres

# Or via Dashboard:
# Click "+ New" → "Database" → "PostgreSQL"
```

**Enable pgvector extension:**

```bash
# Connect to database
railway connect postgres

# Run in psql
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
```

#### 1.3 Add Redis

```bash
# Using CLI
railway add --database redis

# Or via Dashboard:
# Click "+ New" → "Database" → "Redis"
```

#### 1.4 Deploy API Service

**Configure environment variables in Railway:**

```bash
# Database (auto-populated by Railway)
DATABASE_URL=${{Postgres.DATABASE_URL}}
DB_USER=${{Postgres.PGUSER}}
DB_PASSWORD=${{Postgres.PGPASSWORD}}
DB_NAME=${{Postgres.PGDATABASE}}
DB_HOST=${{Postgres.PGHOST}}
DB_PORT=${{Postgres.PGPORT}}

# Redis (auto-populated by Railway)
REDIS_URL=${{Redis.REDIS_URL}}
CELERY_BROKER_URL=${{Redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}

# Security (GENERATE NEW SECRETS!)
JWT_SECRET_KEY=<run: openssl rand -hex 32>
SECRET_KEY=<run: openssl rand -hex 32>

# Application
APP_ENV=production
DEBUG=false
LOG_LEVEL=INFO
CORS_ORIGINS=https://your-app.vercel.app

# ML Configuration
ENABLE_EMBEDDINGS=true
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

**Set custom start command:**

```bash
# In Railway Dashboard → Settings → Deploy
uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT
```

**Generate public domain:**
- Go to Settings → Networking
- Click "Generate Domain"
- Note your API URL: `https://your-api.up.railway.app`

#### 1.5 Deploy Celery Worker

Create a new service from the same repo:

**Start Command:**
```bash
celery -A backend.tasks.celery_app worker --loglevel=info --pool=solo
```

**Environment Variables:**
- Copy all variables from API service
- Or use Railway's "Reference Variables" feature

#### 1.6 Deploy Celery Beat

Create another service from the same repo:

**Start Command:**
```bash
celery -A backend.tasks.celery_app beat --loglevel=info
```

**Environment Variables:**
- Same as API and Worker

⚠️ **Important**: Only run ONE instance of Celery Beat!

#### 1.7 Run Database Migrations

```bash
# Using Railway CLI
railway run alembic upgrade head

# Verify database schema
railway run python scripts/verify_database.py
```

#### 1.8 Configure Persistent Storage

For FAISS indices and ML models:

**Option A: Railway Volumes**
1. Go to API service → Settings → Volumes
2. Add volumes:
   - `/app/models` (5GB) - ML model cache
   - `/app/data/indices` (2GB) - FAISS indices
   - `/app/logs` (1GB) - Application logs

**Option B: Use S3/R2** (Recommended for production)
- Upload models and indices to cloud storage
- Configure S3 credentials in environment variables

---

### Part 2: Frontend Deployment (Vercel)

#### 2.1 Deploy to Vercel

**Via Vercel Dashboard:**

1. Go to https://vercel.com/new
2. Import your `knytt` repository
3. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build` (auto-detected)
   - **Install Command**: `npm install` (auto-detected)

4. Add Environment Variables:
   ```
   NEXT_PUBLIC_API_BASE_URL=https://your-api.up.railway.app
   NEXT_PUBLIC_APP_ENV=production
   ```

5. Click "Deploy"

**Via Vercel CLI:**

```bash
cd frontend
vercel login
vercel --prod
```

#### 2.2 Get Vercel URL

After deployment, you'll get:
- Preview URL: `https://knytt-xxx.vercel.app`
- Production URL (if custom domain): `https://your-domain.com`

#### 2.3 Update CORS in Railway

Update the API service environment variables:

```bash
CORS_ORIGINS=https://knytt-xxx.vercel.app,https://your-domain.com
```

Redeploy the API service for changes to take effect.

---

## Post-Deployment

### Verify Deployment

#### 1. Test API Health

```bash
curl https://your-api.up.railway.app/health
# Expected: {"status":"healthy","timestamp":"..."}
```

#### 2. Test Search Endpoint

```bash
curl "https://your-api.up.railway.app/api/v1/search?q=shoes&limit=10"
# Should return product results
```

#### 3. Test Frontend

Visit your Vercel URL:
```
https://knytt-xxx.vercel.app
```

- Search for products
- Register/login
- Check recommendations
- Verify images load

#### 4. Check Service Logs

**Railway:**
- Go to each service → Logs
- Verify no errors
- Check that FAISS index loaded

**Vercel:**
- Go to Deployments → Latest → Logs
- Check for build/runtime errors

### Configure Monitoring

#### Set Up Sentry (Error Tracking)

1. Create account at https://sentry.io
2. Create projects for Backend (Python) and Frontend (Next.js)
3. Add DSNs to environment variables:

**Railway (API service):**
```bash
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_ENVIRONMENT=production
```

**Vercel:**
```bash
NEXT_PUBLIC_SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
```

#### Configure Backups

Create automated database backups:

```bash
# Use the provided GitHub Action
# See .github/workflows/backup-db.yml

# Or manually with Railway CLI
railway run pg_dump > backup_$(date +%Y%m%d).sql
```

---

## Monitoring

### Railway Metrics

Monitor in Railway Dashboard:
- CPU usage
- Memory usage
- Network traffic
- Request count
- Error rate

### Vercel Analytics

Enable in Vercel Dashboard:
- Page views
- Core Web Vitals
- API response times
- Geographic distribution

### Health Checks

Set up external monitoring (optional):
- [UptimeRobot](https://uptimerobot.com) - Free tier available
- [Pingdom](https://pingdom.com)
- [Better Stack](https://betterstack.com)

Monitor endpoints:
- `https://your-api.up.railway.app/health` (every 5 min)
- `https://knytt-xxx.vercel.app` (every 5 min)

---

## Troubleshooting

### API Returns 502

**Symptoms:** Frontend can't reach API

**Solutions:**
1. Check Railway logs for crashes
2. Verify `PORT` environment variable is used
3. Ensure DATABASE_URL is correct
4. Check health endpoint: `/health`

### CORS Errors

**Symptoms:** Browser console shows CORS policy errors

**Solutions:**
1. Update `CORS_ORIGINS` in Railway
2. Include both Vercel preview and production URLs
3. Redeploy API service
4. Clear browser cache

### Database Connection Failed

**Symptoms:** `OperationalError: could not connect to server`

**Solutions:**
1. Verify DATABASE_URL format
2. Check PostgreSQL service is running
3. Use Railway reference syntax: `${{Postgres.DATABASE_URL}}`
4. Test connection: `railway connect postgres`

### Images Not Loading

**Symptoms:** Product images broken

**Solutions:**
1. Check Next.js image configuration
2. Verify image URLs are valid (check database)
3. Review `next.config.ts` remote patterns
4. Check browser console for errors

### Celery Tasks Not Running

**Symptoms:** Scheduled tasks don't execute

**Solutions:**
1. Check Celery worker logs
2. Verify CELERY_BROKER_URL points to Redis
3. Ensure Redis is running
4. Check only ONE Celery beat instance

### Out of Memory

**Symptoms:** Railway shows "Container killed (OOM)"

**Solutions:**
1. Increase memory in Railway service settings
2. Optimize FAISS index size
3. Enable `USE_FP16=true` for models
4. Consider upgrading Railway plan

---

## Cost Optimization

### Railway

- Start with smaller resource allocations
- Use horizontal scaling only when needed
- Implement caching to reduce database queries
- Monitor usage in Railway dashboard

### Vercel

- Stay on Pro plan ($20/month) for most use cases
- Optimize images (Next.js handles this automatically)
- Use ISR (Incremental Static Regeneration) for product pages
- Enable Edge Caching

---

## Security Checklist

- [ ] Changed all default secrets (JWT_SECRET_KEY, SECRET_KEY)
- [ ] Set DEBUG=false in production
- [ ] Configured proper CORS_ORIGINS
- [ ] Enabled HTTPS (automatic on Railway/Vercel)
- [ ] Set up Sentry for error tracking
- [ ] Configured database backups
- [ ] Reviewed environment variables (no secrets committed)
- [ ] Enabled rate limiting
- [ ] Set up monitoring alerts

---

## Scaling Guide

### When to Scale

Monitor these metrics:
- Response time > 1 second
- CPU usage consistently > 70%
- Memory usage > 80%
- Error rate > 1%

### Horizontal Scaling

**Railway:**
- API service: Scale to 2-3 replicas
- Celery workers: Add more worker instances
- Database: Upgrade to larger instance

**Vercel:**
- Automatically scales with traffic
- Consider upgrading to Enterprise for high traffic

---

## Support Resources

- **Railway**: https://railway.app/help
- **Vercel**: https://vercel.com/support
- **Project Issues**: GitHub Issues in your repo
- **Community**: Stack Overflow with relevant tags

---

## Quick Command Reference

```bash
# Railway
railway login
railway link
railway add --database postgres
railway connect postgres
railway run <command>
railway logs

# Vercel
vercel login
vercel --prod
vercel domains add <domain>
vercel env add

# Database
alembic upgrade head
pg_dump <DATABASE_URL> > backup.sql

# Secrets
openssl rand -hex 32  # Generate secret
```

---

**Deployment Guide Version**: 1.0
**Last Updated**: 2025-11-05
**Estimated Deployment Time**: 2-3 hours
**Monthly Cost**: $70-150
