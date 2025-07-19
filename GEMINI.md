# GEMINI.md

## 

このドキュメントは、Python + AWS 環境を対象に、`gemini-cli` を活用して Issue から PR 作成の自動化、TDD（pytest）、Terraform による AWS デプロイまでを含む、モダンな開発フローを構築するための手順書です。

### 

- **Issue → PR 自動化**: Issue 作成をトリガーに、`gemini-cli` がコード生成やファイル修正を行い、PR を自動作成します。
- **TDD (テスト駆動開発)**: `pytest` を利用したテスト駆動開発を `gemini-cli` がサポートします。
- **IaC (Infrastructure as Code)**: `Terraform` と GitHub Actions を連携させ、AWS インフラの CI/CD を実現します。

---

## 1

- **gemini-cli のインストールと認証**
  ```bash
  npm install -g @google/gemini-cli
  gemini login
  ```
  - GitHub リポジトリに以下のシークレットを設定してください。
    - `GEMINI_API_KEY`: Gemini API キー
    - `AWS_ROLE_ARN`: OIDC 認証用の IAM ロール ARN
    - `SLACK_WEBHOOK_URL`: Slack 通知用の Webhook URL

- **Python 3.12 開発環境 (venv)**
  ```bash
  python3.12 -m venv .venv
  source .venv/bin/activate
  ```

- **各種 CLI ツールの設定**
  - AWS CLI: AWS アカウント設定済み
  - GitHub CLI (`gh`): GitHub 認証済み
  - Terraform: インストール済み（バックエンド設定含む）

---

## 2

Issue が作成された際に、内容に応じた処理を `gemini-cli` が実行し、PR を自動生成するワークフローです。

- **ワークフロー**: `.github/workflows/auto-pr.yml`

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
            /background Issueの内容を分析し、タスクを達成するためのコード生成、ファイル編集、または計画立案を行ってください。
            - 新機能やバグ修正の場合: Pythonモジュールとpytestテストを生成・修正します。
            - ドキュメント更新の場合: 対象のMarkdownファイルを修正します。
            - 複雑なタスクの場合: 実行計画を提案します。
      - name: Create branch & PR
        run: |
          gh auth login --with-token < <(echo ${{ secrets.GITHUB_TOKEN }})
          gh pr create \
            --title "feat: ${{ github.event.issue.title }}" \
            --body "自動生成 PRです。Issue を解決するための変更が含まれています。 \n\nFixes #${{ github.event.issue.number }}" \
            --base main
```

- **ポイント**:
  - `gemini-cli` への指示 (`args`) を柔軟にすることで、コード生成だけでなく、ドキュメント修正や既存コードのリファクタリングなど、様々な Issue に対応できます。
  - `gh pr create` で Issue 番号を紐付けることで、PR がマージされると自動的に Issue が閉じられます。

---

## 3

`gemini-cli` は CI/CD だけでなく、ローカル開発の強力なサポーターにもなります。

- **コード生成**:
  ```bash
  # プロンプトから FastAPI のエンドポイントを生成
  gemini -p "ユーザー情報を管理するための FastAPI エンドポイントを作成してください。CRUD操作（作成、読み取り、更新、削除）を実装してください。" > api/user.py
  ```

- **リファクタリング**:
  ```bash
  # 既存のコードをパイプで渡し、リファクタリングを依頼
  cat old_code.py | gemini -p "このPythonコード
