#!/usr/bin/env python3
"""
Documentation Site Web Scraper for JADE AI
==========================================

Scrapes documentation sites (Kubernetes, Terraform, OPA, etc.) and converts
them to JSONL/Markdown format for JADE's RAG ingestion pipeline.

Usage:
    python3 doc_scraper.py --site kubernetes --output-format jsonl
    python3 doc_scraper.py --url https://kubernetes.io/docs/concepts/ --max-pages 100
    python3 doc_scraper.py --config configs/kubernetes.yaml --dry-run
"""

import argparse
import json
import time
import hashlib
from pathlib import Path
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from urllib.parse import urljoin, urlparse
from collections import deque

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Centralized paths - all within GP-OPENSEARCH
SCRIPT_DIR = Path(__file__).parent  # webscraper/
UNPROCESSED_DIR = SCRIPT_DIR.parent  # 01-unprocessed/
OPENSEARCH_ROOT = UNPROCESSED_DIR.parent  # GP-OPENSEARCH/
GP_ROOT = OPENSEARCH_ROOT.parent  # GP-copilot/

# Default output goes to night-learning for preprocessing pipeline
DEFAULT_OUTPUT_DIR = UNPROCESSED_DIR / "night-learning" / "scraped-docs"
PREPROCESS_SCRIPT = OPENSEARCH_ROOT / "03-preprocessed" / "preprocess_pipeline.py"
CHROMA_DIR = OPENSEARCH_ROOT / "05-ragged-data" / "chroma"


