"""
Comprehensive API endpoint testing for Social Media Post Manager
Tests all endpoints on the deployed Render instance
"""

import requests
import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import time
import urllib3

# Disable SSL warnings for testing
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Base URL for the deployed API
BASE_URL = "https://social-media-backend-mchy.onrender.com"

# Test results storage
test_results = []

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(60)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.RESET}\n")

def print_test(endpoint: str, method: str, description: str):
    """Print test information"""
    print(f"{Colors.BOLD}Testing:{Colors.RESET} {method} {endpoint}")
    print(f"{Colors.BOLD}Description:{Colors.RESET} {description}")

def print_result(success: bool, message: str, details: Optional[Dict] = None):
    """Print test result"""
    if success:
        print(f"{Colors.GREEN}✓ SUCCESS:{Colors.RESET} {message}")
    else:
        print(f"{Colors.RED}✗ FAILED:{Colors.RESET} {message}")
    
    if details:
        print(f"{Colors.YELLOW}Details:{Colors.RESET}")
        print(json.dumps(details, indent=2))
    print("-" * 60)

def test_endpoint(
    method: str,
    endpoint: str,
    description: str,
    data: Optional[Dict] = None,
    params: Optional[Dict] = None,
    expected_status: int = 200
) -> Dict[str, Any]:
    """Test a single endpoint"""
    url = f"{BASE_URL}{endpoint}"
    print_test(endpoint, method, description)
    
    try:
        # Make request based on method
        if method == "GET":
            response = requests.get(url, params=params, timeout=30)
        elif method == "POST":
            response = requests.post(url, json=data, timeout=30)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        # Check status code
        success = response.status_code == expected_status
        
        # Parse response
        try:
            response_data = response.json()
        except:
            response_data = {"raw_response": response.text}
        
        # Store result
        result = {
            "endpoint": endpoint,
            "method": method,
            "description": description,
            "status_code": response.status_code,
            "expected_status": expected_status,
            "success": success,
            "response": response_data,
            "response_time": response.elapsed.total_seconds()
        }
        
        # Print result
        print_result(
            success,
            f"Status: {response.status_code} (expected {expected_status}), Time: {response.elapsed.total_seconds():.2f}s",
            response_data if not success or response.status_code != 200 else None
        )
        
        test_results.append(result)
        return result
        
    except requests.exceptions.Timeout:
        result = {
            "endpoint": endpoint,
            "method": method,
            "description": description,
            "success": False,
            "error": "Request timeout (30s)"
        }
        print_result(False, "Request timeout after 30 seconds")
        test_results.append(result)
        return result
        
    except Exception as e:
        result = {
            "endpoint": endpoint,
            "method": method,
            "description": description,
            "success": False,
            "error": str(e)
        }
        print_result(False, f"Exception: {str(e)}")
        test_results.append(result)
        return result

