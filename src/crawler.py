import asyncio
import aiohttp
import logging
from typing import List, Set
from urllib.parse import urljoin, urlparse
from dataclasses import dataclass
from datetime import datetime, timedelta

@dataclass
class CrawlResult:
    url: str
    status: int
    content: str
    timestamp: datetime
    links: Set[str]

class DistributedCrawler:
    def __init__(self):
        self.visited_urls: Set[str] = set()
        self.rate_limits = {}
        self.session = None
        self.logger = logging.getLogger(__name__)

    async def setup(self):
        self.session = aiohttp.ClientSession()

    async def cleanup(self):
        if self.session:
            await self.session.close()

    def _check_rate_limit(self, domain: str) -> bool:
        now = datetime.now()
        if domain in self.rate_limits:
            last_crawl, count = self.rate_limits[domain]
            if now - last_crawl < timedelta(seconds=60):
                if count >= 10:  # Max 10 requests per minute per domain
                    return False
                self.rate_limits[domain] = (last_crawl, count + 1)
            else:
                self.rate_limits[domain] = (now, 1)
        else:
            self.rate_limits[domain] = (now, 1)
        return True

    def _extract_links(self, content: str, base_url: str) -> Set[str]:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(content, 'html.parser')
        links = set()
        for link in soup.find_all('a'):
            href = link.get('href')
            if href:
                absolute_url = urljoin(base_url, href)
                if self._is_valid_url(absolute_url):
                    links.add(absolute_url)
        return links

    def _is_valid_url(self, url: str) -> bool:
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and \
                   result.scheme in ['http', 'https']
        except:
            return False

    async def crawl_url(self, url: str) -> CrawlResult:
        if url in self.visited_urls:
            return None

        domain = urlparse(url).netloc
        if not self._check_rate_limit(domain):
            self.logger.warning(f'Rate limit reached for domain: {domain}')
            return None

        try:
            async with self.session.get(url, timeout=10) as response:
                content = await response.text()
                self.visited_urls.add(url)
                links = self._extract_links(content, url)
                return CrawlResult(
                    url=url,
                    status=response.status,
                    content=content,
                    timestamp=datetime.now(),
                    links=links
                )
        except Exception as e:
            self.logger.error(f'Error crawling {url}: {str(e)}')
            return None

    async def crawl_batch(self, urls: List[str], max_concurrent: int = 5) -> List[CrawlResult]:
        tasks = []
        results = []
        
        for i in range(0, len(urls), max_concurrent):
            batch = urls[i:i + max_concurrent]
            tasks = [self.crawl_url(url) for url in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            results.extend([r for r in batch_results if r is not None])
        
        return results

    async def start_crawling(self, seed_urls: List[str], max_pages: int = 1000):
        await self.setup()
        try:
            to_crawl = seed_urls
            results = []

            while to_crawl and len(results) < max_pages:
                batch_results = await self.crawl_batch(to_crawl[:10])
                results.extend(batch_results)
                
                # Add new URLs to crawl
                new_urls = set()
                for result in batch_results:
                    new_urls.update(result.links)
                
                to_crawl = list(new_urls - self.visited_urls)
                self.logger.info(f'Crawled: {len(results)}, Queue: {len(to_crawl)}')

            return results
        finally:
            await self.cleanup()
