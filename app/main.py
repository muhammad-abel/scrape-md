"""
Web Crawling Agent API
Menggunakan Crawl4AI untuk mengambil konten web dan mengonversinya ke Markdown
"""
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from crawl4ai import AsyncWebCrawler
from datetime import datetime
import asyncio
import tempfile

from app.models.schemas import (
    CrawlRequest,
    CrawlResponse,
    DebugCrawlResponse
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


@app.post("/clean-markdown")
async def clean_markdown_endpoint(
    file: UploadFile = File(..., description="Markdown file to clean"),
    llm_model: str = Form(default="openrouter/google/gemini-2.5-flash", description="LLM model name")
):
    """
    Upload markdown file (.md) dan download hasil yang sudah di-clean dengan LLM.

    **Simple workflow:**
    1. Upload file .md
    2. LLM akan clean navbar, footer, ads, dll
    3. Download file .md yang sudah bersih

    **Parameters:**
    - file: File .md yang akan di-upload (multipart/form-data)
    - llm_model: (Optional) Model name untuk cleaning (default: openrouter/google/gemini-2.5-flash)

    **Supported Models:**
    - OpenRouter: openrouter/google/gemini-2.5-flash, openrouter/anthropic/claude-3.5-sonnet
    - Anthropic: claude-3-5-haiku-20241022, claude-3-5-sonnet-20241022
    - OpenAI: gpt-4o-mini, gpt-4o
    - Google: gemini-pro, gemini-1.5-pro

    **Returns:**
    - File download (.md) - Cleaned markdown file

    **Example (curl):**
    ```bash
    curl -X POST "http://localhost:8000/clean-markdown" \\
      -F "file=@input.md" \\
      -F "llm_model=openrouter/google/gemini-2.5-flash" \\
      -o cleaned_output.md
    ```

    **Example (Python requests):**
    ```python
    import requests

    with open('input.md', 'rb') as f:
        files = {'file': f}
        data = {'llm_model': 'openrouter/google/gemini-2.5-flash'}
        response = requests.post('http://localhost:8000/clean-markdown', files=files, data=data)

    with open('cleaned_output.md', 'wb') as f:
        f.write(response.content)
    ```
    """
    try:
        # Validate file extension
        if not file.filename.endswith('.md'):
            raise HTTPException(
                status_code=400,
                detail="Only .md files are supported. Please upload a markdown file."
            )

        # Read uploaded file content
        markdown_content = await file.read()
        markdown_content = markdown_content.decode('utf-8')

        # Clean markdown dengan LLM
        llm_result = await clean_markdown_with_llm(
            markdown_content,
            model=llm_model
        )

        if not llm_result["success"]:
            raise HTTPException(
                status_code=500,
                detail=f"LLM cleaning failed: {llm_result.get('error', 'Unknown error')}"
            )

        cleaned_markdown = llm_result["cleaned_markdown"]

        # Save to temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as tmp_file:
            tmp_file.write(cleaned_markdown)
            tmp_file_path = tmp_file.name

        # Generate cleaned filename
        original_filename = file.filename
        cleaned_filename = f"cleaned_{original_filename}"

        # Return file for download
        return FileResponse(
            path=tmp_file_path,
            media_type='text/markdown',
            filename=cleaned_filename,
            headers={
                "X-Original-Length": str(len(markdown_content)),
                "X-Cleaned-Length": str(len(cleaned_markdown)),
                "X-Model-Used": llm_result["model"],
                "X-Input-Tokens": str(llm_result["input_tokens"]),
                "X-Output-Tokens": str(llm_result["output_tokens"])
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing file: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
