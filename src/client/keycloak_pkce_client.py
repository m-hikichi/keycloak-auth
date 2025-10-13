import base64
import hashlib
import os
import secrets
import time
from typing import Any, Dict
from urllib.parse import urlencode

import requests
from flask import Flask, abort, jsonify, redirect, request, session
from jwt import decode as jwt_decode
from api_client import ApiClient, ApiError

# ===== 設定 =====
KC_BASE = os.environ["KC_BASE"]
REALM = os.environ["REALM"]
CLIENT_ID = os.environ["CLIENT_ID"]
REDIRECT_URI = os.environ["REDIRECT_URI"]
SESSION_SECRET = "dev-only-change-me"
SCOPES = "openid profile email"

AUTH_URL = f"{KC_BASE}/realms/{REALM}/protocol/openid-connect/auth"
TOKEN_URL = f"{KC_BASE}/realms/{REALM}/protocol/openid-connect/token"

app = Flask(__name__)
app.config.update(SECRET_KEY=SESSION_SECRET)

api_client = ApiClient()

# ===== ユーティリティ =====
def b64url_no_pad(b: bytes) -> str:
    """Base64URL エンコード（末尾 '=' を削除）。"""
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def create_pkce_pair() -> Dict[str, str]:
    """PKCE 用 verifier/challenge を生成。"""
    verifier = b64url_no_pad(secrets.token_bytes(32))
    challenge = b64url_no_pad(hashlib.sha256(verifier.encode()).digest())
    return {"verifier": verifier, "challenge": challenge}


def decode_jwt_unverified(token: str) -> Dict[str, Any]:
    """署名検証なしで JWT のペイロードをデコード（学習・便宜用）。"""
    try:
        return jwt_decode(token, options={"verify_signature": False, "verify_exp": False})
    except Exception:
        return {}


def is_access_token_expiring_soon(access_token: str, leeway_seconds: int = 30) -> bool:
    """
    access_token の exp を読み、現在時刻 + leeway を過ぎていたら True。
    exp が取れない/不正なら「安全側」で True を返す。
    """
    claims = decode_jwt_unverified(access_token)
    exp = claims.get("exp")
    if not isinstance(exp, (int, float)):
        return True
    now = int(time.time())
    return exp <= now + leeway_seconds


def refresh_tokens() -> Dict[str, Any]:
    """
    セッション内の refresh_token を使ってトークン更新。
    成功すればセッションの tokens を更新して返す。
    失敗時は 401 を投げる（ログアウト扱いにしたい場合はセッションをクリアしてもよい）。
    """
    tokens = session.get("tokens") or {}
    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        abort(401, "no refresh_token in session")

    data = {
        "grant_type": "refresh_token",
        "client_id": CLIENT_ID,
        "refresh_token": refresh_token,
    }
    try:
        tr = requests.post(TOKEN_URL, data=data, timeout=10)
    except requests.RequestException as e:
        abort(502, f"token refresh network error: {e}")

    if tr.status_code != 200:
        # 典型: invalid_grant（期限切れ/取り消し）
        abort(401, f"token refresh failed: {tr.text}")

    new_tokens = tr.json()
    # 必要なフィールドのみを上書き（id_token は返らないこともある）
    session["tokens"] = {
        "access_token": new_tokens.get("access_token"),
        "refresh_token": new_tokens.get("refresh_token", refresh_token),
        "id_token": new_tokens.get("id_token", tokens.get("id_token")),
    }
    return session["tokens"]


# ===== ルーティング =====
@app.route("/")
def root():
    user = session.get("user")
    if user:
        tokens = session.get("tokens")
        access_token = tokens.get("access_token")

        # アクセストークンの期限が近ければ自動更新
        if access_token and is_access_token_expiring_soon(access_token, leeway_seconds=30):
            try:
                tokens = refresh_tokens()
            except Exception as e:
                # リフレッシュ失敗時は未認証扱い（必要なら session.clear() してもよい）
                return jsonify({"message": "token refresh failed", "error": str(e)}), 401

        tokens = session.get("tokens", {})
        return jsonify(
            {
                "user": user,
                "tokens": tokens,
            }
        )

    # PKCE 開始
    state = secrets.token_urlsafe(16)
    nonce = secrets.token_urlsafe(16)
    pkce = create_pkce_pair()

    session["state"] = state
    session["nonce"] = nonce
    session["code_verifier"] = pkce["verifier"]

    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPES,
        "state": state,
        "nonce": nonce,
        "code_challenge": pkce["challenge"],
        "code_challenge_method": "S256",
    }
    return redirect(f"{AUTH_URL}?{urlencode(params)}")


@app.route("/callback")
def callback():
    # Keycloak からエラーが返った場合のハンドリング
    err = request.args.get("error")
    if err:
        abort(400, f"auth error: {err}")

    # 認可サーバから返ってきた code/state を取り出し、基本チェック
    code = request.args.get("code")
    state = request.args.get("state")
    if not code or not state:
        abort(400, "missing code/state")

    # CSRF攻撃を防ぐチェック
    if state != session.get("state"):
        abort(400, "invalid state")

    code_verifier = session.get("code_verifier")
    if not code_verifier:
        abort(400, "missing code_verifier")

    # 認可コードをトークンへ交換（PKCE: code_verifier を送る）
    data = {
        "grant_type": "authorization_code",
        "client_id": CLIENT_ID,
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "code_verifier": code_verifier,
    }
    tr = requests.post(TOKEN_URL, data=data, timeout=10)
    if tr.status_code != 200:
        abort(400, f"token exchange failed: {tr.text}")
    tokens = tr.json()

    # 学習用: 署名検証は省略。ID Token のペイロードを眺めたい場合のみデコード（非検証）
    id_token = tokens.get("id_token")
    claims = {}
    if id_token:
        try:
            claims = jwt_decode(id_token, options={"verify_signature": False})
        except Exception:
            claims = {"note": "failed to decode id_token without verification"}

    # セッションへユーザ情報を保存
    session.clear()
    session["user"] = {
        "sub": claims.get("sub"),
        "preferred_username": claims.get("preferred_username"),
        "email": claims.get("email"),
    }
    session["tokens"] = {
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        "id_token": tokens.get("id_token"),
    }

    return redirect("/")


@app.route("/authorize")
def authorize():
    user = session.get("user")
    if user:
        tokens = session.get("tokens")
        access_token = tokens.get("access_token")

        try:
            response = api_client.call_api(path="/authorize", access_token=access_token)
            print("[green]API call successful![/green]")
            return response
        except ApiError as e:
            return jsonify({"error": "API call failed", "details": e.details}), e.status_code or 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
