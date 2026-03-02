#!/usr/bin/env python3
"""
App Review Sentinel - Mobil Uygulama Yorum Takip Sistemi

App Store ve Google Play Store'dan uygulama yorumlarını çeker,
negatif yorumları tespit eder ve bildirim gönderir.
"""

import os
import json
import ssl
import urllib.request
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict


@dataclass
class Review:
    """Yorum veri modeli"""
    id: str
    platform: str
    app_id: str
    author: str
    rating: int
    title: str
    content: str
    date: str
    version: str
    sentiment: str = "neutral"
    
    def to_dict(self) -> Dict:
        return asdict(self)


class AppStoreClient:
    """App Store yorumlarını çeken client"""
    
    def __init__(self, country: str = "us"):
        self.country = country
        self.base_url = f"https://itunes.apple.com/{country}/rss/customerreviews"
    
    def fetch_reviews(self, app_id: str, limit: int = 50) -> List[Review]:
        """App Store'dan yorumları çek"""
        reviews = []
        url = f"{self.base_url}/id={app_id}/sortBy=mostRecent/json"
        
        try:
            ctx = ssl.create_default_context()
            with urllib.request.urlopen(url, context=ctx, timeout=30) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            entries = data.get('feed', {}).get('entry', [])
            if not isinstance(entries, list):
                entries = [entries] if entries else []
            
            for entry in entries[:limit]:
                try:
                    review = Review(
                        id=str(entry.get('id', {}).get('label', '')),
                        platform='ios',
                        app_id=app_id,
                        author=entry.get('author', {}).get('name', {}).get('label', 'Anonymous'),
                        rating=int(entry.get('im:rating', {}).get('label', 3)),
                        title=entry.get('title', {}).get('label', ''),
                        content=entry.get('content', {}).get('label', ''),
                        date=entry.get('updated', {}).get('label', datetime.now().isoformat()),
                        version=entry.get('im:version', {}).get('label', 'unknown')
                    )
                    review.sentiment = self._analyze_sentiment(review.rating, review.content)
                    reviews.append(review)
                except Exception as e:
                    print(f"Error parsing review: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error fetching App Store reviews: {e}")
        
        return reviews
    
    def _analyze_sentiment(self, rating: int, content: str) -> str:
        """Basit sentiment analizi"""
        negative_keywords = ['bug', 'crash', 'broken', 'waste', 'terrible', 'awful', 
                           'hate', 'sucks', 'useless', 'disappointed', 'problem',
                           'error', 'fail', 'slow', 'freeze', 'buggy', 'garbage']
        
        content_lower = content.lower()
        has_negative_words = any(kw in content_lower for kw in negative_keywords)
        
        if rating <= 2 or (rating == 3 and has_negative_words):
            return 'negative'
        elif rating >= 4:
            return 'positive'
        return 'neutral'


class GooglePlayClient:
    """Google Play Store yorumlarını çeken client"""
    
    def fetch_reviews(self, app_id: str, limit: int = 50) -> List[Review]:
        """Google Play Store'dan yorumları çek"""
        print(f"Note: Google Play scraping requires google-play-scraper package for {app_id}")
        return []


class NotificationService:
    """Bildirim servisi"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url
    
    def send_alert(self, reviews: List[Review], app_name: str) -> bool:
        """Negatif yorumlar için alert gönder"""
        if not self.webhook_url or not reviews:
            return False
        
        negative_reviews = [r for r in reviews if r.sentiment == 'negative']
        
        if not negative_reviews:
            print(f"No negative reviews found for {app_name}")
            return True
        
        message = self._format_message(negative_reviews, app_name)
        
        try:
            payload = json.dumps({
                "text": message,
                "username": "App Review Sentinel",
                "icon_emoji": ":warning:"
            }).encode('utf-8')
            
            req = urllib.request.Request(
                self.webhook_url,
                data=payload,
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            
            with urllib.request.urlopen(req, timeout=30) as response:
                return response.status == 200
                
        except Exception as e:
            print(f"Error sending notification: {e}")
            return False
    
    def _format_message(self, reviews: List[Review], app_name: str) -> str:
        """Slack/Discord formatında mesaj oluştur"""
        lines = [
            f"🚨 *{app_name}* - {len(reviews)} New Negative Review(s)",
            "",
        ]
        
        for review in reviews[:5]:
            stars = "⭐" * review.rating + "☆" * (5 - review.rating)
            lines.extend([
                f"*{stars}* by {review.author}",
                f"Platform: {review.platform.upper()} | Version: {review.version}",
                f"> {review.content[:200]}{'...' if len(review.content) > 200 else ''}",
                ""
            ])
        
        return "\n".join(lines)


class ReviewStorage:
    """Yorumları saklama servisi"""
    
    def __init__(self, storage_path: str = "reviews.json"):
        self.storage_path = storage_path
        self.seen_ids = self._load_seen_ids()
    
    def _load_seen_ids(self) -> set:
        """Daha önce görülen yorum ID'lerini yükle"""
        try:
            if os.path.exists(self.storage_path):
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    return set(data.get('seen_ids', []))
        except Exception as e:
            print(f"Error loading storage: {e}")
        return set()
    
    def get_new_reviews(self, reviews: List[Review]) -> List[Review]:
        """Yeni yorumları filtrele"""
        new_reviews = []
        for review in reviews:
            if review.id not in self.seen_ids:
                new_reviews.append(review)
                self.seen_ids.add(review.id)
        return new_reviews
    
    def save(self):
        """Görülen ID'leri kaydet"""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump({'seen_ids': list(self.seen_ids)}, f)
        except Exception as e:
            print(f"Error saving storage: {e}")


def main():
    """Ana fonksiyon"""
    app_configs = []
    
    configs_env = os.getenv('APP_CONFIGS', '')
    if configs_env:
        for config in configs_env.split(','):
            parts = config.strip().split(':')
            if len(parts) >= 2:
                app_configs.append({
                    'name': parts[0],
                    'ios_id': parts[1] if parts[1] else None,
                    'android_id': parts[2] if len(parts) > 2 and parts[2] else None
                })
    
    if not app_configs:
        print("No app configs found. Set APP_CONFIGS env var.")
        print("Format: app_name:ios_app_id:android_package")
        return
    
    webhook_url = os.getenv('WEBHOOK_URL')
    storage_path = os.getenv('STORAGE_PATH', 'reviews.json')
    
    storage = ReviewStorage(storage_path)
    notifier = NotificationService(webhook_url)
    app_store = AppStoreClient()
    play_store = GooglePlayClient()
    
    print(f"Checking {len(app_configs)} app(s)...")
    
    for app_config in app_configs:
        app_name = app_config['name']
        print(f"\nChecking {app_name}...")
        
        all_reviews = []
        
        if app_config.get('ios_id'):
            ios_reviews = app_store.fetch_reviews(app_config['ios_id'])
            print(f"  Found {len(ios_reviews)} iOS reviews")
            all_reviews.extend(ios_reviews)
        
        if app_config.get('android_id'):
            android_reviews = play_store.fetch_reviews(app_config['android_id'])
            print(f"  Found {len(android_reviews)} Android reviews")
            all_reviews.extend(android_reviews)
        
        new_reviews = storage.get_new_reviews(all_reviews)
        print(f"  {len(new_reviews)} new reviews")
        
        if new_reviews:
            negative_count = len([r for r in new_reviews if r.sentiment == 'negative'])
            print(f"  {negative_count} negative reviews")
            
            if negative_count > 0:
                notifier.send_alert(new_reviews, app_name)
    
    storage.save()
    print("\nDone!")


if __name__ == "__main__":
    main()
