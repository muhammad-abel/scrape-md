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
from dotenv import load_dotenv

# LLM provider via LiteLLM (optional - only imported if smart_clean is used)
try:
    from litellm import acompletion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

# Load environment variables
load_dotenv()

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

    # Smart cleaning with LLM (post-process via LiteLLM)
    smart_clean: Optional[bool] = False
    llm_model: Optional[str] = "openrouter/google/gemini-2.5-flash"  # LiteLLM auto-detects provider from model name

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

# Model untuk debug endpoint
class DebugCrawlResult(BaseModel):
    url: str
    cleaned_html: str
    markdown: str
    metadata: Dict[str, Any]
    status: str
    html_file_path: Optional[str] = None
    markdown_file_path: Optional[str] = None

class DebugCrawlResponse(BaseModel):
    results: List[DebugCrawlResult]
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

async def clean_markdown_with_llm(
    markdown: str,
    model: str = "claude-3-5-haiku-20241022"
) -> Dict[str, Any]:
    """
    Clean markdown content menggunakan LLM (via LiteLLM) untuk remove navbar, footer, ads, dll.

    Parameters:
    - markdown: Raw markdown content
    - model: Model name (LiteLLM auto-detects provider)
      Examples: "claude-3-5-haiku-20241022", "gpt-4o-mini", "gemini-pro"

    Returns:
    - Dict dengan cleaned_markdown dan metadata
    """

    if not LITELLM_AVAILABLE:
        return {
            "cleaned_markdown": markdown,
            "model": model,
            "error": "LiteLLM not installed. Install with: pip install litellm",
            "success": False
        }

    # Prompt untuk LLM
    system_prompt = """You are a content extraction assistant. Your task is to extract ONLY the main article content from the markdown below.

RULES:
1. Remove navigation menus, headers, footers
2. Remove sidebars, advertisements, promotional content
3. Remove "related posts", "you may also like", "trending now", "popular articles"
4. Remove social media widgets, share buttons, comment sections
5. Remove author bio/bylines (unless essential to article)
6. Remove newsletter signup forms, call-to-action buttons
7. Keep the main article title and body content
8. Keep images/figures that are part of the main article
9. Preserve the original markdown formatting exactly
10. Do NOT summarize, paraphrase, or modify the content - extract as-is
11. If you're unsure whether something is content or navigation, include it

OUTPUT: Return ONLY the cleaned markdown, nothing else."""

    user_prompt = f"""Extract the main article content from this markdown:

---
{markdown}
---

Remember: Return ONLY the cleaned markdown content, nothing else. No explanations, no comments."""

    try:
        # LiteLLM automatically routes to the correct provider based on model name
        response = await acompletion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            max_tokens=16000
        )

        cleaned_markdown = response.choices[0].message.content

        # Extract usage info
        usage = response.usage if hasattr(response, 'usage') else None
        input_tokens = usage.prompt_tokens if usage else 0
        output_tokens = usage.completion_tokens if usage else 0

        return {
            "cleaned_markdown": cleaned_markdown,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "success": True
        }

    except Exception as e:
        return {
            "cleaned_markdown": markdown,  # Fallback ke original
            "model": model,
            "error": str(e),
            "success": False
        }

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

async def save_html_to_file(content: str, url: str, output_dir: str) -> str:
    """
    Menyimpan konten HTML ke file
    """
    # Buat direktori jika belum ada
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    # Generate filename dari URL (ganti .md dengan .html)
    filename = sanitize_filename(url).replace('.md', '.html')
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
    css_selector: Optional[str] = None,
    smart_clean: bool = False,
    llm_model: str = "claude-3-5-haiku-20241022"
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
    - smart_clean: Jika True, gunakan LLM untuk clean markdown post-crawl (via LiteLLM)
    - llm_model: Model name (LiteLLM auto-detects provider)
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

        # Smart clean dengan LLM jika diminta
        llm_metadata = {}
        if smart_clean and markdown_content:
            llm_result = await clean_markdown_with_llm(
                markdown_content,
                model=llm_model
            )

            if llm_result["success"]:
                markdown_content = llm_result["cleaned_markdown"]
                llm_metadata = {
                    "llm_model": llm_result["model"],
                    "input_tokens": llm_result["input_tokens"],
                    "output_tokens": llm_result["output_tokens"],
                    "llm_cleaning": "success"
                }
            else:
                llm_metadata = {
                    "llm_model": llm_model,
                    "llm_cleaning": "failed",
                    "llm_error": llm_result.get("error", "Unknown error")
                }

        # Metadata
        metadata = {
            "title": getattr(result, 'title', 'N/A'),
            "status_code": getattr(result, 'status_code', 200),
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "success": result.success,
            "url": url,
            "excluded_tags": tags_to_exclude,
            "css_selector": css_selector,
            **llm_metadata  # Add LLM metadata if available
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

async def debug_crawl_single_url(
    url: str,
    crawler: AsyncWebCrawler,
    save_file: bool = False,
    output_dir: str = "debug_output",
    content_only: bool = False,
    excluded_tags: Optional[List[str]] = None,
    css_selector: Optional[str] = None
) -> DebugCrawlResult:
    """
    Crawl single URL dan return cleaned HTML + markdown untuk debugging
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

        # Extract markdown dan cleaned HTML dari result
        markdown_content = result.markdown if hasattr(result, 'markdown') else result.markdown_v2.raw_markdown
        cleaned_html = result.cleaned_html if hasattr(result, 'cleaned_html') else result.html

        # Metadata
        metadata = {
            "title": getattr(result, 'title', 'N/A'),
            "status_code": getattr(result, 'status_code', 200),
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "success": result.success,
            "url": url,
            "excluded_tags": tags_to_exclude,
            "css_selector": css_selector,
            "html_length": len(cleaned_html) if cleaned_html else 0,
            "markdown_length": len(markdown_content) if markdown_content else 0
        }

        # Simpan ke file jika diminta
        html_file_path = None
        markdown_file_path = None

        if save_file:
            if cleaned_html:
                html_file_path = await save_html_to_file(cleaned_html, url, output_dir)
            if markdown_content:
                markdown_file_path = await save_markdown_to_file(markdown_content, url, output_dir)

        return DebugCrawlResult(
            url=url,
            cleaned_html=cleaned_html if cleaned_html else "",
            markdown=markdown_content if markdown_content else "",
            metadata=metadata,
            status="success" if result.success else "failed",
            html_file_path=html_file_path,
            markdown_file_path=markdown_file_path
        )

    except Exception as e:
        # Handle error
        return DebugCrawlResult(
            url=url,
            cleaned_html="",
            markdown="",
            metadata={
                "error": str(e),
                "status_code": 0,
                "fetched_at": datetime.utcnow().isoformat() + "Z",
                "success": False
            },
            status="failed",
            html_file_path=None,
            markdown_file_path=None
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
