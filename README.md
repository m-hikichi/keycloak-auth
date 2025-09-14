# Keycloak 手順書（Realm／Client／User 作成）

## 1. 前提条件
* Keycloak が `http://localhost:8080` で稼働している
* 管理者アカウントで **Admin Console** にログインできる
* （任意）curl または VS Code の Thunder Client が使える

---

## 2. Realm の作成

**Realm（レルム）** は、ユーザーやクライアント、認証設定をまとめる独立した認証のグループ（テナント）です。1台の Keycloak に複数作れます（例：開発／本番の分離）。

#### ■ 手順
1. 左メニューの **Manage realms** → **Create realm**

2. **Name** に `test-realm` と入力

3. **Create** を押下

> 今後の手順では、この Realm 名を `test-realm` として説明します。

---

## 3. Client の作成

**Client（クライアント）** は「Keycloak にログインやトークン発行を依頼するアプリ」です。  

### ROPC用クライアント

ここでは、**ユーザー名＋パスワードで直接トークンを取得する方式（ROPC: Resource Owner Password Credentials）** を試せるように設定します。  
⚠️ ROPC はセキュリティ上の理由から本番では非推奨です。テスト用途に限定してください。

#### ■ 手順
1. 左メニュー **Clients** → **Create client**

2. 入力項目
   * **Client type**: `OpenID Connect`
   * **Client ID**: 例 `test-client`
   * **Name**: 任意（表示名）

3. **Next**

4. **Capability config** の設定
   * **Client authentication**:
     * サーバー側で動くプログラム（秘密を隠せる）なら → **On**（= Confidential クライアント）
     * ユーザーのスマホやブラウザで直接動くアプリ（秘密を隠せない）なら → **Off**（Public クライアント）
   * **Service accounts**（roles）:
     * Keycloak の Client をユーザーとして扱いたい場合 → **On** 
     * Keycloak の 通常のユーザー（username / password）でログインする場合 → **Off** でOK
   * **Direct access grants**: **On**  
     ↳ **ROPC を使うために必須**
   * **Authorization**: **Off**（今回は不要：UMA/リソース権限管理を使わない）
   * **Standard flow**: **Off**（今回は未使用。将来ブラウザログインを試すときに有効化）

5. **Next** → **Save**

6. 作成後、**Credentials**タブを開き、**Client secret** を控える（Confidential クライアントの場合のみ）

### Auth Code + PKCE用クライアント

ここでは、**ブラウザやネイティブアプリで広く使われる「認可コード + PKCE」方式（Auth Code with PKCE）** を試せるように設定します。  
🔒 PKCE は **パスワードを直接送らない安全な方式** であり、ROPC より推奨される標準的な方法です。

#### ■ 手順

1. 左メニュー **Clients** → **Create client**

2. 入力項目
   * **Client type**: `OpenID Connect`
   * **Client ID**: 例 `test-client`
   * **Name**: 任意（表示名）

3. **Next**

4. **Capability config** の設定
   * **Client authentication**: **Off**
   * **Service accounts**（roles）: **Off**  
     ↳ PKCE では不要。Client を「ユーザー」として使わない。
   * **Direct access grants**: **Off**  
     ↳ ROPC 用の設定。PKCE では不要。
   * **Authorization**: **Off**（今回は不要：UMA/リソース権限管理を使わない）
   * **Standard flow**: **On**  
     ↳ PKCE は「Auth Code Flow」の拡張なので必須
   * Proof Key for Code Exchange (PKCE)
     * PKCE method: `S256`

5. **Next**

6. **設定追加**
   * **Valid redirect URIs** にアプリのコールバックURLを設定
     （例: http://localhost:5000/callback）
   * **Web origins** に必要なオリジンを設定
     （例: http://localhost:5000）

7. **Save**

#### ポイント／注意

* **Standard flow（Auth Code）を使う場合**は、**Valid redirect URIs / Web origins** を必ず設定してください（未設定だとエラーになります）。

---

## 4. User の作成とパスワード設定

