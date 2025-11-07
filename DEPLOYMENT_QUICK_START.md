# Knytt Deployment Quick Start Guide

**Ready to deploy in 2-3 hours!**

## Prerequisites Checklist

- [ ] GitHub account
- [ ] Railway account ([Sign up](https://railway.app))
- [ ] Vercel account ([Sign up](https://vercel.com))
- [ ] Credit card for Railway

## Step 1: Generate Secrets (5 minutes)

```bash
# Run the secret generator
./scripts/generate_secrets.sh

# This will generate:
# - JWT_SECRET_KEY
# - SECRET_KEY
# - DB_PASSWORD (if needed)
```

Save these secrets - you'll need them for Railway!

## Step 2: Deploy Backend to Railway (45-60 minutes)

### 2.1 Create Project

1. Go to https://railway.app/new
2. Click "Deploy from GitHub repo"
3. Select your `knytt` repository

### 2.2 Add Services

**Add PostgreSQL:**
```bash
# Via Dashboard: + New → Database → PostgreSQL
# Enable pgvector extension (see DEPLOYMENT.md)
```

**Add Redis:**
```bash
# Via Dashboard: + New → Database → Redis
```

**Deploy API Service:**
1. Service already created from repo
2. Set start command: `uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT`
3. Add environment variables (copy from `.env.production.example`)
4. Generate domain: Settings → Networking → Generate Domain

**Deploy Celery Worker:**
1. + New → GitHub Repo → Select knytt
2. Set start command: `celery -A backend.tasks.celery_app worker --loglevel=info --pool=solo`
3. Copy environment variables from API service

**Deploy Celery Beat:**
1. + New → GitHub Repo → Select knytt
2. Set start command: `celery -A backend.tasks.celery_app beat --loglevel=info`
3. Copy environment variables from API service

### 2.3 Critical Environment Variables

Set these in Railway (API service):

```bash
# Database (auto-populated)
DATABASE_URL=${{Postgres.DATABASE_URL}}

# Redis (auto-populated)
REDIS_URL=${{Redis.REDIS_URL}}
CELERY_BROKER_URL=${{Redis.REDIS_URL}}

# Security (USE YOUR GENERATED SECRETS!)
JWT_SECRET_KEY=<your-generated-jwt-secret>
SECRET_KEY=<your-generated-secret-key>

# Application
APP_ENV=production
DEBUG=false
CORS_ORIGINS=https://your-app.vercel.app  # Update after Vercel deployment

# ML
ENABLE_EMBEDDINGS=true
```

### 2.4 Run Migrations

```bash
railway run alembic upgrade head
```

### 2.5 Note Your API URL

Your Railway API URL will be: `https://your-api.up.railway.app`

## Step 3: Deploy Frontend to Vercel (30 minutes)

### 3.1 Import Project

1. Go to https://vercel.com/new
2. Import your `knytt` repository
3. Configure:
   - **Framework**: Next.js (auto-detected)
   - **Root Directory**: `frontend`

### 3.2 Set Environment Variables

```bash
NEXT_PUBLIC_API_BASE_URL=https://your-api.up.railway.app
NEXT_PUBLIC_APP_ENV=production
```

### 3.3 Deploy

Click "Deploy" - takes 2-3 minutes

### 3.4 Note Your Frontend URL

Your Vercel URL will be: `https://knytt-xxx.vercel.app`

## Step 4: Update CORS (5 minutes)

1. Go back to Railway
2. API service → Variables
3. Update `CORS_ORIGINS`:
   ```bash
   CORS_ORIGINS=https://knytt-xxx.vercel.app
   ```
4. Service will auto-redeploy

## Step 5: Verify Deployment (15 minutes)

Run the verification script:

```bash
./scripts/verify_deployment.sh \
  https://your-api.up.railway.app \
  https://knytt-xxx.vercel.app
```

**Manual checks:**

1. Visit your frontend URL
2. Try searching for products
3. Register a new account
4. Login
5. Check recommendations

## Step 6: Set Up Monitoring (30 minutes)

### Sentry (Error Tracking)

1. Sign up at https://sentry.io
2. Create projects for Backend (Python) and Frontend (Next.js)
3. Add DSNs to Railway and Vercel:

**Railway:**
```bash
SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
SENTRY_ENVIRONMENT=production
```

**Vercel:**
```bash
NEXT_PUBLIC_SENTRY_DSN=https://xxx@xxx.ingest.sentry.io/xxx
```

### Database Backups

Set up GitHub Action:
1. Go to GitHub repo → Settings → Secrets
2. Add secrets:
   - `DATABASE_URL` (from Railway)
   - `AWS_ACCESS_KEY_ID` (if using S3)
   - `AWS_SECRET_ACCESS_KEY` (if using S3)
   - `S3_BACKUP_BUCKET` (if using S3)

The workflow `.github/workflows/backup-db.yml` will run daily at 2 AM UTC.

## Cost Summary

### Monthly Costs

**Railway (Backend):**
- PostgreSQL: $5-10
- Redis: $5-10
- API: $20-40
- Celery Worker: $15-30
- Celery Beat: $10-20
- **Subtotal: $55-110/month**

**Vercel (Frontend):**
- Pro Plan: $20/month
- **Subtotal: $20/month**

**Total: ~$75-130/month**

## Optimization Tips

### Cost Optimization

1. Start with smaller Railway resources
2. Use Railway's usage-based pricing
3. Stay on Vercel Pro (don't need Enterprise for MVP)
4. Monitor usage in dashboards

### Performance Optimization

1. Enable caching in Redis
2. Use Vercel's Edge caching
3. Optimize FAISS index size
4. Monitor response times

## Troubleshooting

### Common Issues

**API returns 502:**
- Check Railway logs
- Verify DATABASE_URL is set
- Check health endpoint: `/health`

**CORS errors:**
- Update `CORS_ORIGINS` in Railway
- Include Vercel URL
- Redeploy API service

**Images not loading:**
- Check Next.js image config
- Verify image URLs in database
- Check browser console

**Celery tasks not running:**
- Check worker logs in Railway
- Verify Redis connection
- Ensure only ONE beat instance

### Get Help

- Railway: https://railway.app/help
- Vercel: https://vercel.com/support
- Full docs: See `DEPLOYMENT.md`

## Next Steps After Deployment

- [ ] Set up custom domain (optional)
- [ ] Configure monitoring alerts
- [ ] Test all user flows
- [ ] Review security checklist in `SECURITY.md`
- [ ] Set up status page (e.g., https://upptime.js.org)
- [ ] Plan scaling strategy

## Quick Commands

```bash
# Generate secrets
./scripts/generate_secrets.sh

# Verify deployment
./scripts/verify_deployment.sh <api-url> <frontend-url>

# Backup database
./scripts/backup_database.sh

# Railway CLI
railway login
railway link
railway run alembic upgrade head
railway logs

# Vercel CLI
vercel login
vercel --prod
```

---

**Need detailed instructions?** See [DEPLOYMENT.md](./DEPLOYMENT.md)

**Security concerns?** See [SECURITY.md](./SECURITY.md)

**Questions?** Open an issue on GitHub

---

**Deployment Time**: 2-3 hours
**Monthly Cost**: $75-130
**Difficulty**: Beginner-friendly

✨ **You're ready to deploy!** ✨
