import os
import requests

API_BASE = "http://app:8000"
API_PATH = "/protected"
TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "10"))


class ApiError(Exception):
    """Custom exception for API call failures."""
    def __init__(self, message, status_code=None, details=None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


def call_protected_api(access_token: str) -> dict:
    """
    アクセストークンを引数に受け取り、Authorization ヘッダを付与して API を叩く
    """
    if not access_token:
        raise ValueError("Access token is required")

    url = API_BASE.rstrip("/") + API_PATH
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        r = requests.get(url, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        try:
            details = e.response.json()
        except ValueError:
            details = e.response.text
        raise ApiError(
            f"API call failed with status {e.response.status_code}",
            status_code=e.response.status_code,
            details=details
        ) from e
    except requests.RequestException as e:
        raise ApiError(f"Network error during API call: {e}") from e
