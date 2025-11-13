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
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# LLM provider via OpenAI SDK (compatible with LiteLLM Proxy)
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# Fallback to litellm direct if OpenAI SDK not available
try:
    from litellm import acompletion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

# Markdown stripping service
try:
    from app.services.markdown_strip_service import strip_markdown
    MARKDOWN_STRIP_AVAILABLE = True
except ImportError:
    MARKDOWN_STRIP_AVAILABLE = False

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

    # Smart cleaning with LLM (post-process via LiteLLM Proxy)
    smart_clean: Optional[bool] = False
    llm_model: Optional[str] = "azure/gpt-5-mini"  # Model name for LiteLLM Proxy

    # Markdown stripping (final cleanup - remove links, images, HTML)
    markdown_strip: Optional[bool] = False

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
    model: str = "openrouter/google/gemini-2.5-flash"
) -> Dict[str, Any]:
    """
    Clean markdown content menggunakan LLM untuk remove navbar, footer, ads, dll.

    Parameters:
    - markdown: Raw markdown content
    - model: Model name (defaults to gemini-2.5-flash via OpenRouter)
      Examples: "openrouter/google/gemini-2.5-flash", "openrouter/anthropic/claude-3.5-sonnet"

    Returns:
    - Dict dengan cleaned_markdown dan metadata
    """

    # Check if OpenAI SDK available (preferred for LiteLLM Proxy)
    if not OPENAI_AVAILABLE and not LITELLM_AVAILABLE:
        return {
            "cleaned_markdown": markdown,
            "model": model,
            "error": "OpenAI SDK or LiteLLM not installed. Install with: pip install openai",
            "success": False
        }

    # Prompt untuk LLM
    system_prompt = """You are a content extraction assistant. Your task is to extract ONLY the main article content from the markdown below.

RULES - REMOVE THESE (BE AGGRESSIVE):
1. Navigation menus, headers, footers, breadcrumbs
2. Sidebars, advertisements, promotional banners
3. "Related posts", "Berita Terkait", "Rekomendasi untuk Anda", "You may also like", "Trending now", "Popular articles"
4. Social media widgets, share buttons ("BAGIKAN", "Share"), comment sections
5. Author bio/bylines (unless essential to understanding the article)
6. Newsletter signup forms, subscription prompts, call-to-action buttons
7. Internal cross-links like "Baca juga:", "Read more:", "See also:", "Simak Video:", "Saksikan Live:"
8. Links to other articles that are NOT part of the main narrative
9. Category tags, topic tags (e.g., "prabowo subianto", "luwu utara")
10. "ADVERTISEMENT", "Sponsored", "Promoted content" sections
11. Footer sections (Layanan, Informasi, Jaringan Media, Kategori)
12. Video embeds that are NOT central to the article
13. Copyright notices, publication metadata
14. Search trending sections ("Yang sedang ramai dicari")

RULES - KEEP THESE:
1. The main article title (headline)
2. All body paragraphs that are part of the main article narrative
3. Images/figures that illustrate the main content
4. Inline quotes from sources
5. Essential data, tables, charts
6. Section headers/subheadings within the article body

FORMATTING:
- Preserve the original markdown formatting exactly
- Do NOT summarize, paraphrase, or rewrite - extract as-is
- If unsure whether standalone text/link is navigation or content, REMOVE it (be aggressive with removal)
- Keep ONLY the essential article body

OUTPUT: Return ONLY the cleaned markdown, nothing else. No explanations, no comments, no metadata."""

    user_prompt = f"""Extract the main article content from this markdown:

---
{markdown}
---

Remember: Return ONLY the cleaned markdown content, nothing else. No explanations, no comments."""

    # Messages for LLM
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    try:
        # Get proxy configuration from environment
        proxy_base_url = os.getenv("LITELLM_PROXY_BASE_URL")
        proxy_api_key = os.getenv("LITELLM_PROXY_API_KEY", "dummy-key")

        # Use OpenAI SDK with LiteLLM Proxy (like your working example!)
        if proxy_base_url and OPENAI_AVAILABLE:
            client = AsyncOpenAI(
                api_key=proxy_api_key,
                base_url=proxy_base_url
            )

            # Prepare completion parameters
            # Note: Azure GPT-4o/GPT-5 models require 'max_completion_tokens' instead of 'max_tokens'
            completion_params = {
                "model": model,
                "messages": messages,
            }

            # Use max_completion_tokens for Azure models, max_tokens for others
            # Azure models: gpt-4o, gpt-5, o1, etc.
            if "azure" in model.lower() or "gpt-4o" in model.lower() or "gpt-5" in model.lower() or "o1" in model.lower():
                completion_params["max_completion_tokens"] = 16000
            else:
                completion_params["max_tokens"] = 16000

            response = await client.chat.completions.create(**completion_params)

            cleaned_markdown = response.choices[0].message.content
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

        # Fallback to litellm direct (for non-proxy usage)
        elif LITELLM_AVAILABLE:
            response = await acompletion(
                model=model,
                messages=messages,
                max_tokens=16000
            )

            cleaned_markdown = response.choices[0].message.content
            usage = response.usage if hasattr(response, 'usage') else None
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

        else:
            return {
                "cleaned_markdown": markdown,
                "model": model,
                "error": "No LLM client available. Set LITELLM_PROXY_BASE_URL or install litellm.",
                "success": False
            }

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
    llm_model: str = "azure/gpt-5-mini",
    markdown_strip: bool = False
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
        logger.info(f"🌐 [CRAWL] Starting crawl for URL: {url}")
        logger.info(f"🌐 [CRAWL] Pipeline: HTML filter={'✅' if content_only else '❌'} | LLM clean={'✅' if smart_clean else '❌'} | Markdown strip={'✅' if markdown_strip else '❌'}")

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
            logger.info(f"🤖 [LLM] Starting smart clean for URL: {url}")
            logger.info(f"🤖 [LLM] Model: {llm_model}")
            logger.info(f"🤖 [LLM] Input length: {len(markdown_content)} chars")

            llm_result = await clean_markdown_with_llm(
                markdown_content,
                model=llm_model
            )

            if llm_result["success"]:
                original_len = len(markdown_content)
                markdown_content = llm_result["cleaned_markdown"]
                cleaned_len = len(markdown_content)
                reduction = ((original_len - cleaned_len) / original_len * 100) if original_len > 0 else 0

                logger.info(f"✅ [LLM] Smart clean successful")
                logger.info(f"✅ [LLM] Output length: {cleaned_len} chars (reduced {reduction:.1f}%)")
                logger.info(f"✅ [LLM] Tokens used: {llm_result['input_tokens']} input, {llm_result['output_tokens']} output")

                llm_metadata = {
                    "llm_model": llm_result["model"],
                    "input_tokens": llm_result["input_tokens"],
                    "output_tokens": llm_result["output_tokens"],
                    "llm_cleaning": "success"
                }
            else:
                logger.error(f"❌ [LLM] Smart clean failed: {llm_result.get('error', 'Unknown error')}")
                llm_metadata = {
                    "llm_model": llm_model,
                    "llm_cleaning": "failed",
                    "llm_error": llm_result.get("error", "Unknown error")
                }

        # Markdown strip (final cleanup - remove links, images, HTML)
        strip_metadata = {}
        if markdown_strip and markdown_content:
            logger.info(f"📝 [STRIP] Starting markdown strip for URL: {url}")
            logger.info(f"📝 [STRIP] Input length: {len(markdown_content)} chars")

            if MARKDOWN_STRIP_AVAILABLE:
                try:
                    original_length = len(markdown_content)
                    markdown_content = strip_markdown(markdown_content)
                    stripped_length = len(markdown_content)
                    reduction = ((original_length - stripped_length) / original_length * 100) if original_length > 0 else 0

                    logger.info(f"✅ [STRIP] Markdown strip successful")
                    logger.info(f"✅ [STRIP] Output length: {stripped_length} chars (reduced {reduction:.1f}%)")
                    logger.info(f"✅ [STRIP] Removed: links, images, and HTML tags")

                    strip_metadata = {
                        "markdown_strip": "success",
                        "original_length": original_length,
                        "stripped_length": stripped_length
                    }
                except Exception as e:
                    logger.error(f"❌ [STRIP] Markdown strip failed: {str(e)}")
                    strip_metadata = {
                        "markdown_strip": "failed",
                        "strip_error": str(e)
                    }
            else:
                logger.warning(f"⚠️  [STRIP] Markdown strip unavailable: markdown-it-py not installed")
                strip_metadata = {
                    "markdown_strip": "unavailable",
                    "strip_error": "markdown-it-py not installed"
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
            **llm_metadata,  # Add LLM metadata if available
            **strip_metadata  # Add markdown strip metadata if available
        }

        # Simpan ke file jika diminta
        file_path = None
        if save_file and markdown_content:
            file_path = await save_markdown_to_file(markdown_content, url, output_dir)
            logger.info(f"💾 [SAVE] File saved to: {file_path}")

        logger.info(f"✨ [COMPLETE] Crawl completed for URL: {url}")
        logger.info(f"✨ [COMPLETE] Final markdown length: {len(markdown_content)} chars")

        return CrawlResult(
            url=url,
            markdown=markdown_content if markdown_content else "",
            metadata=metadata,
            status="success" if result.success else "failed",
            file_path=file_path
        )

    except Exception as e:
        # Handle error
        logger.error(f"❌ [ERROR] Crawl failed for URL: {url}")
        logger.error(f"❌ [ERROR] Error: {str(e)}")
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
    - llm_model: (Optional) Model name (LiteLLM auto-detects provider) (default: azure/gpt-5-mini)
    - markdown_strip: (Optional) Jika True, remove links, images, dan HTML dari markdown (default: False)

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
    - Smart clean with LLM: {"urls": ["https://example.com"], "smart_clean": true}
    - Full 3-stage pipeline: {"urls": ["https://example.com"], "content_only": true, "smart_clean": true, "markdown_strip": true}
    - Markdown strip only: {"urls": ["https://example.com"], "markdown_strip": true}
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
                llm_model=request.llm_model,
                markdown_strip=request.markdown_strip
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
