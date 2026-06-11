# Real RAG Setup Guide (Gemini API + PostgreSQL Vector Store)

Your project now has **production-grade RAG** integrated with your **Gemini API** and **PostgreSQL**!

## What's Included

- **Embeddings**: sentence-transformers `all-MiniLM-L6-v2` (FREE, no API key needed)
- **Vector Database**: PostgreSQL with pgvector extension (same database as your app data!)
- **LLM**: Gemini API (via your existing GEMINI_API_KEY)
- **Automatic Ingestion**: documents are indexed on app startup
- **Manual Control**: CLI script + API endpoint for on-demand ingestion

---

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Initialize Database with RAG Tables

PostgreSQL and pgvector will be automatically set up when you run:
```bash
python App.py
# or
python main.py
```

The app will automatically:
- Create the `pgvector` extension
- Create the `rag_documents` table
- Create necessary indexes for fast vector similarity search

### 3. You're Ready! (Your GEMINI_API_KEY is already in .env)

No additional API keys needed. Just use your existing `GEMINI_API_KEY`.

### 4. Ingest Project Docs (Two Options)

**Option A: Automatic (on app startup)**
```bash
python main.py
# RAG will automatically ingest docs when the app starts
```

**Option B: Manual CLI**
```bash
python scripts/ingest_rag_docs.py
```

**Option C: API Endpoint** (admin only)
```bash
curl -X POST http://localhost:8000/api/rag/ingest \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json"
```

---

## How RAG Works in Your App

When a user asks a question in the **Chatbot** tab:

1. **Question Vector** — converted to embedding using FREE sentence-transformers
2. **Semantic Search** — PostgreSQL pgvector finds top 3 similar docs from your project
3. **Context Augmentation** — retrieved docs + prescription context sent to Gemini
4. **Smart Answer** — Gemini generates answer using all context

Example:
```
User: "How do patient reminders work?"
↓
RAG retrieves relevant snippets using vector similarity:
  - /pages/admin_sections/email_reminder.py
  - /routers/emails_router.py
  - /services/email_service.py
↓
Answer includes actual code context from your project
```

---

## Endpoints

### Trigger Ingestion
```bash
POST /api/rag/ingest
Response: { success, message, docs_ingested }
```

### Check RAG Status
```bash
GET /api/rag/status
Response: { rag_enabled, embedding_model, llm, vector_store_exists, ... }
```

---

## Files Created/Updated

| File | Change |
|------|--------|
| `requirements.txt` | Replaced: chromadb → pgvector; added langchain, sentence-transformers, langchain-community |
| `db_postgres.py` | Added: pgvector extension setup, `rag_documents` table, vector indexes |
| `services/postgres_vectorstore.py` | **NEW**: PostgreSQL vector store class with add_text(), similarity_search(), get_stats() |
| `services/gemini.py` | Updated: `ingest_project_docs()` uses PostgreSQL, `_retrieve_docs()` uses pgvector |
| `routers/rag_router.py` | Updated: `/api/rag/ingest`, `/api/rag/status` now return PostgreSQL stats |
| `scripts/ingest_rag_docs.py` | Updated: References PostgreSQL vector store |

---

## Troubleshooting

### "No documents ingested"
- Verify project structure (`pages/`, `routers/`, `services/`, `scripts/` exist)
- Check PostgreSQL connection in `config.DB_CONFIG`
- Run: `python scripts/ingest_rag_docs.py` manually with verbose output

### Slow ingestion?
- First run: 30-60 seconds (downloading + running embedding model)
- Building pgvector indexes takes time on large datasets
- Check: `GET /api/rag/status` to see total documents ingested

### Want to reset vector store?
```bash
# Connect to PostgreSQL and run:
DELETE FROM rag_documents;

# Then reingest:
python scripts/ingest_rag_docs.py
```

### PostgreSQL pgvector not found?
```bash
# Ensure pgvector is installed:
pip install pgvector

# Your PostgreSQL must have pgvector extension available
# On Linux: sudo apt install postgresql-15-pgvector
# On macOS: brew install pgvector
```

---

## Performance Notes

- **Embedding Cost**: FREE (sentence-transformers is local)
- **Vector DB**: PostgreSQL pgvector (same database as your app data)
- **Query Speed**: ~50-200ms per RAG query (depends on index size)
- **Storage**: Vector embeddings stored in same PostgreSQL instance
- **Indexing**: Uses IvfFlat for fast approximate nearest neighbor search
- **Scalability**: Handles thousands of documents efficiently
- **LLM Cost**: Uses your existing Gemini API quota

---

## Next Steps

1. **Test the setup**:
   ```bash
   python scripts/ingest_rag_docs.py  # Ingest project docs
   python main.py                      # Start app with RAG enabled
   ```

2. **Monitor system**:
   - Check `/api/rag/status` endpoint for vector store health
   - View total documents ingested and vector dimension

3. **Customize RAG**:
   - Adjust `top_k=3` in `services/postgres_vectorstore.py` to retrieve more/fewer docs
   - Customize chunk size (500 chars) in `services/gemini.py` for different context windows
   - Modify search directories in `ingest_project_docs()`

4. **Production tips**:
   - Create PostgreSQL backups regularly
   - Monitor index usage with: `SELECT * FROM pg_indexes WHERE tablename='rag_documents';`
   - Consider REINDEX for performance after many deletions

Enjoy your production-grade RAG with PostgreSQL + Gemini! 🚀
