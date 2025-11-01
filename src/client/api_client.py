import os
import requests

API_BASE = "http://app:8000"
TIMEOUT = float(os.getenv("HTTP_TIMEOUT", "10"))


class ApiError(Exception):
    """Custom exception for API call failures."""
    def __init__(self, message, status_code=None, details=None):
        super().__init__(message)
        self.status_code = status_code
        self.details = details


class ApiClient:
    def __init__(self, base_url: str = API_BASE, timeout: float = TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def call_api(
        self,
        path: str,
        access_token: str,
        method: str = "GET",
        **kwargs
    ) -> dict:
        """
        汎用的なAPI呼び出しメソッド
        """
        if not access_token:
            raise ValueError("Access token is required")

        url = self.base_url + path
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {access_token}"

        try:
            response = requests.request(
                method,
                url,
                headers=headers,
                timeout=self.timeout,
                **kwargs
            )
            response.raise_for_status()
            # No Contentの場合は空のdictを返す
            if response.status_code == 204:
                return {}
            return response.json()
        except requests.HTTPError as e:
            try:
                details = e.response.json()
            except (ValueError, TypeError):
                details = e.response.text
            raise ApiError(
                f"API call failed with status {e.response.status_code}",
                status_code=e.response.status_code,
                details=details
            ) from e
        except requests.RequestException as e:
            raise ApiError(f"Network error during API call: {e}") from e
