# Streamlit AI OCR・問診票アプリ

## セットアップ手順

1. 必要なPythonパッケージをインストール

```
pip install -r requirements.txt
```

2. `.streamlit/secrets.toml` を作成し、APIキーやエンドポイントを記載

例:
```toml
openai_api_key = "YOUR_OPENAI_API_KEY"
huggingface_token = "YOUR_HF_TOKEN"
claude_api_key = "YOUR_CLAUDE_API_KEY"
gemini_api_key = "YOUR_GEMINI_API_KEY"
azure_vision_endpoint = "YOUR_AZURE_ENDPOINT"
azure_vision_key = "YOUR_AZURE_KEY"
```

※ 機密情報は絶対にGitHubにpushしないでください。 `.gitignore` で除外してください。

3. `Settings.json` でプロンプトテンプレートを管理

例:
```json
{
  "prompts": {
    "PL": "PL用プロンプト例...",
    "BS": "BS用プロンプト例..."
  }
}
```

4. Streamlitアプリを起動

```
streamlit run app.py
```
または `pages/02_読み取り機能.py` などを直接指定

## デプロイ（Streamlit Cloud）
- GitHubにpush後、Streamlit Cloudでリポジトリを指定しデプロイ
- secretsはStreamlit Cloudの「Secrets」設定画面で入力
- `requirements.txt` と `Settings.json` もリポジトリに含めてください

## 注意
- `db/` ディレクトリやサンプルDBファイルが必要な場合は同梱してください
- secretsや個人情報は絶対に公開リポジトリに含めないでください 