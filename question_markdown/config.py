"""
設定管理モジュール

はてなブログAPIの認証情報や設定を管理します。
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


class Config:
    """設定管理クラス"""

    DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/question_markdown/config.json")
    DEFAULT_CONFIG = {
        "hatena_id": "",
        "blog_id": "",
        "api_key": "",
        "default_output_dir": "posts",
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        設定管理クラスの初期化

        Args:
            config_path: 設定ファイルのパス（省略時はデフォルトパス）
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config = self.DEFAULT_CONFIG.copy()
        self.load()

    def load(self) -> Dict[str, Any]:
        """
        設定ファイルを読み込む

        Returns:
            設定辞書
        """
        config_file = Path(self.config_path)
        if config_file.exists():
            try:
                with open(config_file, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                    self.config.update(loaded_config)
            except (json.JSONDecodeError, IOError) as e:
                print(f"設定ファイルの読み込みに失敗しました: {e}")
        return self.config

    def save(self) -> bool:
        """
        設定ファイルを保存する

        Returns:
            保存成功時はTrue、失敗時はFalse
        """
        config_file = Path(self.config_path)
        try:
            # 親ディレクトリが存在しない場合は作成
            config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            # パーミッションを600に設定（ユーザーのみ読み書き可能）
            os.chmod(config_file, 0o600)
            return True
        except IOError as e:
            print(f"設定ファイルの保存に失敗しました: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        設定値を取得する

        Args:
            key: 設定キー
            default: キーが存在しない場合のデフォルト値

        Returns:
            設定値
        """
        return self.config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """
        設定値を設定する

        Args:
            key: 設定キー
            value: 設定値
        """
        self.config[key] = value

    def is_configured(self) -> bool:
        """
        必須設定が構成されているかチェック

        Returns:
            必須設定が構成されていればTrue
        """
        return all(self.config.get(key) for key in ["hatena_id", "blog_id", "api_key"])

    def get_api_credentials(self) -> Dict[str, str]:
        """
        API認証情報を取得

        Returns:
            API認証情報の辞書
        """
        return {
            "hatena_id": self.config.get("hatena_id", ""),
            "blog_id": self.config.get("blog_id", ""),
            "api_key": self.config.get("api_key", ""),
        }

    def setup_wizard(self) -> bool:
        """
        対話形式で設定を行うウィザード

        Returns:
            設定成功時はTrue
        """
        print("はてなマークダウン管理ツール 設定ウィザード")
        print("----------------------------------------")
        print("はてなブログAPIの認証情報を入力してください。")

        self.config["hatena_id"] = input(
            f"はてなID [{self.config.get('hatena_id', '')}]: "
        ) or self.config.get("hatena_id", "")
        self.config["blog_id"] = input(
            f"ブログID [{self.config.get('blog_id', '')}]: "
        ) or self.config.get("blog_id", "")
        self.config["api_key"] = input(
            f"APIキー [{self.config.get('api_key', '')}]: "
        ) or self.config.get("api_key", "")
        self.config["default_output_dir"] = input(
            f"デフォルト出力ディレクトリ [{self.config.get('default_output_dir', 'posts')}]: "
        ) or self.config.get("default_output_dir", "posts")

        return self.save()


# シングルトンインスタンス
_config_instance = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    設定インスタンスを取得（シングルトン）

    Args:
        config_path: 設定ファイルのパス（省略時はデフォルトパス）

    Returns:
        設定インスタンス
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance
