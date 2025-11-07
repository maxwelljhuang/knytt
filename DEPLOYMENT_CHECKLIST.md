# Knytt Deployment Checklist ✅

Use this checklist to ensure you don't miss any steps during deployment.

## Pre-Deployment Preparation

### Local Setup
- [ ] All code committed to GitHub
- [ ] Local Docker build successful: `docker-compose build`
- [ ] Local services running: `docker-compose up -d`
- [ ] Tests passing
- [ ] No uncommitted secrets in Git

### Account Setup
- [ ] GitHub account ready
- [ ] Railway account created ([Sign up](https://railway.app))
- [ ] Vercel account created ([Sign up](https://vercel.com))
- [ ] Credit card added to Railway

### Secrets Generation
- [ ] Ran `./scripts/generate_secrets.sh`
- [ ] Saved `JWT_SECRET_KEY`
- [ ] Saved `SECRET_KEY`
- [ ] Saved `DB_PASSWORD` (if needed)

---

## Railway Backend Deployment

### PostgreSQL Database
- [ ] PostgreSQL service created
- [ ] Connected to database: `railway connect postgres`
- [ ] Enabled pgvector extension: `CREATE EXTENSION vector;`
- [ ] Enabled uuid-ossp extension: `CREATE EXTENSION "uuid-ossp";`
- [ ] Enabled pg_trgm extension: `CREATE EXTENSION pg_trgm;`
- [ ] Noted DATABASE_URL

### Redis Cache
- [ ] Redis service created
- [ ] Noted REDIS_URL

### API Service
- [ ] Service created from GitHub repo
- [ ] Start command set: `uvicorn backend.api.main:app --host 0.0.0.0 --port $PORT`
- [ ] Environment variables configured:
  - [ ] DATABASE_URL (reference: `${{Postgres.DATABASE_URL}}`)
  - [ ] REDIS_URL (reference: `${{Redis.REDIS_URL}}`)
  - [ ] JWT_SECRET_KEY (your generated secret)
  - [ ] SECRET_KEY (your generated secret)
  - [ ] APP_ENV=production
  - [ ] DEBUG=false
  - [ ] LOG_LEVEL=INFO
  - [ ] CORS_ORIGINS (will update after Vercel)
  - [ ] ENABLE_EMBEDDINGS=true
- [ ] Public domain generated
- [ ] Health check configured: `/health`
- [ ] API URL noted: `https://______.up.railway.app`

### Celery Worker Service
- [ ] Service created from GitHub repo
- [ ] Start command set: `celery -A backend.tasks.celery_app worker --loglevel=info --pool=solo`
- [ ] Environment variables copied from API service
- [ ] Service deployed successfully
- [ ] Logs show: "Ready to process tasks"

### Celery Beat Service
- [ ] Service created from GitHub repo
- [ ] Start command set: `celery -A backend.tasks.celery_app beat --loglevel=info`
- [ ] Environment variables copied from API service
- [ ] Only ONE instance running (important!)
- [ ] Service deployed successfully
- [ ] Logs show: "Scheduler started"

### Database Migrations
- [ ] Ran: `railway run alembic upgrade head`
- [ ] Migration completed successfully
- [ ] Verified: `railway run python scripts/verify_database.py`

### Persistent Storage (Optional but Recommended)
- [ ] Added volume for `/app/models` (5GB)
- [ ] Added volume for `/app/data/indices` (2GB)
- [ ] Added volume for `/app/logs` (1GB)

---

## Vercel Frontend Deployment

### Project Import
- [ ] Imported `knytt` repository
- [ ] Framework detected: Next.js
- [ ] Root directory set: `frontend`
- [ ] Build command: `npm run build` (auto-detected)
- [ ] Install command: `npm install` (auto-detected)

### Environment Variables
- [ ] NEXT_PUBLIC_API_BASE_URL=https://your-api.up.railway.app
- [ ] NEXT_PUBLIC_APP_ENV=production

### Deployment
- [ ] Clicked "Deploy"
- [ ] Build successful
- [ ] Deployment successful
- [ ] Frontend URL noted: `https://______.vercel.app`

### Custom Domain (Optional)
- [ ] Domain added in Vercel
- [ ] DNS records configured
- [ ] SSL certificate issued (automatic)

---

## Post-Deployment Configuration

### Update CORS
- [ ] Went back to Railway → API service → Variables
- [ ] Updated CORS_ORIGINS with Vercel URL
- [ ] Service redeployed automatically

### Verify Deployment
- [ ] Ran verification script:
  ```bash
  ./scripts/verify_deployment.sh \
    https://your-api.up.railway.app \
    https://your-app.vercel.app
  ```
- [ ] All checks passed ✅

### Manual Testing
- [ ] Frontend loads successfully
- [ ] Search works (search for "shoes")
- [ ] User registration works
- [ ] User login works
- [ ] Recommendations display
- [ ] Images load correctly
- [ ] No "No image" fallbacks appear
- [ ] Cart functionality works
- [ ] Profile page accessible

### Service Health
- [ ] API health endpoint: `https://api-url/health` returns `{"status":"healthy"}`
- [ ] API docs accessible: `https://api-url/docs`
- [ ] Railway logs show no errors
- [ ] Vercel logs show no errors
- [ ] FAISS index loaded in API logs

---

## Monitoring & Security Setup

### Error Tracking (Sentry)
- [ ] Created Sentry account
- [ ] Created backend project (Python)
- [ ] Created frontend project (Next.js)
- [ ] Added SENTRY_DSN to Railway (API service)
- [ ] Added NEXT_PUBLIC_SENTRY_DSN to Vercel
- [ ] Verified errors are being tracked

### Database Backups
- [ ] GitHub Actions workflow enabled
- [ ] Secrets added to GitHub:
  - [ ] DATABASE_URL
  - [ ] AWS_ACCESS_KEY_ID (if using S3)
  - [ ] AWS_SECRET_ACCESS_KEY (if using S3)
  - [ ] S3_BACKUP_BUCKET (if using S3)
- [ ] Workflow tested manually
- [ ] Backup scheduled: Daily at 2 AM UTC

### Uptime Monitoring (Optional)
- [ ] Set up UptimeRobot or similar
- [ ] Monitor: `https://api-url/health` (every 5 min)
- [ ] Monitor: `https://frontend-url` (every 5 min)
- [ ] Email/SMS alerts configured

---

## Security Review

### Secrets & Environment
- [ ] All production secrets are unique and strong
- [ ] No secrets committed to Git
- [ ] `.env.production.local` in `.gitignore`
- [ ] DEBUG=false in production
- [ ] CORS_ORIGINS set to specific domains (not `*`)

### Database
- [ ] Strong database password (if self-managed)
- [ ] Database not publicly accessible
- [ ] Automated backups configured
- [ ] Connection pooling configured

### API
- [ ] HTTPS enabled (automatic on Railway)
- [ ] Rate limiting enabled
- [ ] Health checks configured
- [ ] Authentication working

### Frontend
- [ ] HTTPS enabled (automatic on Vercel)
- [ ] No sensitive data in client code
- [ ] Environment variables properly scoped

---

## Performance Optimization

### Railway
- [ ] Monitored CPU usage in dashboard
- [ ] Monitored memory usage in dashboard
- [ ] Set appropriate resource limits
- [ ] Configured auto-scaling if needed

### Vercel
- [ ] Edge caching enabled
- [ ] Image optimization working (automatic)
- [ ] Analytics enabled

### Database
- [ ] Indexes created on frequently queried columns
- [ ] Connection pooling optimized
- [ ] Query performance monitored

---

## Documentation & Maintenance

### Documentation
- [ ] Updated README with deployment details
- [ ] Documented custom domain setup (if applicable)
- [ ] Noted all service URLs
- [ ] Created runbook for common issues

### Team Access
- [ ] Added team members to Railway (if applicable)
- [ ] Added team members to Vercel (if applicable)
- [ ] Shared access to Sentry
- [ ] Documented deployment process for team

### Maintenance Schedule
- [ ] Weekly: Review logs and errors
- [ ] Monthly: Update dependencies
- [ ] Quarterly: Rotate secrets
- [ ] Annually: Security audit

---

## Launch Checklist

Before announcing to users:

- [ ] All features tested end-to-end
- [ ] Performance tested under load
- [ ] Error tracking working
- [ ] Backups verified
- [ ] Monitoring alerts configured
- [ ] Support email/contact set up
- [ ] Privacy policy published
- [ ] Terms of service published
- [ ] Status page set up (optional)

---

## Emergency Contacts

**Railway Support**: https://railway.app/help
**Vercel Support**: https://vercel.com/support
**Sentry Support**: https://sentry.io/support

**Team Contacts**:
- Technical Lead: [email]
- DevOps: [email]
- Support: [email]

---

## Rollback Plan

If something goes wrong:

1. **Immediate Actions**:
   - [ ] Check Railway logs for errors
   - [ ] Check Vercel logs for errors
   - [ ] Check Sentry for error spike

2. **Rollback Frontend** (if needed):
   ```bash
   # In Vercel dashboard:
   # Deployments → Previous deployment → Promote to Production
   ```

3. **Rollback Backend** (if needed):
   ```bash
   # In Railway dashboard:
   # Service → Deployments → Previous deployment → Redeploy
   ```

4. **Database Restore** (if needed):
   ```bash
   # Download latest backup
   # Restore: psql $DATABASE_URL < backup.sql
   ```

---

## Success Criteria

Deployment is successful when:

- ✅ All services healthy in Railway
- ✅ Frontend accessible and functional
- ✅ API responding with <500ms latency
- ✅ Search returns results
- ✅ User flows working (register, login, search)
- ✅ No errors in logs
- ✅ Error tracking working
- ✅ Backups running
- ✅ Monitoring configured

---

**Deployment Date**: __________

**Deployed By**: __________

**Deployment Time**: __________ hours

**Issues Encountered**: __________

**Notes**: __________

---

✨ **Congratulations! Your deployment is complete!** ✨
