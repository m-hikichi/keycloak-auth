# Keycloak 手順書（Realm／Client／User 作成）

## 1. 前提条件
* Keycloak が `http://localhost:8080` で稼働している
* 管理者アカウントで **Admin Console** にログインできる

---

## 2. Realm の作成

### ■ なぜ必要？

**Realm（レルム）** は「独立した認証のグループ（テナント）」です。  
1つの Keycloak サーバーに複数の Realm を作成でき、それぞれ別々のユーザーやクライアントを管理できます。

例えば「開発用」「本番用」を分けて運用することも可能です。

### ■ 手順
1. 左メニューの **Manage realms** → **Create realm**

2. **Name** に `test-realm` と入力

3. **Create** を押下

> 今後の手順では、この Realm 名を test-realm として説明します。

---

## 3. Client の作成

### ■ なぜ必要？

**Client（クライアント）** は「Keycloak にログイン認証を依頼するアプリケーション」です。
WebアプリやバックエンドAPIなど、Keycloak を使いたいシステムごとに Client を作成します。

ここではテスト用クライアントを作成し、トークンを取得できるようにします。

### ■ 手順
1. 左メニューの **Clients** → **Create client**

2. 入力項目
   * **Client type**: `OpenID Connect`  
    → 一般的な認証規格（OIDC）を使用する
   * **Client ID**: 例 `test-client`
    → アプリを識別するためのID（接続時に利用）
   * **Name**: 任意（表示名）

3. **Next**

4. **Capability config** の設定
   * **Client authentication**: **On**
     → クライアント自身が「秘密鍵（secret）」で認証する設定
   * **Authorization**: **On**
     → 認可機能を有効化（誰がどのリソースにアクセスできるか）
   * **Standard flow**: **On**
     → Webアプリのログインで使われる「認可コードフロー」を有効化
   * **Direct access grants**: 任意（パスワード認証を使う場合のみ On）
     → ユーザー名＋パスワードを直接送ってトークンを取得する方式（テスト用）

5. **Next** → **Save**

6. 作成後、**Credentials**タブを開き、**Client secret** を控える

> この設定で `grant_type=client_credentials` を使ってトークンを取得できるようになります。

---

## 4. User の作成とパスワード設定

### ■ なぜ必要？

**User（ユーザー）** は実際にログインする人（あるいはサービスアカウント）です。  
Keycloak ではユーザーを登録し、パスワードを設定して利用します。

今回は「メール認証なし」でシンプルに作成します。

### ■ 手順
1. 左メニューの **Users** → **Create new user**

2. 入力項目
   * **Username**: 例 `user1`
   * **Email**: 任意（空でも可）
   * **First / Last name**: 任意
   * **Email verified**: **On**
     → メール認証をスキップするため、管理者が「確認済み」とする
   * **Required user actions**: 空欄
     → 「Verify Email」などを強制しない
   * **Create**

3. 作成後、**Credentials** タブ → **Set password**
   * 新しいパスワードを入力
   * **Temporary**: **Off**（初回変更を求めない）
   * **Save**

---

## 5. 認証フローの必須アクションを無効化

### ■ なぜ必要？

ユーザーを作成しても、Keycloak のデフォルト設定で「追加アクション」が有効になっている場合があります。  
例: Verify Email（メール確認）や Update Profile（プロフィール更新）。

これが残っていると、ログイン時に「Account is not fully set up」と表示されることがあります。


### ■ 手順

1. 左メニューの **Authentication** → **Required actions**

2. 以下を Disabled に変更
   * **Verify Email**
   * **Update Profile**
   * **Verify Profile**

> これで「メール送信なし」でログインできるようになります。

---

## 6. 動作確認：トークン取得

### ■ なぜ必要？

作成した Client / User が正しく設定されているか確認します。
トークンが取得できれば Keycloak の認証が成功しています。

### ■ エンドポイント

```
http://localhost:8080/realms/test-realm/protocol/openid-connect/token
```

### 6-1. Client Credentials Flow（アプリ認証）

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

#### Thunder Client（VS Code）

* **Method**: POST
* **URL**: 上記トークンURL
* **Headers**:
  * `Content-Type`: `application/x-www-form-urlencoded`
* **Body / Form-encode**:
  * `grant_type`: `client_credentials`
  * `client_id`: `test-client`
  * `client_secret`: `<控えたシークレット>`


### 6-2. Resource Owner Password Credentials Flow（ユーザー認証）

ユーザー名とパスワードで直接トークンを取得する方式です。  
※ テスト用途のみ。本番では推奨されません。

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
