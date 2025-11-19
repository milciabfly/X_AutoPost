"""
設定ファイルの読み書き管理
"""
import os
import json


DATA_DIR = os.path.join(os.getcwd(), "data")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")


def ensure_data_dir():
    """dataディレクトリが存在しない場合は作成"""
    os.makedirs(DATA_DIR, exist_ok=True)


def load_config():
    """設定ファイルを読み込む。存在しない場合は空の辞書を返す"""
    ensure_data_dir()
    if os.path.isfile(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_config(cfg):
    """設定をJSONファイルに保存"""
    ensure_data_dir()
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
