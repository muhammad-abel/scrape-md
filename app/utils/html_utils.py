"""
HTML utilities for building excluded tags and content filtering
"""
from typing import List, Optional


def build_excluded_tags(content_only: bool = False, custom_tags: Optional[List[str]] = None) -> List[str]:
    """
    Build list of HTML tags yang akan di-exclude dari crawling

    Args:
        content_only: Jika True, gunakan preset tags untuk clean content
        custom_tags: Additional tags yang mau di-exclude

    Returns:
        List of tags yang akan di-exclude
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
