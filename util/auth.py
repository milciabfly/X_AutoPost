import tweepy
import os
from dotenv import load_dotenv, set_key

load_dotenv()

def get_client():
    """OAuth 1.0a認証のClientを返す（読み取り、投稿用）"""
    client = tweepy.Client(
        bearer_token=os.getenv("BEARER_TOKEN"),
        consumer_key=os.getenv("CONSUMER_KEY"),
        consumer_secret=os.getenv("CONSUMER_SECRET"),
        access_token=os.getenv("ACCESS_TOKEN"),
        access_token_secret=os.getenv("ACCESS_TOKEN_SECRET")
    )
    return client


def get_api():
    """tweepy.API (v1.1) を返す。メディアアップロードやいいねに使用する。"""
    consumer_key = os.getenv("CONSUMER_KEY")
    consumer_secret = os.getenv("CONSUMER_SECRET")
    access_token = os.getenv("ACCESS_TOKEN")
    access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")
    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        raise RuntimeError("APIキーが.envに設定されていません。get_api()にはCONSUMER_KEY, CONSUMER_SECRET, ACCESS_TOKEN, ACCESS_TOKEN_SECRETが必要です")

    # OAuth1 ハンドラを作成して API を返す
    auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)
    api = tweepy.API(auth)
    return api


def get_oauth1():
    """requests向けのOAuth1オブジェクトを返す（requests_oauthlib 用）"""
    from requests_oauthlib import OAuth1

    consumer_key = os.getenv("CONSUMER_KEY")
    consumer_secret = os.getenv("CONSUMER_SECRET")
    access_token = os.getenv("ACCESS_TOKEN")
    access_token_secret = os.getenv("ACCESS_TOKEN_SECRET")
    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        raise RuntimeError("OAuth1情報が不足しています: CONSUMER_KEY/CONSUMER_SECRET/ACCESS_TOKEN/ACCESS_TOKEN_SECRET を.envに設定してください")
    return OAuth1(consumer_key, consumer_secret, access_token, access_token_secret)
