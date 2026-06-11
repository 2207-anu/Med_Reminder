"""RAG Management Router - Uses Gemini API + Free Embeddings"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from auth import require_admin
from services.gemini import ingest_project_docs

router = APIRouter(prefix="/api/rag", tags=["rag"])


class IngestResponse(BaseModel):
    success: bool
    message: str
    docs_ingested: int = 0


@router.post("/ingest")
def trigger_rag_ingestion(user: dict = Depends(require_admin)) -> IngestResponse:
    """Manually trigger document ingestion into RAG vector store."""
    try:
        docs = ingest_project_docs(max_docs=500)
        return IngestResponse(
            success=True,
            message=f"✅ Successfully ingested {docs} document chunks into PostgreSQL vector store",
            docs_ingested=docs
        )
    except Exception as e:
        return IngestResponse(
            success=False,
            message=f"❌ Ingestion failed: {str(e)}",
            docs_ingested=0
        )


@router.get("/status")
def rag_status(user: dict = Depends(require_admin)):
    """Check RAG system status."""
    try:
        from services.postgres_vectorstore import PostgresVectorStore, PGVECTOR_AVAILABLE
        
        if not PGVECTOR_AVAILABLE:
            return {
                "rag_enabled": False,
                "error": "pgvector not installed",
                "message": "pgvector extension not available. Install with: pip install pgvector"
            }
        
        vector_store = PostgresVectorStore()
        stats = vector_store.get_stats()
        
        return {
            "rag_enabled": True,
            "embedding_model": "sentence-transformers (all-MiniLM-L6-v2)",
            "llm": "Gemini",
            "vector_store": "PostgreSQL with pgvector",
            "vector_store_exists": True,
            "total_documents": stats.get("total_documents", 0),
            "vector_dimension": stats.get("vector_dimension", 384),
            "message": "RAG is active with Gemini API + PostgreSQL vector store"
        }
    except Exception as e:
        return {
            "rag_enabled": False,
            "error": str(e),
            "message": "Failed to connect to PostgreSQL vector store"
        }
