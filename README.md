# Web Crawling Agent 🕷️

Sebuah API web crawling agent yang menggunakan **Crawl4AI** untuk mengambil konten dari halaman web dan mengonversinya menjadi format Markdown yang bersih dan siap digunakan dalam pipeline RAG atau embedding.

## ✨ Fitur

- ✅ Crawling halaman web dengan Crawl4AI
- ✅ Konversi otomatis ke format Markdown yang bersih
- ✅ Support untuk single URL atau batch crawling
- ✅ Async/concurrent processing untuk performa optimal
- ✅ **Content filtering** - Opsi untuk mengambil hanya konten utama tanpa navbar, footer, sidebar
- ✅ **Custom exclusion** - Exclude HTML tags tertentu sesuai kebutuhan
- ✅ **CSS Selector** - Target specific element dengan CSS selector
- ✅ **🤖 Smart Clean with LLM** - Post-process cleaning dengan AI (Claude/GPT) untuk website non-semantic
- ✅ Error handling untuk URL tidak valid atau halaman yang tidak dapat diakses
- ✅ Opsi untuk menyimpan hasil ke file `.md`
- ✅ Metadata lengkap (title, status code, timestamp, LLM usage)
- ✅ RESTful API dengan FastAPI

## 🚀 Instalasi

### 1. Clone repository

```bash
git clone <repository-url>
cd scrape-md
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup API Keys (Optional - hanya untuk smart_clean)

Jika ingin menggunakan fitur **smart_clean** dengan LLM:

```bash
# Copy .env.example ke .env
cp .env.example .env

# Edit .env dan tambahkan API key
# Untuk Anthropic Claude:
ANTHROPIC_API_KEY=your_key_here

# Atau untuk OpenAI GPT:
OPENAI_API_KEY=your_key_here
```

**Get API Keys:**
- Anthropic: https://console.anthropic.com/
- OpenAI: https://platform.openai.com/api-keys

### 4. Jalankan server

```bash
python main.py
```

Atau dengan uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Server akan berjalan di `http://localhost:8000`

## 📖 API Documentation

### Endpoints

#### `GET /`
Root endpoint dengan informasi API

#### `GET /health`
Health check endpoint

#### `POST /crawl`
Crawl satu atau beberapa URL dan return hasil dalam format Markdown

## 🔧 Penggunaan

### Example 1: Basic - Single URL

```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com"]
  }'
```

### Example 2: Multiple URLs

```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": [
      "https://example.com",
      "https://github.com"
    ]
  }'
```

### Example 3: Content Only Mode (🔥 NEW!)

Ambil hanya konten utama tanpa navbar, footer, sidebar, dll. **Ideal untuk RAG/embedding!**

```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com"],
    "content_only": true
  }'
```

**Tags yang otomatis di-exclude saat `content_only: true`:**
- `nav` - Navigation menu
- `footer` - Footer
- `header` - Header
- `aside` - Sidebar
- `script`, `style`, `noscript` - Scripts & styles
- `iframe` - iFrames
- `button`, `input`, `select`, `textarea` - Form elements
- `figure` - Figures (biasanya ads)

### Example 4: Custom Excluded Tags

Exclude tags tertentu sesuai kebutuhan:

```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com"],
    "excluded_tags": ["nav", "footer", "aside"]
  }'
```

### Example 5: CSS Selector - Target Specific Element

Ambil hanya element tertentu menggunakan CSS selector:

```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com"],
    "css_selector": "article.main-content"
  }'
```

**Contoh CSS selectors:**
- `"article"` - Semua tag `<article>`
- `"#main-content"` - Element dengan ID `main-content`
- `".post-content"` - Element dengan class `post-content`
- `"div.container > article"` - Article dalam container

### Example 6: Smart Clean with LLM (🔥 NEW!)

Gunakan AI untuk automatically clean content - **Perfect untuk website non-semantic HTML!**

```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://www.moneycontrol.com/news/..."],
    "smart_clean": true
  }'
```

