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
- ✅ Error handling untuk URL tidak valid atau halaman yang tidak dapat diakses
- ✅ Opsi untuk menyimpan hasil ke file `.md`
- ✅ Metadata lengkap (title, status code, timestamp)
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

### 3. Jalankan server

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

### Example 6: Kombinasi + Save to File

Gabungkan semua opsi untuk hasil maksimal:

```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com"],
    "content_only": true,
    "excluded_tags": ["figure", "img"],
    "save_to_file": true,
    "output_dir": "output_markdown"
  }'
```

### Request Body Schema

```json
{
  "urls": ["string"],                    // Required: List URL yang akan di-crawl
  "save_to_file": false,                 // Optional: Simpan hasil ke file .md
  "output_dir": "output_markdown",       // Optional: Direktori output
  "content_only": false,                 // Optional: Ambil hanya konten utama
  "excluded_tags": ["nav", "footer"],    // Optional: Custom tags yang di-exclude
  "css_selector": "article"              // Optional: CSS selector untuk target element
}
```

**Parameter Priority:**
- `css_selector` (highest) - Jika ada, hanya ambil element yang match
- `excluded_tags` - Custom tags ditambahkan ke daftar exclusion
- `content_only` - Preset exclusion untuk konten bersih

### Response Schema

```json
{
  "results": [
    {
      "url": "string",
      "markdown": "string",
      "metadata": {
        "title": "string",
        "status_code": 200,
        "fetched_at": "2025-11-12T13:55:00Z",
        "success": true,
        "url": "string",
        "excluded_tags": ["form", "nav", "footer"],
        "css_selector": null
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

### 1. Content Only Mode
Set `content_only: true` untuk mengaktifkan preset clean content:
```json
{"urls": ["..."], "content_only": true}
```
Otomatis exclude: nav, footer, header, aside, script, style, iframe, button, input, select, textarea, figure

### 2. Custom Excluded Tags
Specify tags tertentu yang mau di-exclude:
```json
{"urls": ["..."], "excluded_tags": ["nav", "footer", "aside"]}
```

### 3. CSS Selector
Target element tertentu dengan CSS selector:
```json
{"urls": ["..."], "css_selector": "article.main-content"}
```

### Kombinasi
Semua opsi bisa digabung dengan priority: `css_selector` > `excluded_tags` > `content_only`

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
