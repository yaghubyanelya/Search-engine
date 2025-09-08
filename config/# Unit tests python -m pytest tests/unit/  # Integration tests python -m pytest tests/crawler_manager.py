

```python
import asyncio
import aiohttp
import logging
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
from typing import List, Set, Optional
import yaml
import time
from .url_frontier import URLFrontier
from .robots_parser import RobotsParser
from .content_parser import ContentParser
from .duplicate_detector import DuplicateDetector
from .politeness_manager import PolitenessManager

@dataclass
class CrawledPage:
    url: str
    title: str
    content: str
    links: List[str]
    timestamp: float
    status_code: int
    content_type: str

class CrawlerManager:
    def __init__(self, config_path: str):
        """Initialize crawler with configuration"""
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.url_frontier = URLFrontier(max_size=self.config['crawler']['max_queue_size'])
        self.robots_parser = RobotsParser()
        self.content_parser = ContentParser()
        self.duplicate_detector = DuplicateDetector()
        self.politeness_manager = PolitenessManager(
            delay_ms=self.config['crawler']['delay_ms']
        )
        
        self.crawled_urls: Set[str] = set()
        self.session: Optional[aiohttp.ClientSession] = None
        self.logger = logging.getLogger(__name__)
        
        # Statistics
        self.pages_crawled = 0
        self.start_time = time.time()
        
    async def start_crawling(self, seed_urls: List[str]) -> None:
        """Start the crawling process with seed URLs"""
        self.logger.info(f"Starting crawler with {len(seed_urls)} seed URLs")
        
        # Add seed URLs to frontier
        for url in seed_urls:
            await self.url_frontier.add_url(url, priority=1.0)
        
        # Create HTTP session
        connector = aiohttp.TCPConnector(limit=self.config['crawler']['max_connections'])
        timeout = aiohttp.ClientTimeout(total=self.config['crawler']['timeout'])
        self.session = aiohttp.ClientSession(connector=connector, timeout=timeout)
        
        try:
            # Start crawler workers
            tasks = []
            for i in range(self.config['crawler']['max_threads']):
                task = asyncio.create_task(self._crawler_worker(f"worker-{i}"))
                tasks.append(task)
            
            # Wait for completion or max pages limit
            await asyncio.gather(*tasks)
            
        finally:
            if self.session:
                await self.session.close()
            
        self.logger.info(f"Crawling completed. Total pages: {self.pages_crawled}")
    
    async def _crawler_worker(self, worker_id: str) -> None:
        """Individual crawler worker thread"""
        self.logger.info(f"Starting crawler worker: {worker_id}")
        
        while self.pages_crawled < self.config['crawler']['max_pages']:
            try:
                # Get next URL from frontier
                url_info = await self.url_frontier.get_next_url()
                if not url_info:
                    await asyncio.sleep(1)
                    continue
                
                url, priority = url_info
                
                # Skip if already crawled
                if url in self.crawled_urls:
                    continue
                
                # Check robots.txt
                if not await self.robots_parser.can_crawl(url, 'SearchBot'):
                    self.logger.debug(f"Robots.txt disallows crawling: {url}")
                    continue
                
                # Apply politeness delay
                domain = urlparse(url).netloc
                await self.politeness_manager.wait_for_domain(domain)
                
                # Crawl the page
                crawled_page = await self._crawl_page(url)
                if crawled_page:
                    self.crawled_urls.add(url)
                    self.pages_crawled += 1
                    
                    # Process extracted links
                    await self._process_extracted_links(crawled_page.links, url)
                    
                    # Store crawled page (implement based on your storage)
                    await self._store_crawled_page(crawled_page)
                    
                    self.logger.info(f"Crawled ({self.pages_crawled}): {url}")
                
            except Exception as e:
                self.logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(5)
    
    async def _crawl_page(self, url: str) -> Optional[CrawledPage]:
        """Crawl a single page"""
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    return None
                
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('text/html'):
                    return None
                
                html_content = await response.text()
                
                # Parse content
                parsed_content = self.content_parser.parse_html(html_content, url)
                
                # Check for duplicates
                if self.duplicate_detector.is_duplicate(parsed_content['content']):
                    self.logger.debug(f"Duplicate content detected: {url}")
                    return None
                
                return CrawledPage(
                    url=url,
                    title=parsed_content['title'],
                    content=parsed_content['content'],
                    links=parsed_content['links'],
                    timestamp=time.time(),
                    status_code=response.status,
                    content_type=content_type
                )
                
        except Exception as e:
            self.logger.error(f"Error crawling {url}: {e}")
            return None
    
    async def _process_extracted_links(self, links: List[str], base_url: str) -> None:
        """Process and add extracted links to frontier"""
        for link in links:
            try:
                # Convert relative URLs to absolute
                absolute_url = urljoin(base_url, link)
                
                # Basic URL validation
                parsed = urlparse(absolute_url)
                if parsed.scheme not in ['http', 'https']:
                    continue
                
                # Calculate priority (simple heuristic)
                priority = self._calculate_url_priority(absolute_url, base_url)
                
                await self.url_frontier.add_url(absolute_url, priority)
                
            except Exception as e:
                self.logger.debug(f"Error processing link {link}: {e}")
    
    def _calculate_url_priority(self, url: str, referring_url: str) -> float:
        """Calculate crawl priority for URL (0.0 to 1.0)"""
        priority = 0.5  # Base priority
        
        # Higher priority for same domain
        url_domain = urlparse(url).netloc
        ref_domain = urlparse(referring_url).netloc
        if url_domain == ref_domain:
            priority += 0.2
        
        # Lower priority for deep URLs
        path_depth = len(urlparse(url).path.strip('/').split('/'))
        priority -= path_depth * 0.05
        
        return max(0.0, min(1.0, priority))
    
    async def _store_crawled_page(self, page: CrawledPage) -> None:
        """Store crawled page (implement based on your storage system)"""
        # This would typically store to database or file system
        # For now, just log the action
        self.logger.debug(f"Storing page: {page.title} ({len(page.content)} chars)")
        
        # Example: Could store to MongoDB, PostgreSQL, or file system
        # await self.storage.store_page(page)
    
    def get_crawl_statistics(self) -> dict:
        """Get current crawling statistics"""
        elapsed_time = time.time() - self.start_time
        crawl_rate = self.pages_crawled / elapsed_time if elapsed_time > 0 else 0
        
        return {
            'pages_crawled': self.pages_crawled,
            'elapsed_time': elapsed_time,
            'crawl_rate': crawl_rate,
            'queue_size': self.url_frontier.size(),
            'unique_urls': len(self.crawled_urls)
        }

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Web Crawler')
    parser.add_argument('--config', default='config/development.yaml', 
                       help='Configuration file path')
    parser.add_argument('--seeds', nargs='+', 
                       default=['https://example.com'],
                       help='Seed URLs to start crawling')
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Start crawler
    crawler = CrawlerManager(args.config)
    asyncio.run(crawler.start_crawling(args.seeds))
