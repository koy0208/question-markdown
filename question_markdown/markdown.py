"""
マークダウン処理モジュール

マークダウンファイルの読み書きとFrontMatterの処理を行います。
"""

import os
import base64
import hashlib
import re
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
import html2text


class MarkdownHandler:
    """マークダウンファイル処理クラス"""

    FRONTMATTER_PATTERN = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    def __init__(self, default_output_dir: str = "posts"):
        """
        マークダウンファイル処理クラスの初期化

        Args:
            default_output_dir: デフォルトの出力ディレクトリ
        """
        self.default_output_dir = default_output_dir
        self.h2t = html2text.HTML2Text()
        self.h2t.ignore_links = False
        self.h2t.body_width = 0  # 行の折り返しを無効化

    def read_markdown_file(self, file_path: str) -> Tuple[Dict[str, Any], str]:
        """
        マークダウンファイルを読み込み、FrontMatterとコンテンツを分離

        Args:
            file_path: マークダウンファイルのパス

        Returns:
            (FrontMatter辞書, 本文)
        """
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # FrontMatterの抽出
            frontmatter = {}
            match = self.FRONTMATTER_PATTERN.match(content)
            if match:
                try:
                    frontmatter = yaml.safe_load(match.group(1))
                    # FrontMatterを除いた本文を取得
                    body = content[match.end() :]
                except yaml.YAMLError as e:
                    print(f"FrontMatterのパースに失敗しました: {e}")
                    body = content
            else:
                body = content

            return frontmatter or {}, body
        except IOError as e:
            print(f"ファイルの読み込みに失敗しました: {e}")
            return {}, ""

    def write_markdown_file(
        self, file_path: str, frontmatter: Dict[str, Any], body: str
    ) -> bool:
        """
        FrontMatterと本文をマークダウンファイルに書き込む

        Args:
            file_path: 出力ファイルパス
            frontmatter: FrontMatter辞書
            body: 本文

        Returns:
            成功時はTrue
        """
        try:
            # 親ディレクトリが存在しない場合は作成
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)

            # FrontMatterのYAML形式への変換
            frontmatter_yaml = yaml.dump(
                frontmatter, default_flow_style=False, allow_unicode=True
            )

            # マークダウンファイルの作成
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("---\n")
                f.write(frontmatter_yaml)
                f.write("---\n\n")
                f.write(body)

            return True
        except IOError as e:
            print(f"ファイルの書き込みに失敗しました: {e}")
            return False

    def html_to_markdown(self, html_content: str) -> str:
        """
        HTMLをマークダウンに変換

        Args:
            html_content: HTML形式の文字列

        Returns:
            マークダウン形式の文字列
        """
        return self.h2t.handle(html_content)

    def get_output_path(
        self,
        entry_id: str,
        title: str,
        output_dir: Optional[str] = None,
        created: Optional[str] = None,
    ) -> str:
        """
        記事IDとタイトルから出力ファイルパスを生成

        Args:
            entry_id: 記事ID
            title: 記事タイトル
            output_dir: 出力ディレクトリ（省略時はデフォルト）

        Returns:
            出力ファイルパス
        """
        # 出力ディレクトリの設定
        if created:
            try:
                dt = datetime.fromisoformat(created)
                date_folder = dt.strftime("%Y%m%d")
                dir_path = os.path.join(self.default_output_dir, date_folder)
            except Exception:
                dir_path = self.default_output_dir
        else:
            dir_path = self.default_output_dir
        if output_dir:
            dir_path = output_dir

        # ファイル名の生成（タイトルからファイル名に使えない文字を除去）
        safe_title = re.sub(r"[^\w\s-]", "", title).strip().lower()
        safe_title = re.sub(r"[-\s]+", "-", safe_title)

        # ファイル名が空の場合はIDを使用
        filename = safe_title or entry_id

        # 拡張子の追加
        if not filename.endswith(".md"):
            filename += ".md"

        return os.path.join(dir_path, filename)

    def save_entry_as_markdown(
        self,
        entry_data: Dict[str, Any],
        output_path: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        記事データをマークダウンファイルとして保存

        Args:
            entry_data: 記事データ
            output_path: 出力ファイルパス（省略時は自動生成）

        Returns:
            (成功フラグ, 出力ファイルパス)
        """
        # 必須フィールドのチェック
        if not all(k in entry_data for k in ["id", "title", "content"]):
            return False, "記事データが不完全です"

        # 出力パスの決定
        if not output_path:
            output_path = self.get_output_path(entry_data["id"], entry_data["title"])

        # コンテンツタイプに応じた変換
        content = entry_data["content"]
        if entry_data.get("content_type") in ["html", "text/html"]:
            content = self.html_to_markdown(content)

        # FrontMatterの作成
        frontmatter = {
            "title": entry_data["title"],
            "id": entry_data["id"],
            "draft": entry_data.get("draft", False),
        }

        # カテゴリがあれば追加
        if "categories" in entry_data and entry_data["categories"]:
            frontmatter["categories"] = entry_data["categories"]

        # マークダウンファイルの書き込み
        success = self.write_markdown_file(output_path, frontmatter, content)
        if success:
            return True, output_path
        else:
            return False, "ファイルの書き込みに失敗しました"

    def prepare_entry_data(
        self, file_path: str, title: Optional[str] = None, draft: Optional[bool] = None
    ) -> Tuple[Dict[str, Any], str]:
        """
        マークダウンファイルから記事データを準備

        Args:
            file_path: マークダウンファイルのパス
            title: タイトル（省略時はFrontMatterから取得）
            draft: 下書きフラグ（省略時はFrontMatterから取得）

        Returns:
            (記事データ, マークダウン本文)
        """
        # マークダウンファイルの読み込み
        frontmatter, body = self.read_markdown_file(file_path)

        # 記事データの準備
        entry_data = {}

        # タイトルの設定
        entry_data["title"] = title or frontmatter.get("title", "無題")

        # 記事IDの設定（既存の記事の場合）
        if "id" in frontmatter:
            entry_data["id"] = frontmatter["id"]

        # 下書きフラグの設定
        if draft is not None:
            entry_data["draft"] = draft
        elif "draft" in frontmatter:
            # YAMLでは様々な形式でブール値を表現できるため、明示的に変換
            draft_value = frontmatter["draft"]
            if isinstance(draft_value, str):
                draft_value = draft_value.lower()
                entry_data["draft"] = draft_value in ["true", "yes", "on", "y", "1"]
            else:
                entry_data["draft"] = bool(draft_value)
        else:
            entry_data["draft"] = False

        # カテゴリの設定
        if "categories" in frontmatter:
            entry_data["categories"] = frontmatter["categories"]

        return entry_data, body

    def upload_image(self, image_path: str, config: dict) -> Optional[str]:
        """指定した画像ファイルをはてなフォトライフにアップロードし、[f:id:...] 形式の文字列を返す"""
        import requests, base64, mimetypes
        import xml.etree.ElementTree as ET

        if not os.path.isfile(image_path):
            print(f"画像ファイルが見つかりません: {image_path}")
            return None

        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "application/octet-stream"

        try:
            with open(image_path, "rb") as f:
                data = f.read()
        except IOError as e:
            print(f"画像ファイルの読み込みに失敗しました: {e}")
            return None

        b64_data = base64.b64encode(data).decode("utf-8")
        filename = os.path.basename(image_path)

        xml_payload = f"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://purl.org/atom/ns#" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <title>{filename}</title>
  <content mode="base64" type="{mime_type}">{b64_data}</content>
</entry>
"""

        endpoint = "https://f.hatena.ne.jp/atom/post"
        hatena_id = config.get("hatena_id")
        api_key = config.get("api_key")

        nonce = os.urandom(16)
        nonce_b64 = base64.b64encode(nonce).decode("utf-8")
        created = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        digest = hashlib.sha1(
            nonce + created.encode("utf-8") + api_key.encode("utf-8")
        ).digest()
        password_digest = base64.b64encode(digest).decode("utf-8")
        wsse_header = f'UsernameToken Username="{hatena_id}", PasswordDigest="{password_digest}", Nonce="{nonce_b64}", Created="{created}"'

        try:
            response = requests.post(
                endpoint,
                data=xml_payload.encode("utf-8"),
                headers={"Content-Type": "application/xml", "X-WSSE": wsse_header},
            )
        except Exception as e:
            print(f"画像アップロードリクエストの送信に失敗しました: {e}")
            return None

        if response.status_code != 201:
            print(
                f"画像アップロードに失敗しました: {response.status_code} {response.text}"
            )
            return None

        try:
            root = ET.fromstring(response.content)
            syntax = None
            for elem in root.iter():
                if "syntax" in elem.tag:
                    syntax = elem.text
                    break
            if syntax:
                return f"[{syntax}]"
            else:
                print("レスポンスから[f:id]形式の情報が取得できませんでした")
                return None
        except ET.ParseError as e:
            print(f"レスポンスXMLのパースに失敗しました: {e}")
            return None

    def upload_and_replace_images(self, body: str, config: dict, base_dir: str) -> str:
        """Markdown本文中のローカル画像を検出し、アップロード後に[f:id:...]形式に置換します.
        base_dir はマークダウンファイルがあるフォルダのパスを指定してください。画像はこのフォルダ内の 'images' フォルダに配置されていると仮定します。
        """

        def replacer(match):
            alt_text = match.group(1)
            image_path = match.group(2).strip()
            # 画像は常に base_dir の 'images' サブフォルダ内にあると仮定
            abs_path = os.path.join(base_dir, "img", os.path.basename(image_path))
            result = self.upload_image(abs_path, config)
            return result if result else match.group(0)

        pattern = re.compile(r"!\[(.*?)\]\((?!https?://)(.*?)\)")
        new_body = pattern.sub(replacer, body)
        return new_body