**Kenapa pakai smart_clean?**
- ✅ Otomatis detect dan remove navbar, footer, ads, related posts
- ✅ Works untuk website yang tidak pakai semantic HTML (`<nav>`, `<footer>`, dll)
- ✅ Context-aware cleaning (AI understands content vs noise)
- ✅ Ideal untuk website lama atau custom structure

**Default:** Claude 3.5 Haiku (fast & cheap: ~$0.001 per request)

### Example 7: Smart Clean with Different Models

**Powered by LiteLLM** - Switch models easily, auto-routing to correct provider!

```bash
# GPT-4o-mini (OpenAI)
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com"],
    "smart_clean": true,
    "llm_model": "gpt-4o-mini"
  }'

# Gemini Pro (Google)
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com"],
    "smart_clean": true,
    "llm_model": "gemini-pro"
  }'

# Claude Sonnet (more powerful)
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com"],
    "smart_clean": true,
    "llm_model": "claude-3-5-sonnet-20241022"
  }'
```

### Example 8: Kombinasi Semua Fitur

Gabungkan pre-filter + LLM cleaning untuk hasil terbaik:

```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com"],
    "content_only": true,
    "smart_clean": true,
    "save_to_file": true,
    "output_dir": "output_markdown"
  }'
```

**Flow:** Pre-filter HTML tags → Crawl → LLM post-process → Clean markdown!

### Request Body Schema

```json
{
  "urls": ["string"],                    // Required: List URL yang akan di-crawl
  "save_to_file": false,                 // Optional: Simpan hasil ke file .md
  "output_dir": "output_markdown",       // Optional: Direktori output

  // Content filtering (pre-crawl)
  "content_only": false,                 // Optional: Ambil hanya konten utama
  "excluded_tags": ["nav", "footer"],    // Optional: Custom tags yang di-exclude
  "css_selector": "article",             // Optional: CSS selector untuk target element

  // Smart cleaning (post-crawl with LLM via LiteLLM)
  "smart_clean": false,                  // Optional: Clean dengan AI
  "llm_model": "claude-3-5-haiku-20241022" // Optional: Model name (auto-routes to provider)
}
```

**Cleaning Strategy:**
- **Pre-crawl filtering:** `css_selector` > `excluded_tags` > `content_only`
- **Post-crawl cleaning:** `smart_clean` (AI-powered, most flexible)

**Supported Models (via LiteLLM):**
- Anthropic: `claude-3-5-haiku-20241022`, `claude-3-5-sonnet-20241022`
- OpenAI: `gpt-4o-mini`, `gpt-4o`, `gpt-3.5-turbo`
- Google: `gemini-pro`, `gemini-1.5-pro`
- Cohere: `command`, `command-light`
- And 100+ more! See: https://docs.litellm.ai/docs/providers

### Response Schema

```json
{
  "results": [
    {
      "url": "string",
      "markdown": "string",  // Cleaned markdown content
      "metadata": {
        "title": "string",
        "status_code": 200,
        "fetched_at": "2025-11-12T13:55:00Z",
        "success": true,
        "url": "string",
        "excluded_tags": ["form", "nav", "footer"],
        "css_selector": null,
        // LLM metadata (jika smart_clean=true)
        "llm_model": "claude-3-5-haiku-20241022",
        "input_tokens": 5243,
        "output_tokens": 2156,
        "llm_cleaning": "success"
      },
      "status": "success",
      "file_path": "output_markdown/example_com.md"
    }
  ],
  "total_urls": 1,
  "successful": 1,
  "failed": 0
}
```

## 📝 Contoh Response

```json
{
  "results": [
    {
      "url": "https://jdih.esdm.go.id/index.php/web/home/detail/19912",
      "markdown": "# Peraturan Menteri ESDM Nomor 12 Tahun 2021\n\n## Tentang\nPemanfaatan Energi Terbarukan...",
      "metadata": {
        "title": "Permen ESDM No. 12 Tahun 2021",
        "status_code": 200,
        "fetched_at": "2025-11-12T13:55:00Z",
        "success": true
      },
      "status": "success",
      "file_path": "output_markdown/jdih_esdm_go_id_index_php_web_home_detail_19912.md"
    }
  ],
  "total_urls": 1,
  "successful": 1,
  "failed": 0
}
```

