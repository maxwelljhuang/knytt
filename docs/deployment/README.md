# Knytt Deployment Guide

Complete deployment guide for the Knytt AI-powered product discovery platform.

## Architecture Overview

Knytt uses a modern serverless architecture with three main components:

```
┌─────────────────────────────────────────────────────────────────┐
│                         PRODUCTION STACK                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │  Cloudflare  │      │  GCP Cloud   │      │   Supabase   │ │
│  │    Pages     │─────▶│     Run      │─────▶│    Cloud     │ │
│  │              │      │              │      │              │ │
│  │  (Frontend)  │      │  (Backend)   │      │ (Database)   │ │
│  │   Next.js    │      │   FastAPI    │      │  PostgreSQL  │ │
│  │              │      │   + CLIP     │      │  + pgvector  │ │
│  └──────────────┘      └──────────────┘      └──────────────┘ │
│         │                      │                      │        │
│    Global CDN           Serverless API         Auth + DB      │
│   300+ edge             Auto-scaling           Managed         │
│    locations            Pay per use            Backups         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Component Details

| Component | Service | Purpose | Technology |
|-----------|---------|---------|------------|
| **Frontend** | Cloudflare Pages | Web UI, user interactions | Next.js 16, React 19, Tailwind CSS |
| **Backend API** | GCP Cloud Run | REST API, ML inference | FastAPI, Python 3.12, CLIP |
| **Database** | Supabase Cloud | Data persistence, auth | PostgreSQL 15 + pgvector |
| **CDN** | Cloudflare | Global content delivery | 300+ edge locations |
| **Auth** | Supabase Auth | User authentication | JWT tokens, OAuth |
| **Storage** | Supabase Storage | Product images (optional) | S3-compatible |

## Deployment Guides

Follow these guides in order to deploy the complete stack:

### 1. Database - Supabase Cloud
**[→ Read the Supabase deployment guide](./supabase.md)**

Deploy PostgreSQL database with:
- 6-table schema (users, products, embeddings, interactions)
- pgvector extension for CLIP embeddings
- JWT authentication
- Row-level security
- Automated backups

**Time**: 15-30 minutes
**Cost**: Free tier available, Pro from $25/month

---

### 2. Backend API - GCP Cloud Run
**[→ Read the GCP Cloud Run deployment guide](./gcp-cloud-run.md)**

Deploy FastAPI backend with:
- Serverless auto-scaling
- Docker container deployment
- Secret management
- Custom domain support
- CI/CD with GitHub Actions

**Time**: 30-60 minutes
**Cost**: Free tier available, ~$5-50/month based on usage

---

### 3. Frontend - Cloudflare Pages
**[→ Read the Cloudflare Pages deployment guide](./cloudflare-pages.md)**

Deploy Next.js frontend with:
- Global CDN distribution
- Automatic HTTPS
- Preview deployments
- Zero-config builds
- Unlimited bandwidth

**Time**: 15-30 minutes
**Cost**: Free tier (sufficient for most projects)

---

## Quick Start (TL;DR)

### Prerequisites
- Accounts: Supabase, Google Cloud (with billing), Cloudflare
- Tools: `gcloud` CLI, Supabase CLI, Node.js 18+, Python 3.12+
- Repository: GitHub/GitLab with Knytt code

### 1. Deploy Database (Supabase)
```bash
# Create project at supabase.com
# Link local project
supabase link --project-ref your-project-ref

# Deploy schema
DATABASE_URL="postgresql://..." python create_db.py
```

### 2. Deploy Backend (GCP Cloud Run)
```bash
# Build and deploy
gcloud builds submit --tag gcr.io/PROJECT_ID/knytt-backend
gcloud run deploy knytt-backend \
  --image gcr.io/PROJECT_ID/knytt-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### 3. Deploy Frontend (Cloudflare Pages)
