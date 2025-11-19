# X_AutoPost - Twitter自動投稿ツール

X(Twitter) 自動ツイートツール シャドウバン対策済みバージョン

## 主な機能

- ✅ **自動ツイート投稿**: Post Delay 設定できる1時間ごとのDelay + 自動で適用される1分単位でのDelay (±30分)
- ✅ **複数スロット管理**: 最大10個のツイート内容を事前設定可能
- ✅ **OpenAI統合**: GPT-4o-miniを使用した文章追加機能 ※APIを使用します
- ✅ **メディアアップロード**: 各ツイートスロットに、画像を最大4枚まで添付可能（シンプル/チャンク自動判定）
- ✅ **GUI管理**: コマンドでの操作ではないため、ツイート内容の変更などが容易

## システム要件

- Python 3.8以上
- Twitter Developer Account（API v2アクセス）
- OpenAI APIキー（オプション、AI文章生成機能を使用する場合）

## セットアップ手順

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd X_AutoPost
```

### 2. 仮想環境の作成（推奨）

#### Windows (PowerShell)

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

#### Ubuntu / Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. 依存パッケージのインストール

#### Windows

```powershell
pip install -r requirements.txt
```

#### Ubuntu / Linux / macOS

```bash
pip install -r requirements.txt
```

### 4. Twitter API認証情報の取得

1. [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard) にアクセス
  - 以下使用
    - API Key (Consumer Key)
    - API Key Secret (Consumer Secret)
    - Access Token
    - Access Token Secret
    - Bearer Token

### 5. OpenAI APIキーの取得（オプション）

1. [OpenAI Platform](https://platform.openai.com/) にアクセス
2. API Keysセクションから新しいキーを生成

### 6. 環境変数の設定

プロジェクトルートに `.env` ファイルを作成:

```bash
# Windows
New-Item -Path .env -ItemType File

# Ubuntu/Linux/macOS
touch .env
```

`.env` ファイルに以下の内容を記述:

```env
# Twitter API v2 認証情報（必須）
BEARER_TOKEN=bearerトークン
CONSUMER_KEY=consumerキー
CONSUMER_SECRET=consumerシークレット
ACCESS_TOKEN=accessトークン
ACCESS_TOKEN_SECRET=accessトークンシークレット

# OpenAI API（オプション - AI文章生成機能を使用する場合のみ）
OPENAI_API_KEY=OpenaiApiキー
```

## 使用方法

### アプリケーションの起動

#### Windows

```powershell
python main.py
```

#### Ubuntu / Linux / macOS

```bash
python3 main.py
```

### 基本操作

1. **ツイートスロットの作成**:
   - 左側の `+` ボタンをクリックしてスロットを追加
   - `編集` ボタンでツイート内容と画像を設定

2. **投稿間隔の設定**:
   - `delay (hours)` で投稿間隔を1〜120時間で設定
   - 実際の投稿時間は±30分のランダム幅が追加されます

3. **OpenAI機能の有効化**（オプション）:
   - `OpenAI: 有効` をチェック
   - **追加位置**: ツイートの上または下にAI生成文を追加
   - **追加文字数**: AI生成文の最大文字数
   - **プロンプト**: AI生成の指示内容を入力

4. **自動投稿の開始**:
   - `自動ツイート開始` ボタンをクリック
   - ログエリアで進捗を確認

5. **テスト投稿**:
   - スロットを選択して `テストツイート` ボタンでテスト実行

6. **設定の保存**:
   - `保存` ボタンで現在の設定を保存

## プロジェクト構成

```
X_AutoPost/
├── main.py                 # メインアプリケーション（GUIとメインロジック）
├── requirements.txt        # Pythonパッケージ依存関係
├── .env                    # 環境変数（認証情報）
├── .gitignore             # Git除外設定
├── README.md              # このファイル
├── data/
│   └── config.json        # アプリ設定（自動生成）
└── util/
    ├── auth.py            # Twitter API認証
    ├── config.py          # 設定ファイル管理
    ├── openai_helper.py   # OpenAI API統合
    ├── post_v2.py         # ツイート投稿とメディアアップロード（ファイル名ランダム化対応）
    ├── search.py          # Twitter検索機能
    └── ui.py              # GUIウィジェット（EditPopup等）
```

## 依存パッケージ

- `tweepy` - Twitter API v2 クライアント
- `python-dotenv` - 環境変数管理
- `requests` - HTTPリクエスト
- `requests-oauthlib` - OAuth 1.0a認証
- `openai` - OpenAI API公式クライアント

## OpenAI機能の詳細

### 使用モデル
- **gpt-4o-mini**: GPT-4oの70%コスト削減版、高速で効率的

### プロンプト例

**ツイートの補足説明を追加**:
```
このツイートに関連する豆知識やトリビアを50文字程度で追加してください。
```

**ハッシュタグの提案**:
```
このツイートに適したハッシュタグを3つ提案してください。
```

**感情的な表現を追加**:
```
このツイートをより親しみやすく、感情的な表現にリライトしてください。
```

## トラブルシューティング (仮: 開発時に起きた事象まとめ)

### Twitter API認証エラー

**エラー**: `401 Unauthorized`
- `.env` の認証情報が正しいか確認
- Twitter Developer Portalでアプリのアクセス権限を確認

**エラー**: `429 Too Many Requests`
- APIレート制限に達しています
- 15分待ってから再試行してください

### OpenAI API エラー

**エラー**: `openai.AuthenticationError`
- `OPENAI_API_KEY` が正しく設定されているか確認
- APIキーの有効期限を確認

**エラー**: プロンプトが空
- プロンプト欄にテキストを入力してください
- OpenAI機能を無効にするか、プロンプトを設定してください

### メディアアップロードエラー

**エラー**: `413 Payload Too Large`
- 画像サイズは5MB以下を推奨
- チャンクアップロードは5MB超の画像に自動適用されます

### GUI起動エラー（Ubuntu/Linux）

**エラー**: `_tkinter.TclError: no display name`

```bash
# X11 Display設定
export DISPLAY=:0

# またはXvfbを使用（ヘッドレス環境）
sudo apt-get install xvfb
xvfb-run python3 main.py
```

