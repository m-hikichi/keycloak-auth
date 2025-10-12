# Keycloak 認可（RBAC）実装手順

**/public（誰でもOK）／/protected（ログインした人だけ）／/authorize（特定権限が必要）**の3段階アクセスを、Keycloakの基本機能（認証＋ロール）だけで実現できるようにします。

---

## 全体像（まず考え方）

* **web-spa**：ブラウザでログインするための受付用クライアント（Public, PKCE）。
* **backend-api**：API側の権限（ロール）を定義するクライアント（Confidential, PKCE）。
* ロール（例：`app:guest`、`app:member`、`app:owner`）は **backend-api** に作る → ユーザーのトークンに `resource_access.backend-api.roles` として入る。
* SPA が取得するトークンを API が受け付けられるように、**Audience マッパー**で `aud` に `backend-api` を追加する。
* ユーザーのロールは **Group** で表現し、**Group にロールを付与** → ユーザーは所属するだけ。ロール変更＝所属入れ替え（ユーザー作り直し不要）。

---

## 前提

* 管理者で Keycloak Admin Console にログインできること
* 例として Realm 名は `test-realm` を使用

---

## 手順A：クライアントを2つ作る（どちらもPKCE）

### 1) web-spa（受付用・Public）

1. **左メニュー → Clients → Create client**
2. **Client ID**：`web-spa`
3. **Client authentication**：**OFF**（＝Public）
4. 作成後、**Settings** タブで次を設定：

   * **Standard Flow Enabled**：**ON**
   * **Code Challenge Method**：**S256**
   * **Valid Redirect URIs**：例 `http://localhost:5000/callback`
   * **Web origins**：例 `http://localhost:5000`
5. **Save**

### 2) backend-api（API用・Confidential）

1. **左メニュー → Clients → Create**
2. **Client ID**：`backend-api`
3. **Client authentication**：**ON**（＝Confidential）
4. 作成後、**Settings** タブで次を設定：

   * **Standard Flow Enabled**：**ON**（管理・検証用途でブラウザログイン可）
   * **Code Challenge Method**：**S256**
   * **Valid Redirect URIs**：必要に応じて（テスト用のコールバックでもOK）
5. **Save**

> 補足：`web-spa` は **Public**、`backend-api` は **Confidential** にするのが基本。性質の違い（ブラウザにシークレットを置けない／API側で権限を持つ）を分けるためです。

---

## 手順B：Audience マッパーを追加（web-spa → backend-api）

**目的**：SPAで取得したアクセストークンの `aud`（宛先）に `backend-api` を含め、APIが「自分宛のトークン」と判断できるようにする。

1. **左メニュー → Clients → web-spa → Client scopes → web-spa-dedicated**
2. **Configure a new mapper → Audience** を選択
3. フィールド設定：

   * **Included Client Audience**：`backend-api`
   * **Add to access token**：**ON**
4. **Save**

> これで `/protected` のようなAPIの受け口で `aud` が `backend-api` に合致するか簡単に判定できます。

---

## 手順C：ロールを作る（backend-api 側）

**目的**：`/authorize` に入れる人だけが持つ「特別ハンコ」を用意する。

1. **左メニュー → Clients → backend-api → Roles → Create role**
2. **Role name**：`app:owner`（自由に命名可）
3. **Save**

> 必要に応じて `app:guest` のような汎用ロールを作って `/protected` 用に使ってもOKです。

---

## 手順D：Group を作り、Group に“ロール”を付与

**目的**：役職ごとに付与する権限をまとめて管理する（ユーザーは所属するだけ）。

1. **左メニュー → Groups → Create group**

   * `Guest` / `Member` / `Owner` など
2. 各グループを開き、**Role mapping** タブへ
3. 右側の **Assign role** のプルダウンで **Client roles*** を選択
4. 表示されたロール一覧から付けたい**ロール（例：`app:guest`）を選択 → Add**

   * 例：

     * Guest  → （なし or `app:guest`）
     * Member → `app:guest` + **`app:member`**
     * Owner  → `app:guest` + `app:member` + **`app:owner`**

> 重要：**グループに付与するのは“クライアント（backend-api）ではなく、クライアントに属する“ロール”**です。

---

## 手順E：ユーザーをグループに所属させる

1. **左メニュー → Users →（対象ユーザー） → Groups**
2. **Join Group** で `Guest／Member／Owner` のいずれかに所属させる
3. 役職変更があったら、**所属グループを入れ替えるだけ**（ユーザー作り直し不要）

---

## 手順F：動作確認（最低限）

1. ブラウザで **web-spa**（Public）に **PKCE（S256）** でログインして **access_token** を取得
2. 取得したトークンをデコードして確認：

   * `aud` に **`backend-api`** を含むこと（Audience マッパーが効いている）
   * `resource_access.backend-api.roles` に **`app:owner`** が入るユーザー／入らないユーザーを用意
3. API 呼び出し（例）：

   * `GET /public` → 無条件で200
   * `GET /protected`（Authorization: Bearer <token>）→ ログイン済みなら200、未ログインなら401
   * `GET /authorize`（Authorization: Bearer <token>）→ `api:authorized` があれば200、なければ403

> 実際の呼び出しは Thunder Client / curl / Postman などでOK。トークンの署名検証・`iss/aud/exp` の確認はAPI側実装で必須です。

---

## よくあるハマり

* **/protected が 401**：`aud` に `backend-api` が入っていない → Audience マッパーを web-spa に追加しているか？
* **/authorize が 403**：`app:owner` がトークンにない → ユーザーが `Owner` グループ（など権限付与済）か？ グループへ付与したのは“ロール”になっているか？
* **Authorization（AuthZ Services）トグルが押せない**：クライアントが Public のまま → これは今回は**不要**（RBACのみで十分）。

---

## 用語ミニ辞典

* **Public / Confidential**：ブラウザに秘密鍵を置けない (=Public)。サーバ側クライアントはシークレットを持てる (=Confidential)。
* **PKCE**：ブラウザからの安全な認可コード受け取りの仕組み（`S256` を使用）。
* **aud（Audience）**：トークンの“宛先”。API は `aud` に自分（`backend-api`）が入っているトークンだけ受け付けるのが安全。
* **Clientロール**：特定クライアント（ここでは `backend-api`）に属する権限。トークンでは `resource_access.<client>.roles` に出る。
* **Group**：ユーザーをまとめる箱。**グループにロールを付ける**→ユーザーは所属するだけ。
