#!/bin/bash

# Verify Deployment Health
# This script checks that all services are running correctly

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
API_URL="${1:-}"
FRONTEND_URL="${2:-}"

echo "================================================"
echo "   Knytt Deployment Verification"
echo "================================================"
echo ""

if [ -z "$API_URL" ] || [ -z "$FRONTEND_URL" ]; then
    echo -e "${RED}Usage: $0 <api-url> <frontend-url>${NC}"
    echo ""
    echo "Example:"
    echo "  $0 https://your-api.up.railway.app https://your-app.vercel.app"
    echo ""
    exit 1
fi

echo -e "${BLUE}API URL:${NC} $API_URL"
echo -e "${BLUE}Frontend URL:${NC} $FRONTEND_URL"
echo ""

# Function to check endpoint
check_endpoint() {
    local url=$1
    local description=$2
    local expected_status=${3:-200}

    echo -n "Checking $description... "

    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$url" || echo "000")

    if [ "$http_code" -eq "$expected_status" ]; then
        echo -e "${GREEN}✓ OK (HTTP $http_code)${NC}"
        return 0
    else
        echo -e "${RED}✗ FAILED (HTTP $http_code)${NC}"
        return 1
    fi
}

# Function to check JSON response
check_json_endpoint() {
    local url=$1
    local description=$2
    local expected_field=$3

    echo -n "Checking $description... "

    response=$(curl -s "$url" || echo "{}")

    if echo "$response" | grep -q "$expected_field"; then
        echo -e "${GREEN}✓ OK${NC}"
        echo "  Response: $response"
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        echo "  Response: $response"
        return 1
    fi
}

echo "================================================"
echo "   API Health Checks"
echo "================================================"
echo ""

# Check API health endpoint
check_json_endpoint "$API_URL/health" "API Health Endpoint" "healthy"

# Check API search endpoint
check_json_endpoint "$API_URL/api/v1/search?q=test&limit=5" "Search Endpoint" "results"

# Check API documentation
check_endpoint "$API_URL/docs" "API Documentation" 200

echo ""
echo "================================================"
echo "   Frontend Health Checks"
echo "================================================"
echo ""

# Check frontend homepage
check_endpoint "$FRONTEND_URL" "Frontend Homepage" 200

# Check frontend search page
check_endpoint "$FRONTEND_URL/search?q=test" "Frontend Search Page" 200

echo ""
echo "================================================"
echo "   CORS Configuration Check"
echo "================================================"
echo ""

echo "Checking CORS headers..."
cors_headers=$(curl -s -I -X OPTIONS \
    -H "Origin: $FRONTEND_URL" \
    -H "Access-Control-Request-Method: GET" \
    "$API_URL/health" | grep -i "access-control" || echo "")

if [ -n "$cors_headers" ]; then
    echo -e "${GREEN}✓ CORS headers present${NC}"
    echo "$cors_headers"
else
    echo -e "${YELLOW}⚠ No CORS headers found${NC}"
    echo "  Make sure CORS_ORIGINS includes: $FRONTEND_URL"
fi

echo ""
echo "================================================"
echo "   SSL/HTTPS Check"
echo "================================================"
echo ""

# Check API SSL
if [[ $API_URL == https://* ]]; then
    echo -e "${GREEN}✓ API uses HTTPS${NC}"
else
    echo -e "${RED}✗ API should use HTTPS in production${NC}"
fi

# Check Frontend SSL
if [[ $FRONTEND_URL == https://* ]]; then
    echo -e "${GREEN}✓ Frontend uses HTTPS${NC}"
else
    echo -e "${RED}✗ Frontend should use HTTPS in production${NC}"
fi

echo ""
echo "================================================"
echo "   Performance Check"
echo "================================================"
echo ""

echo "Measuring API response time..."
start_time=$(date +%s%N)
curl -s "$API_URL/health" > /dev/null
end_time=$(date +%s%N)
response_time=$(( (end_time - start_time) / 1000000 ))

echo "API response time: ${response_time}ms"

if [ "$response_time" -lt 500 ]; then
    echo -e "${GREEN}✓ Response time is good${NC}"
elif [ "$response_time" -lt 1000 ]; then
    echo -e "${YELLOW}⚠ Response time is acceptable${NC}"
else
    echo -e "${RED}✗ Response time is slow${NC}"
fi

echo ""
echo "================================================"
echo "   Database Connection Check"
echo "================================================"
echo ""

# Try to get products (requires DB connection)
echo "Checking database connectivity via API..."
db_response=$(curl -s "$API_URL/api/v1/search?q=shoes&limit=1" || echo "{}")

if echo "$db_response" | grep -q "results"; then
    echo -e "${GREEN}✓ Database connection working${NC}"
else
    echo -e "${RED}✗ Database connection may have issues${NC}"
    echo "  Response: $db_response"
fi

echo ""
echo "================================================"
echo "   Summary"
echo "================================================"
echo ""

echo -e "${BLUE}Deployment verification complete!${NC}"
echo ""
echo "Next steps:"
echo "1. Monitor logs in Railway dashboard"
echo "2. Check Vercel deployment logs"
echo "3. Set up monitoring (Sentry, UptimeRobot, etc.)"
echo "4. Test user flows (register, login, search, etc.)"
echo "5. Verify Celery tasks are running (check Railway logs)"
echo ""
echo "For continuous monitoring, consider setting up:"
echo "- UptimeRobot: https://uptimerobot.com"
echo "- Sentry: https://sentry.io"
echo "- Better Stack: https://betterstack.com"
echo ""
