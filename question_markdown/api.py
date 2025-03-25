"""
はてなブログAPI連携モジュール

はてなブログAtomPub APIを使用して記事の取得、投稿、更新を行います。
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple, Any
import requests
from xml.sax.saxutils import escape
import os
import base64
import hashlib
from datetime import datetime
import mimetypes


class HatenaAPI:
    """はてなブログAPI連携クラス"""

    def __init__(self, hatena_id: str, blog_id: str, api_key: str):
        """
        はてなブログAPI連携クラスの初期化

        Args:
            hatena_id: はてなID
            blog_id: ブログID
            api_key: APIキー
        """
        self.hatena_id = hatena_id
        self.blog_id = blog_id
        self.api_key = api_key
        self.atom_endpoint = f"https://blog.hatena.ne.jp/{hatena_id}/{blog_id}/atom"
        self.auth = (hatena_id, api_key)
        self.namespaces = {
            "atom": "http://www.w3.org/2005/Atom",
            "app": "http://www.w3.org/2007/app",
            "hatena": "http://www.hatena.ne.jp/info/xmlns#",
        }

    def create_entry_xml(
        self,
        title: str,
        content_md: str,
        categories: Optional[List[str]] = None,
        draft: bool = False,
    ) -> bytes:
        """
        タイトル・Markdown本文・カテゴリからAtomPubエントリXMLを生成

        Args:
            title: 記事タイトル
            content_md: Markdown形式の本文
            categories: カテゴリリスト
            draft: 下書きフラグ

        Returns:
            AtomPubエントリXMLのバイト列
        """
        # 本文中の特殊文字をエスケープ
        content_xml = escape(content_md)
        # カテゴリ要素の組み立て
        cat_elems = "".join([f'<category term="{c}" />' for c in (categories or [])])
        # draftフラグ ("yes" or "no")
        draft_flag = "yes" if draft else "no"
        # AtomPubエントリXMLの構築
        entry_xml = f"""<?xml version="1.0" encoding="utf-8"?>
<entry xmlns="http://www.w3.org/2005/Atom" xmlns:app="http://www.w3.org/2007/app">
  <title>{title}</title>
  <author><name>{self.hatena_id}</name></author>
  <content type="text/x-markdown">{content_xml}</content>
  {cat_elems}
  <app:control><app:draft>{draft_flag}</app:draft></app:control>