## 🛠️ Teknologi yang Digunakan

- **FastAPI** - Modern web framework untuk Python
- **Crawl4AI** - Library untuk web crawling dan scraping
- **LiteLLM** - Unified interface untuk 100+ LLM providers
- **Pydantic** - Data validation menggunakan Python type hints
- **Uvicorn** - ASGI server

## 📂 Struktur Project

```
scrape-md/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── prp.md              # Spesifikasi agent
├── README.md           # Dokumentasi
└── output_markdown/    # Folder untuk hasil crawling (auto-created)
```

## ⚙️ Content Filtering Options

### Pre-Crawl Filtering (HTML-based)

#### 1. Content Only Mode
Set `content_only: true` untuk mengaktifkan preset clean content:
```json
{"urls": ["..."], "content_only": true}
```
Otomatis exclude: nav, footer, header, aside, script, style, iframe, button, input, select, textarea, figure

#### 2. Custom Excluded Tags
Specify tags tertentu yang mau di-exclude:
```json
{"urls": ["..."], "excluded_tags": ["nav", "footer", "aside"]}
```

#### 3. CSS Selector
Target element tertentu dengan CSS selector:
```json
{"urls": ["..."], "css_selector": "article.main-content"}
```

**Priority:** `css_selector` > `excluded_tags` > `content_only`

---

### 🤖 Post-Crawl Smart Cleaning (AI-powered via LiteLLM)

**Perfect untuk website dengan struktur non-standard!**

```json
{"urls": ["..."], "smart_clean": true}
```

**How it works:**
1. Crawl halaman (dengan atau tanpa pre-filtering)
2. Convert ke markdown
3. Pass ke LLM via **LiteLLM** dengan prompt khusus
4. LLM analyze dan remove navigation, ads, related posts, dll
5. Return cleaned markdown

**Advantages:**
- ✅ Works untuk ANY website structure
- ✅ Semantic understanding (AI knows content vs noise)
- ✅ No need to analyze HTML structure
- ✅ Handles dynamic/custom layouts
- ✅ **100+ models** supported via LiteLLM
- ✅ **Easy switching** between providers

**Cost & Speed:**
- Claude 3.5 Haiku: ~$0.001 per request, ~3-5s latency
- GPT-4o-mini: ~$0.002 per request, ~3-5s latency
- Gemini Pro: ~$0.0001 per request, ~2-4s latency

**When to use:**
- Website tidak pakai semantic HTML
- Custom/unique layouts
- High-quality extraction lebih penting dari speed
- Budget ada untuk LLM API calls

**Popular Models (LiteLLM auto-routes):**
- `claude-3-5-haiku-20241022` (default, fast & cheap)
- `claude-3-5-sonnet-20241022` (more powerful)
- `gpt-4o-mini` (OpenAI, good quality)
- `gpt-4o` (highest quality, expensive)
- `gemini-pro` (Google, very cheap)
- `command` (Cohere)

See all: https://docs.litellm.ai/docs/providers

## ⚙️ Default Crawl4AI Configuration

- `word_count_threshold=10` - Minimum jumlah kata
- `excluded_tags=[...]` - Tag HTML yang diabaikan (dynamic based on options)
- `remove_overlay_elements=True` - Hapus elemen overlay/popup

## 🔒 Error Handling

API ini menangani berbagai error case:
- ❌ URL tidak valid → Validation error
- ❌ Halaman tidak dapat diakses → Status "failed" dengan error message
- ❌ Timeout atau network error → Status "failed" dengan detail error

## 📄 License

MIT License

## 🤝 Contributing

Contributions, issues, and feature requests are welcome!

## 👤 Author

Created as a web crawling agent for RAG and embedding pipelines.
