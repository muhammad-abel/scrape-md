"""
File utilities for saving crawled content
"""
import os
import re
from pathlib import Path


def sanitize_filename(url: str) -> str:
    """
    Membuat nama file yang aman dari URL

    Args:
        url: URL string

    Returns:
        Safe filename string
    """
    # Hapus protocol
    name = re.sub(r'^https?://', '', url)
    # Replace karakter tidak valid dengan underscore
    name = re.sub(r'[^\w\-\.]', '_', name)
    # Batasi panjang filename
    if len(name) > 200:
        name = name[:200]
    return f"{name}.md"


async def save_markdown_to_file(content: str, url: str, output_dir: str) -> str:
    """
    Menyimpan konten Markdown ke file

    Args:
        content: Markdown content string
        url: Original URL (untuk generate filename)
        output_dir: Output directory path

    Returns:
        Path to saved file
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

    Args:
        content: HTML content string
        url: Original URL (untuk generate filename)
        output_dir: Output directory path

    Returns:
        Path to saved file
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