```bash
# Connect GitHub repo to Cloudflare Pages
# Set environment variables:
# - NEXT_PUBLIC_SUPABASE_URL
# - NEXT_PUBLIC_SUPABASE_ANON_KEY
# - NEXT_PUBLIC_API_URL (Cloud Run URL)
# Click "Save and Deploy"
```

### 4. Verify
```bash
# Test backend
curl https://your-backend.run.app/health

# Test frontend
open https://your-frontend.pages.dev
```

## Environment Variables Reference

### Backend (.env)
```bash
# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Database
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@...pooler.supabase.com:6543/postgres

# API
API_HOST=0.0.0.0
API_PORT=8080

# CORS
CORS_ORIGINS=https://your-frontend.pages.dev,https://yourdomain.com

# ML
CLIP_MODEL=ViT-B/32
EMBEDDING_DIMENSION=512

# Security
JWT_SECRET_KEY=your-secret-key-minimum-32-characters
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Frontend (.env.local)
```bash
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=https://your-backend.run.app
```

## Cost Estimation

### Development (Free Tier)
| Service | Free Tier | Cost |
|---------|-----------|------|
| Supabase | 500MB DB, 1GB storage, 50K MAU | $0/mo |
| Cloud Run | 2M requests, 360K GB-sec | $0/mo |
| Cloudflare Pages | Unlimited bandwidth, 500 builds | $0/mo |
| **Total** | | **$0/month** |

### Small Production (~10K users/month)
| Service | Usage | Cost |
|---------|-------|------|
| Supabase | Pro tier (8GB DB) | $25/mo |
| Cloud Run | 100K requests, 512MB, 1 CPU | $5-10/mo |
| Cloudflare Pages | Free tier | $0/mo |
| **Total** | | **~$30-35/month** |

### Medium Production (~100K users/month)
| Service | Usage | Cost |
|---------|-------|------|
| Supabase | Pro tier (20GB DB) | $40/mo |
| Cloud Run | 1M requests, 1GB, 2 CPU | $30-50/mo |
| Cloudflare Pages | Pro tier (5K builds) | $20/mo |
| **Total** | | **~$90-110/month** |

## Monitoring and Observability

### Health Checks
All services include health monitoring:

**Backend:**
```bash
# Liveness check
curl https://your-backend.run.app/health

# Detailed status
curl https://your-backend.run.app/status
```

**Frontend:**
```bash
# Cloudflare Pages dashboard
https://dash.cloudflare.com/pages

# Web Analytics (free)
Automatically enabled in Cloudflare
```

**Database:**
```bash
# Supabase dashboard
https://app.supabase.com/project/your-project

# Logs, metrics, and SQL editor available
```

### Logging

**Backend (Cloud Run):**
```bash
# View logs
gcloud run services logs read knytt-backend --region us-central1 --limit 50 --follow

# Or in Cloud Console
https://console.cloud.google.com/run/detail/REGION/SERVICE/logs
```

**Database (Supabase):**
```bash
# Access logs in Supabase Dashboard
https://app.supabase.com/project/your-project/logs

# Logs available:
# - Postgres logs (queries, errors)
# - Auth logs (login, register)
# - Realtime logs (if using)
```

**Frontend (Cloudflare):**
```bash
# View deployment logs in Cloudflare Pages dashboard
https://dash.cloudflare.com/pages/view/your-project

# Real-time visitor analytics included
```

### Alerts

Set up alerts for critical issues:

**Cloud Run:**
- High error rate (>5% 5xx responses)
- High latency (>2s p95)
- Container crashes

**Supabase:**
- Connection pool exhaustion
- Database size approaching limit
- Failed auth attempts spike

**Cloudflare:**
- Deployment failures
- High error rates
- DDoS attacks

## CI/CD Pipeline

### Recommended Workflow

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   GitHub    │      │   GitHub    │      │   Deploy    │
│   Push      │─────▶│   Actions   │─────▶│   to Prod   │
│   (main)    │      │   (CI/CD)   │      │             │
└─────────────┘      └─────────────┘      └─────────────┘
                            │
                            ▼
                    ┌───────────────┐
                    │  Run Tests    │
                    │  Lint Code    │
                    │  Build Docker │
                    │  Deploy       │
                    └───────────────┘
```

