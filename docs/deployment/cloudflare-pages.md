# Deploying Frontend to Cloudflare Pages

This guide walks you through deploying the Next.js frontend to Cloudflare Pages, a fast and secure platform for static and dynamic websites.

## Overview

**Cloudflare Pages** provides:
- **Global CDN** - 300+ edge locations worldwide
- **Unlimited bandwidth** - No data transfer fees
- **Automatic deployments** - Deploy on every git push
- **Preview deployments** - Unique URL for every branch/PR
- **Zero configuration** - Auto-detects Next.js
- **Free SSL** - Automatic HTTPS certificates
- **Edge rendering** - Fast serverless functions at the edge

## Prerequisites

- Cloudflare account (free tier available at [cloudflare.com](https://cloudflare.com))
- GitHub/GitLab repository with frontend code
- Backend API deployed to Cloud Run (see [gcp-cloud-run.md](./gcp-cloud-run.md))
- Supabase Cloud database (see [supabase.md](./supabase.md))

## Step 1: Prepare Next.js for Deployment

### 1.1 Verify next.config.ts

Check `frontend/next.config.ts` is configured for static export or server-side rendering:

```typescript
// frontend/next.config.ts
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Enable static optimization
  output: 'standalone', // For server-side rendering on Cloudflare

  // Or for static export (SSG only):
  // output: 'export',

  // Image optimization
  images: {
    unoptimized: false, // Use Cloudflare image optimization
    domains: ['your-supabase-project.supabase.co'],
  },

  // Environment variables exposed to client
  env: {
    NEXT_PUBLIC_SUPABASE_URL: process.env.NEXT_PUBLIC_SUPABASE_URL,
    NEXT_PUBLIC_SUPABASE_ANON_KEY: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY,
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
};

export default nextConfig;
```

### 1.2 Test Production Build Locally

```bash
cd frontend

# Build for production
npm run build

# Test production build
npm run start

# Verify it works at http://localhost:3000
```

### 1.3 Update Environment Variables Template

Ensure `frontend/.env.local.example` is up to date:

```bash
# .env.local.example
NEXT_PUBLIC_SUPABASE_URL=https://your-project-ref.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
NEXT_PUBLIC_API_URL=https://your-backend-api.run.app
```

## Step 2: Connect Repository to Cloudflare Pages

### 2.1 Sign Up / Log In to Cloudflare

1. Go to [dash.cloudflare.com](https://dash.cloudflare.com)
2. Sign up or log in
3. Navigate to **Pages** in the left sidebar

### 2.2 Create New Project

1. Click **"Create a project"**
2. Click **"Connect to Git"**
3. Authorize Cloudflare to access your GitHub/GitLab account
4. Select your repository: `your-username/knytt`

### 2.3 Configure Build Settings

**Build configuration:**

```
Project name: knytt-frontend (or your preferred name)
Production branch: main
Build command: cd frontend && npm run build
Build output directory: frontend/.next
Root directory: /
```

**Framework preset:** Next.js (automatically detected)

**Node version:** 18 or later (set in Environment Variables)

### 2.4 Add Environment Variables

In the build settings, add environment variables:

| Variable Name | Value | Type |
|--------------|-------|------|
| `NEXT_PUBLIC_SUPABASE_URL` | `https://your-project-ref.supabase.co` | Plain text |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | `your-anon-key` | Plain text |
| `NEXT_PUBLIC_API_URL` | `https://your-backend.run.app` | Plain text |
| `NODE_VERSION` | `18` or `20` | Plain text |

**Note:** Since these start with `NEXT_PUBLIC_`, they're exposed to the browser, so don't put secrets here.

### 2.5 Deploy

Click **"Save and Deploy"**

Cloudflare Pages will:
1. Clone your repository
2. Install dependencies (`npm install`)
3. Run build command (`npm run build`)
4. Deploy to global CDN

**First deployment takes ~2-5 minutes.**

## Step 3: Verify Deployment

### 3.1 Check Build Logs

Monitor the build in real-time:
- View logs in Cloudflare Pages dashboard
- Check for any errors or warnings

### 3.2 Access Deployed Site

Once deployed, you'll get a URL like:
```
https://knytt-frontend.pages.dev
```

**Test the deployment:**
1. Open the URL in a browser
2. Check that home page loads correctly
3. Test authentication (login/register)
4. Test search functionality
5. Check browser console for errors

### 3.3 View Deployment Details

In Cloudflare Pages dashboard:
- **Deployments** - View all deployments
- **Settings** - Configure environment variables
- **Custom domains** - Add your own domain
- **Analytics** - View traffic and performance

## Step 4: Configure Custom Domain (Optional)

### 4.1 Add Custom Domain

1. Go to **Pages** > Your Project > **Custom domains**
2. Click **"Set up a custom domain"**
3. Enter your domain: `knytt.com` or `app.knytt.com`
4. Click **"Continue"**

### 4.2 Update DNS Records

Cloudflare will provide DNS records to add:

**For root domain (knytt.com):**
```
Type: CNAME
Name: @
Value: knytt-frontend.pages.dev
```

**For subdomain (app.knytt.com):**
```
Type: CNAME
Name: app
Value: knytt-frontend.pages.dev
```

**If using Cloudflare as DNS provider:**
- Records are automatically added
- SSL certificate is automatically provisioned

**If using external DNS provider:**
- Add the CNAME record manually
- Wait for DNS propagation (5-60 minutes)
- SSL certificate will be provisioned automatically

### 4.3 Enable HTTPS

Cloudflare automatically provisions SSL certificates. Settings:

1. Go to **SSL/TLS** > **Overview**
2. Set encryption mode to **"Full (strict)"**
3. Enable **"Always Use HTTPS"**
4. Enable **"Automatic HTTPS Rewrites"**

## Step 5: Configure CORS in Backend

Update backend CORS settings to allow your Cloudflare Pages domain.

### 5.1 Update Cloud Run Environment Variables

```bash
# Add your Cloudflare Pages URL to CORS_ORIGINS
gcloud run services update knytt-backend \
  --region us-central1 \
  --update-env-vars "CORS_ORIGINS=https://knytt-frontend.pages.dev,https://knytt.com,https://app.knytt.com"
```

### 5.2 Or Update in Code

Edit `backend/api/main.py`:

```python
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8080",
    "https://knytt-frontend.pages.dev",
    "https://knytt.com",
    "https://app.knytt.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Step 6: Set Up Preview Deployments

Cloudflare Pages automatically creates preview deployments for:
- Every push to any branch
- Every pull request

### 6.1 Preview URL Format

```
https://<BRANCH>.<PROJECT-NAME>.pages.dev

# Examples:
https://dev.knytt-frontend.pages.dev
https://feature-auth.knytt-frontend.pages.dev
https://pr-42.knytt-frontend.pages.dev
```

### 6.2 Configure Branch Deployments

1. Go to **Settings** > **Builds & deployments**
2. **Preview deployments**: Enable/disable
3. **Branch build controls**: Specify which branches to deploy

### 6.3 Environment Variables for Preview

Set different environment variables for preview vs production:

**Production only:**
```
NEXT_PUBLIC_API_URL=https://api.knytt.com
```

**Preview only:**
```
NEXT_PUBLIC_API_URL=https://api-dev.knytt.com
```

## Step 7: Set Up CI/CD with GitHub Actions (Alternative)

While Cloudflare Pages has built-in CI/CD, you can use GitHub Actions for more control.

### 7.1 Install Wrangler CLI

Wrangler is Cloudflare's CLI tool:

```bash
npm install -g wrangler

# Or in project:
cd frontend
npm install --save-dev wrangler
```

### 7.2 Get Cloudflare API Token

1. Go to [dash.cloudflare.com/profile/api-tokens](https://dash.cloudflare.com/profile/api-tokens)
2. Click **"Create Token"**
3. Use **"Edit Cloudflare Workers"** template
4. Or create custom token with permissions:
   - **Account > Cloudflare Pages** - Edit
5. Copy the token (save it securely)

### 7.3 Create GitHub Actions Workflow

Create `.github/workflows/deploy-frontend.yml`:

```yaml
name: Deploy Frontend to Cloudflare Pages

on:
  push:
    branches:
      - main
    paths:
      - 'frontend/**'
      - '.github/workflows/deploy-frontend.yml'

jobs:
  deploy:
    runs-on: ubuntu-latest

    permissions:
      contents: read
      deployments: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json

      - name: Install dependencies
        run: |
          cd frontend
          npm ci

      - name: Build application
        run: |
          cd frontend
          npm run build
        env:
          NEXT_PUBLIC_SUPABASE_URL: ${{ secrets.NEXT_PUBLIC_SUPABASE_URL }}
          NEXT_PUBLIC_SUPABASE_ANON_KEY: ${{ secrets.NEXT_PUBLIC_SUPABASE_ANON_KEY }}
          NEXT_PUBLIC_API_URL: ${{ secrets.NEXT_PUBLIC_API_URL }}

      - name: Deploy to Cloudflare Pages
        uses: cloudflare/pages-action@v1
        with:
          apiToken: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          accountId: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          projectName: knytt-frontend
          directory: frontend/.next
          gitHubToken: ${{ secrets.GITHUB_TOKEN }}
```

### 7.4 Add GitHub Secrets

Add these secrets to your GitHub repository:

| Secret Name | Value | Where to Find |
|------------|-------|---------------|
| `CLOUDFLARE_API_TOKEN` | Your API token | Created in step 7.2 |
| `CLOUDFLARE_ACCOUNT_ID` | Your account ID | Cloudflare Dashboard > Pages > Project |
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase URL | Supabase Dashboard |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anon key | Supabase Dashboard |
| `NEXT_PUBLIC_API_URL` | Backend API URL | Cloud Run service URL |

## Step 8: Optimize Performance

### 8.1 Enable Cloudflare Caching

Create `frontend/public/_headers`:

```
/*
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=()

/_next/static/*
  Cache-Control: public, max-age=31536000, immutable

/static/*
  Cache-Control: public, max-age=31536000, immutable

/*.jpg
  Cache-Control: public, max-age=604800

/*.png
  Cache-Control: public, max-age=604800

/*.webp
  Cache-Control: public, max-age=604800
```

### 8.2 Configure Redirects

Create `frontend/public/_redirects`:

```
# Redirect www to non-www (if applicable)
https://www.knytt.com/* https://knytt.com/:splat 301!

# Redirect old URLs
/old-page /new-page 301

# SPA fallback (if using client-side routing)
/* /index.html 200
```

### 8.3 Enable Image Optimization

Cloudflare Pages supports Next.js Image Optimization automatically when using:

```tsx
import Image from 'next/image';

<Image
  src="/product.jpg"
  alt="Product"
  width={500}
  height={500}
  priority // For above-the-fold images
/>
```

### 8.4 Use Cloudflare Web Analytics (Free)

1. Go to **Pages** > Your Project > **Web Analytics**
2. Click **"Enable Web Analytics"**
3. Add the provided script tag to your app, or it's auto-injected

## Step 9: Monitoring and Analytics

### 9.1 View Deployment Logs

```bash
# Using Wrangler CLI
wrangler pages deployment list --project-name=knytt-frontend

# View specific deployment logs
wrangler pages deployment tail
```

### 9.2 View Analytics

In Cloudflare Dashboard:
- **Analytics** > **Web Analytics**: Page views, visitors, performance
- **Speed** > **Performance**: Core Web Vitals
- **Security** > **Events**: Security events and threats

### 9.3 Set Up Alerts

Go to **Notifications** to create alerts for:
- Deployment failures
- High error rates
- Security threats
- Performance degradation

## Step 10: Troubleshooting

### Build Fails with "Module not found"

**Solution:**
```bash
# Ensure all dependencies are in package.json
cd frontend
npm install --save <missing-package>
git add package.json package-lock.json
git commit -m "Add missing dependency"
git push
```

### Environment Variables Not Working

**Solution:**
1. Ensure variables start with `NEXT_PUBLIC_` for client-side access
2. Re-deploy after updating environment variables
3. Check capitalization (case-sensitive)

### CORS Errors

**Solution:**
1. Update backend CORS_ORIGINS to include Cloudflare Pages URL
2. Ensure `credentials: "include"` in fetch requests
3. Check backend is deployed and accessible

### Custom Domain Not Working

**Solution:**
1. Verify DNS records are correct
2. Wait for DNS propagation (up to 48 hours, usually 5-60 minutes)
3. Check SSL certificate status in Cloudflare Dashboard
4. Try accessing via HTTPS (HTTP may redirect)

### Slow Page Load Times

**Solution:**
1. Enable image optimization
2. Use `next/image` component
3. Implement code splitting
4. Check bundle size: `npm run build` shows size analysis
5. Use dynamic imports for large components

## Cost Estimation

Cloudflare Pages pricing:

### Free Tier
- **Bandwidth**: Unlimited
- **Builds**: 500 builds/month
- **Requests**: Unlimited
- **Concurrent builds**: 1
- **Collaborators**: Unlimited
- **Custom domains**: 100

**Cost**: $0/month

### Pro Tier ($20/month)
- **Builds**: 5,000 builds/month
- **Concurrent builds**: 5
- Everything else same as Free tier

### Business Tier ($200/month)
- **Builds**: 20,000 builds/month
- **Concurrent builds**: 20
- Priority support

**For most projects, the Free tier is sufficient.**

## Security Best Practices

### 10.1 Enable Security Headers

Already configured in `_headers` file (see Step 8.1).

### 10.2 Use Environment Variables for Secrets

Never commit API keys or secrets:
- Use Cloudflare Pages environment variables
- Never hardcode in code
- Use `.env.local` for local development (git-ignored)

### 10.3 Enable DDoS Protection

Cloudflare includes:
- Automatic DDoS mitigation
- Bot protection
- Rate limiting (via Cloudflare Firewall)

### 10.4 Configure Firewall Rules (Optional)

Go to **Security** > **WAF** to create rules:
- Block specific countries
- Block known bots
- Rate limit by IP
- Challenge suspicious requests

## Next Steps

1. Update backend CORS to allow Cloudflare Pages domain
2. Test all functionality on production domain
3. Set up monitoring and alerts
4. Configure custom domain (if desired)
5. Set up preview environments for staging

## Resources

- [Cloudflare Pages Documentation](https://developers.cloudflare.com/pages/)
- [Deploy Next.js to Cloudflare Pages](https://developers.cloudflare.com/pages/framework-guides/deploy-a-nextjs-site/)
- [Wrangler CLI](https://developers.cloudflare.com/workers/wrangler/)
- [Cloudflare Web Analytics](https://developers.cloudflare.com/analytics/web-analytics/)
- [Cloudflare Pages GitHub Action](https://github.com/cloudflare/pages-action)
