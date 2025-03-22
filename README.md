# はてなマークダウン管理ツール

はてなブログAPIを使用して、マークダウン形式で記事を管理するコマンドラインツールです。

## 機能

- 記事一覧の取得
- 記事のダウンロード（マークダウン形式）
- 新規記事の作成
- 既存記事の更新
- 下書き管理

## インストール

### 依存関係のインストール

```bash
poetry install
```

または

```bash
pip install -r requirements.txt
```

### 実行権限の付与

```bash
chmod +x question-md
```

## 設定

初回実行時に設定ウィザードが起動します。以下の情報を入力してください：

- はてなID
- ブログID
- APIキー
- デフォルト出力ディレクトリ

または、手動で設定を行うこともできます：

```bash
./question-md config --wizard
```

## 使い方

### 記事一覧の取得

```bash
./question-md list
./question-md list --draft  # 下書き記事のみ表示
./question-md list --format json  # JSON形式で出力
```

### 記事の取得（ダウンロード）

```bash
./question-md get <entry_id>
./question-md get <entry_id> --output path/to/file.md
```

### 新規記事の作成

```bash
./question-md create path/to/markdown.md
./question-md create path/to/markdown.md --title "記事タイトル" --categories "カテゴリ1,カテゴリ2" --draft
```

### 記事の更新

```bash
./question-md update path/to/markdown.md  # マークダウンファイルから記事IDを自動取得
./question-md update --entry-id <entry_id> path/to/markdown.md  # 記事IDを明示的に指定
./question-md update path/to/markdown.md --title "新しいタイトル" --categories "カテゴリ1,カテゴリ2" --draft
```

マークダウンファイルのFrontMatterに`id`が含まれている場合、`--entry-id`オプションを省略できます。

### 下書き管理

```bash
./question-md drafts list  # 下書き一覧
./question-md drafts publish <entry_id>  # 下書きを公開
```

## マークダウンファイル形式

マークダウンファイルはFrontMatter形式（YAMLヘッダー）を使用します：

```markdown
---
title: 記事タイトル
categories:
  - カテゴリ1
  - カテゴリ2
draft: true
id: 12345678901234567
---

# 記事の本文

これは記事の本文です...
```

## ライセンス

MIT
