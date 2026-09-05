import json
import urllib.request
import xml.etree.ElementTree as ET
import logging
from datetime import datetime, timezone
import re

logger = logging.getLogger("news_feed")

class RegulatoryNewsFeed:
    """
    Ingests free real-time news feeds regarding banking fraud, UPI scams, 
    and RBI regulatory guidelines from Google News RSS and Reddit.
    """
    def __init__(self):
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def fetch_google_news(self, query: str = "rbi banking fraud upi scam") -> list:
        """Fetches and parses structured news elements from Google News RSS."""
        news_items = []
        encoded_query = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-IN&gl=IN&ceid=IN:en"
        
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                xml_data = response.read()
                root = ET.fromstring(xml_data)
                
                # Parse standard RSS items
                for item in root.findall(".//item")[:10]:
                    title = item.find("title").text if item.find("title") is not None else ""
                    link = item.find("link").text if item.find("link") is not None else ""
                    pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                    
                    # Estimate risk score based on high-severity keywords
                    risk_score = self._calculate_risk_score(title)
                    
                    news_items.append({
                        "title": title,
                        "link": link,
                        "source": "GOOGLE_NEWS",
                        "published_at": pub_date,
                        "risk_score": risk_score,
                        "sentiment": "HIGH_RISK" if risk_score > 0.6 else "INFORMATIONAL"
                    })
        except Exception as e:
            logger.warning(f"Failed to fetch Google News RSS feed: {e}")
            
        return news_items

    def fetch_reddit_news(self, query: str = "upi scam bank fraud") -> list:
        """Fetches trending security complaints and scams from Reddit search API."""
        news_items = []
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.reddit.com/r/india/search.json?q={encoded_query}&restrict_sr=1&sort=new&limit=10"
        
        req = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode('utf-8'))
                children = data.get("data", {}).get("children", [])
                
                for child in children:
                    post = child.get("data", {})
                    title = post.get("title", "")
                    permalink = f"https://reddit.com{post.get('permalink', '')}"
                    created_utc = post.get("created_utc", 0)
                    
                    pub_date = datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat()
                    risk_score = self._calculate_risk_score(title + " " + post.get("selftext", ""))
                    
                    news_items.append({
                        "title": title,
                        "link": permalink,
                        "source": "REDDIT",
                        "published_at": pub_date,
                        "risk_score": risk_score,
                        "sentiment": "HIGH_RISK" if risk_score > 0.6 else "INFORMATIONAL"
                    })
        except Exception as e:
            logger.warning(f"Failed to fetch Reddit news feed: {e}")
            
        return news_items

    def get_unified_feed(self) -> list:
        """Combines and returns all active regulatory news streams sorted by threat level."""
        google_news = self.fetch_google_news()
        reddit_news = self.fetch_reddit_news()
        
        all_news = google_news + reddit_news
        # Sort by risk score descending
        all_news.sort(key=lambda x: x["risk_score"], reverse=True)
        return all_news

    def _calculate_risk_score(self, text: str) -> float:
        """Applies dynamic banking security keyword matches to rank news threat severity."""
        text = text.lower()
        score = 0.1
        
        keywords = {
            "arrested": 0.3,
            "scam": 0.25,
            "leak": 0.2,
            "blocked": 0.2,
            "rbi caution": 0.35,
            "fiu": 0.3,
            "npci warning": 0.3,
            "mule account": 0.4,
            "cyber arrest": 0.3,
            "unauthorized": 0.15,
            "compromised": 0.2
        }
        
        for kw, weight in keywords.items():
            if re.search(r'\b' + re.escape(kw) + r'\b', text):
                score += weight
                
        return min(score, 1.0)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    feed = RegulatoryNewsFeed()
    print("Fetching real-time Google News & Reddit updates...")
    items = feed.get_unified_feed()
    for item in items[:5]:
        print(f"\n[{item['source']}] (Risk: {item['risk_score']:.2f} // {item['sentiment']})")
        print(f"  Title: {item['title']}")
        print(f"  Link:  {item['link']}")
