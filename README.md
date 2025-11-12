# Web Crawling Agent 🕷️

Sebuah API web crawling agent yang menggunakan **Crawl4AI** untuk mengambil konten dari halaman web dan mengonversinya menjadi format Markdown yang bersih dan siap digunakan dalam pipeline RAG atau embedding.

## ✨ Fitur

- ✅ Crawling halaman web dengan Crawl4AI
- ✅ Konversi otomatis ke format Markdown yang bersih
- ✅ Support untuk single URL atau batch crawling
- ✅ Async/concurrent processing untuk performa optimal
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

### Example 1: Single URL

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

### Example 3: Dengan menyimpan ke file

```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "urls": ["https://example.com"],
    "save_to_file": true,
    "output_dir": "output_markdown"
  }'
```

### Request Body Schema

```json
{
  "urls": ["string"],           // Required: List URL yang akan di-crawl
  "save_to_file": false,        // Optional: Simpan hasil ke file .md
  "output_dir": "output_markdown" // Optional: Direktori output
}
```

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
        "success": true
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

## ⚙️ Konfigurasi Crawl4AI

Agent ini menggunakan konfigurasi berikut:
- `word_count_threshold=10` - Minimum jumlah kata
- `excluded_tags=['form', 'nav']` - Tag HTML yang diabaikan
- `remove_overlay_elements=True` - Hapus elemen overlay

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
