"""
コマンドラインインターフェースモジュール

コマンドラインからはてなブログの記事を管理するためのインターフェースを提供します。
"""

import argparse
import sys
import os
from typing import List, Optional, Dict, Any, Tuple

from . import __version__
from .config import get_config
from .api import HatenaAPI
from .markdown import MarkdownHandler
from .utils import (
    format_entry_list,
    confirm_action,
    ensure_dir_exists,
    parse_categories,
    extract_entry_id_from_url,
    print_error,
    print_success,
)


def create_parser() -> argparse.ArgumentParser:
    """
    コマンドライン引数パーサーを作成

    Returns:
        ArgumentParser
    """
    parser = argparse.ArgumentParser(
        description="はてなブログの記事をマークダウンで管理するツール",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--version", action="version", version=f"hatena-markdown {__version__}"
    )
    parser.add_argument(
        "--config",
        help="設定ファイルのパス",
        default=None,
    )

    subparsers = parser.add_subparsers(dest="command", help="コマンド")

    # configコマンド
    config_parser = subparsers.add_parser("config", help="設定の確認・変更")
    config_parser.add_argument("--show", action="store_true", help="現在の設定を表示")
    config_parser.add_argument(
        "--wizard", action="store_true", help="設定ウィザードを実行"
    )

    # listコマンド
    list_parser = subparsers.add_parser("list", help="記事一覧を表示")
    list_parser.add_argument(
        "--limit", type=int, help="取得する記事数の上限", default=None
    )
    list_parser.add_argument("--draft", action="store_true", help="下書き記事のみ表示")
    list_parser.add_argument(
        "--format",
        choices=["text", "json", "csv"],
        default="text",
        help="出力形式",
    )

    # getコマンド
    get_parser = subparsers.add_parser("get", help="記事を取得")
    get_parser.add_argument("entry_id", help="記事ID")
    get_parser.add_argument("--output", "-o", help="出力ファイルパス", default=None)

    # createコマンド
    create_parser = subparsers.add_parser("create", help="新規記事を作成")
    create_parser.add_argument("file", help="マークダウンファイルパス")
    create_parser.add_argument(
        "--title", help="記事タイトル（省略時はファイルから取得）"
    )
    create_parser.add_argument("--categories", help="カテゴリ（カンマ区切り）")
    create_parser.add_argument("--draft", action="store_true", help="下書きとして保存")

    # updateコマンド
    update_parser = subparsers.add_parser("update", help="記事を更新")
    update_parser.add_argument("entry_id", help="記事ID")
    update_parser.add_argument("file", help="マークダウンファイルパス")
    update_parser.add_argument(
        "--title", help="記事タイトル（省略時はファイルから取得）"
    )
    update_parser.add_argument("--categories", help="カテゴリ（カンマ区切り）")
    update_parser.add_argument("--draft", action="store_true", help="下書きとして保存")

    # draftsコマンド
    drafts_parser = subparsers.add_parser("drafts", help="下書き管理")
    drafts_subparsers = drafts_parser.add_subparsers(
        dest="drafts_command", help="下書きコマンド"
    )

    # drafts listコマンド
    drafts_list_parser = drafts_subparsers.add_parser("list", help="下書き一覧")
    drafts_list_parser.add_argument(
        "--format",
        choices=["text", "json", "csv"],
        default="text",
        help="出力形式",
    )

    # drafts publishコマンド
    drafts_publish_parser = drafts_subparsers.add_parser("publish", help="下書きを公開")
    drafts_publish_parser.add_argument("entry_id", help="記事ID")

    return parser


def handle_config(args: argparse.Namespace) -> int:
    """
    configコマンドの処理

    Args:
        args: コマンドライン引数

    Returns:
        終了コード
    """
    config = get_config(args.config)

    if args.show:
        # 設定を表示
        print("現在の設定:")
        print(f"はてなID: {config.get('hatena_id')}")
        print(f"ブログID: {config.get('blog_id')}")
        print(f"APIキー: {'*' * 8 if config.get('api_key') else ''}")
        print(f"デフォルト出力ディレクトリ: {config.get('default_output_dir')}")
        return 0

    if args.wizard or not config.is_configured():
        # 設定ウィザードを実行
        if not config.is_configured():
            print("必須設定が構成されていません。設定ウィザードを実行します。")

        if config.setup_wizard():
            print("設定を保存しました。")
            return 0
        else:
            print_error("設定の保存に失敗しました。")
            return 1

    # 引数が指定されていない場合はヘルプを表示
    print("使用法: question-md config [--show] [--wizard]")
    return 0


