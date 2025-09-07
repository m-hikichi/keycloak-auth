import os

import requests
from rich import print


class TokenAcquisitionError(Exception):
    """Custom exception for token acquisition failures."""

    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details


class KeycloakClient:
    """
    A client for interacting with Keycloak to obtain access tokens.
    """

    def __init__(self, base_url, realm, client_id, client_secret):
        self.base_url = base_url
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = (
            f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"
        )

    def get_token_with_password(self, username, password):
        """
        Get a token directly using the Resource Owner Password Credentials grant.
        """
        payload = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": username,
            "password": password,
        }
        try:
            r = requests.post(self.token_url, data=payload)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.HTTPError as e:
            try:
                error_details = e.response.json()
            except ValueError:
                error_details = {"raw_response": e.response.text}
            raise TokenAcquisitionError(
                f"Failed to acquire token: {e.response.status_code}",
                details=error_details,
            ) from e


if __name__ == "__main__":
    # --- Example Usage ---
    client = KeycloakClient(
        base_url=os.environ["KC_BASE"],
        realm=os.environ["REALM"],
        client_id=os.environ["CLIENT_ID"],
        client_secret=os.environ["CLIENT_SECRET"],
    )

    try:
        token_data = client.get_token_with_password(
            os.environ["USERNAME"], os.environ["PASSWORD"]
        )
        print("Successfully obtained token:")
        print(token_data)
    except TokenAcquisitionError as e:
        print(f"Error: {e}")
        if e.details:
            print(f"Details: {e.details}")