def run_all_tests():
    """Run all API endpoint tests"""
    print_header("Social Media Post Manager API Tests")
    print(f"Testing API at: {BASE_URL}")
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Store session ID for later tests
    session_id = None
    
    # Test 1: Root endpoint
    test_endpoint(
        "GET", "/",
        "Test root endpoint - should return API info"
    )
    
    # Test 2: Health check
    test_endpoint(
        "GET", "/health",
        "Test health check - should return health status"
    )
    
    # Test 3: API Documentation endpoints
    print_header("API Documentation Endpoints")
    
    test_endpoint(
        "GET", "/docs",
        "Test Swagger documentation endpoint",
        expected_status=200
    )
    
    test_endpoint(
        "GET", "/redoc",
        "Test ReDoc documentation endpoint",
        expected_status=200
    )
    
    # Test 4: Session Management
    print_header("Session Management Endpoints")
    
    # Create session
    create_result = test_endpoint(
        "POST", "/api/sessions/create",
        "Create a new session",
        data={"preferences": {"theme": "dark", "notifications": True}}
    )
    
    if create_result["success"]:
        session_id = create_result["response"].get("sessionId")
        print(f"{Colors.GREEN}Session created:{Colors.RESET} {session_id}\n")
    
    # Test with session ID if available
    if session_id:
        # Get session
        test_endpoint(
            "GET", f"/api/sessions/{session_id}",
            "Get session information"
        )
        
        # Get quota
        test_endpoint(
            "GET", f"/api/sessions/{session_id}/quota",
            "Get session quota information"
        )
        
        # Update preferences
        test_endpoint(
            "PUT", f"/api/sessions/{session_id}/preferences",
            "Update session preferences",
            data={"theme": "light", "notifications": False, "language": "en"}
        )
        
        # Get history
        test_endpoint(
            "GET", f"/api/sessions/{session_id}/history",
            "Get session history",
            params={"limit": 5, "offset": 0}
        )
    
    # Test invalid session
    test_endpoint(
        "GET", "/api/sessions/invalid-session-id",
        "Test with invalid session ID (should return 404)",
        expected_status=404
    )
    
    # Test 5: News Endpoints
    print_header("News Service Endpoints")
    
    # News health check
    test_endpoint(
        "GET", "/api/news/health",
        "News service health check"
    )
    
    # Get available models
    test_endpoint(
        "GET", "/api/news/models",
        "Get available LLM models"
    )
    
    # Get topic suggestions
    test_endpoint(
        "GET", "/api/news/topics",
        "Get suggested topics"
    )
    
    # Test news fetch with valid data
    if session_id:
        # Get today's date
        today = datetime.now().strftime("%Y-%m-%d")
        
        test_endpoint(
            "POST", "/api/news/fetch",
            "Fetch news articles (valid request)",
            data={
                "topic": "AI",
                "date": today,
                "topN": 3,
                "llmModel": "claude-3-5-sonnet",
                "sessionId": session_id
            }
        )
        
        # Test with yesterday's date
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
        test_endpoint(
            "POST", "/api/news/fetch",
            "Fetch news articles for yesterday",
            data={
                "topic": "Technology",
                "date": yesterday,
                "topN": 2,
                "llmModel": "gpt-4-turbo",
                "sessionId": session_id
            }
        )
    
    # Test 6: Error Cases
    print_header("Error Case Testing")
    
    # Invalid news request - missing fields
    test_endpoint(
        "POST", "/api/news/fetch",
        "News fetch with missing fields (should return 422)",
        data={"topic": "AI"},
        expected_status=422
    )
    
    # Invalid news request - bad date format
    test_endpoint(
        "POST", "/api/news/fetch",
        "News fetch with invalid date format (should return 422)",
        data={
            "topic": "AI",
            "date": "2024/01/15",  # Wrong format
            "topN": 3,
            "llmModel": "claude-3-5-sonnet",
            "sessionId": session_id or "test-session"
        },
        expected_status=422
    )
    
    # Invalid news request - topN out of range
    test_endpoint(
        "POST", "/api/news/fetch",
        "News fetch with topN out of range (should return 422)",
        data={
            "topic": "AI",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "topN": 20,  # Max is 12
            "llmModel": "claude-3-5-sonnet",
            "sessionId": session_id or "test-session"
        },
        expected_status=422
    )
    
    # Test 7: Clean up - Delete session
    if session_id:
        print_header("Cleanup")
        test_endpoint(
            "DELETE", f"/api/sessions/{session_id}",
            "Delete test session"
        )
    
    # Print summary
    print_header("Test Summary")
    total_tests = len(test_results)
    successful_tests = sum(1 for r in test_results if r.get("success", False))
    failed_tests = total_tests - successful_tests
    
    print(f"{Colors.BOLD}Total Tests:{Colors.RESET} {total_tests}")
    print(f"{Colors.GREEN}Successful:{Colors.RESET} {successful_tests}")
    print(f"{Colors.RED}Failed:{Colors.RESET} {failed_tests}")
    print(f"{Colors.BOLD}Success Rate:{Colors.RESET} {(successful_tests/total_tests*100):.1f}%")
    
    # List failed tests
    if failed_tests > 0:
        print(f"\n{Colors.RED}Failed Tests:{Colors.RESET}")
        for result in test_results:
            if not result.get("success", False):
                print(f"  - {result['method']} {result['endpoint']}: {result.get('error', f'Status {result.get('status_code')}')}")
    
    # Save detailed results
    with open("api_test_results.json", "w") as f:
        json.dump({
            "test_date": datetime.now().isoformat(),
            "base_url": BASE_URL,
            "summary": {
                "total": total_tests,
                "successful": successful_tests,
                "failed": failed_tests,
                "success_rate": f"{(successful_tests/total_tests*100):.1f}%"
            },
            "results": test_results
        }, f, indent=2)
    
    print(f"\n{Colors.BLUE}Detailed results saved to:{Colors.RESET} api_test_results.json")

if __name__ == "__main__":
    run_all_tests()
