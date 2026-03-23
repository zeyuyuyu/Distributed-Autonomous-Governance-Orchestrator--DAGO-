import requests
import json
from typing import List, Dict
from collections import deque

class DecentralizedCrawler:
    def __init__(self, seed_urls: List[str], max_depth: int = 3):
        self.seed_urls = seed_urls
        self.max_depth = max_depth
        self.visited_urls = set()
        self.url_queue = deque(seed_urls)

    def crawl(self) -> List[Dict[str, any]]:
        results = []
        while self.url_queue and len(self.visited_urls) < self.max_depth:
            url = self.url_queue.popleft()
            if url not in self.visited_urls:
                self.visited_urls.add(url)
                try:
                    response = requests.get(url)
                    response.raise_for_status()
                    data = response.json()
                    results.append(data)
                    for link in self.extract_links(data):
                        self.url_queue.append(link)
                except (requests.exceptions.RequestException, ValueError):
                    pass
        return results

    def extract_links(self, data: Dict[str, any]) -> List[str]:
        links = []
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, str) and value.startswith('http'):
                    links.append(value)
                elif isinstance(value, list):
                    for item in value:
                        links.extend(self.extract_links(item))
                elif isinstance(value, dict):
                    links.extend(self.extract_links(value))
        elif isinstance(data, list):
            for item in data:
                links.extend(self.extract_links(item))
        return links
