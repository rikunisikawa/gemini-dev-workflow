---PR_TITLE---
feat: SAMを用いたmHealthデータ基盤の構築
---PR_BODY---
## 概要

Issue: #<ISSUE_NUMBER>

KaggleのmHealthデータセットを処理し、Athenaで分析可能にするための自動データパイプラインをAWS SAMで構築しました。

## 変更内容

本PRでは、以下のリソースを含むSAMアプリケーションを新規に作成しました。

- **S3バケット**: `raw`, `stage`, `processed` の各層でデータを管理します。
- **Lambda関数 (Python 3.11)**:
  1.  `DownloadFunction`: Kaggle APIを利用してmHealthデータセット（.logファイル）をダウンロードし、S3の`raw`ディレクトリにアップロードします。Kaggleの認証情報はAWS Secrets Managerから安全に取得します。
  2.  `ConvertToParquetFunction`: `raw`ディレクトリのログファイルをPandasで読み込み、Parquet形式に変換して`stage`ディレクトリに保存します。
- **AWS Glueジョブ**:
  - `stage`のParquetデータを入力とし、カラム名の正規化やデータ型の変換などの整形処理を実施します。
  - 処理済み���データを`processed`ディレクトリに出力し、Athenaでのクエリを可能にするためにGlueデータカタログを更新します。
- **AWS Step Functions**:
  - `Download` → `Convert` → `Glue` のETL処理フロー全体を管理・オーケストレーションするステートマシンを定義しました。
  - 各ステップでのエラーハンドリングも含まれています。
- **Amazon EventBridge**:
  - 定期的（デフォルトでは1日1回）にStep Functionsのステートマシンをトリガーし、ETLパイプラインを自動実行します。
- **IAMロール**:
  - 各AWSサービス（Lambda, Glue, Step Functions, EventBridge）が必要とする最小限の権限を持つIAMロールを定義しました。

## デプロイとテストの方法

1.  **前提条件**:
    - AWS SAM CLIのインストール
    - Dockerのインストール
    - AWS認証情報の設定
    - `kaggle.json` の内容をAWS Secrets Managerにシークレットとして保存

2.  **デプロイ手順**:
    ```bash
    # SAMアプリケーションのルートディレクトリに移動
    cd sam-app

    # SAMビルド
    sam build

    # SAMデプロイ（ガイド付き）
    sam deploy --guided
    ```
    デプロイ中に、`template.yaml`で定義されたパラメータ（`BucketName`, `KaggleSecretName`など）の入力を求められます。

3.  **テスト**:
    - デプロイ後、設定したEventBridgeルールによってパイプラインが自動的に実行されます。
    - AWSコンソールでStep Functionsの実行状況を確認できます。
    - パイプラインが正常に完了したら、Amazon Athenaで`mhealth_db.mhealth_data`テーブルに対して`SELECT`クエリを実行し、データが正しく格納されていることを確認します。
