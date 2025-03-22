"""
はてなブログAPI連携モジュール

はてなブログAtomPub APIを使用して記事の取得、投稿、更新を行います。
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple, Any
import requests
from xml.sax.saxutils import escape


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
            limit: 取得する記事数の上限

        Returns:
            (成功フラグ, 記事リスト, エラーメッセージ)
        """
        try:
            resp = requests.get(f"{self.atom_endpoint}/entry", auth=self.auth)
            if resp.status_code != 200:
                return False, None, f"API エラー: {resp.status_code} - {resp.text}"

            # XMLのパース
            root = ET.fromstring(resp.content)
            entries = []

            # 各記事の情報を抽出
            for entry in root.findall("atom:entry", self.namespaces):
                # entry_idは<id>タグに格納されており、例: "tag:blog.hatena.ne.jp,2007:entry/12345678901234567"
                raw_id = entry.find("atom:id", self.namespaces).text
                # "entry/"以降を抽出する
                entry_id = raw_id.split("entry/")[-1] if "entry/" in raw_id else raw_id

                title = entry.find("atom:title", self.namespaces).text or ""

                # 更新日時
                updated = entry.find("atom:updated", self.namespaces).text

                # 公開状態（下書きかどうか）
                draft_elem = entry.find(".//app:draft", self.namespaces)
                is_draft = draft_elem is not None and draft_elem.text == "yes"

                # カテゴリ
                categories = [
                    cat.get("term")
                    for cat in entry.findall("atom:category", self.namespaces)
                ]

                # 編集用URL
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

                if limit and len(entries) >= limit:
                    break

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
