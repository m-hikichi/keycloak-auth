import os
from typing import Dict, Any

import jwt
from jwt import PyJWKClient, InvalidTokenError
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# ====== 設定（環境変数から） ======
KC_BASE = os.getenv("KC_BASE", "http://keycloak:8080").rstrip("/")
REALM = os.getenv("REALM", "test-realm")
# 監査強化したければ AUDIENCE（= クライアントID）を入れて検証する（今回は最小のため未使用）
# EXPECTED_AUD = os.getenv("AUDIENCE")  # 例: "test-client"

ISSUER = f"{KC_BASE}/realms/{REALM}"
JWKS_URL = f"{ISSUER}/protocol/openid-connect/certs"

# ====== 準備：JWKS クライアント（PyJWT が内部でキャッシュしてくれます） ======
_jwks_client = PyJWKClient(JWKS_URL)

# ====== FastAPI アプリ ======
app = FastAPI(title="Minimal Keycloak-protected API")

# “Authorization: Bearer <token>” を受け取るための簡易セキュリティスキーム
bearer_scheme = HTTPBearer(auto_error=True)

def verify_access_token(
    creds: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Dict[str, Any]:
    """
    Authorization ヘッダの Bearer トークンを受け取り、
    Keycloak の公開鍵(JWKS)で署名検証してデコードする最小実装。
    """
    token = creds.credentials
    try:
        signing_key = _jwks_client.get_signing_key_from_jwt(token).key

        # 最小：署名と iss（発行者）だけ検証（aud 検証はオフ）
        # 監査を強めたい場合は options を外し、aud=EXPECTED_AUD を指定して下さい。
        payload = jwt.decode(
            token,
            signing_key,
            algorithms=["RS256"],
            issuer=ISSUER,
            options={"verify_aud": False},  # 最小化のため audience 検証は無効
            # audience=EXPECTED_AUD,        # 監査強化したい場合はこちらを使う
        )
        return payload

    except InvalidTokenError as e:
        # 署名不正／期限切れなど
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {e}",
        )

# ====== ルート ======

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/protected")
def protected(claims: Dict[str, Any] = Depends(verify_access_token)):
    """
    Keycloak アクセストークンが有効なら通る保護 API の最小例。
    代表的なクレームを返すだけ。
    """
    # よく使うクレーム例：
    #  - sub: 一意ID
    #  - preferred_username: ユーザー名
    #  - scope: アクセストークンのスコープ
    #  - realm_access / resource_access: ロール情報
    return {
        "message": "You are authenticated 🎉",
        "sub": claims.get("sub"),
        "preferred_username": claims.get("preferred_username"),
        "scope": claims.get("scope"),
        "realm_roles": (claims.get("realm_access") or {}).get("roles"),
    }
