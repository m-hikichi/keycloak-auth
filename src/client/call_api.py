import os
import sys
from rich import print

from api_client import ApiError, call_protected_api
from keycloak_ropc_client import KeycloakClient, TokenAcquisitionError


def get_access_token() -> str:
    """
    Keycloak ROPC でアクセストークンを取得
    """
    if "USERNAME" not in os.environ or "PASSWORD" not in os.environ:
        print("[bold red]ERROR: USERNAME/PASSWORD を環境変数で指定してください。[/bold red]", file=sys.stderr)
        sys.exit(1)

    kc = KeycloakClient(
        base_url=os.environ["KC_BASE_INTERNAL"],
        realm=os.environ["REALM"],
        client_id=os.environ["CLIENT_ID"],
        client_secret=None,
    )

    token_data = kc.get_token_with_password(
        os.environ["USERNAME"], os.environ["PASSWORD"]
    )
    access_token = token_data.get("access_token")
    if not access_token:
        print(f"[bold red]ERROR: トークン応答に access_token がありません: {token_data}[/bold red]", file=sys.stderr)
        sys.exit(2)

    return access_token


if __name__ == "__main__":
    access_token = ""
    try:
        access_token = get_access_token()
        print(access_token)
        print("Successfully obtained token.")
    except TokenAcquisitionError as e:
        print(f"[bold red][TOKEN ERROR] {e}[/bold red]", file=sys.stderr)
        if getattr(e, "details", None):
            print(f"details: {e.details}", file=sys.stderr)
        sys.exit(5)

    try:
        print("Calling protected API...")
        response = call_protected_api(access_token)
        print("[green]API call successful![/green]")
        print(response)
    except ApiError as e:
        print(f"[bold red][API ERROR] {e}[/bold red]", file=sys.stderr)
        if getattr(e, "details", None):
            print(f"details: {e.details}", file=sys.stderr)
        sys.exit(6)
