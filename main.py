"""
Web Crawling Agent API
Menggunakan Crawl4AI untuk mengambil konten web dan mengonversinya ke Markdown
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, HttpUrl, validator
from crawl4ai import AsyncWebCrawler
from typing import List, Optional, Dict, Any
from datetime import datetime
import re
import os
from pathlib import Path
import asyncio

app = FastAPI(
    title="Web Crawling Agent",
    description="API untuk crawling halaman web dan konversi ke Markdown format",
    version="1.0.0"
)

# Model untuk request
class CrawlRequest(BaseModel):
    urls: List[str]
    save_to_file: Optional[bool] = False
    output_dir: Optional[str] = "output_markdown"

    # Content filtering options
    content_only: Optional[bool] = False
    excluded_tags: Optional[List[str]] = None
    css_selector: Optional[str] = None

    @validator('urls')
    def validate_urls(cls, v):
        if not v:
            raise ValueError('URLs list cannot be empty')

        # Validasi format URL
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain
            r'localhost|'  # localhost
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # IP
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)

        for url in v:
            if not url_pattern.match(url):
                raise ValueError(f'Invalid URL format: {url}')

        return v

# Model untuk response
class CrawlResult(BaseModel):
    url: str
    markdown: str
    metadata: Dict[str, Any]
    status: str
    file_path: Optional[str] = None

class CrawlResponse(BaseModel):
    results: List[CrawlResult]
    total_urls: int
    successful: int
    failed: int

def sanitize_filename(url: str) -> str:
    """
    Membuat nama file yang aman dari URL
    """
    # Hapus protocol
    name = re.sub(r'^https?://', '', url)
    # Replace karakter tidak valid dengan underscore
    name = re.sub(r'[^\w\-\.]', '_', name)
    # Batasi panjang filename
    if len(name) > 200:
        name = name[:200]
    return f"{name}.md"

def build_excluded_tags(content_only: bool = False, custom_tags: Optional[List[str]] = None) -> List[str]:
    """
    Build list of HTML tags yang akan di-exclude dari crawling

    Parameters:
    - content_only: Jika True, gunakan preset tags untuk clean content
    - custom_tags: Additional tags yang mau di-exclude

    Returns:
    - List of tags yang akan di-exclude
    """
    # Base tags yang selalu di-exclude
    base_tags = ['form']

    # Preset untuk content_only mode - exclude elemen navigasi dan UI
    clean_content_tags = [
        'nav',           # Navigation menu
        'footer',        # Footer
        'header',        # Header
        'aside',         # Sidebar
        'script',        # JavaScript
        'style',         # CSS inline
        'noscript',      # NoScript tags
        'iframe',        # iFrames
        'button',        # Buttons
        'input',         # Input fields
        'select',        # Select dropdowns
        'textarea',      # Text areas
        'figure',        # Figures (sering untuk ads)
    ]

    excluded = base_tags.copy()

    if content_only:
        excluded.extend(clean_content_tags)

    # Tambah custom tags jika ada
    if custom_tags:
        excluded.extend(custom_tags)

    # Remove duplicates
    return list(set(excluded))

async def save_markdown_to_file(content: str, url: str, output_dir: str) -> str:
    """
    Menyimpan konten Markdown ke file
    """
    # Buat direktori jika belum ada
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Generate filename dari URL
    filename = sanitize_filename(url)
    filepath = os.path.join(output_dir, filename)

    # Tulis file
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

    return filepath

async def crawl_single_url(
    url: str,
    crawler: AsyncWebCrawler,
    save_file: bool = False,
    output_dir: str = "output_markdown",
    content_only: bool = False,
    excluded_tags: Optional[List[str]] = None,
    css_selector: Optional[str] = None
) -> CrawlResult:
    """
    Crawl satu URL dan return hasilnya

    Parameters:
    - url: URL yang akan di-crawl
    - crawler: AsyncWebCrawler instance
    - save_file: Simpan hasil ke file
    - output_dir: Direktori output
    - content_only: Jika True, hanya ambil konten utama (exclude navbar, footer, dll)
    - excluded_tags: Custom list HTML tags yang akan di-exclude
    - css_selector: CSS selector untuk target specific element
    """
    try:
        # Build excluded tags list
        tags_to_exclude = build_excluded_tags(content_only, excluded_tags)

        # Prepare crawl parameters
        crawl_params = {
            "url": url,
            "word_count_threshold": 10,
            "excluded_tags": tags_to_exclude,
            "remove_overlay_elements": True,
        }

        # Add CSS selector jika ada (highest priority)
        if css_selector:
            crawl_params["css_selector"] = css_selector

        # Jalankan crawling
        result = await crawler.arun(**crawl_params)

        # Extract markdown dari result
        markdown_content = result.markdown if hasattr(result, 'markdown') else result.markdown_v2.raw_markdown

        # Metadata
        metadata = {
            "title": getattr(result, 'title', 'N/A'),
            "status_code": getattr(result, 'status_code', 200),
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "success": result.success,
            "url": url,
            "excluded_tags": tags_to_exclude,
            "css_selector": css_selector
        }

        # Simpan ke file jika diminta
        file_path = None
        if save_file and markdown_content:
            file_path = await save_markdown_to_file(markdown_content, url, output_dir)

        return CrawlResult(
            url=url,
            markdown=markdown_content if markdown_content else "",
            metadata=metadata,
            status="success" if result.success else "failed",
            file_path=file_path
        )

    except Exception as e:
        # Handle error
        return CrawlResult(
            url=url,
            markdown="",
            metadata={
                "error": str(e),
                "status_code": 0,
                "fetched_at": datetime.utcnow().isoformat() + "Z",
                "success": False
            },
            status="failed",
            file_path=None
        )

@app.get("/")
async def root():
    """
    Root endpoint dengan informasi API
    """
    return {
        "message": "Web Crawling Agent API",
        "version": "1.0.0",
        "endpoints": {
            "/crawl": "POST - Crawl satu atau beberapa URL",
            "/health": "GET - Health check"
        }
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

@app.post("/crawl", response_model=CrawlResponse)
async def crawl_urls(request: CrawlRequest):
    """
    Crawl satu atau beberapa URL dan return hasil dalam format Markdown

    Parameters:
    - urls: List URL yang akan di-crawl
    - save_to_file: (Optional) Simpan hasil ke file .md
    - output_dir: (Optional) Direktori untuk menyimpan file (default: output_markdown)
    - content_only: (Optional) Jika True, hanya ambil konten utama tanpa navbar, footer, dll (default: False)
    - excluded_tags: (Optional) Custom list HTML tags yang akan di-exclude
    - css_selector: (Optional) CSS selector untuk target specific element (contoh: "article", "#main-content")

    Returns:
    - results: List hasil crawling untuk setiap URL
    - total_urls: Total URL yang diproses
    - successful: Jumlah URL yang berhasil
    - failed: Jumlah URL yang gagal

    Examples:
    - Basic crawl: {"urls": ["https://example.com"]}
    - Clean content only: {"urls": ["https://example.com"], "content_only": true}
    - Custom exclusion: {"urls": ["https://example.com"], "excluded_tags": ["nav", "footer"]}
    - Target specific element: {"urls": ["https://example.com"], "css_selector": "article.main"}
    """
    # Initialize crawler
    async with AsyncWebCrawler(verbose=False) as crawler:
        # Jalankan crawling untuk semua URL secara concurrent
        tasks = [
            crawl_single_url(
                url=url,
                crawler=crawler,
                save_file=request.save_to_file,
                output_dir=request.output_dir,
                content_only=request.content_only,
                excluded_tags=request.excluded_tags,
                css_selector=request.css_selector
            )
            for url in request.urls
        ]

        results = await asyncio.gather(*tasks)

    # Hitung statistik
    successful = sum(1 for r in results if r.status == "success")
    failed = len(results) - successful

    return CrawlResponse(
        results=results,
        total_urls=len(request.urls),
        successful=successful,
        failed=failed
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
