import requests
from bs4 import BeautifulSoup
import urllib.parse

# We use a search query for 'Artificial Intelligence' which mimics the AI section
# but is much more stable than a Topic ID hash.
QUERY = "Artificial Intelligence"
encoded_query = urllib.parse.quote(QUERY)

# 2026 Updated RSS URL Format
RSS_URL = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

def get_ai_news():
    # Adding a more robust User-Agent to avoid the '400' filter
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept": "application/xml, text/xml, */*"
    }
    
    print(f"Bypassing the algorithm... Fetching AI News via RSS.")
    
    try:
        response = requests.get(RSS_URL, headers=headers, timeout=10)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, features="xml")
            items = soup.find_all('item')
            
            print(f"✅ Found {len(items)} raw AI headlines.\n")
            
            for i, item in enumerate(items[:10]):
                title = item.title.text
                link = item.link.text
                # Removing the ' - Source Name' from the title for a cleaner look
                clean_title = title.split(" - ")[0]
                source = title.split(" - ")[-1] if " - " in title else "Unknown"
                
                print(f"[{i+1}] {clean_title}")
                print(f"    📰 Source: {source}")
                print(f"    🔗 {link}\n")
        else:
            print(f"❌ Still getting a {response.status_code}. Google might be throttling this IP.")
            
    except Exception as e:
        print(f"❌ An error occurred: {e}")

if __name__ == "__main__":
    get_ai_news()