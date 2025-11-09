# Knytt Backend Infrastructure

This directory contains Terraform configuration for deploying the Knytt backend to Google Cloud Platform.

## Architecture

- **Cloud Run**: Serverless backend hosting
- **Artifact Registry**: Docker image storage
- **Secret Manager**: Secure environment variable storage
- **Workload Identity**: Secure GitHub Actions authentication (no service account keys)

## Prerequisites

1. **Google Cloud Platform Account**
   - Project ID: `knytt-backend`
   - Billing enabled

2. **Installed Tools**
   ```bash
   # Terraform
   brew install terraform

   # Google Cloud SDK
   brew install --cask google-cloud-sdk

   # Authenticate
   gcloud auth login
   gcloud auth application-default login
   ```

3. **GitHub Repository**
   - Repository must be pushed to GitHub
   - Update `github_repo` variable in `terraform.tfvars`

## Setup Instructions

### Step 1: Create Terraform State Bucket (One-time)

```bash
# Create GCS bucket for Terraform state
gsutil mb -p knytt-backend -l us-central1 gs://knytt-terraform-state

# Enable versioning
gsutil versioning set on gs://knytt-terraform-state
```

### Step 2: Configure Variables

```bash
cd terraform

# Copy example file
cp terraform.tfvars.example terraform.tfvars

# Edit terraform.tfvars with your values
# Copy values from ../.env.cloudrun
```

### Step 3: Initialize Terraform

```bash
terraform init
```

### Step 4: Review Plan

```bash
terraform plan
```

### Step 5: Apply Infrastructure

```bash
terraform apply
```

This will create:
- Artifact Registry repository
- Secret Manager secrets (with your environment variables)
- Service accounts for Cloud Run and GitHub Actions
- Workload Identity pool and provider
- Cloud Run service

### Step 6: Configure GitHub Secrets

After running `terraform apply`, set these secrets in your GitHub repository:

```bash
# Get the values from Terraform outputs
terraform output workload_identity_provider
terraform output github_actions_service_account
```

Go to GitHub → Settings → Secrets and variables → Actions:

1. `WIF_PROVIDER`: Value from `workload_identity_provider` output
2. `WIF_SERVICE_ACCOUNT`: Value from `github_actions_service_account` output

### Step 7: Test Deployment

Push a commit to the `main` branch that modifies `backend/**`:

```bash
git add .
git commit -m "Test automated deployment"
git push origin main
```

Check GitHub Actions tab to see the deployment in progress.

## File Structure

```
terraform/
├── main.tf                 # Provider and API configuration
├── variables.tf            # Input variable definitions
├── terraform.tfvars        # Variable values (gitignored, contains secrets)
├── terraform.tfvars.example # Template for terraform.tfvars
├── artifact-registry.tf    # Docker repository
├── iam.tf                  # Service accounts and permissions
├── secrets.tf              # Secret Manager configuration
├── cloud-run.tf            # Cloud Run service
├── outputs.tf              # Output values
└── .gitignore             # Ignore sensitive files
```

## Updating Secrets

To update a secret value:

1. Update the value in `terraform.tfvars`
2. Run `terraform apply`
3. Terraform will update the secret version
4. Cloud Run will use the new version on next deployment

## Destroying Infrastructure

**⚠️ WARNING: This will delete all resources!**

```bash
terraform destroy
```

## Troubleshooting

### Error: API not enabled

```bash
gcloud services enable run.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable iamcredentials.googleapis.com
```

### Error: Permission denied

Ensure your GCP user has the following roles:
- Cloud Run Admin
- Artifact Registry Admin
- Secret Manager Admin
- Service Account Admin
- Workload Identity Pool Admin

```bash
# Grant yourself the necessary roles
gcloud projects add-iam-policy-binding knytt-backend \
  --member="user:your-email@example.com" \
  --role="roles/owner"
```

### GitHub Actions failing

1. Verify Workload Identity is configured correctly
2. Check that GitHub secrets are set
3. Ensure the service account has necessary permissions
4. Check GitHub Actions logs for detailed errors

## Manual Deployment (Without GitHub Actions)

If you need to deploy manually:

```bash
# Build and push image
cd ..
gcloud builds submit --tag us-central1-docker.pkg.dev/knytt-backend/knytt-backend/backend:manual

# Deploy to Cloud Run (secrets are already configured via Terraform)
gcloud run deploy knytt-backend \
  --image us-central1-docker.pkg.dev/knytt-backend/knytt-backend/backend:manual \
  --region us-central1 \
  --allow-unauthenticated
```

## Security Notes

- All secrets are stored in Secret Manager (encrypted at rest)
- No service account keys in GitHub (using Workload Identity Federation)
- Cloud Run service account has minimal permissions
- HTTPS enforced by default
- Secrets are never exposed in logs or Terraform state

## Cost Optimization

- Cloud Run scales to zero (no cost when idle)
- First 2 million requests/month are free
- Artifact Registry: 0.5 GB free storage
- Secret Manager: 6 active secret versions free

## Monitoring

View logs and metrics:

```bash
# Cloud Run logs
gcloud run services logs read knytt-backend --region=us-central1

# Cloud Run metrics (in GCP Console)
open https://console.cloud.google.com/run/detail/us-central1/knytt-backend/metrics
```

## Next Steps

1. Set up Cloud Run custom domain
2. Configure Cloud CDN for static assets
3. Set up Cloud Monitoring alerts
4. Enable Cloud Trace for request tracing
5. Set up automated backups
