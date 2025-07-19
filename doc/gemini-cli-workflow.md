# ✅ GitHub Actions 自動化要件まとめ：Issue → Gemini → ブランチ作成 & コミット & Push & PR

このドキュメントは、GitHub Issue を起点に Google Gemini CLI を用いて Python コードとテストを自動生成し、Git ブランチ作成・コミット・プッシュ・PR 作成までを完全自動化するワークフローの要件を整理したものです。

---

## 🎯 目的

- **Issue作成** をトリガーに、Gemini でコード・テストを自動生成
- **Gitブランチ作成 → 変更のコミット → リモートpush → PR作成** までを自動で実行
- 開発者はレビューと修正だけに集中できる開発体験を実現

---

## 🧱 前提条件

- Google Gemini API キー（`GEMINI_API_KEY`）が GitHub Secrets に登録されていること
- GitHub CLI（`gh`）が有効な環境
- Gemini CLI が以下の機能を持つこと：
  - Issue 内容を解析してコード・テストを生成
  - ファイルを書き出す（ただしブランチ作成・コミット・プッシュまではアクションで対応）

---

## 🧩 要件一覧

| カテゴリ | 要件内容 |
|----------|----------|
| ✅ トリガー       | `on.issues.types: [opened]` によって Issue 作成時に起動 |
| ✅ Gemini入力     | `prompt:` に Issue タイトル・本文を渡す（背景指示付き） |
| ✅ Gemini出力     | `outputs.branch_name` を取得し、なければデフォルト名 `feature/issue-<番号>` を使用 |
| ✅ Git 設定       | `user.name` / `user.email` を `github-actions[bot]` に設定 |
| ✅ ブランチ作成・切替 | `git fetch` によるリモートの確認後、`git switch` または `git switch -c` |
| ✅ コミット処理   | `git status --porcelain` により差分チェック → `add` → `commit` 実行 |
| ✅ プッシュ処理   | `git push -u origin <branch>` によってリモート反映 |
| ✅ PR作成         | `gh pr create` により PR 作成（すでに存在する場合はスキップ） |
| ✅ PR本文         | Issue 番号リンク、チェックリスト、自動生成コメントを含める |
| ✅ fetch対応     | `actions/checkout@v3` では `fetch-depth: 0` を使用（浅いクローンを防止） |
| ✅ エラーハンドリング | Gemini が失敗しても `continue-on-error: true` で全体が止まらないようにする |

---

## 🪛 処理フロー（ステップ別）

1. **リポジトリのクローン**
   - `actions/checkout@v3` + `fetch-depth: 0`

2. **Gemini CLI 実行**
   - `Issue Title` と `Issue Body` を含むプロンプトを投げる
   - コードとテストを自動生成（ファイル出力）

3. **ブランチ作成／切替**
   - `outputs.branch_name` がある場合はそれを使う
   - なければ `feature/issue-<番号>` を使用
   - `git fetch` → `git ls-remote` でブランチ存在確認 → `git switch` または `git switch -c`

4. **Git コミット & プッシュ**
   - 差分がある場合のみ：
     - `git add -A`
     - `git commit -m "auto: generate code from issue #<番号>"`
     - `git push -u origin <branch>`

5. **PR 作成**
   - `gh pr create` を使って PR を作成
   - PR タイトルは `feat: <Issue Title>`
   - PR 本文に Issue リンクとレビュー用チェックリストを含める
   - PR ラベルに `auto-generated` を追加
   - 既にPRが存在する場合はスキップ

---

## 🛑 問題点と対応策

| 問題点 | 解決内容 |
|--------|----------|
| `git checkout -b` が main からブランチを作ってしまい、Gemini 生成結果が含まれない | Gemini 出力ブランチを `fetch` ＆ `switch` するよう修正 |
| commit/push ステップが欠落していた | `git add → commit → push` を明示的に追加 |
| `fetch-depth: 1` による履歴不足 | `fetch-depth: 0` に設定し履歴を完全に取得 |
| PR が重複作成される可能性 | `gh pr view` により事前に存在確認し、重複防止 |

---