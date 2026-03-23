import requests
from bs4 import BeautifulSoup
import hashlib
import json
import multiprocessing as mp

class DistributedCrawler:
    def __init__(self, seed_urls, max_depth=3, num_workers=4):
        self.seed_urls = seed_urls
        self.max_depth = max_depth
        self.num_workers = num_workers
        self.crawl_queue = mp.Queue()
        self.content_queue = mp.Queue()
        self.visited_urls = set()
        self.crawl_depth = 0
        
    def crawl(self):
        # Add seed URLs to the queue
        for url in self.seed_urls:
            self.crawl_queue.put((url, 0))
        
        # Start worker processes
        processes = []
        for _ in range(self.num_workers):
            p = mp.Process(target=self.worker)
            p.start()
            processes.append(p)
        
        # Wait for all workers to finish
        for p in processes:
            p.join()
        
        # Process the content queue
        while not self.content_queue.empty():
            url, content = self.content_queue.get()
            self.process_content(url, content)
    
    def worker(self):
        while True:
            try:
                url, depth = self.crawl_queue.get(block=False)
            except mp.queues.Empty:
                return
            
            if depth > self.max_depth:
                continue
            
            if url in self.visited_urls:
                continue
            
            self.visited_urls.add(url)
            content = self.fetch_content(url)
            self.content_queue.put((url, content))
            
            for link in self.extract_links(content):
                self.crawl_queue.put((link, depth + 1))
    
    def fetch_content(self, url):
        response = requests.get(url)
        return response.text
    
    def extract_links(self, content):
        soup = BeautifulSoup(content, 'html.parser')
        return [link.get('href') for link in soup.find_all('a')]
    
    def process_content(self, url, content):
        # Implement content analysis logic here
        print(f'Processed content from {url}')
        # Example: Calculate a content hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        print(f'Content hash: {content_hash}')
        # Save the content or perform other actions
        with open(f'{content_hash}.json', 'w') as f:
            json.dump({'url': url, 'content': content}, f)
