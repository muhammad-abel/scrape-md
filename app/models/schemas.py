"""
Pydantic models for request/response schemas
"""
from pydantic import BaseModel, validator
from typing import List, Optional, Dict, Any
import re


class CrawlRequest(BaseModel):
    """Request schema for crawling URLs"""
    urls: List[str]
    save_to_file: Optional[bool] = False
    output_dir: Optional[str] = "output_markdown"

    # Content filtering options
    content_only: Optional[bool] = False
    excluded_tags: Optional[List[str]] = None
    css_selector: Optional[str] = None

    # Smart cleaning with LLM (post-process via LiteLLM)
    smart_clean: Optional[bool] = False
    llm_model: Optional[str] = "claude-3-5-haiku-20241022"

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


class CrawlResult(BaseModel):
    """Result schema for a single crawled URL"""
    url: str
    markdown: str
    metadata: Dict[str, Any]
    status: str
    file_path: Optional[str] = None


class CrawlResponse(BaseModel):
    """Response schema for crawl endpoint"""
    results: List[CrawlResult]
    total_urls: int
    successful: int
    failed: int


class DebugCrawlResult(BaseModel):
    """Result schema for debug crawl endpoint"""
    url: str
    cleaned_html: str
    markdown: str
    metadata: Dict[str, Any]
    status: str
    html_file_path: Optional[str] = None
    markdown_file_path: Optional[str] = None


class DebugCrawlResponse(BaseModel):
    """Response schema for debug crawl endpoint"""
    results: List[DebugCrawlResult]
    total_urls: int
    successful: int
    failed: int


class CleanMarkdownRequest(BaseModel):
    """Request schema for cleaning markdown content"""
    markdown_content: Optional[str] = None
    file_path: Optional[str] = None
    llm_model: Optional[str] = "claude-3-5-haiku-20241022"
    save_to_file: Optional[bool] = False
    output_dir: Optional[str] = "output_markdown"
    output_filename: Optional[str] = None

    @validator('markdown_content', 'file_path')
    def validate_content_or_file(cls, v, values, field):
        # At least one must be provided
        if field.name == 'file_path' and not v and not values.get('markdown_content'):
            raise ValueError('Either markdown_content or file_path must be provided')
        return v


class CleanMarkdownResponse(BaseModel):
    """Response schema for clean-markdown endpoint"""
    original_length: int
    cleaned_length: int
    cleaned_markdown: str
    model: str
    input_tokens: int
    output_tokens: int
    status: str
    file_path: Optional[str] = None
    error: Optional[str] = None
