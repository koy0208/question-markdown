"""
ユーティリティモジュール

ユーティリティ関数を提供します。
"""

import os
import sys
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime


def format_entry_list(entries: List[Dict[str, Any]], format_type: str = "text") -> str:
    """
    記事一覧を指定された形式でフォーマット

    Args:
        entries: 記事リスト
        format_type: 出力形式（text, json, csv）

    Returns:
        フォーマットされた文字列
    """
    if not entries:
        return "記事が見つかりませんでした。"

    if format_type == "json":
        import json

        return json.dumps(entries, ensure_ascii=False, indent=2)

    elif format_type == "csv":
        import csv
        from io import StringIO

        output = StringIO()
        fieldnames = ["id", "title", "updated", "draft", "categories"]
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for entry in entries:
            row = {
                "id": entry["id"],
                "title": entry["title"],
                "updated": entry["updated"],
                "draft": "yes" if entry.get("draft") else "no",
                "categories": ",".join(entry.get("categories", [])),
            }
            writer.writerow(row)

        return output.getvalue()

    else:  # text
        lines = []
        for entry in entries:
            draft_mark = "[下書き] " if entry.get("draft") else ""
            categories = (
                f" ({', '.join(entry.get('categories', []))})"
                if entry.get("categories")
                else ""
            )
            updated = format_datetime(entry.get("updated", ""))

            lines.append(f"{draft_mark}{entry['title']}{categories}")
            lines.append(f"  ID: {entry['id']}")
            lines.append(f"  更新日時: {updated}")
            lines.append("")

        return "\n".join(lines)


def format_datetime(iso_datetime: str) -> str:
    """
    ISO形式の日時を読みやすい形式に変換

    Args:
        iso_datetime: ISO形式の日時文字列

    Returns:
        フォーマットされた日時文字列
    """
    if not iso_datetime:
        return ""

    try:
        dt = datetime.fromisoformat(iso_datetime.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return iso_datetime


def confirm_action(message: str) -> bool:
    """
    ユーザーに確認を求める

    Args:
        message: 確認メッセージ

    Returns:
        ユーザーが確認した場合はTrue
    """
    response = input(f"{message} [y/N]: ").strip().lower()
    return response in ["y", "yes"]


def ensure_dir_exists(dir_path: str) -> bool:
    """
    ディレクトリが存在することを確認し、存在しない場合は作成

    Args:
        dir_path: ディレクトリパス

    Returns:
        成功時はTrue
    """
    try:
        os.makedirs(dir_path, exist_ok=True)
        return True
    except OSError as e:
        print(f"ディレクトリの作成に失敗しました: {e}")
        return False


def parse_categories(categories_str: str) -> List[str]:
    """
    カンマ区切りのカテゴリ文字列をリストに変換

    Args:
        categories_str: カンマ区切りのカテゴリ文字列

    Returns:
        カテゴリリスト
    """
    if not categories_str:
        return []

    return [cat.strip() for cat in categories_str.split(",") if cat.strip()]


def extract_entry_id_from_url(url: str) -> Optional[str]:
    """
    URLから記事IDを抽出

    Args:
        url: 記事URL

    Returns:
        記事ID
    """
    if not url:
        return None

    # 末尾のスラッシュを削除
    url = url.rstrip("/")

    # 最後のパス要素を取得
    parts = url.split("/")
    if not parts:
        return None

    return parts[-1]


def print_error(message: str) -> None:
    """
    エラーメッセージを標準エラー出力に出力

    Args:
        message: エラーメッセージ
    """
    print(f"エラー: {message}", file=sys.stderr)


def print_success(message: str) -> None:
    """
    成功メッセージを出力

    Args:
        message: 成功メッセージ
    """
    print(f"成功: {message}")