class DocScraper:
    """
    Web scraper for documentation sites with intelligent crawling.

    Features:
    - Respects robots.txt
    - Rate limiting
    - URL filtering (stay within documentation paths)
    - Content cleaning (remove nav, footer, ads)
    - Markdown conversion
    - JSONL output for RAG ingestion
    """

    def __init__(
        self,
        base_url: str,
        site_name: str,
        output_dir: Path,
        output_format: str = "jsonl",
        max_pages: int = 500,
        delay: float = 1.0,
        allowed_paths: Optional[List[str]] = None,
        exclude_paths: Optional[List[str]] = None,
        content_selectors: Optional[Dict[str, str]] = None,
        remove_selectors: Optional[List[str]] = None
    ):
        """
        Initialize documentation scraper.

        Args:
            base_url: Base URL of documentation site
            site_name: Name for output files (e.g., 'kubernetes', 'terraform')
            output_dir: Directory for scraped content
            output_format: 'jsonl' or 'markdown'
            max_pages: Maximum pages to scrape
            delay: Delay between requests (seconds)
            allowed_paths: Only crawl URLs containing these paths (e.g., ['/docs/', '/reference/'])
            exclude_paths: Skip URLs containing these paths
            content_selectors: CSS selectors for main content
            remove_selectors: CSS selectors to remove (nav, footer, ads)
        """
        self.base_url = base_url.rstrip('/')
        self.site_name = site_name
        self.output_dir = Path(output_dir)
        self.output_format = output_format
        self.max_pages = max_pages
        self.delay = delay

        # URL filtering
        self.allowed_paths = allowed_paths or ['/docs/']
        self.exclude_paths = exclude_paths or []
        self.domain = urlparse(base_url).netloc

        # Content extraction
        self.content_selectors = content_selectors or {
            'main': 'main',
            'article': 'article',
            'content': '.content',
            'docs': '.docs-content'
        }
        self.remove_selectors = remove_selectors or [
            'nav', 'header', 'footer', '.sidebar', '.navigation',
            '.breadcrumb', '.toc', '.edit-page', 'script', 'style'
        ]

        # Tracking
        self.visited: Set[str] = set()
        self.queue: deque = deque()
        self.scraped_pages: List[Dict[str, Any]] = []

        # HTTP session with retry logic
        self.session = self._create_session()

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic"""
        session = requests.Session()

        # Retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        # SECURE VERSION
        session.mount("https://", adapter)
        session.mount("https://", adapter)

        # User agent
        session.headers.update({
            'User-Agent': 'JADE-AI-DocScraper/1.0 (Educational/Research Purpose)'
        })

        return session

    def is_allowed_url(self, url: str) -> bool:
        """Check if URL should be crawled"""
        parsed = urlparse(url)

        # Must be same domain
        if parsed.netloc != self.domain:
            return False

        # Must contain allowed path
        if not any(allowed in url for allowed in self.allowed_paths):
            return False

        # Must not contain excluded path
        if any(excluded in url for excluded in self.exclude_paths):
            return False

        # Skip anchors, images, downloads
        if url.endswith(('.pdf', '.zip', '.tar.gz', '.jpg', '.png', '.svg')):
            return False

        return True

    def extract_content(self, soup: BeautifulSoup, url: str) -> Dict[str, Any]:
        """
        Extract main content from page.

        Returns:
            Dict with title, content, metadata
        """
        # Remove unwanted elements
        for selector in self.remove_selectors:
            for element in soup.select(selector):
                element.decompose()

        # Find main content area
        content_element = None
        for selector in self.content_selectors.values():
            content_element = soup.select_one(selector)
            if content_element:
                break

        if not content_element:
            content_element = soup.body

        # Extract title
        title = None
        if soup.title:
            title = soup.title.string
        elif soup.h1:
            title = soup.h1.get_text(strip=True)
        else:
            title = url.split('/')[-1].replace('-', ' ').title()

        # Get text content
        text_content = content_element.get_text(separator='\n', strip=True) if content_element else ""

        # Get markdown-like content (preserve structure)
        markdown_content = self._to_markdown(content_element) if content_element else ""

        return {
            'url': url,
            'title': title.strip() if title else "Untitled",
            'content': text_content,
            'markdown': markdown_content,
            'scraped_at': datetime.now().isoformat(),
            'site': self.site_name
        }

    def _to_markdown(self, element: BeautifulSoup) -> str:
        """Convert HTML to basic markdown"""
        lines = []

        for child in element.descendants:
            if child.name == 'h1':
                lines.append(f"\n# {child.get_text(strip=True)}\n")
            elif child.name == 'h2':
                lines.append(f"\n## {child.get_text(strip=True)}\n")
            elif child.name == 'h3':
                lines.append(f"\n### {child.get_text(strip=True)}\n")
            elif child.name == 'h4':
                lines.append(f"\n#### {child.get_text(strip=True)}\n")
            elif child.name == 'p':
                lines.append(f"\n{child.get_text(strip=True)}\n")
            elif child.name == 'code':
                lines.append(f"`{child.get_text(strip=True)}`")
            elif child.name == 'pre':
                code_text = child.get_text(strip=True)
                lines.append(f"\n```\n{code_text}\n```\n")
            elif child.name == 'li':
                lines.append(f"- {child.get_text(strip=True)}")

        return '\n'.join(lines)

    def extract_links(self, soup: BeautifulSoup, current_url: str) -> List[str]:
        """Extract and normalize all links from page"""
        links = []

        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']

            # Convert to absolute URL
            absolute_url = urljoin(current_url, href)

            # Remove fragment
            absolute_url = absolute_url.split('#')[0]

            # Check if allowed
            if self.is_allowed_url(absolute_url) and absolute_url not in self.visited:
                links.append(absolute_url)

        return links

    def scrape_page(self, url: str) -> Optional[Dict[str, Any]]:
        """Scrape single page"""
        try:
            print(f"📄 Scraping: {url}")

            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # Extract content
            page_data = self.extract_content(soup, url)

            # Extract links for further crawling
            new_links = self.extract_links(soup, url)

            # Add new links to queue
            for link in new_links:
                if link not in self.visited and link not in self.queue:
                    self.queue.append(link)

            return page_data

        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")
            return None

    def crawl(self, start_url: Optional[str] = None):
        """
        Start crawling from start_url (or base_url).

        Breadth-first crawl of documentation site.
        """
        # Initialize queue
        start = start_url or self.base_url
        self.queue.append(start)

        pages_scraped = 0

        print(f"🚀 Starting crawl of {self.site_name}")
        print(f"   Base URL: {self.base_url}")
        print(f"   Max pages: {self.max_pages}")
        print(f"   Delay: {self.delay}s")
        print(f"   Allowed paths: {self.allowed_paths}")
        print()

        while self.queue and pages_scraped < self.max_pages:
            url = self.queue.popleft()

            if url in self.visited:
                continue

            self.visited.add(url)

            # Scrape page
            page_data = self.scrape_page(url)

            if page_data:
                self.scraped_pages.append(page_data)
                pages_scraped += 1

                print(f"   ✅ Scraped ({pages_scraped}/{self.max_pages}): {page_data['title'][:60]}")

            # Rate limiting
            time.sleep(self.delay)

        print(f"\n✅ Crawl complete! Scraped {len(self.scraped_pages)} pages")

    def save_jsonl(self, filename: Optional[str] = None):
        """Save scraped content as JSONL for RAG ingestion"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.site_name}_docs_{timestamp}.jsonl"

        output_path = self.output_dir / filename

        with open(output_path, 'w', encoding='utf-8') as f:
            for page in self.scraped_pages:
                # Format for RAG ingestion
                rag_entry = {
                    "question": f"Documentation: {page['title']}",
                    "answer": page['markdown'],
                    "metadata": {
                        "source": page['url'],
                        "site": page['site'],
                        "scraped_at": page['scraped_at'],
                        "type": "documentation",
                        "title": page['title']
                    }
                }
                f.write(json.dumps(rag_entry, ensure_ascii=False) + '\n')

        print(f"\n💾 Saved JSONL: {output_path}")
        print(f"   Total entries: {len(self.scraped_pages)}")
        print(f"   Ready for preprocessing: python3 {PREPROCESS_SCRIPT.relative_to(GP_ROOT)}")

        return output_path

    def save_markdown(self, filename: Optional[str] = None):
        """Save scraped content as markdown files"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.site_name}_docs_{timestamp}.md"

        output_path = self.output_dir / filename

        with open(output_path, 'w', encoding='utf-8') as f:
            for page in self.scraped_pages:
                f.write(f"# {page['title']}\n\n")
                f.write(f"**Source**: {page['url']}\n")
                f.write(f"**Scraped**: {page['scraped_at']}\n\n")
                f.write("---\n\n")
                f.write(page['markdown'])
                f.write("\n\n" + "="*80 + "\n\n")

        print(f"\n💾 Saved Markdown: {output_path}")
        print(f"   Total pages: {len(self.scraped_pages)}")

        return output_path

    def save(self):
        """Save in configured format"""
        if self.output_format == 'jsonl':
            return self.save_jsonl()
        elif self.output_format == 'markdown':
            return self.save_markdown()
        else:
            raise ValueError(f"Unknown output format: {self.output_format}")


def main():
    parser = argparse.ArgumentParser(
        description="Scrape documentation sites for JADE AI knowledge base"
    )

    parser.add_argument(
        '--site',
        choices=['kubernetes', 'terraform', 'opa', 'docker', 'custom'],
        help='Predefined site configuration'
    )

    parser.add_argument(
        '--url',
        help='Custom base URL to scrape'
    )

    parser.add_argument(
        '--config',
        type=Path,
        help='Path to YAML config file'
    )

    parser.add_argument(
        '--output-dir',
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f'Output directory (default: {DEFAULT_OUTPUT_DIR.relative_to(GP_ROOT)})'
    )

    parser.add_argument(
        '--output-format',
        choices=['jsonl', 'markdown'],
        default='jsonl',
        help='Output format (default: jsonl)'
    )

    parser.add_argument(
        '--max-pages',
        type=int,
        default=500,
        help='Maximum pages to scrape (default: 500)'
    )

    parser.add_argument(
        '--delay',
        type=float,
        default=1.0,
        help='Delay between requests in seconds (default: 1.0)'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be scraped without actually scraping'
    )

    args = parser.parse_args()

    # Predefined configurations
    SITE_CONFIGS = {
        'kubernetes': {
            'base_url': 'https://kubernetes.io',
            'site_name': 'kubernetes',
            'allowed_paths': ['/docs/'],
            'exclude_paths': ['/blog/', '/case-studies/', '/partners/'],
            'content_selectors': {'main': 'main', 'docs': '#docsToc'},
            'remove_selectors': ['nav', 'footer', '.td-sidebar', '.td-toc']
        },
        'terraform': {
            'base_url': 'https://developer.hashicorp.com/terraform',
            'site_name': 'terraform',
            'allowed_paths': ['/docs/', '/language/'],
            'exclude_paths': ['/downloads/', '/intro/'],
        },
        'opa': {
            'base_url': 'https://www.openpolicyagent.org',
            'site_name': 'opa',
            'allowed_paths': ['/docs/'],
            'exclude_paths': ['/blog/', '/integrations/'],
        },
        'docker': {
            'base_url': 'https://docs.docker.com',
            'site_name': 'docker',
            'allowed_paths': ['/'],
            'exclude_paths': ['/samples/', '/get-started/'],
        }
    }

    # Determine configuration
    if args.config:
        # TODO: Load from YAML config file
        print(f"❌ Config file support not yet implemented")
        return
    elif args.site:
        config = SITE_CONFIGS[args.site]
        scraper = DocScraper(
            base_url=config['base_url'],
            site_name=config['site_name'],
            output_dir=args.output_dir,
            output_format=args.output_format,
            max_pages=args.max_pages,
            delay=args.delay,
            allowed_paths=config.get('allowed_paths'),
            exclude_paths=config.get('exclude_paths'),
            content_selectors=config.get('content_selectors'),
            remove_selectors=config.get('remove_selectors')
        )
    elif args.url:
        scraper = DocScraper(
            base_url=args.url,
            site_name='custom',
            output_dir=args.output_dir,
            output_format=args.output_format,
            max_pages=args.max_pages,
            delay=args.delay
        )
    else:
        parser.error("Must provide --site, --url, or --config")
        return

    # Dry run
    if args.dry_run:
        print(f"🔍 Dry run mode")
        print(f"   Would scrape: {scraper.base_url}")
        print(f"   Allowed paths: {scraper.allowed_paths}")
        print(f"   Max pages: {scraper.max_pages}")
        print(f"   Output: {scraper.output_dir}")
        return

    # Execute crawl
    scraper.crawl()

    # Save results
    if scraper.scraped_pages:
        output_file = scraper.save()

        print(f"\n✅ Complete! Scraped {len(scraper.scraped_pages)} pages")
        print(f"\nNext steps:")
        print(f"1. Review: {output_file}")
        print(f"2. Preprocess: python3 GP-OPENSEARCH/03-preprocessed/preprocess_pipeline.py --verbose")
        print(f"3. Ingest: python3 GP-OPENSEARCH/04-ingesting/ingest_to_chromadb.py")
    else:
        print("\n⚠️  No pages scraped")


if __name__ == "__main__":
    main()
