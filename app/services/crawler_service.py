"""
Web crawler service using Crawl4AI
"""
from crawl4ai import AsyncWebCrawler
from typing import Optional, List, Dict, Any
from datetime import datetime

from app.models.schemas import CrawlResult, DebugCrawlResult
from app.utils.html_utils import build_excluded_tags
from app.utils.file_utils import save_markdown_to_file, save_html_to_file
from app.services.llm_service import clean_markdown_with_llm


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

    Args:
        url: URL yang akan di-crawl
        crawler: AsyncWebCrawler instance
        save_file: Simpan hasil ke file
        output_dir: Direktori output
        content_only: Jika True, hanya ambil konten utama (exclude navbar, footer, dll)
        excluded_tags: Custom list HTML tags yang akan di-exclude
        css_selector: CSS selector untuk target specific element
        smart_clean: Jika True, gunakan LLM untuk clean markdown post-crawl (via LiteLLM)
        llm_model: Model name (LiteLLM auto-detects provider)

    Returns:
        CrawlResult object
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

    Args:
        url: URL yang akan di-crawl
        crawler: AsyncWebCrawler instance
        save_file: Simpan hasil ke file
        output_dir: Direktori output
        content_only: Jika True, hanya ambil konten utama
        excluded_tags: Custom list HTML tags yang akan di-exclude
        css_selector: CSS selector untuk target specific element

    Returns:
        DebugCrawlResult object
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
