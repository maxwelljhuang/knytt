#!/bin/bash

# Database Backup Script for Railway PostgreSQL
# This script creates a backup of your production database

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "================================================"
echo "   Knytt Database Backup"
echo "================================================"
echo ""

# Check if DATABASE_URL is provided
DATABASE_URL="${DATABASE_URL:-}"

if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}Error: DATABASE_URL not set${NC}"
    echo ""
    echo "Usage:"
    echo "  1. Get DATABASE_URL from Railway:"
    echo "     railway variables | grep DATABASE_URL"
    echo ""
    echo "  2. Run this script:"
    echo "     DATABASE_URL='postgresql://...' ./scripts/backup_database.sh"
    echo ""
    echo "  Or set it as environment variable:"
    echo "     export DATABASE_URL='postgresql://...'"
    echo "     ./scripts/backup_database.sh"
    echo ""
    exit 1
fi

# Create backup directory
BACKUP_DIR="database/backups"
mkdir -p "$BACKUP_DIR"

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/greenthumb_backup_$TIMESTAMP.sql"

echo -e "${BLUE}Starting database backup...${NC}"
echo "Database: $DATABASE_URL"
echo "Backup file: $BACKUP_FILE"
echo ""

# Create backup
echo -e "${YELLOW}Creating backup...${NC}"
pg_dump "$DATABASE_URL" > "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Backup created successfully${NC}"

    # Get file size
    FILE_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "File size: $FILE_SIZE"
    echo ""

    # Compress backup
    echo -e "${YELLOW}Compressing backup...${NC}"
    gzip "$BACKUP_FILE"
    COMPRESSED_FILE="$BACKUP_FILE.gz"

    if [ $? -eq 0 ]; then
        COMPRESSED_SIZE=$(du -h "$COMPRESSED_FILE" | cut -f1)
        echo -e "${GREEN}✓ Backup compressed${NC}"
        echo "Compressed size: $COMPRESSED_SIZE"
        echo "Compressed file: $COMPRESSED_FILE"
    else
        echo -e "${RED}✗ Compression failed${NC}"
    fi

else
    echo -e "${RED}✗ Backup failed${NC}"
    exit 1
fi

echo ""
echo "================================================"
echo "   Backup Summary"
echo "================================================"
echo ""
echo -e "${GREEN}Backup completed successfully!${NC}"
echo ""
echo "Backup location: $COMPRESSED_FILE"
echo ""
echo "To restore this backup:"
echo "  gunzip $COMPRESSED_FILE"
echo "  psql \$DATABASE_URL < $BACKUP_FILE"
echo ""
echo "To upload to S3 (if configured):"
echo "  aws s3 cp $COMPRESSED_FILE s3://your-bucket/backups/"
echo ""

# Optional: Upload to S3
read -p "Upload to S3? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    S3_BUCKET="${S3_BUCKET:-}"

    if [ -z "$S3_BUCKET" ]; then
        read -p "Enter S3 bucket name: " S3_BUCKET
    fi

    if [ -n "$S3_BUCKET" ]; then
        echo -e "${YELLOW}Uploading to S3...${NC}"
        aws s3 cp "$COMPRESSED_FILE" "s3://$S3_BUCKET/backups/$(basename $COMPRESSED_FILE)"

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ Uploaded to S3${NC}"
        else
            echo -e "${RED}✗ S3 upload failed${NC}"
        fi
    fi
fi

echo ""
echo -e "${BLUE}Backup process complete!${NC}"
echo ""

# Cleanup old backups (keep last 7 days)
echo "Cleaning up old backups (keeping last 7 days)..."
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete
echo -e "${GREEN}✓ Cleanup complete${NC}"
echo ""
