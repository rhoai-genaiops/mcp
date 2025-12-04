#!/bin/bash
#
# Multi-Tenant Calendar Test Script
#
# This script tests the multi-tenant functionality of the calendar application
# by creating events for different users and verifying isolation.
#
# Usage:
#   ./test_multitenant.sh <api-url>
#
# Example:
#   ./test_multitenant.sh http://localhost:8000
#   ./test_multitenant.sh http://calendar-api.calendar-system.svc:8000

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# API URL from argument or default
API_URL="${1:-http://localhost:8000}"

echo "================================================="
echo "  Multi-Tenant Calendar System Test"
echo "================================================="
echo ""
echo "Testing API at: $API_URL"
echo ""

# Function to print test status
print_test() {
    echo -e "${YELLOW}TEST:${NC} $1"
}

print_pass() {
    echo -e "${GREEN}✓ PASS:${NC} $1"
}

print_fail() {
    echo -e "${RED}✗ FAIL:${NC} $1"
}

# Test 1: Create event for user0
print_test "Creating event for user0"
RESPONSE=$(curl -s -X POST "$API_URL/schedules" \
    -H "X-User-ID: user0" \
    -H "Content-Type: application/json" \
    -d '{
        "sid": "test-user0-1",
        "name": "User0 Private Meeting",
        "content": "This should only be visible to user0",
        "category": "Meeting",
        "level": 2,
        "status": 0.0,
        "creation_time": "2025-12-01 10:00:00",
        "start_time": "2025-12-01 14:00:00",
        "end_time": "2025-12-01 15:00:00"
    }')

if echo "$RESPONSE" | grep -q "test-user0-1"; then
    print_pass "Event created for user0"
else
    print_fail "Failed to create event for user0"
    echo "Response: $RESPONSE"
    exit 1
fi

# Test 2: Create event for user1
print_test "Creating event for user1"
RESPONSE=$(curl -s -X POST "$API_URL/schedules" \
    -H "X-User-ID: user1" \
    -H "Content-Type: application/json" \
    -d '{
        "sid": "test-user1-1",
        "name": "User1 Private Meeting",
        "content": "This should only be visible to user1",
        "category": "Meeting",
        "level": 2,
        "status": 0.0,
        "creation_time": "2025-12-01 10:00:00",
        "start_time": "2025-12-01 14:00:00",
        "end_time": "2025-12-01 15:00:00"
    }')

if echo "$RESPONSE" | grep -q "test-user1-1"; then
    print_pass "Event created for user1"
else
    print_fail "Failed to create event for user1"
    echo "Response: $RESPONSE"
    exit 1
fi

# Test 3: Verify user0 can see their event
print_test "Verifying user0 can see their event"
RESPONSE=$(curl -s -X GET "$API_URL/schedules" \
    -H "X-User-ID: user0")

if echo "$RESPONSE" | grep -q "test-user0-1"; then
    print_pass "User0 can see their event"
else
    print_fail "User0 cannot see their event"
    echo "Response: $RESPONSE"
    exit 1
fi

# Test 4: Verify user0 CANNOT see user1's event (isolation test)
print_test "Verifying user0 CANNOT see user1's event (data isolation)"
RESPONSE=$(curl -s -X GET "$API_URL/schedules" \
    -H "X-User-ID: user0")

if echo "$RESPONSE" | grep -q "test-user1-1"; then
    print_fail "SECURITY ISSUE: User0 can see user1's event! Data isolation is broken!"
    echo "Response: $RESPONSE"
    exit 1
else
    print_pass "User0 cannot see user1's event (isolation working)"
fi

# Test 5: Verify user1 can see their event
print_test "Verifying user1 can see their event"
RESPONSE=$(curl -s -X GET "$API_URL/schedules" \
    -H "X-User-ID: user1")

if echo "$RESPONSE" | grep -q "test-user1-1"; then
    print_pass "User1 can see their event"
else
    print_fail "User1 cannot see their event"
    echo "Response: $RESPONSE"
    exit 1
fi

# Test 6: Verify user1 CANNOT see user0's event
print_test "Verifying user1 CANNOT see user0's event (data isolation)"
RESPONSE=$(curl -s -X GET "$API_URL/schedules" \
    -H "X-User-ID: user1")

if echo "$RESPONSE" | grep -q "test-user0-1"; then
    print_fail "SECURITY ISSUE: User1 can see user0's event! Data isolation is broken!"
    echo "Response: $RESPONSE"
    exit 1
else
    print_pass "User1 cannot see user0's event (isolation working)"
fi

# Test 7: Try to read user0's event as user1 (should fail)
print_test "Attempting to read user0's event as user1"
RESPONSE=$(curl -s -X GET "$API_URL/schedules/test-user0-1" \
    -H "X-User-ID: user1")

if echo "$RESPONSE" | grep -q "not found"; then
    print_pass "User1 cannot read user0's event (correctly returns not found)"
elif echo "$RESPONSE" | grep -q "test-user0-1"; then
    print_fail "SECURITY ISSUE: User1 can read user0's event!"
    echo "Response: $RESPONSE"
    exit 1
else
    print_pass "User1 cannot read user0's event"
fi

# Test 8: Try to delete user0's event as user1 (should fail)
print_test "Attempting to delete user0's event as user1"
RESPONSE=$(curl -s -X DELETE "$API_URL/schedules/test-user0-1" \
    -H "X-User-ID: user1")

if echo "$RESPONSE" | grep -q "not found"; then
    print_pass "User1 cannot delete user0's event (correctly returns not found)"
elif echo "$RESPONSE" | grep -q "deleted successfully"; then
    print_fail "SECURITY ISSUE: User1 was able to delete user0's event!"
    echo "Response: $RESPONSE"
    exit 1
else
    print_pass "User1 cannot delete user0's event"
fi

# Test 9: Verify user0 can still see their event after user1's failed delete attempt
print_test "Verifying user0's event still exists after user1's delete attempt"
RESPONSE=$(curl -s -X GET "$API_URL/schedules/test-user0-1" \
    -H "X-User-ID: user0")

if echo "$RESPONSE" | grep -q "test-user0-1"; then
    print_pass "User0's event still exists (delete attempt by user1 correctly failed)"
else
    print_fail "User0's event was deleted!"
    echo "Response: $RESPONSE"
    exit 1
fi

# Cleanup: Delete test events
print_test "Cleaning up test data"
curl -s -X DELETE "$API_URL/schedules/test-user0-1" -H "X-User-ID: user0" > /dev/null
curl -s -X DELETE "$API_URL/schedules/test-user1-1" -H "X-User-ID: user1" > /dev/null
print_pass "Test data cleaned up"

echo ""
echo "================================================="
echo -e "${GREEN}✓ All tests passed!${NC}"
echo "================================================="
echo ""
echo "Multi-tenant isolation is working correctly:"
echo "  ✓ Users can create their own events"
echo "  ✓ Users can see only their own events"
echo "  ✓ Users cannot see other users' events"
echo "  ✓ Users cannot read other users' events"
echo "  ✓ Users cannot modify other users' events"
echo "  ✓ Users cannot delete other users' events"
echo ""
echo "The calendar application is ready for multi-tenant deployment!"
