from googlenewsdecoder import new_decoderv1
from newspaper import Article

url = "https://news.google.com/rss/articles/CBMiJWh0dHBzOi8vd3d3LmJiYy5jb20vbmV3cy9hcnRpY2xlcy9jOXdyM2Q1M25qb2_SAQA?oc=5"
result = new_decoderv1(url)
print("Decoded URL:", result)

if result.get("status"):
    article = Article(result["decoded_url"])
    article.download()
    article.parse()
    print("Top image:", article.top_image)
    print("Snippet:", article.text[:200])
