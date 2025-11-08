# Deploying Backend to GCP Cloud Run

This guide walks you through deploying the FastAPI backend to Google Cloud Run, a fully managed serverless platform.

## Overview

**Cloud Run** provides:
- **Serverless** - No infrastructure management
- **Auto-scaling** - Scales from 0 to N instances based on traffic
- **Pay per use** - Only pay when requests are being processed
- **Fast deployments** - Deploy from Docker images
- **Custom domains** - Map your own domain
- **HTTPS by default** - Automatic SSL certificates

## Prerequisites

- Google Cloud account with billing enabled
- `gcloud` CLI installed ([installation guide](https://cloud.google.com/sdk/docs/install))
- Docker installed locally
- Supabase Cloud database set up (see [supabase.md](./supabase.md))
- Backend running locally

## Step 1: Set Up Google Cloud Project

### 1.1 Install gcloud CLI

```bash
# macOS
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Or via Homebrew
brew install --cask google-cloud-sdk
```

### 1.2 Initialize gcloud

```bash
gcloud init

# Follow prompts to:
# 1. Login with your Google account
# 2. Select or create a project
# 3. Choose default region (e.g., us-central1, us-east1)
```

### 1.3 Enable Required APIs

```bash
# Enable Cloud Run API
gcloud services enable run.googleapis.com

# Enable Container Registry API
gcloud services enable containerregistry.googleapis.com

# Enable Artifact Registry API (recommended over Container Registry)
gcloud services enable artifactregistry.googleapis.com

# Enable Secret Manager API (for environment variables)
gcloud services enable secretmanager.googleapis.com
```

### 1.4 Set Default Project

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
gcloud config set project $PROJECT_ID
```

## Step 2: Create Dockerfile for Backend

Create a production-ready Dockerfile in the project root:

### 2.1 Create Dockerfile

```dockerfile
# Dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/ ./backend/
COPY create_db.py .
COPY .env .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    chown -R appuser:appuser /app
USER appuser

# Expose port (Cloud Run uses PORT env variable)
ENV PORT=8080
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application with Uvicorn
CMD uvicorn backend.api.main:app --host 0.0.0.0 --port ${PORT:-8080} --workers 1
```

### 2.2 Create .dockerignore

Create `.dockerignore` to exclude unnecessary files:

```
# .dockerignore
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
.env.local
.env.production
.venv
pip-log.txt
pip-delete-this-directory.txt
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.log
.git
.gitignore
.pytest_cache/
.mypy_cache/
.DS_Store
*.md
frontend/
docs/
tests/
.github/
```

## Step 3: Configure Environment Variables

### 3.1 Create Production Environment File

Create `.env.production` with production values:

```bash
# Supabase Cloud
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_KEY=your-service-role-key

# Database - use Supabase connection pooler
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-us-east-1.pooler.supabase.com:6543/postgres

# API Configuration
API_HOST=0.0.0.0
API_PORT=8080

# CORS - Add your frontend domain
CORS_ORIGINS=https://your-frontend.pages.dev,https://yourdomain.com

# ML Configuration
CLIP_MODEL=ViT-B/32
EMBEDDING_DIMENSION=512

# Security
JWT_SECRET_KEY=your-super-secret-jwt-key-minimum-32-characters
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# Optional: Redis for caching
REDIS_URL=redis://your-redis-instance:6379
```

### 3.2 Store Secrets in Google Secret Manager

```bash
# Create secrets for sensitive values
echo -n "your-database-url" | gcloud secrets create DATABASE_URL --data-file=-
echo -n "your-supabase-service-key" | gcloud secrets create SUPABASE_SERVICE_KEY --data-file=-
echo -n "your-jwt-secret" | gcloud secrets create JWT_SECRET_KEY --data-file=-

# Verify secrets created
gcloud secrets list
```

## Step 4: Build and Push Docker Image

### 4.1 Configure Docker Authentication

```bash
# Configure Docker to use gcloud as credential helper
gcloud auth configure-docker
```

### 4.2 Build Docker Image Locally (Test)

```bash
# Build image
docker build -t knytt-backend:latest .

# Test locally
docker run -p 8080:8080 --env-file .env.production knytt-backend:latest

# Test in another terminal
curl http://localhost:8080/health
```

### 4.3 Build for Cloud Run

Choose one of these methods:

#### Option A: Build Locally and Push

```bash
# Set variables
export PROJECT_ID="your-project-id"
export REGION="us-central1"
export IMAGE_NAME="knytt-backend"

# Build and tag
docker build -t gcr.io/$PROJECT_ID/$IMAGE_NAME:latest .

# Push to Google Container Registry
docker push gcr.io/$PROJECT_ID/$IMAGE_NAME:latest
```

#### Option B: Use Cloud Build (Recommended)

```bash
# Build directly on Google Cloud (faster, no local build needed)
gcloud builds submit --tag gcr.io/$PROJECT_ID/$IMAGE_NAME:latest .

# This is better because:
# - No need to build locally
# - Faster upload (builds in cloud)
# - Better caching
```

## Step 5: Deploy to Cloud Run

### 5.1 Deploy with gcloud

```bash
gcloud run deploy knytt-backend \
  --image gcr.io/$PROJECT_ID/$IMAGE_NAME:latest \
  --platform managed \
  --region $REGION \
  --allow-unauthenticated \
  --port 8080 \
  --memory 512Mi \
  --cpu 1 \
  --min-instances 0 \
  --max-instances 10 \
  --timeout 300 \
  --set-env-vars "API_HOST=0.0.0.0,API_PORT=8080,CLIP_MODEL=ViT-B/32,EMBEDDING_DIMENSION=512" \
  --set-secrets "DATABASE_URL=DATABASE_URL:latest,SUPABASE_SERVICE_KEY=SUPABASE_SERVICE_KEY:latest,JWT_SECRET_KEY=JWT_SECRET_KEY:latest" \
  --set-env-vars "SUPABASE_URL=https://your-project-ref.supabase.co" \
  --set-env-vars "SUPABASE_ANON_KEY=your-anon-key" \
  --set-env-vars "CORS_ORIGINS=https://your-frontend.pages.dev,https://yourdomain.com"
```

### 5.2 Alternative: Deploy with YAML Configuration

Create `cloudrun.yaml`:

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: knytt-backend
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: '0'
        autoscaling.knative.dev/maxScale: '10'
    spec:
      containerConcurrency: 80
      timeoutSeconds: 300
      containers:
      - image: gcr.io/your-project-id/knytt-backend:latest
        ports:
        - containerPort: 8080
        resources:
          limits:
            cpu: '1'
            memory: 512Mi
        env:
        - name: API_HOST
          value: "0.0.0.0"
        - name: API_PORT
          value: "8080"
        - name: SUPABASE_URL
          value: "https://your-project-ref.supabase.co"
        - name: SUPABASE_ANON_KEY
          value: "your-anon-key"
        - name: CLIP_MODEL
          value: "ViT-B/32"
        - name: EMBEDDING_DIMENSION
          value: "512"
        - name: CORS_ORIGINS
          value: "https://your-frontend.pages.dev,https://yourdomain.com"
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: DATABASE_URL
              key: latest
        - name: SUPABASE_SERVICE_KEY
          valueFrom:
            secretKeyRef:
              name: SUPABASE_SERVICE_KEY
              key: latest
        - name: JWT_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: JWT_SECRET_KEY
              key: latest
```

Deploy with:
```bash
gcloud run services replace cloudrun.yaml --region $REGION
```

### 5.3 Get Service URL

```bash
# Get the deployed URL
gcloud run services describe knytt-backend --region $REGION --format="value(status.url)"

# Output example: https://knytt-backend-abc123-uc.a.run.app
```

## Step 6: Test Deployment

### 6.1 Test Health Endpoint

```bash
export SERVICE_URL=$(gcloud run services describe knytt-backend --region $REGION --format="value(status.url)")

# Test health
curl $SERVICE_URL/health

# Expected response:
# {"status":"healthy","timestamp":"2025-11-08T..."}
```

### 6.2 Test Authentication

```bash
# Register a user
curl -X POST $SERVICE_URL/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123",
    "name": "Test User"
  }'

# Login
curl -X POST $SERVICE_URL/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'
```

### 6.3 Test API Documentation

Visit in browser:
```
https://knytt-backend-abc123-uc.a.run.app/docs
```

You should see the interactive Swagger UI.

## Step 7: Configure Custom Domain (Optional)

### 7.1 Verify Domain Ownership

```bash
# Map your domain to Cloud Run
gcloud run domain-mappings create \
  --service knytt-backend \
  --domain api.yourdomain.com \
  --region $REGION
```

### 7.2 Update DNS Records

You'll get DNS records to add to your domain registrar:

```
Type: CNAME
Name: api
Value: ghs.googlehosted.com
```

### 7.3 Wait for SSL Certificate

Cloud Run automatically provisions an SSL certificate. This can take 15-60 minutes.

Check status:
```bash
gcloud run domain-mappings describe --domain api.yourdomain.com --region $REGION
```

## Step 8: Set Up Continuous Deployment (CI/CD)

### 8.1 Create GitHub Actions Workflow

Create `.github/workflows/deploy-backend.yml`:

```yaml
name: Deploy Backend to Cloud Run

on:
  push:
    branches:
      - main
    paths:
      - 'backend/**'
      - 'requirements.txt'
      - 'Dockerfile'
      - '.github/workflows/deploy-backend.yml'

env:
  PROJECT_ID: your-project-id
  REGION: us-central1
  SERVICE_NAME: knytt-backend

jobs:
  deploy:
    runs-on: ubuntu-latest

    permissions:
      contents: read
      id-token: write

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2

      - name: Configure Docker
        run: gcloud auth configure-docker

      - name: Build Docker image
        run: |
          docker build -t gcr.io/$PROJECT_ID/$SERVICE_NAME:$GITHUB_SHA .
          docker tag gcr.io/$PROJECT_ID/$SERVICE_NAME:$GITHUB_SHA gcr.io/$PROJECT_ID/$SERVICE_NAME:latest

      - name: Push Docker image
        run: |
          docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:$GITHUB_SHA
          docker push gcr.io/$PROJECT_ID/$SERVICE_NAME:latest

      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy $SERVICE_NAME \
            --image gcr.io/$PROJECT_ID/$SERVICE_NAME:$GITHUB_SHA \
            --platform managed \
            --region $REGION \
            --allow-unauthenticated \
            --quiet
```

### 8.2 Create Service Account for GitHub Actions

```bash
# Create service account
gcloud iam service-accounts create github-actions \
  --description="Service account for GitHub Actions" \
  --display-name="GitHub Actions"

# Grant necessary roles
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:github-actions@$PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Create and download key
gcloud iam service-accounts keys create key.json \
  --iam-account=github-actions@$PROJECT_ID.iam.gserviceaccount.com

# Add key.json content to GitHub Secrets as GCP_SA_KEY
# Go to: Repository Settings > Secrets and variables > Actions > New repository secret
```

## Step 9: Monitoring and Logging

### 9.1 View Logs

```bash
# Stream logs in real-time
gcloud run services logs read knytt-backend --region $REGION --limit 50 --follow

# Or view in Cloud Console
# https://console.cloud.google.com/run/detail/REGION/SERVICE_NAME/logs
```

### 9.2 Set Up Alerts

Create alert policies in Cloud Monitoring:

```bash
# Go to Cloud Console > Monitoring > Alerting
# Create alerts for:
# - High error rate (>5% 5xx responses)
# - High latency (>2s p95)
# - Low instance count during business hours
```

### 9.3 View Metrics

```bash
# View in Cloud Console
# https://console.cloud.google.com/run/detail/REGION/SERVICE_NAME/metrics

# Metrics available:
# - Request count
# - Request latency
# - Container instance count
# - CPU utilization
# - Memory utilization
# - Billable container time
```

## Step 10: Optimize for Production

### 10.1 Adjust Auto-scaling

```bash
# Update min/max instances
gcloud run services update knytt-backend \
  --region $REGION \
  --min-instances 1 \
  --max-instances 100 \
  --concurrency 80
```

**Recommendations:**
- **min-instances: 0** - Dev/staging (cost-effective, cold starts)
- **min-instances: 1-2** - Production (avoid cold starts)
- **max-instances: 10-100** - Based on expected traffic
- **concurrency: 80** - Requests per container instance

### 10.2 Configure CPU and Memory

```bash
# Update resources based on load testing
gcloud run services update knytt-backend \
  --region $REGION \
  --cpu 2 \
  --memory 1Gi
```

**Recommendations:**
- Start with: 1 CPU, 512Mi
- ML-heavy workloads: 2-4 CPU, 1-2Gi
- Monitor and adjust based on metrics

### 10.3 Enable CPU Throttling

```bash
# CPU is only allocated during request processing (default)
gcloud run services update knytt-backend \
  --region $REGION \
  --cpu-throttling

# Or: CPU always allocated (better for background tasks)
gcloud run services update knytt-backend \
  --region $REGION \
  --no-cpu-throttling
```

### 10.4 Set Request Timeout

```bash
# Max 3600 seconds (1 hour)
gcloud run services update knytt-backend \
  --region $REGION \
  --timeout 60
```

## Troubleshooting

### Container Fails to Start

Check logs:
```bash
gcloud run services logs read knytt-backend --region $REGION --limit 100
```

Common issues:
- Port mismatch (ensure app listens on $PORT)
- Missing environment variables
- Database connection failures

### High Cold Start Time

Solutions:
- Set min-instances to 1+
- Optimize Docker image size
- Use lighter base image (python:3.12-slim)
- Pre-compile Python files

### Database Connection Errors

- Use Supabase connection pooler (port 6543)
- Set connection pool size appropriately
- Enable `pool_pre_ping=True` in SQLAlchemy

### Memory Exceeded

- Increase memory allocation
- Monitor memory usage in metrics
- Check for memory leaks

## Cost Estimation

Cloud Run pricing (as of 2025):

### Free Tier (Monthly)
- 2 million requests
- 360,000 GB-seconds (memory)
- 180,000 vCPU-seconds
- 1 GB network egress (North America)

### Paid Usage
- **CPU**: $0.00002400 per vCPU-second
- **Memory**: $0.00000250 per GB-second
- **Requests**: $0.40 per million requests
- **Network egress**: $0.12 per GB

### Example: Small Production App
- 100K requests/month
- Average 200ms response time
- 512Mi memory, 1 CPU
- Minimal egress

**Estimated cost**: $5-10/month

### Example: Medium Production App
- 1M requests/month
- Average 500ms response time
- 1Gi memory, 2 CPU
- min-instances: 1

**Estimated cost**: $30-50/month

## Next Steps

1. Deploy frontend to **Cloudflare Pages** - see [cloudflare-pages.md](./cloudflare-pages.md)
2. Update frontend `.env` with Cloud Run URL
3. Set up monitoring and alerting
4. Configure custom domain
5. Set up CI/CD pipeline

## Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud Run Pricing](https://cloud.google.com/run/pricing)
- [Best Practices](https://cloud.google.com/run/docs/best-practices)
- [Troubleshooting](https://cloud.google.com/run/docs/troubleshooting)
