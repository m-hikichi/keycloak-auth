import os

import requests
from rich import print


class TokenAcquisitionError(Exception):
    """トークン取得に失敗した場合に投げられるカスタム例外。"""

    def __init__(self, message, details=None):
        super().__init__(message)
        self.details = details


class KeycloakClient:
    """
    Keycloak とやり取りしてアクセストークンやリフレッシュトークンを取得・更新するクライアント。
    """

    def __init__(self, base_url, realm, client_id, client_secret=None):
        """
        Keycloak クライアントを初期化する。

        Args:
            base_url (str): Keycloak サーバのベースURL
            realm (str): Keycloak の Realm 名
            client_id (str): クライアント ID
            client_secret (str, optional): クライアントシークレット（Confidential Client の場合は必須）
        """
        self.base_url = base_url.rstrip("/")
        self.realm = realm
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = (
            f"{self.base_url}/realms/{self.realm}/protocol/openid-connect/token"
        )

    def _post_token(self, payload):
        """
        トークンエンドポイントに対してリクエストを送信する内部ヘルパー関数。

        Args:
            payload (dict): リクエストパラメータ

        Returns:
            dict: Keycloak から返却された JSON レスポンス

        Raises:
            TokenAcquisitionError: 通信エラーや認証エラーが発生した場合
        """
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
                f"トークン取得に失敗しました: {e.response.status_code}",
                details=error_details,
            ) from e
        except requests.RequestException as e:
            raise TokenAcquisitionError("トークンリクエスト中にネットワークエラーが発生しました", details=str(e)) from e

    def get_token_with_password(self, username, password):
        """
        Resource Owner Password Credentials (ROPC) フローでアクセストークンを取得する。

        Args:
            username (str): ユーザー名
            password (str): パスワード

        Returns:
            dict: トークンレスポンス（access_token, refresh_token などを含む）
        """
        payload = {
            "grant_type": "password",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "username": username,
            "password": password,
        }

        return self._post_token(payload)

    def get_token_with_refresh_token(self, refresh_token):
        """
        リフレッシュトークンを使ってアクセストークンを更新する。

        Args:
            refresh_token (str): 有効なリフレッシュトークン

        Returns:
            dict: 新しいトークンレスポンス
        """
        payload = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
        }

        return self._post_token(payload)


if __name__ == "__main__":
    # --- 使用例 ---
    client = KeycloakClient(
        base_url=os.environ["KC_BASE_INTERNAL"],
        realm=os.environ["REALM"],
        client_id=os.environ["CLIENT_ID"],
        # client_secret=os.environ["CLIENT_SECRET"],
    )

    try:
        # 1) ユーザー名とパスワードでトークン取得
        token_data = client.get_token_with_password(
            os.environ["USERNAME"], os.environ["PASSWORD"]
        )
        print("[bold green]アクセストークンを取得しました:[/]")
        print(token_data)

        # 2) リフレッシュトークンで更新
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            print("[yellow]レスポンスに refresh_token が含まれていません。"
                  "クライアント/Realm 側でリフレッシュトークン発行を許可してください。[/]")
        else:
            refreshed = client.get_token_with_refresh_token(refresh_token)
            print("[bold green]リフレッシュトークンで更新しました:[/]")
            print(refreshed)
    
    except TokenAcquisitionError as e:
        print(f"[red]エラー:[/] {e}")
        if e.details:
            print(f"詳細: {e.details}")