実際にログインする**人**です。今回はメール認証なしでシンプルに作成します。

#### ■ 手順
1. 左メニューの **Users** → **Create new user**

2. 入力項目
   * **Username**: 例 `user1`
   * **Email**: 任意（空でも可）
   * **First / Last name**: 任意
   * **Email verified**: **On**（メール確認を省略）
   * **User enabled**: **On**（通常は既定で On）
   * **Required user actions**: 空欄
   
3. **Create**

4. 作成後、**Credentials** タブ → **Set password**
   * 新しいパスワードを入力
   * **Temporary**: **Off**（初回変更を求めない）
   * **Save**

---

## 5. 認証フローの必須アクションを無効化

#### ■ なぜ必要？

ユーザーを作成しても、Keycloak のデフォルト設定で「追加アクション」が有効になっている場合があります。  
例: Verify Email（メール確認）や Update Profile（プロフィール更新）。

これが残っていると、ログイン時に「Account is not fully set up」と表示されることがあります。


#### ■ 手順

1. 左メニューの **Authentication** → **Required actions**

2. 以下を Disabled に変更
   * **Verify Email**
   * **Update Profile**
   * **Verify Profile**

> これで「メール送信なし」でログインできるようになります。

---

## 6. エンドポイント一覧

作成した Realmに対応する OIDC エンドポイントは以下です。

- **Issuer**:
`KC_BASE/realms/example-realm`

- **Authorization endpoint**:
`KC_BASE/realms/example-realm/protocol/openid-connect/auth`

- **Token endpoint**:
`KC_BASE/realms/example-realm/protocol/openid-connect/token`

- **Logout endpoint**:
`KC_BASE/realms/example-realm/protocol/openid-connect/logout`

- **UserInfo endpoint**:
`KC_BASE/realms/example-realm/protocol/openid-connect/userinfo`

- **JWKS** (公開鍵) :
`KC_BASE/realms/example-realm/protocol/openid-connect/certs`

---

## 7. 動作確認：トークン取得

作成した Client / User が正しく設定されているか確認します。
トークンが取得できれば Keycloak の認証が成功しています。

### 7-1. Client Credentials Flow（アプリ認証）

サーバー同士で通信するときに使う方式です。

#### curl

```bash
curl -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=client_credentials" \
  -d "client_id=test-client" \
  -d "client_secret=<控えたシークレット>" \
  http://localhost:8080/realms/test-realm/protocol/openid-connect/token
```

> Public Client の場合、 client_secret を省略可能です。

#### Thunder Client（VS Code）

* **Method**: POST
* **URL**: 上記トークンURL
* **Headers**:
  * `Content-Type`: `application/x-www-form-urlencoded`
* **Body / Form-encode**:
  * `grant_type`: `client_credentials`
  * `client_id`: `test-client`
  * `client_secret`: `<控えたシークレット>`

> Public Client の場合、 client_secret を省略可能です。

### 7-2. Resource Owner Password Credentials（ユーザー認証：テスト用途のみ）

ユーザー名とパスワードで直接トークンを取得する方式です。  
> 注意：ROPC はセキュリティ上の理由で本番非推奨です（OAuth 2.1 では廃止方向）。本番は **Authorization Code + PKCE** を推奨。

#### curl

```bash
curl -X POST \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=password" \
  -d "client_id=test-client" \
  -d "client_secret=<控えたシークレット>" \
  -d "username=user1" \
  -d "password=<設定したパスワード>" \
  http://localhost:8080/realms/test-realm/protocol/openid-connect/token
```

> Public Client の場合、 client_secret を省略可能です。

#### Thunder Client

* **Method**: POST
* **URL**: 上記トークンURL
* **Headers**:
  * `Content-Type`: `application/x-www-form-urlencoded`
* **Body/Form-encode**:
  * `grant_type`: `password`
  * `client_id`: `test-client`
  * `client_secret`: `<控えたシークレット>`
  * `username`: `user1`
  * `password`: `<パスワード>`

> Public Client の場合、 client_secret を省略可能です。