### GitHub Actions Setup

See individual guides for CI/CD configuration:
- [Backend CI/CD with GitHub Actions](./gcp-cloud-run.md#step-8-set-up-continuous-deployment-cicd)
- [Frontend CI/CD with GitHub Actions](./cloudflare-pages.md#step-7-set-up-cicd-with-github-actions-alternative)

## Security Best Practices

### 1. Environment Variables
- Never commit secrets to git
- Use Secret Manager (GCP) for backend secrets
- Use Cloudflare environment variables for frontend
- Rotate secrets regularly

### 2. Authentication
- Use JWT tokens with httpOnly cookies
- Set appropriate token expiration times
- Implement refresh token rotation
- Use Supabase Auth for user management

### 3. Database Security
- Enable Row Level Security (RLS)
- Use connection pooling
- Limit service role key usage to backend only
- Regular automated backups

### 4. API Security
- Enable CORS with specific origins
- Rate limit endpoints (via Cloudflare)
- Validate all inputs
- Use HTTPS only

### 5. Frontend Security
- Set security headers (CSP, X-Frame-Options)
- Sanitize user inputs
- Use environment variables for config
- Enable Cloudflare DDoS protection

## Troubleshooting

### Common Issues

**Backend won't start:**
- Check environment variables are set correctly
- Verify database connection string
- Check Cloud Run logs for errors
- Ensure port is set to 8080

**Frontend can't connect to backend:**
- Verify CORS settings in backend
- Check NEXT_PUBLIC_API_URL is correct
- Ensure backend is deployed and running
- Check browser console for errors

**Database connection errors:**
- Use connection pooler URL (port 6543)
- Check connection pool size settings
- Verify credentials are correct
- Check Supabase service status

**Build failures:**
- Check build logs for specific errors
- Verify all dependencies are in package.json/requirements.txt
- Check Node/Python version compatibility
- Clear cache and rebuild

## Support and Resources

### Documentation
- [Supabase Docs](https://supabase.com/docs)
- [Cloud Run Docs](https://cloud.google.com/run/docs)
- [Cloudflare Pages Docs](https://developers.cloudflare.com/pages/)
- [Next.js Docs](https://nextjs.org/docs)
- [FastAPI Docs](https://fastapi.tiangolo.com/)

### Community
- [Knytt GitHub Issues](https://github.com/your-org/knytt/issues)
- [Supabase Discord](https://discord.supabase.com/)
- [Cloudflare Discord](https://discord.gg/cloudflaredev)

## Next Steps

After deployment:

1. **Test thoroughly** - Verify all features work in production
2. **Set up monitoring** - Configure alerts and dashboards
3. **Configure custom domains** - Use your own domain names
4. **Optimize performance** - Monitor and tune based on metrics
5. **Set up CI/CD** - Automate deployments
6. **Plan for scaling** - Monitor usage and adjust resources
7. **Implement backups** - Regular database backups
8. **Security audit** - Review and harden security settings

## Deployment Checklist

- [ ] Create Supabase Cloud project
- [ ] Deploy database schema
- [ ] Configure Supabase Auth settings
- [ ] Set up Google Cloud project
- [ ] Build and deploy backend to Cloud Run
- [ ] Configure backend environment variables
- [ ] Test backend API endpoints
- [ ] Create Cloudflare Pages project
- [ ] Deploy frontend to Cloudflare Pages
- [ ] Configure frontend environment variables
- [ ] Update CORS settings in backend
- [ ] Test frontend-backend integration
- [ ] Set up custom domains (optional)
- [ ] Configure monitoring and alerts
- [ ] Set up CI/CD pipelines
- [ ] Review security settings
- [ ] Create deployment documentation
- [ ] Train team on deployment process

## License

MIT License - see LICENSE file for details

