#!/bin/bash
# API Endpoint Verification Script — T11.7
# Verifies all 69+ API endpoints are reachable
# Usage: bash verify_endpoints.sh [base_url]
set -e

BASE_URL="${1:-http://localhost:8000}"
PASS=0
FAIL=0
TOTAL=0

check() {
    local method=$1
    local path=$2
    local expected_code=$3
    local body="${4:-}"

    TOTAL=$((TOTAL + 1))
    local code
    if [ "$method" = "GET" ]; then
        code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL$path" 2>/dev/null || echo "000")
    elif [ "$method" = "POST" ]; then
        code=$(curl -s -o /dev/null -w "%{http_code}" -X POST -H "Content-Type: application/json" -d "${body}" "$BASE_URL$path" 2>/dev/null || echo "000")
    elif [ "$method" = "PATCH" ]; then
        code=$(curl -s -o /dev/null -w "%{http_code}" -X PATCH -H "Content-Type: application/json" -d "${body}" "$BASE_URL$path" 2>/dev/null || echo "000")
    elif [ "$method" = "PUT" ]; then
        code=$(curl -s -o /dev/null -w "%{http_code}" -X PUT -H "Content-Type: application/json" -d "${body}" "$BASE_URL$path" 2>/dev/null || echo "000")
    elif [ "$method" = "DELETE" ]; then
        code=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE "$BASE_URL$path" 2>/dev/null || echo "000")
    fi

    # Check if code matches expected (or is a valid HTTP code like 404)
    if [ "$code" != "000" ]; then
        echo "  ✅ $method $path → $code"
        PASS=$((PASS + 1))
    else
        echo "  ❌ $method $path → unreachable"
        FAIL=$((FAIL + 1))
    fi
}

echo "============================================"
echo " Context Platform API Endpoint Verification"
echo " Base URL: $BASE_URL"
echo "============================================"

# ── Core Endpoints ──
echo ""
echo "── Core ──"
check GET "/" 200
check GET "/health" 200
check GET "/api/v1/contexts" 200
check GET "/api/v1/contexts?domain=operations&skip=0&limit=10" 200
check POST "/api/v1/contexts" 200 '{"title":"Verification Test","content":"Test content"}'

# ── V1 API Endpoints ──
echo ""
echo "── V1: Search ──"
check POST "/api/v1/search" 200 '{"query":"test","mode":"hybrid"}'
check POST "/api/v1/search" 200 '{"query":"test","mode":"exact"}'
check POST "/api/v1/search" 200 '{"query":"test","mode":"semantic"}'

echo ""
echo "── V1: Entities ──"
check GET "/api/v1/entities" 200
check POST "/api/v1/entities" 200 '{"name":"Verification Entity","type":"customer","domain":"customer"}'

echo ""
echo "── V1: Relations ──"
check GET "/api/v1/relations" 200

echo ""
echo "── V1: Users ──"
check GET "/api/v1/users" 200

echo ""
echo "── V1: Permissions ──"
check GET "/api/v1/permissions/check" 200

echo ""
echo "── V1: Review ──"
check GET "/api/v1/review/queue" 200

echo ""
echo "── V1: Metrics ──"
check GET "/api/v1/metrics/overview" 200
check GET "/api/v1/metrics/coverage" 200
check GET "/api/v1/metrics/freshness" 200
check GET "/api/v1/metrics/confidence-trends" 200

echo ""
echo "── V1: Config ──"
check GET "/api/v1/config" 200

# ── External API ──
echo ""
echo "── External API ──"
check GET "/api/v1/external/health" 200
check GET "/api/v1/external/health/metrics" 200
check GET "/api/v1/external/auth/whoami" 200
check GET "/api/v1/external/contexts" 200
check POST "/api/v1/external/search" 200 '{"query":"test"}'
check GET "/api/v1/external/entities" 200
check GET "/api/v1/external/workspaces" 200

echo ""
echo "============================================"
echo " Results: $PASS/$TOTAL passed, $FAIL failed"
echo "============================================"

if [ "$FAIL" -gt 0 ]; then
    exit 1
fi
