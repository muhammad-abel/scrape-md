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

async def crawl_single_url(url: str, crawler: AsyncWebCrawler, save_file: bool = False, output_dir: str = "output_markdown") -> CrawlResult:
    """
    Crawl satu URL dan return hasilnya
    """
    try:
        # Jalankan crawling
        result = await crawler.arun(
            url=url,
            word_count_threshold=10,
            excluded_tags=['form', 'nav'],
            remove_overlay_elements=True,
        )

        # Extract markdown dari result
        markdown_content = result.markdown if hasattr(result, 'markdown') else result.markdown_v2.raw_markdown

        # Metadata
        metadata = {
            "title": getattr(result, 'title', 'N/A'),
            "status_code": getattr(result, 'status_code', 200),
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "success": result.success,
            "url": url
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

    Returns:
    - results: List hasil crawling untuk setiap URL
    - total_urls: Total URL yang diproses
    - successful: Jumlah URL yang berhasil
    - failed: Jumlah URL yang gagal
    """
    # Initialize crawler
    async with AsyncWebCrawler(verbose=False) as crawler:
        # Jalankan crawling untuk semua URL secara concurrent
        tasks = [
            crawl_single_url(
                url,
                crawler,
                request.save_to_file,
                request.output_dir
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
