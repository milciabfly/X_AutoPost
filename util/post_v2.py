import os
import time
import mimetypes
import shutil
import tempfile
import random
import string
from typing import List, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from util.auth import get_oauth1


CHUNK_SIZE = 4 * 1024 * 1024
SIMPLE_UPLOAD_LIMIT = 5 * 1024 * 1024


def _generate_random_filename(original_path: str) -> str:
    """
    元のファイル名からランダムなファイル名を生成
    拡張子は維持される
    
    Args:
        original_path: 元のファイルパス
    
    Returns:
        ランダムな文字列 + 元の拡張子
    """
    _, ext = os.path.splitext(original_path)
    random_name = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    return f"{random_name}{ext}"


def _create_temp_copy_with_random_name(original_path: str) -> str:
    """
    元のファイルを一時ディレクトリにランダムなファイル名でコピー
    
    Args:
        original_path: 元のファイルパス
    
    Returns:
        コピーされたファイルのパス（一時ファイル）
    """
    random_filename = _generate_random_filename(original_path)
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, random_filename)
    shutil.copy2(original_path, temp_path)
    return temp_path


def _get_session_with_retry():
    """リトライ機能付きのHTTPセッションを作成"""
    session = requests.Session()
    retry = Retry(
        total=3,
        read=3,
        connect=3,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


def _simple_upload(oauth, file_path: str) -> str:
    """
    5MB以下の画像用シンプルアップロード（チャンク不要）
    
    Args:
        oauth: OAuth1認証オブジェクト
        file_path: アップロードするファイルパス
    
    Returns:
        media_id_string
    """
    url = "https://upload.twitter.com/1.1/media/upload.json"
    session = _get_session_with_retry()
    
    with open(file_path, 'rb') as f:
        files = {'media': f}
        r = session.post(url, files=files, auth=oauth, timeout=60)
        r.raise_for_status()
        return r.json()["media_id_string"]


def _init_upload(oauth, total_bytes: int, media_type: str, media_category: Optional[str] = None):
    """
    チャンクアップロードの初期化（INIT）
    
    Args:
        oauth: OAuth1認証オブジェクト
        total_bytes: ファイルの総バイト数
        media_type: MIMEタイプ
        media_category: メディアカテゴリ（tweet_image, tweet_videoなど）
    
    Returns:
        media_id_string
    """
    url = "https://upload.twitter.com/1.1/media/upload.json"
    data = {"command": "INIT", "total_bytes": str(total_bytes), "media_type": media_type}
    if media_category:
        data["media_category"] = media_category
    session = _get_session_with_retry()
    r = session.post(url, data=data, auth=oauth, timeout=60)
    r.raise_for_status()
    return r.json()["media_id_string"]


def _append_upload(oauth, media_id: str, segment_index: int, chunk: bytes):
    """
    チャンクアップロードのデータ追加（APPEND）
    
    Args:
        oauth: OAuth1認証オブジェクト
        media_id: メディアID
        segment_index: チャンクのインデックス番号
        chunk: アップロードするバイナリデータ
    
    Returns:
        HTTPステータスコード
    """
    url = "https://upload.twitter.com/1.1/media/upload.json"
    files = {"media": ("blob", chunk)}
    data = {"command": "APPEND", "media_id": media_id, "segment_index": str(segment_index)}
    session = _get_session_with_retry()
    r = session.post(url, data=data, files=files, auth=oauth, timeout=120)
    r.raise_for_status()
    return r.status_code


def _finalize_upload(oauth, media_id: str):
    """
    チャンクアップロードの完了処理（FINALIZE）
    
    Args:
        oauth: OAuth1認証オブジェクト
        media_id: メディアID
    
    Returns:
        APIレスポンスのJSON
    """
    url = "https://upload.twitter.com/1.1/media/upload.json"
    data = {"command": "FINALIZE", "media_id": media_id}
    session = _get_session_with_retry()
    r = session.post(url, data=data, auth=oauth, timeout=60)
    r.raise_for_status()
    return r.json()


def _check_status(oauth, media_id: str, interval=5):
    """
    メディア処理のステータスチェック（STATUS）
    動画などの非同期処理完了を待機
    
    Args:
        oauth: OAuth1認証オブジェクト
        media_id: メディアID
        interval: デフォルトのチェック間隔（秒）
    
    Returns:
        APIレスポンスのJSON
    """
    url = "https://upload.twitter.com/1.1/media/upload.json"
    params = {"command": "STATUS", "media_id": media_id}
    session = _get_session_with_retry()
    while True:
        r = session.get(url, params=params, auth=oauth, timeout=60)
        r.raise_for_status()
        j = r.json()
        proc = j.get("processing_info")
        if not proc:
            return j
        state = proc.get("state")
        if state == "succeeded":
            return j
        if state == "failed":
            raise RuntimeError(f"メディア処理が失敗しました: {proc}")
        # pending または in_progress
        check_after = proc.get("check_after_secs", interval)
        time.sleep(check_after)


def upload_media_v2(file_path: str):
    """
    メディアをアップロードし、media_id_string を返す
    
    アップロード時にファイル名をランダム化（元ファイルは変更しない）
    - 5MB以下の画像: シンプルアップロード（チャンク不要）
    - 5MB超 or 動画: チャンクアップロード（INIT/APPEND/FINALIZE）
    """
    oauth = get_oauth1()
    
    # ランダムなファイル名で一時コピーを作成
    temp_file = _create_temp_copy_with_random_name(file_path)
    
    try:
        size = os.path.getsize(temp_file)
        mime, _ = mimetypes.guess_type(temp_file)
        if not mime:
            mime = "application/octet-stream"
        
        is_video = mime.startswith("video")
        
        # 小さい画像はシンプルアップロード（最大4枚まで高速処理）
        if not is_video and size <= SIMPLE_UPLOAD_LIMIT:
            return _simple_upload(oauth, temp_file)
        
        # 大きいファイルや動画はチャンクアップロード
        media_category = None
        if is_video:
            media_category = "tweet_video"
        elif mime.startswith("image"):
            media_category = "tweet_image"

        media_id = _init_upload(oauth, size, mime, media_category)

        # チャンクを分割してアップロード
        with open(temp_file, "rb") as f:
            segment_index = 0
            while True:
                chunk = f.read(CHUNK_SIZE)
                if not chunk:
                    break
                _append_upload(oauth, media_id, segment_index, chunk)
                segment_index += 1

        res = _finalize_upload(oauth, media_id)
        # 動画の場合は非同期処理が発生する可能性がある
        if "processing_info" in res:
            _check_status(oauth, media_id)
        return media_id
    
    finally:
        # 一時ファイルを削除
        if os.path.exists(temp_file):
            os.remove(temp_file)


def post_v2_with_media(text: str, media_ids: List[str], dry_run: bool = False):
    """
    Twitter API v2でメディア付きツイートを作成
    
    Args:
        text: ツイート本文
        media_ids: メディアIDのリスト（media_id_strings）
        dry_run: テストモード（実際には投稿しない）
    
    Returns:
        APIレスポンスのJSON（dry_runの場合はNone）
    """
    if dry_run:
        print("DRY RUN: メディア付きツイート作成:", media_ids)
        return None
    oauth = get_oauth1()
    url = "https://api.twitter.com/2/tweets"
    payload = {"text": text, "media": {"media_ids": media_ids}}
    session = _get_session_with_retry()
    r = session.post(url, json=payload, auth=oauth, timeout=60)
    r.raise_for_status()
    return r.json()


def post(client, text: str, image_paths: Optional[List[str]] = None, dry_run: bool = False):
    """
    ツイート投稿のエントリポイント
    画像があればv2のチャンクアップロードを経て投稿する
    
    Args:
        client: Tweepy Client（メディアなしツイート用）
        text: ツイート本文
        image_paths: 画像ファイルパスのリスト（最大4枚）
        dry_run: テストモード（実際には投稿しない）
    
    Returns:
        APIレスポンス（dry_runの場合はNone）
    """
    if dry_run:
        print("DRY RUN: ツイート本文=", text)
        if image_paths:
            print("DRY RUN: 画像=", image_paths)
        return None

    media_ids: List[str] = []
    if image_paths:
        for p in image_paths[:4]:  # 最大4枚まで
            if not os.path.isfile(p):
                continue
            media_id = upload_media_v2(p)
            media_ids.append(media_id)

    if media_ids:
        return post_v2_with_media(text, media_ids, dry_run=dry_run)

    # メディアなしの場合はTweepy Clientで投稿
    response = client.create_tweet(text=text)
    return response
