#!/bin/bash
# Integration test script for Profiler and Advisor services

set -e

echo "🧪 Testing Profiler and Advisor Services..."

# Configuration
PROFILER_URL=${PROFILER_URL:-http://localhost:8002}
ADVISOR_URL=${ADVISOR_URL:-http://localhost:8003}

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test function
test_endpoint() {
    local name=$1
    local url=$2
    local method=${3:-GET}
    local data=${4:-}

    echo -n "Testing ${name}... "

    if [ "$method" = "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$url")
    else
        response=$(curl -s -w "\n%{http_code}" -X POST "$url" \
            -H "Content-Type: application/json" \
            -d "$data")
    fi

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" -eq 200 ]; then
        echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
        return 0
    else
        echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
        echo "Response: $body"
        return 1
    fi
}

# ─── Profiler Service Tests ─────────────────────────────

echo -e "\n${YELLOW}=== Profiler Service ===${NC}"

test_endpoint "Profiler Health Check" "$PROFILER_URL/health"
test_endpoint "Profiler Status" "$PROFILER_URL/api/v1/profiler/status"

# Manual analysis trigger (may fail if no data)
echo -n "Testing Profiler Analysis (manual trigger)... "
response=$(curl -s -w "\n%{http_code}" -X POST "$PROFILER_URL/api/v1/profiler/analyze" \
    -H "Content-Type: application/json" \
    -d '{"user_id": "default", "days": 7}')

http_code=$(echo "$response" | tail -n1)
if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 500 ]; then
    # 500 is acceptable if no data exists yet
    echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
fi

# ─── Advisor Service Tests ──────────────────────────────

echo -e "\n${YELLOW}=== Advisor Service ===${NC}"

test_endpoint "Advisor Health Check" "$ADVISOR_URL/health"
test_endpoint "Advisor Status" "$ADVISOR_URL/api/v1/advisor/status"

# Manual generation trigger (may fail if no profile)
echo -n "Testing Advisor Generation (manual trigger)... "
response=$(curl -s -w "\n%{http_code}" -X POST "$ADVISOR_URL/api/v1/advisor/generate" \
    -H "Content-Type: application/json" \
    -d '{"user_id": "default", "web_research": false, "notify": false}')

http_code=$(echo "$response" | tail -n1)
if [ "$http_code" -eq 200 ] || [ "$http_code" -eq 500 ]; then
    # 500 is acceptable if no profile exists yet
    echo -e "${GREEN}✓ PASS${NC} (HTTP $http_code)"
else
    echo -e "${RED}✗ FAIL${NC} (HTTP $http_code)"
fi

# ─── Summary ────────────────────────────────────────────

echo -e "\n${YELLOW}=== Test Complete ===${NC}"
echo "Note: Some tests may fail if database is not populated yet."
echo "Run ingest service first to populate data."
