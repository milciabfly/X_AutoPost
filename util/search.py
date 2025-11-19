def search(client, query, max_results=10):
    tweets = client.search_recent_tweets(query=query, max_results=max_results)
    if tweets.data:
        for tweet in tweets.data:
            print(f"{tweet.author_id}: {tweet.text}")
    return tweets

# おまけで残してるだけです。
# 使いたい場合は改変して使ってください。