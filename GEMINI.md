# GEMINI.md

## 🎯 目的・概要

このドキュメントは、Python + AWS を対象に、`gemini-cli` を活用して Issue → PR 自動化、TDD（pytest）、Terraform による AWS デプロイを行う開発フローの手順書です。

### 🛠 構成

- Issue 作成 → ブランチ＆PR 自動生成（gemini-cli + GitHub Actions + gh）
- pytest によるテスト駆動開発（TDD）
- Terraform＋GitHub Actions による AWS インフラデプロイ（OIDC 認証付き CI/CD）

---

## 1️⃣ 前提条件

- **gemini-cli のインストールと認証**  
  ```bash
  npm install -g @google/gemini-cli
  gemini login
  ```
  - GitHub リポジトリに以下のシークレットを設定
    - `GEMINI_API_KEY`: Gemini APIキー
    - `AWS_ROLE_ARN`: OIDC認証用のIAMロールARN
    - `SLACK_WEBHOOK_URL`: Slack通知用のWebhook URL

- **Python 3.12 開発環境 (venv)**
  ```bash
  python3.12 -m venv .venv
  source .venv/bin/activate
  ```

- AWS CLI, AWS 設定済み

- GitHub CLI (`gh`)

- Terraform 及び関連バックエンド設定（S3 + DynamoDB）

---

## 2️⃣ Issue → PR 自動化

- ワークフロー: `.github/workflows/auto-pr.yml`

```yaml
name: "Issue → ブランチ＆PR 自動化"

on:
  issues:
    types: [opened]

jobs:
  auto-pr:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: google-gemini/gemini-cli-action@v1
        with:
          api_key: ${{ secrets.GEMINI_API_KEY }}
          args: |
            /background Issue内容を解析し、新規 Python モジュール + pytest テストを生成
      - name: Create branch & PR
        run: |
          gh auth login --with-token < <(echo ${{ secrets.GITHUB_TOKEN }})
          gh pr create \
            --title "feat: ${{ github.event.issue.title }}" \
            --body "自動生成 PR\n\nIssue: #${{ github.event.issue.number }}" \
            --base main
```

- `gemini-cli` が Issue 内容から初期コードとテストを生成、`gh pr create` により PR を自動生成
- 必要に応じてラベル付与やレビュー担当者割り当ても可能

---

## 3️⃣ pytest を使った TDD 導入

- pytest の導入:

  ```bash
  pip install pytest
  pytest --init
  ```

- PR 作成時に `gemini generate-tests` を追加しテスト案をコメント挿入
- PR テンプレートに「pytest テスト追加」チェックリストを設置

---

## 4️⃣ Terraform による AWS デプロイ

- ディレクトリ構成（例）:

  ```
  terraform/
  ├─ main.tf            # provider, backend 設定
  └─ modules/…          # 必要なモジュール
  ```

- ⭐ リモートステート管理例:

  ```hcl
  terraform {
    backend "s3" {
      bucket         = "gemini-dev-workslow-data-platform"
      key            = "terraform.tfstate"
      region         = "ap-northeast-1"
      dynamodb_table = "terraform-lock"
      encrypt        = true
    }
  }
  ```

- S3 + DynamoDB により安全な状態管理とロックを実現

- 🔐 OIDC 認証設定  
  GitHub Actions → AWS OIDC プロバイダー作成、IAM ロール設定（`id-token: write` 権限必須）

---

## 5️⃣ GitHub Actions ワークフロー

### PR作成時: Terraform Plan（`.github/workflows/ci-terraform.yml`）

```yaml
on:
  pull_request:
    paths:
      - 'terraform/**'

permissions:
  id-token: write
  contents: read
  pull-requests: write

jobs:
  terraform-plan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: AWS 認証（OIDC）
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ap-northeast-1
      - uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: "latest"
      - run: |
          terraform fmt -check
          terraform init
          terraform plan -out=tfplan
      - name: プラン結果出力
        run: terraform show -no-color tfplan
```

### main マージ後: Terraform Apply（`.github/workflows/deploy-terraform.yml`）

```yaml
on:
  push:
    branches: [main]
    paths:
      - 'terraform/**'

permissions:
  contents: read
  id-token: write

jobs:
  terraform-apply:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: AWS 認証（OIDC）
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: ${{ secrets.AWS_ROLE_ARN }}
          aws-region: ap-northeast-1
      - uses: hashicorp/setup-terraform@v2
        with:
          terraform_version: "latest"
      - run: |
          terraform init
          terraform apply -auto-approve
      - name: Slack 通知
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## 6️⃣ ワークフロー全体フロー

| フロー名                | イベント                        | 実行内容概要                                      |
|-------------------------|---------------------------------|---------------------------------------------------|
| auto-pr.yml             | issues.opened                   | Issue → ブランチ＆PR 自動生成                      |
| ci-terraform.yml        | PR 作成時（Terraform 配下変更） | terraform fmt/check + plan → PR コメント出力       |
| deploy-terraform.yml    | main に Terraform 変更 Push     | Apply → Slack 通知                                 |

---

## ✅ ベストプラクティス

- OIDC + IAM ロールで静的鍵不使用＆セキュア認証
- Terraform とアプリコードは分離されたワークフローで運用
- Terraform Plan / pytest テスト生成結果は必ず PR に可視化
- リソース変更にはロールバック戦略（例: Git Revert → 再 Apply）

---

## 📌 今後の拡張案

- Lint／Static Analysis／セキュリティスキャン
- Terraform モジュール化とレビューガイドライン整備
- Atlantis や HCP Terraform による高度な PR 処理
- ラベル・レビュアー自動アサインなどの開発支援機能追加

---

## 7️⃣ 用語・関連リンク

- Gemini CLI：Open‑source AI agent for code & automation  
  [GitHub](https://github.com/google/gemini-cli)  
  [codelabs.developers.google.com](https://codelabs.developers.google.com/)  
- GitHub Actions + OIDC 認証による AWS 操作
- Terraform on GitHub Actions ワーカー例