def handle_list(args: argparse.Namespace) -> int:
    """
    listコマンドの処理

    Args:
        args: コマンドライン引数

    Returns:
        終了コード
    """
    config = get_config(args.config)
    if not config.is_configured():
        print_error(
            "APIの認証情報が設定されていません。'question-md config --wizard'を実行してください。"
        )
        return 1

    # APIクライアントの初期化
    credentials = config.get_api_credentials()
    api = HatenaAPI(
        credentials["hatena_id"], credentials["blog_id"], credentials["api_key"]
    )

    # 記事一覧の取得
    success, entries, error = api.get_entry_list(args.limit)
    if not success:
        print_error(error or "記事一覧の取得に失敗しました。")
        return 1

    # 下書きフィルタリング
    if args.draft and entries:
        entries = [entry for entry in entries if entry.get("draft")]

    # 結果の表示
    print(format_entry_list(entries, args.format))
    return 0


def handle_get(args: argparse.Namespace) -> int:
    """
    getコマンドの処理

    Args:
        args: コマンドライン引数

    Returns:
        終了コード
    """
    config = get_config(args.config)
    if not config.is_configured():
        print_error(
            "APIの認証情報が設定されていません。'question-md config --wizard'を実行してください。"
        )
        return 1

    # APIクライアントの初期化
    credentials = config.get_api_credentials()
    api = HatenaAPI(
        credentials["hatena_id"], credentials["blog_id"], credentials["api_key"]
    )

    # マークダウンハンドラの初期化
    md_handler = MarkdownHandler(config.get("default_output_dir"))

    # 記事IDの処理（URLからの抽出）
    entry_id = extract_entry_id_from_url(args.entry_id) or args.entry_id

    # 記事の取得
    success, entry_data, error = api.get_entry(entry_id)
    if not success:
        print_error(error or f"記事ID '{entry_id}' の取得に失敗しました。")
        return 1

    # 出力パスの決定
    output_path = args.output
    if not output_path:
        output_path = md_handler.get_output_path(
            entry_id, entry_data["title"], created=entry_data["created"]
        )
        print(f"記事を '{output_path}' に保存します。")

    # マークダウンファイルとして保存
    success, result = md_handler.save_entry_as_markdown(entry_data, output_path)
    if not success:
        print_error(result or "マークダウンファイルの保存に失敗しました。")
        return 1

    print_success(f"記事を '{result}' に保存しました。")
    return 0


def handle_create(args: argparse.Namespace) -> int:
    """
    createコマンドの処理

    Args:
        args: コマンドライン引数

    Returns:
        終了コード
    """
    config = get_config(args.config)
    if not config.is_configured():
        print_error(
            "APIの認証情報が設定されていません。'question-md config --wizard'を実行してください。"
        )
        return 1

    # ファイルの存在確認
    if not os.path.isfile(args.file):
        print_error(f"ファイル '{args.file}' が見つかりません。")
        return 1

    # APIクライアントの初期化
    credentials = config.get_api_credentials()
    api = HatenaAPI(
        credentials["hatena_id"], credentials["blog_id"], credentials["api_key"]
    )

    # マークダウンハンドラの初期化
    md_handler = MarkdownHandler(config.get("default_output_dir"))

    # マークダウンファイルの読み込み
    entry_data, body = md_handler.prepare_entry_data(args.file, args.title, args.draft)

    # カテゴリの処理
    if args.categories:
        entry_data["categories"] = parse_categories(args.categories)

    # 記事の作成
    success, entry_id, error = api.create_entry(
        entry_data["title"],
        body,
        entry_data.get("categories"),
        entry_data.get("draft", False),
    )

    if not success:
        print_error(error or "記事の作成に失敗しました。")
        return 1

    print_success(f"記事を作成しました。ID: {entry_id}")

    # 作成した記事IDをマークダウンファイルに追記
    if entry_id:
        entry_data["id"] = entry_id
        md_handler.write_markdown_file(args.file, entry_data, body)
        print(f"記事IDをマークダウンファイルに追記しました: {args.file}")

    return 0


