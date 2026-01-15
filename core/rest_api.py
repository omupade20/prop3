import requests
from config.settings import ACCESS_TOKEN, API_BASE_URL

def make_api_request(endpoint: str, method: str = "GET", params=None, data=None):
    """
    Make a basic REST API request to Upstox API.
    Uses the ACCESS_TOKEN from config/settings.py
    """
    url = API_BASE_URL + endpoint
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Accept": "application/json"
    }

    try:
        response = requests.request(method, url, headers=headers, params=params, json=data)
        response_data = response.json()
    except Exception as e:
        print(f"Error while making API call: {e}")
        return None

    if response.status_code == 401:
        print("Unauthorized — token may be expired or invalid.")
        print("Please update ACCESS_TOKEN in config/settings.py")
        return None

    if response.status_code >= 400:
        print(f"API Error {response.status_code}: {response_data}")
        return None

    return response_data


def get_user_profile():
    """
    Test API call: Get Profile of authenticated user
    """
    return make_api_request("user/profile")
