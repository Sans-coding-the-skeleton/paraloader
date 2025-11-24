import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    import requests

    print("✅ Requests module imported successfully!")

    # Test a simple request
    response = requests.get('https://httpbin.org/get', timeout=10)
    print(f"✅ HTTP request test passed! Status: {response.status_code}")

except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please run: pip install requests")
except Exception as e:
    print(f"❌ Other error: {e}")