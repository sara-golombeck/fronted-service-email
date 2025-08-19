# #!/usr/bin/env python3
# """
# Integration Test for EmailService API
# Target: http://13.204.97.37/
# """

# import requests
# import sys

# BASE_URL = "http://13.204.97.37"
# TIMEOUT = 10

# def test_health():
#     """Test service health endpoint"""
#     resp = requests.get(f"{BASE_URL}/api/health", timeout=TIMEOUT)
#     assert resp.status_code == 200
#     data = resp.json()
#     assert data["status"] == "Healthy"
#     print("PASS: Health check")

# def test_login_valid():
#     """Test login with valid email"""
#     payload = {"email": "test@example.com"}
#     resp = requests.post(f"{BASE_URL}/api/auth/login", json=payload, timeout=TIMEOUT)
#     assert resp.status_code == 200
#     data = resp.json()
#     assert data["success"] is True
#     print("PASS: Valid login")

# def test_login_invalid():
#     """Test login with invalid email"""
#     payload = {"email": "invalid-email"}
#     resp = requests.post(f"{BASE_URL}/api/auth/login", json=payload, timeout=TIMEOUT)
#     assert resp.status_code == 400
#     data = resp.json()
#     assert data["success"] is False
#     print("PASS: Invalid email validation")

# def test_performance():
#     """Test basic performance"""
#     import time
#     start = time.time()
#     resp = requests.get(f"{BASE_URL}/api/health", timeout=TIMEOUT)
#     duration = time.time() - start
#     assert resp.status_code == 200
#     assert duration < 2.0
#     print(f"PASS: Performance test ({duration:.2f}s)")

# def main():
#     """Run all tests"""
#     tests = [test_health, test_login_valid, test_login_invalid, test_performance]
    
#     print(f"Running integration tests on {BASE_URL}")
#     print("-" * 50)
    
#     failed = 0
#     for test in tests:
#         try:
#             test()
#         except Exception as e:
#             print(f"FAIL: {test.__name__} - {e}")
#             failed += 1
    
#     print("-" * 50)
#     if failed == 0:
#         print(f"SUCCESS: All {len(tests)} tests passed")
#         sys.exit(0)
#     else:
#         print(f"FAILED: {failed}/{len(tests)} tests failed")
#         sys.exit(1)

# if __name__ == "__main__":
#     main()

#!/usr/bin/env python3
"""
Integration Test for EmailService API
Target: Configurable via environment or default to localhost
"""

import requests
import sys
import os

# Support for environment variables - flexible for different environments
BASE_URL = os.getenv('BASE_URL', 'http://localhost:8080')  # Default to local docker-compose
TIMEOUT = int(os.getenv('TIMEOUT', '10'))

def test_health():
    """Test service health endpoint"""
    resp = requests.get(f"{BASE_URL}/api/health", timeout=TIMEOUT)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "Healthy"
    print("PASS: Health check")

def test_login_valid():
    """Test login with valid email"""
    payload = {"email": "test@example.com"}
    resp = requests.post(f"{BASE_URL}/api/auth/login", json=payload, timeout=TIMEOUT)
    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    print("PASS: Valid login")

def test_login_invalid():
    """Test login with invalid email"""
    payload = {"email": "invalid-email"}
    resp = requests.post(f"{BASE_URL}/api/auth/login", json=payload, timeout=TIMEOUT)
    assert resp.status_code == 400
    data = resp.json()
    assert data["success"] is False
    print("PASS: Invalid email validation")

def test_performance():
    """Test basic performance"""
    import time
    start = time.time()
    resp = requests.get(f"{BASE_URL}/api/health", timeout=TIMEOUT)
    duration = time.time() - start
    assert resp.status_code == 200
    assert duration < 2.0
    print(f"PASS: Performance test ({duration:.2f}s)")

def main():
    """Run all tests"""
    tests = [test_health, test_login_valid, test_login_invalid, test_performance]
    
    print(f"Running integration tests on {BASE_URL}")
    print("-" * 50)
    
    failed = 0
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"FAIL: {test.__name__} - {e}")
            failed += 1
    
    print("-" * 50)
    if failed == 0:
        print(f"SUCCESS: All {len(tests)} tests passed")
        sys.exit(0)
    else:
        print(f"FAILED: {failed}/{len(tests)} tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()