#!/bin/bash

# Generate Secrets for Production Deployment
# This script generates secure random secrets for production use

set -e

echo "================================================"
echo "   Knytt Production Secrets Generator"
echo "================================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Generate secrets
echo -e "${GREEN}Generating secure secrets...${NC}"
echo ""

JWT_SECRET=$(openssl rand -hex 32)
APP_SECRET=$(openssl rand -hex 32)
DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

echo "================================================"
echo "   GENERATED SECRETS (SAVE THESE SECURELY!)"
echo "================================================"
echo ""

echo -e "${YELLOW}JWT_SECRET_KEY:${NC}"
echo "$JWT_SECRET"
echo ""

echo -e "${YELLOW}SECRET_KEY:${NC}"
echo "$APP_SECRET"
echo ""

echo -e "${YELLOW}DB_PASSWORD (if needed):${NC}"
echo "$DB_PASSWORD"
echo ""

echo "================================================"
echo ""

# Option to save to file
read -p "Save secrets to .env.production.local? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]
then
    ENV_FILE=".env.production.local"

    if [ -f "$ENV_FILE" ]; then
        echo -e "${RED}Warning: $ENV_FILE already exists!${NC}"
        read -p "Overwrite? (y/n) " -n 1 -r
        echo ""
        if [[ ! $REPLY =~ ^[Yy]$ ]]
        then
            echo "Aborted. Secrets not saved."
            exit 0
        fi
    fi

    cat > "$ENV_FILE" << EOF
# Production Secrets - GENERATED $(date)
# DO NOT COMMIT THIS FILE TO GIT!

# Security Secrets
JWT_SECRET_KEY=$JWT_SECRET
SECRET_KEY=$APP_SECRET

# Database Password (if using custom DB)
DB_PASSWORD=$DB_PASSWORD

# Add other production environment variables here
# Copy from .env.production.example and fill in the values
EOF

    echo -e "${GREEN}Secrets saved to $ENV_FILE${NC}"
    echo -e "${RED}IMPORTANT: Add $ENV_FILE to .gitignore to prevent committing secrets!${NC}"

    # Check if file is in .gitignore
    if grep -q ".env.production.local" .gitignore 2>/dev/null; then
        echo -e "${GREEN}✓ $ENV_FILE is already in .gitignore${NC}"
    else
        echo -e "${YELLOW}⚠ Adding $ENV_FILE to .gitignore...${NC}"
        echo ".env.production.local" >> .gitignore
        echo -e "${GREEN}✓ Added to .gitignore${NC}"
    fi
else
    echo "Secrets not saved. Copy them manually to your deployment platform."
fi

echo ""
echo "================================================"
echo "   Next Steps:"
echo "================================================"
echo "1. Add these secrets to Railway environment variables"
echo "2. Update CORS_ORIGINS with your Vercel URL"
echo "3. Configure database connection (Railway will provide DATABASE_URL)"
echo "4. Review and update other variables in .env.production.example"
echo ""
echo "For Railway:"
echo "  railway variables set JWT_SECRET_KEY=<value>"
echo "  railway variables set SECRET_KEY=<value>"
echo ""
echo "Or add via Railway Dashboard → Service → Variables"
echo ""
