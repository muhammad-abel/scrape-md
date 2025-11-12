"""
Web Crawling Agent API
Menggunakan Crawl4AI untuk mengambil konten web dan mengonversinya ke Markdown
"""
from fastapi import FastAPI
from crawl4ai import AsyncWebCrawler
from datetime import datetime
import asyncio

from app.models.schemas import (
    CrawlRequest,
    CrawlResponse,
    DebugCrawlResponse
)
from app.services.crawler_service import crawl_single_url, debug_crawl_single_url
from app.config import settings


# Initialize FastAPI app
app = FastAPI(
    title="Web Crawling Agent",
    description="API untuk crawling halaman web dan konversi ke Markdown format",
    version="1.0.0"
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
            "/crawl": "POST - Crawl satu atau beberapa URL (return markdown)",
            "/debug-crawl": "POST - Crawl dengan cleaned HTML untuk debugging",
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
    - smart_clean: (Optional) Jika True, gunakan LLM untuk clean markdown post-crawl (default: False)
    - llm_model: (Optional) Model name (LiteLLM auto-detects provider) (default: claude-3-5-haiku-20241022)

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
    - Smart clean with Claude: {"urls": ["https://example.com"], "smart_clean": true}
    - Smart clean with GPT: {"urls": ["https://example.com"], "smart_clean": true, "llm_model": "gpt-4o-mini"}
    - Smart clean with Gemini: {"urls": ["https://example.com"], "smart_clean": true, "llm_model": "gemini-pro"}
    - Smart clean with OpenRouter: {"urls": ["https://example.com"], "smart_clean": true, "llm_model": "openrouter/google/gemini-2.5-flash"}
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
                css_selector=request.css_selector,
                smart_clean=request.smart_clean,
                llm_model=request.llm_model
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


@app.post("/debug-crawl", response_model=DebugCrawlResponse)
async def debug_crawl_endpoint(request: CrawlRequest):
    """
    Debug endpoint untuk crawl URLs dan return cleaned HTML + markdown

    Berguna untuk debugging dan melihat hasil cleaning HTML sebelum convert ke markdown.

    Parameters sama dengan /crawl endpoint, tapi response include cleaned_html.
    Output directory default: "debug_output"
    """
    async with AsyncWebCrawler(verbose=True) as crawler:
        # Jalankan debug crawling untuk semua URL secara concurrent
        tasks = [
            debug_crawl_single_url(
                url=url,
                crawler=crawler,
                save_file=request.save_to_file,
                output_dir=request.output_dir if request.output_dir != "output_markdown" else "debug_output",
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

    return DebugCrawlResponse(
        results=results,
        total_urls=len(request.urls),
        successful=successful,
        failed=failed
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
