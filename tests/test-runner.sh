#!/bin/bash
set -e

echo "Starting integration tests..."

# Start services
docker-compose -f docker-compose.test.yml up -d

# Wait for services to be ready
echo "Waiting for services to start..."
timeout 120 bash -c 'until curl -f http://localhost:8081/api/health; do sleep 5; done'

# Run tests
echo "Running integration tests..."

# Test 1: Health check
echo "Testing health endpoint..."
curl -f http://localhost:8081/api/health

# Test 2: Login endpoint with valid email
echo "Testing login with valid email..."
curl -X POST http://localhost:8081/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"test@example.com"}' \
     --fail

# Test 3: Login endpoint with invalid email
echo "Testing login with invalid email..."
response=$(curl -s -o /dev/null -w "%{http_code}" \
     -X POST http://localhost:8081/api/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"invalid-email"}')

if [ "$response" != "400" ]; then
    echo "Expected 400 status code for invalid email, got $response"
    exit 1
fi

echo "All integration tests passed!"

# Cleanup
docker-compose -f docker-compose.test.yml down -v