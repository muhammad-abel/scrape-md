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
