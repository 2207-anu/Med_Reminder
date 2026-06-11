"""
PostgreSQL Vector Store for RAG - No pgvector extension required.

Stores embeddings as JSON arrays in PostgreSQL and does similarity
search in Python using numpy. Works with any PostgreSQL version.
"""

import json
import numpy as np
import psycopg2
import psycopg2.extras

from sentence_transformers import SentenceTransformer
from config import DB_CONFIG

# pgvector is optional - we don't need it anymore
PGVECTOR_AVAILABLE = False
try:
    from pgvector.psycopg2 import register_vector
    PGVECTOR_AVAILABLE = True
except ImportError:
    pass  # Fine - we use JSON-based storage instead


class PostgresVectorStore:
    """Vector store using PostgreSQL with JSON-based embedding storage.
    No pgvector extension required."""

    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        """Initialize the vector store with embedding model."""
        self.embedding_model = embedding_model
        self.embedder = SentenceTransformer(embedding_model)
        self._ensure_table()

    def _ensure_table(self):
        """Create the rag_documents table if it doesn't exist."""
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cur = conn.cursor()
            cur.execute("""
                CREATE TABLE IF NOT EXISTS rag_documents (
                    id SERIAL PRIMARY KEY,
                    document_name TEXT NOT NULL,
                    content TEXT NOT NULL,
                    embedding JSONB NOT NULL,
                    metadata JSONB DEFAULT '{}'
                )
            """)
            conn.commit()
            cur.close()
            conn.close()
            print("✅ PostgreSQL vector store initialized")
        except Exception as e:
            print(f"❌ Failed to initialize table: {e}")

    def get_connection(self):
        """Get a database connection."""
        return psycopg2.connect(**DB_CONFIG)

    def add_text(self, text: str, document_name: str, metadata: dict = None) -> bool:
        """Add a text chunk to the vector store."""
        try:
            # Generate embedding and store as JSON array
            embedding = self.embedder.encode(text, convert_to_numpy=True).tolist()

            conn = self.get_connection()
            cur = conn.cursor()

            cur.execute(
                """
                INSERT INTO rag_documents (document_name, content, embedding, metadata)
                VALUES (%s, %s, %s::jsonb, %s)
                """,
                (
                    document_name,
                    text,
                    json.dumps(embedding),
                    psycopg2.extras.Json(metadata or {})
                )
            )

            conn.commit()
            cur.close()
            conn.close()
            return True

        except Exception as e:
            print(f"❌ Error adding text to vector store: {e}")
            return False

    def add_texts(self, texts: list, document_name: str, metadatas: list = None) -> int:
        """Add multiple text chunks to the vector store."""
        added = 0
        for i, text in enumerate(texts):
            metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
            if self.add_text(text, document_name, metadata):
                added += 1
        return added

    def similarity_search(self, query: str, k: int = 3) -> list:
        """Search for similar documents using cosine similarity in Python."""
        try:
            # Generate query embedding
            query_embedding = self.embedder.encode(query, convert_to_numpy=True)
            query_norm = query_embedding / (np.linalg.norm(query_embedding) + 1e-10)

            conn = self.get_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

            # Fetch all documents (for small-medium datasets this is fine)
            cur.execute("SELECT id, document_name, content, embedding FROM rag_documents")
            rows = cur.fetchall()
            cur.close()
            conn.close()

            if not rows:
                return []

            # Compute cosine similarity in Python
            scored = []
            for row in rows:
                emb = np.array(json.loads(row['embedding']), dtype=np.float32)
                emb_norm = emb / (np.linalg.norm(emb) + 1e-10)
                score = float(np.dot(query_norm, emb_norm))
                scored.append((score, row['content']))

            # Sort by similarity descending and return top k
            scored.sort(key=lambda x: x[0], reverse=True)
            return [content for _, content in scored[:k]]

        except Exception as e:
            print(f"❌ Error searching vector store: {e}")
            return []

    def clear(self) -> bool:
        """Clear all documents from the vector store."""
        try:
            conn = self.get_connection()
            cur = conn.cursor()
            cur.execute("DELETE FROM rag_documents")
            conn.commit()
            cur.close()
            conn.close()
            return True
        except Exception as e:
            print(f"❌ Error clearing vector store: {e}")
            return False

    def get_stats(self) -> dict:
        """Get statistics about the vector store."""
        try:
            conn = self.get_connection()
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cur.execute("SELECT COUNT(*) as total_docs FROM rag_documents")
            result = cur.fetchone()
            cur.close()
            conn.close()
            return {
                "total_documents": result['total_docs'],
                "embedding_model": self.embedding_model,
                "vector_dimension": 384
            }
        except Exception:
            return {}