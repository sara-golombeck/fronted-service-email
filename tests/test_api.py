import requests
import time
import sys
import json

class IntegrationTests:
    def __init__(self, base_url="http://localhost"):
        self.base_url = base_url
        self.session = requests.Session()
    
    def wait_for_service(self, timeout=120):
        """Wait for the service to be ready"""
        for _ in range(timeout):
            try:
                response = self.session.get(f"{self.base_url}/api/health")
                if response.status_code == 200:
                    return True
            except requests.exceptions.RequestException:
                pass
            time.sleep(1)
        return False
    
    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.session.get(f"{self.base_url}/api/health")
        assert response.status_code == 200
        data = response.json()
        assert "Status" in data
        print("✓ Health endpoint test passed")
    
    def test_login_valid_email(self):
        """Test login with valid email"""
        payload = {"email": "test@example.com"}
        response = self.session.post(
            f"{self.base_url}/api/auth/login",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        print("✓ Valid email login test passed")
    
    def test_login_invalid_email(self):
        """Test login with invalid email"""
        payload = {"email": "invalid-email"}
        response = self.session.post(
            f"{self.base_url}/api/auth/login",
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 400
        data = response.json()
        assert data["success"] is False
        print("✓ Invalid email login test passed")
    
    def run_all_tests(self):
        """Run all integration tests"""
        print("Starting integration tests...")
        
        if not self.wait_for_service():
            print("✗ Service failed to start within timeout")
            return False
        
        try:
            self.test_health_endpoint()
            self.test_login_valid_email()
            self.test_login_invalid_email()
            print("✓ All integration tests passed!")
            return True
        except Exception as e:
            print(f"✗ Test failed: {e}")
            return False

if __name__ == "__main__":
    tests = IntegrationTests()
    success = tests.run_all_tests()
    sys.exit(0 if success else 1)