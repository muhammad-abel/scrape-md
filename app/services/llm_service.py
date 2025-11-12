"""
LLM service for smart content cleaning using LiteLLM
"""
from typing import Dict, Any
from app.config import settings

# LLM provider via LiteLLM (optional - only imported if smart_clean is used)
try:
    from litellm import acompletion
    LITELLM_AVAILABLE = True
except ImportError:
    LITELLM_AVAILABLE = False

# OpenAI SDK for proxy compatibility
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


# System prompt for LLM content extraction
CONTENT_EXTRACTION_SYSTEM_PROMPT = """You are a content extraction assistant. Your task is to extract ONLY the main article content from the markdown below.

RULES - REMOVE THESE:
1. Navigation menus, headers, footers, breadcrumbs
2. Sidebars, advertisements, promotional banners
3. "Related posts", "You may also like", "Trending now", "Popular articles", "Recommended for you"
4. Social media widgets, share buttons, comment sections
5. Author bio/bylines (unless essential to understanding the article)
6. Newsletter signup forms, subscription prompts
7. Internal cross-links and navigational links such as:
   - "Also read:", "Read more:", "Follow our blog:", "See also:", "Check out:", "Learn more:"
   - Links to live blogs, live updates, liveblog pages
   - "Click here for...", "Visit our...", "Subscribe to..."
8. Standalone links that redirect to other articles/pages (not part of the main narrative)
9. Call-to-action buttons/links that are NOT part of the article content
10. Table of contents, jump links (unless critical for navigation within the article)
11. Disclaimer text, copyright notices, publication metadata
12. Ad markers like "Advertisement", "Sponsored", "Promoted content"

RULES - KEEP THESE:
1. The main article title and all body paragraphs
2. Images/figures that illustrate the main content
3. Inline links that are part of sentences/paragraphs and add context
4. Tables, charts, data that support the main content
5. Quotes, blockquotes from sources
6. Lists that are part of the article's core content
7. Section headers/subheadings within the article

FORMATTING:
- Preserve the original markdown formatting exactly
- Do NOT summarize, paraphrase, or rewrite - extract as-is
- If unsure whether standalone text/link is navigation or content, REMOVE it (be aggressive with removal)
- Keep only the essential article body

OUTPUT: Return ONLY the cleaned markdown, nothing else. No explanations, no comments, no metadata."""


def build_user_prompt(markdown: str) -> str:
    """
    Build user prompt for LLM content extraction

    Args:
        markdown: Raw markdown content

    Returns:
        Formatted user prompt string
    """
    return f"""Extract the main article content from this markdown:

---
{markdown}
---

Remember: Return ONLY the cleaned markdown content, nothing else. No explanations, no comments."""


async def clean_markdown_with_llm(
    markdown: str,
    model: str = "openrouter/google/gemini-2.5-flash"
) -> Dict[str, Any]:
    """
    Clean markdown content menggunakan LLM (via LiteLLM) untuk remove navbar, footer, ads, dll.

    Args:
        markdown: Raw markdown content
        model: Model name (LiteLLM auto-detects provider)
            Examples: "claude-3-5-haiku-20241022", "gpt-4o-mini", "gemini-pro", "openrouter/google/gemini-2.5-flash"

    Returns:
        Dict dengan cleaned_markdown dan metadata
        {
            "cleaned_markdown": str,
            "model": str,
            "input_tokens": int,
            "output_tokens": int,
            "success": bool,
            "error": str (if failed)
        }
    """

    # Prepare messages
    messages = [
        {"role": "system", "content": CONTENT_EXTRACTION_SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(markdown)}
    ]

    try:
        # If using LiteLLM Proxy, use OpenAI SDK for better compatibility
        if settings.LITELLM_PROXY_BASE_URL:
            if not OPENAI_AVAILABLE:
                return {
                    "cleaned_markdown": markdown,
                    "model": model,
                    "error": "OpenAI SDK not installed. Install with: pip install openai",
                    "success": False
                }

            # Use OpenAI SDK with proxy (like user's working example)
            client = AsyncOpenAI(
                api_key=settings.LITELLM_PROXY_API_KEY or "dummy-key",
                base_url=settings.LITELLM_PROXY_BASE_URL
            )

            response = await client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=16000
            )

            cleaned_markdown = response.choices[0].message.content
            usage = response.usage
            input_tokens = usage.prompt_tokens if usage else 0
            output_tokens = usage.completion_tokens if usage else 0

        else:
            # Use LiteLLM for direct provider routing
            if not LITELLM_AVAILABLE:
                return {
                    "cleaned_markdown": markdown,
                    "model": model,
                    "error": "LiteLLM not installed. Install with: pip install litellm",
                    "success": False
                }

            response = await acompletion(
                model=model,
                messages=messages,
                max_tokens=16000
            )

            cleaned_markdown = response.choices[0].message.content
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
