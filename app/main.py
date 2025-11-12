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
    DebugCrawlResponse,
    CleanMarkdownRequest,
    CleanMarkdownResponse
)
from app.services.crawler_service import crawl_single_url, debug_crawl_single_url
from app.services.llm_service import clean_markdown_with_llm
from app.utils.file_utils import save_markdown_to_file
from app.config import settings
import os
from pathlib import Path


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
            "/clean-markdown": "POST - Clean markdown file dengan LLM (smart clean)",
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


@app.post("/clean-markdown", response_model=CleanMarkdownResponse)
async def clean_markdown_endpoint(request: CleanMarkdownRequest):
    """
    Clean markdown content dengan LLM untuk remove navbar, footer, ads, dll.

    Endpoint ini khusus untuk cleaning markdown yang sudah ada (hasil crawling atau dari file).
    Berguna untuk:
    - Clean hasil crawl yang sudah tersimpan tanpa perlu crawl ulang
    - Post-process markdown dari source manapun
    - Batch cleaning multiple markdown files

    Parameters:
    - markdown_content: (Optional) Markdown content string langsung
    - file_path: (Optional) Path ke file .md yang akan di-clean
    - llm_model: (Optional) Model name (LiteLLM auto-detects provider) (default: claude-3-5-haiku-20241022)
    - save_to_file: (Optional) Simpan hasil cleaned ke file
    - output_dir: (Optional) Direktori untuk menyimpan file (default: output_markdown)
    - output_filename: (Optional) Custom output filename (default: cleaned_<original_name>.md)

    Returns:
    - original_length: Panjang markdown original
    - cleaned_length: Panjang markdown setelah cleaning
    - cleaned_markdown: Hasil markdown yang sudah di-clean
    - model: Model yang digunakan
    - input_tokens: Token yang digunakan untuk input
    - output_tokens: Token yang digunakan untuk output
    - status: Status cleaning (success/failed)
    - file_path: Path ke file hasil cleaning (jika save_to_file=true)
    - error: Error message (jika ada)

    Examples:
    - Clean from content: {"markdown_content": "# Title\n\nContent..."}
    - Clean from file: {"file_path": "output_markdown/example.md"}
    - Clean and save: {"file_path": "input.md", "save_to_file": true}
    - Custom model: {"markdown_content": "...", "llm_model": "gpt-4o-mini"}
    - OpenRouter: {"file_path": "input.md", "llm_model": "openrouter/google/gemini-2.5-flash"}
    """
    try:
        # Get markdown content
        markdown_content = ""

        if request.markdown_content:
            # Use content from request body
            markdown_content = request.markdown_content
        elif request.file_path:
            # Read from file
            file_path = Path(request.file_path)
            if not file_path.exists():
                return CleanMarkdownResponse(
                    original_length=0,
                    cleaned_length=0,
                    cleaned_markdown="",
                    model=request.llm_model,
                    input_tokens=0,
                    output_tokens=0,
                    status="failed",
                    error=f"File not found: {request.file_path}"
                )

            with open(file_path, 'r', encoding='utf-8') as f:
                markdown_content = f.read()
        else:
            return CleanMarkdownResponse(
                original_length=0,
                cleaned_length=0,
                cleaned_markdown="",
                model=request.llm_model,
                input_tokens=0,
                output_tokens=0,
                status="failed",
                error="Either markdown_content or file_path must be provided"
            )

        original_length = len(markdown_content)

        # Clean markdown dengan LLM
        llm_result = await clean_markdown_with_llm(
            markdown_content,
            model=request.llm_model
        )

        if not llm_result["success"]:
            return CleanMarkdownResponse(
                original_length=original_length,
                cleaned_length=0,
                cleaned_markdown=markdown_content,  # Return original on error
                model=request.llm_model,
                input_tokens=0,
                output_tokens=0,
                status="failed",
                error=llm_result.get("error", "Unknown error")
            )

        cleaned_markdown = llm_result["cleaned_markdown"]
        cleaned_length = len(cleaned_markdown)

        # Save to file if requested
        saved_file_path = None
        if request.save_to_file:
            # Generate output filename
            if request.output_filename:
                output_filename = request.output_filename
            elif request.file_path:
                # Use original filename with "cleaned_" prefix
                original_filename = Path(request.file_path).name
                output_filename = f"cleaned_{original_filename}"
            else:
                # Generate timestamp-based filename
                timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                output_filename = f"cleaned_{timestamp}.md"

            # Save file
            output_path = os.path.join(request.output_dir, output_filename)
            Path(request.output_dir).mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(cleaned_markdown)

            saved_file_path = output_path

        return CleanMarkdownResponse(
            original_length=original_length,
            cleaned_length=cleaned_length,
            cleaned_markdown=cleaned_markdown,
            model=llm_result["model"],
            input_tokens=llm_result["input_tokens"],
            output_tokens=llm_result["output_tokens"],
            status="success",
            file_path=saved_file_path
        )

    except Exception as e:
        return CleanMarkdownResponse(
            original_length=0,
            cleaned_length=0,
            cleaned_markdown="",
            model=request.llm_model,
            input_tokens=0,
            output_tokens=0,
            status="failed",
            error=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