def handle_update(args: argparse.Namespace) -> int:
    """
    updateコマンドの処理

    Args:
        args: コマンドライン引数

    Returns:
        終了コード
    """
    config = get_config(args.config)
    if not config.is_configured():
        print_error(
            "APIの認証情報が設定されていません。'question-md config --wizard'を実行してください。"
        )
        return 1

    # ファイルの存在確認
    if not os.path.isfile(args.file):
        print_error(f"ファイル '{args.file}' が見つかりません。")
        return 1

    # APIクライアントの初期化
    credentials = config.get_api_credentials()
    api = HatenaAPI(
        credentials["hatena_id"], credentials["blog_id"], credentials["api_key"]
    )

    # マークダウンハンドラの初期化
    md_handler = MarkdownHandler(config.get("default_output_dir"))

    # 記事IDの処理（URLからの抽出）
    entry_id = extract_entry_id_from_url(args.entry_id) or args.entry_id

    # マークダウンファイルの読み込み
    entry_data, body = md_handler.prepare_entry_data(args.file, args.title, args.draft)

    # カテゴリの処理
    if args.categories:
        entry_data["categories"] = parse_categories(args.categories)

    # 記事の更新
    success, error = api.update_entry(
        entry_id,
        entry_data["title"],
        body,
        entry_data.get("categories"),
        entry_data.get("draft", False),
    )

    if not success:
        print_error(error or f"記事ID '{entry_id}' の更新に失敗しました。")
        return 1

    print_success(f"記事ID '{entry_id}' を更新しました。")

    # 更新した記事IDをマークダウンファイルに追記（まだない場合）
    if "id" not in entry_data:
        entry_data["id"] = entry_id
        md_handler.write_markdown_file(args.file, entry_data, body)
        print(f"記事IDをマークダウンファイルに追記しました: {args.file}")

    return 0


def handle_drafts(args: argparse.Namespace) -> int:
    """
    draftsコマンドの処理

    Args:
        args: コマンドライン引数

    Returns:
        終了コード
    """
    if not args.drafts_command:
        print("使用法: question-md drafts {list|publish} [options]")
        return 0

    config = get_config(args.config)
    if not config.is_configured():
        print_error(
            "APIの認証情報が設定されていません。'question-md config --wizard'を実行してください。"
        )
        return 1

    # APIクライアントの初期化
    credentials = config.get_api_credentials()
    api = HatenaAPI(
        credentials["hatena_id"], credentials["blog_id"], credentials["api_key"]
    )

    if args.drafts_command == "list":
        # 下書き一覧の取得
        success, entries, error = api.get_entry_list()
        if not success:
            print_error(error or "記事一覧の取得に失敗しました。")
            return 1

        # 下書きのみをフィルタリング
        if entries:
            entries = [entry for entry in entries if entry.get("draft")]

        # 結果の表示
        print(format_entry_list(entries, args.format))
        return 0

    elif args.drafts_command == "publish":
        # 記事IDの処理（URLからの抽出）
        entry_id = extract_entry_id_from_url(args.entry_id) or args.entry_id

        # 下書きの公開
        if confirm_action(f"記事ID '{entry_id}' を公開しますか？"):
            success, error = api.publish_draft(entry_id)
            if not success:
                print_error(error or f"記事ID '{entry_id}' の公開に失敗しました。")
                return 1

            print_success(f"記事ID '{entry_id}' を公開しました。")
            return 0
        else:
            print("操作をキャンセルしました。")
            return 0

    return 0


def main() -> int:
    """
    メイン関数

    Returns:
        終了コード
    """
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    # 各コマンドのハンドラを呼び出す
    if args.command == "config":
        return handle_config(args)
    elif args.command == "list":
        return handle_list(args)
    elif args.command == "get":
        return handle_get(args)
    elif args.command == "create":
        return handle_create(args)
    elif args.command == "update":
        return handle_update(args)
    elif args.command == "drafts":
        return handle_drafts(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
