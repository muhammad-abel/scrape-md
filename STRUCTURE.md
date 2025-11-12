# Project Structure

Project ini telah di-refactor untuk memisahkan concerns dan meningkatkan maintainability.

## Directory Structure

```
scrape-md/
├── app/                          # Application package
│   ├── __init__.py
│   ├── config.py                 # Configuration & environment variables
│   ├── main.py                   # FastAPI app & routes
│   ├── models/                   # Data models
│   │   ├── __init__.py
│   │   └── schemas.py            # Pydantic schemas (Request/Response models)
│   ├── services/                 # Business logic services
│   │   ├── __init__.py
│   │   ├── crawler_service.py    # Web crawling logic (Crawl4AI)
│   │   └── llm_service.py        # LLM integration (LiteLLM)
│   └── utils/                    # Utility functions
│       ├── __init__.py
│       ├── file_utils.py         # File operations (save markdown/HTML)
│       └── html_utils.py         # HTML tag filtering utilities
├── main.py                       # Entry point (imports from app.main)
├── main.py.old                   # Backup of original monolithic main.py
├── requirements.txt
├── .env.example
├── README.md
└── STRUCTURE.md                  # This file
```

## Modules Overview

### `app/config.py`
Manages all configuration and environment variables:
- LiteLLM Proxy settings (base URL, API key)
- Provider API keys (Anthropic, OpenAI, Gemini, OpenRouter, dll)
- HTTP Proxy settings
- Default values

**Usage:**
```python
from app.config import settings
print(settings.LITELLM_PROXY_BASE_URL)
```

### `app/models/schemas.py`
Pydantic models untuk request/response validation:
- `CrawlRequest` - Request schema untuk /crawl endpoint
- `CrawlResult` - Result schema untuk single URL crawl
- `CrawlResponse` - Response schema untuk /crawl endpoint
- `DebugCrawlResult` - Result schema untuk /debug-crawl
- `DebugCrawlResponse` - Response schema untuk /debug-crawl

### `app/services/crawler_service.py`
Web crawling business logic:
- `crawl_single_url()` - Crawl single URL dan return markdown
- `debug_crawl_single_url()` - Crawl dengan cleaned HTML untuk debugging

**Features:**
- Content filtering (content_only, excluded_tags, css_selector)
- Smart cleaning dengan LLM post-processing
- File saving integration

### `app/services/llm_service.py`
LLM integration untuk smart content cleaning:
- `clean_markdown_with_llm()` - Clean markdown menggunakan LLM
- LiteLLM Proxy support
- Multiple provider support (Claude, GPT, Gemini, OpenRouter, dll)

**Features:**
- Automatic proxy configuration dari environment variables
- Error handling & fallback
- Token usage tracking

### `app/utils/file_utils.py`
File operations:
- `sanitize_filename()` - Generate safe filename dari URL
- `save_markdown_to_file()` - Save markdown content
- `save_html_to_file()` - Save HTML content

### `app/utils/html_utils.py`
HTML processing utilities:
- `build_excluded_tags()` - Build list of HTML tags to exclude

## Running the Application

### Development
```bash
# Run with auto-reload
python main.py

# Or with uvicorn directly
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

## Benefits of New Structure

✅ **Separation of Concerns** - Logic terseparasi berdasarkan tanggung jawab
✅ **Better Testability** - Setiap module bisa di-test secara independen
✅ **Easier Maintenance** - Lebih mudah menemukan dan modify code
✅ **Scalability** - Mudah menambah features baru tanpa mengubah existing code
✅ **Code Reusability** - Utility functions bisa di-reuse di berbagai tempat
✅ **Clean Imports** - Dependency yang jelas antar modules

## Migration dari main.py Lama

Jika Anda memiliki code yang import dari `main.py` lama:

**Before:**
```python
from main import crawl_single_url, clean_markdown_with_llm
```

**After:**
```python
from app.services.crawler_service import crawl_single_url
from app.services.llm_service import clean_markdown_with_llm
```

## Adding New Features

### Menambah Endpoint Baru
Edit `app/main.py` dan tambahkan route baru:
```python
@app.post("/new-endpoint")
async def new_endpoint(request: NewRequest):
    # Your logic here
    pass
```

### Menambah Service Baru
1. Buat file baru di `app/services/` (contoh: `summary_service.py`)
2. Implement logic Anda
3. Import di route yang membutuhkan

### Menambah Utility Function
1. Buat function di `app/utils/` yang sesuai (file_utils.py, html_utils.py, atau buat baru)
2. Import di service/route yang membutuhkan

## Environment Variables

Semua environment variables di-manage di `app/config.py`. Untuk menambah config baru:

1. Tambahkan di `Settings` class di `config.py`
2. Update `.env.example`
3. Gunakan via `from app.config import settings`
