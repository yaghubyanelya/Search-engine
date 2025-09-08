import asyncio
import heapq
from typing import Optional, Tuple, Set
from urllib.parse import urlparse
import logging

class URLInfo:
    """Container for URL information"""
    def __init__(self, url: str, priority: float, discovery_time: float):
        self.url = url
        self.priority = priority
        self.discovery_time = discovery_time
        self.domain = urlparse(url).netloc
        
    def __lt__(self, other):
        # Higher priority URLs come first (reverse order for heapq)
        return self.priority > other.priority

class URLFrontier:
    """Priority queue for URLs to be crawled"""
    
    def __init__(self, max_size: int = 1000000):
        self.max_size = max_size
        self.queue = []
        self.seen_urls: Set[str] = set()
        self.lock = asyncio.Lock()
        self.logger = logging.getLogger(__name__)
        
    async def add_url(self, url: str, priority: float = 0.5) -> bool:
        """Add URL to frontier if not already seen"""
        async with self.lock:
            if url in self.seen_urls:
                return False
            
            if len(self.queue) >= self.max_size:
                self.logger.warning("URL frontier at maximum capacity")
                return False
            
            import time
            url_info = URLInfo(url, priority, time.time())
            heapq.heappush(self.queue, url_info)
            self.seen_urls.add(url)
            
            return True
    
    async def get_next_url(self) -> Optional[Tuple[str, float]]:
        """Get next URL to crawl with its priority"""
        async with self.lock:
            if not self.queue:
                return None
            
            url_info = heapq.heappop(self.queue)
            return url_info.url, url_info.priority
    
    def size(self) -> int:
        """Get current queue size"""
        return len(self.queue)
    
    def is_empty(self) -> bool:
        """Check if frontier is empty"""
        return len(self.queue) == 0