</entry>"""
        return entry_xml.encode("utf-8")

    def create_entry(
        self,
        title: str,
        content_md: str,
        categories: Optional[List[str]] = None,
        draft: bool = False,
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        新規記事を作成

        Args:
            title: 記事タイトル
            content_md: Markdown形式の本文
            categories: カテゴリリスト
            draft: 下書きフラグ

        Returns:
            (成功フラグ, 記事ID, エラーメッセージ)
        """
        xml_data = self.create_entry_xml(title, content_md, categories, draft)
        try:
            resp = requests.post(
                f"{self.atom_endpoint}/entry",
                auth=self.auth,
                data=xml_data,
                headers={"Content-Type": "application/xml"},
            )

            if resp.status_code == 201:
                # 成功時、Locationヘッダから記事IDを抽出
                location = resp.headers.get("Location", "")
                entry_id = location.split("/")[-1] if location else None
                return True, entry_id, None
            else:
                return False, None, f"API エラー: {resp.status_code} - {resp.text}"
        except requests.RequestException as e:
            return False, None, f"リクエストエラー: {e}"

    def update_entry(
        self,
        entry_id: str,
        title: str,
        content_md: str,
        categories: Optional[List[str]] = None,
        draft: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        """
        既存記事を更新

        Args:
            entry_id: 記事ID
            title: 記事タイトル
            content_md: Markdown形式の本文
            categories: カテゴリリスト
            draft: 下書きフラグ

        Returns:
            (成功フラグ, エラーメッセージ)
        """
        xml_data = self.create_entry_xml(title, content_md, categories, draft)
        try:
            resp = requests.put(
                f"{self.atom_endpoint}/entry/{entry_id}",
                auth=self.auth,
                data=xml_data,
                headers={"Content-Type": "application/xml"},
            )

            if resp.status_code == 200:
                return True, None
            else:
                return False, f"API エラー: {resp.status_code} - {resp.text}"
        except requests.RequestException as e:
            return False, f"リクエストエラー: {e}"

    def get_entry_list(
        self, limit: Optional[int] = None
    ) -> Tuple[bool, Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        記事一覧を取得

        Args:
            limit: 取得する記事数の上限（指定しない場合はすべて取得）

        Returns:
            (成功フラグ, 記事リスト, エラーメッセージ)
        """
        try:
            entries = []
            url = f"{self.atom_endpoint}/entry"
            while True:
                resp = requests.get(url, auth=self.auth)
                if resp.status_code != 200:
                    return False, None, f"API エラー: {resp.status_code} - {resp.text}"

                root = ET.fromstring(resp.content)
                for entry in root.findall("atom:entry", self.namespaces):
                    raw_id = entry.find("atom:id", self.namespaces).text
                    entry_id = raw_id.split("-")[-1]

                    title = entry.find("atom:title", self.namespaces).text or ""

                    updated = entry.find("atom:updated", self.namespaces).text

                    draft_elem = entry.find(".//app:draft", self.namespaces)
                    is_draft = draft_elem is not None and draft_elem.text == "yes"

                    categories = [
                        cat.get("term")
                        for cat in entry.findall("atom:category", self.namespaces)
                    ]

                    edit_url = None
                    for link in entry.findall("atom:link", self.namespaces):
                        if link.get("rel") == "edit":
                            edit_url = link.get("href")
                            break

                    entries.append(
                        {
                            "id": entry_id,
                            "title": title,
                            "updated": updated,
                            "draft": is_draft,
                            "categories": categories,
                            "edit_url": edit_url,
                        }
                    )

                    if limit is not None and len(entries) >= limit:
                        return True, entries[:limit], None

                next_link = root.find("atom:link[@rel='next']", self.namespaces)
                if next_link is None or not next_link.get("href"):
                    break
                url = next_link.get("href")
            return True, entries, None
        except requests.RequestException as e:
            return False, None, f"リクエストエラー: {e}"
        except ET.ParseError as e:
            return False, None, f"XMLパースエラー: {e}"

    def get_entry(
        self, entry_id: str
    ) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        指定したIDの記事を取得

        Args:
            entry_id: 記事ID

        Returns:
            (成功フラグ, 記事データ, エラーメッセージ)
        """
        try:
            resp = requests.get(
                f"{self.atom_endpoint}/entry/{entry_id}", auth=self.auth
            )
            if resp.status_code != 200:
                return False, None, f"API エラー: {resp.status_code} - {resp.text}"

            # XMLのパース
            root = ET.fromstring(resp.content)

            # 記事情報の抽出
            title = root.find("atom:title", self.namespaces).text or ""

            # 本文
            content_elem = root.find("atom:content", self.namespaces)
            content_type = content_elem.attrib.get("type", "")
            content = content_elem.text or ""

            # 更新日時
            updated = root.find("atom:updated", self.namespaces).text
            # 作成日時
            created = root.find("atom:published", self.namespaces).text

            # 公開状態（下書きかどうか）
            draft_elem = root.find(".//app:draft", self.namespaces)
            is_draft = draft_elem is not None and draft_elem.text == "yes"

            # カテゴリ
            categories = [
                cat.get("term")
                for cat in root.findall("atom:category", self.namespaces)
            ]

            # 編集用URL
            edit_url = None
            for link in root.findall("atom:link", self.namespaces):
                if link.get("rel") == "edit":
                    edit_url = link.get("href")
                    break

            entry_data = {
                "id": entry_id,
                "title": title,
                "content": content,
                "content_type": content_type,
                "created": created,
                "updated": updated,
                "draft": is_draft,
                "categories": categories,
                "edit_url": edit_url,
            }

            return True, entry_data, None
        except requests.RequestException as e:
            return False, None, f"リクエストエラー: {e}"
        except ET.ParseError as e:
            return False, None, f"XMLパースエラー: {e}"

    def publish_draft(self, entry_id: str) -> Tuple[bool, Optional[str]]:
        """
        下書き記事を公開する

        Args:
            entry_id: 記事ID

        Returns:
            (成功フラグ, エラーメッセージ)
        """
        # まず記事を取得
        success, entry_data, error = self.get_entry(entry_id)
        if not success:
            return False, error

        if not entry_data["draft"]:
            return False, "指定された記事は既に公開されています"

        # 下書きフラグをFalseにして更新
        return self.update_entry(
            entry_id,
            entry_data["title"],
            entry_data["content"],
            entry_data["categories"],
            draft=False,
        )

    def upload_image(self, image_path: str) -> Optional[str]:
        """指定した画像ファイルをはてなフォトライフにアップロードし、[f:id:...] 形式の文字列を返す"""
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
        hatena_id = self.hatena_id
        api_key = self.api_key

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