、より効率的で可読性の高いコードにリファクタリングしてください。"
  ```

- **テストコード生成**:
  ```bash
  # ファイルをコンテキストとして渡し、テストコードを生成
  gemini -c "api/user.py" -p "このFastAPIエンドポイントに対するpytestテストコードを生成してください。" > tests/test_user.py
  ```

---

## 4

`gemini-cli` を活用して、テスト駆動開発を効率化します。

- **pytest の導入**:
  ```bash
  pip install pytest
  pytest --init # pytest.ini 設定ファイルを生成
  ```

- **TDD の実践**:
  1. **テスト先行**: まずは `gemini-cli` でテストの雛形を生成します。
     ```bash
     gemini -p "ユーザー登録機能のテストケースを5つ考えて、pytest形式で出力してください。" > tests/test_registration.py
     ```
  2. **実装**: 生成されたテストが通るように、プロダクトコードを実装します。
  3. **リファクタリング**: テストを維持したまま、コードを改善します。

---

## 5

Terraform を用いて AWS リソースをコードで管理し、GitHub Actions でデプロイを自動化します。

- **ディレク
リ構成例**:
  ```
  terraform/
  ├─ main.tf      # Provider, Backend, モジュール呼び出し
  └─ modules/
     └─ s3/
        ├─ main.tf
        ├─ variables.tf
        └─ outputs.tf
  ```

- **リモートステート管理 (S3 + DynamoDB)**:
  `terraform/main.tf` にバックエンド設定を記述し、複数人での安全な状態管理を実現します。
  ```hcl
  terraform {
    backend "s3" {
      bucket         = "gemini-dev-workflow-tfstate" # 一意のバケット名に変更してください
      key            = "terraform.tfstate"
      region         = "ap-northeast-1"
      dynamodb_table = "terraform-lock"
      encrypt        = true
    }
  }
  ```

- **OIDC 認証**:
  GitHub Actions から AWS を操作するために、静的なアクセスキーの代わりに OIDC を利用した一時的な認証情報を取得します。これによりセキュリティが向上します。

---

## 6

### PR作成時: Terraform Plan (`.github/workflows/ci-terraform.yml`)

PR 作成時に `terraform plan` を実行し、変更内容を PR 上にコメントします。

```yaml
# .github/workflows/ci-terraform.yml
# (内容は変更なし)
```

### main マージ後: Terraform Apply (`.github/workflows/deploy-terraform.yml`)

main ブランチにマージされたら `terraform apply` を実行し、インフラを更新します。

```yaml
# .github/workflows/deploy-terraform.yml
# (内容は変更なし)
```

---

## 7

| フロー名             | イベント                        | 実行内容概要                                     |
| -------------------- | ------------------------------- | ------------------------------------------------ |
| `auto-pr.yml`        | `issues.opened`                 | Issue → ブランチ＆PR 自動生成                     |
| `ci-terraform.yml`   | PR 作成時（Terraform 変更）     | `terraform plan` → PR コメント出力              |
| `deploy-terraform.yml` | `main` に Push（Terraform 変更） | `terraform apply` → Slack 通知                   |

---

## 8

- **セキュリティ**: OIDC + IAM ロールを利用し、静的なクレデンシャルを排除します。
- **ワークフロー分離**: アプリケーションコードとインフラコード (Terraform) の CI/CD は分離して管理します。
- **可視化**: `terraform plan` の結果やテスト生成内容は、必ず PR 上で確認できるようにします。
- **ロールバック**: 問題発生時は、PR の Revert → 再 Apply を基本戦略とします。

---

## 9

- **静的解析とセキュリティスキャン**: `ruff`, `bandit`, `Trivy` などを CI に組み込み、コード品質とセキュリティを向上させます。
- **Terraform 高度化**: Terraform モジュールを拡充し、`Atlantis` や `HCP Terraform` の導入を検討します。
- **開発者体験向上**: Issue や PR のラベルに応じた自動アサインや、リリースノート自動生成などの機能を追加します。

---

## 10

- **Gemini CLI**: Open‑source AI agent for code & automation
  - [GitHub Repository](https://github.com/google/gemini-cli)
  - [Codelabs Tutorial](https://codelabs.developers.google.com/codelabs/gemini-cli)
- **GitHub Actions + OIDC**:
  - [AWS公式ドキュメント](https://docs.aws.amazon.com/ja_jp/IAM/latest/UserGuide/id_roles_providers_create_oidc.html)
- **Terraform on GitHub Actions**:
  - [HashiCorp 公式チュートリアル](https://developer.hashicorp.com/terraform/tutorials/ci-cd/github-actions)