#!/usr/bin/env python

import sys
from pathlib import Path

# Add project root to Python path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

print("SCRIPT STARTED")


def ingest_project_docs(max_docs: int = 1000) -> int:
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from services.postgres_vectorstore import PostgresVectorStore
    except ImportError as e:
        print(f"❌ Import Error: {e}")
        return 0

    try:
        repo_root = PROJECT_ROOT
        print(f"\n📂 Project Root: {repo_root}")

        # Initialize vector store (auto-creates table)
        vector_store = PostgresVectorStore()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50,
        )

        docs_added = 0
        files_found = 0

        allowed_extensions = {".py", ".md", ".txt", ".json", ".yaml", ".yml"}

        ignored_dirs = {
            "__pycache__", ".git", ".venv", "venv",
            "node_modules", ".idea", ".vscode",
        }

        print("\n🔍 Searching project files...\n")

        for file_path in repo_root.rglob("*"):
            if not file_path.is_file():
                continue
            if any(part in ignored_dirs for part in file_path.parts):
                continue
            if file_path.suffix.lower() not in allowed_extensions:
                continue

            files_found += 1
            print(f"📄 Processing: {file_path.relative_to(repo_root)}")

            try:
                text = file_path.read_text(encoding="utf-8", errors="ignore")

                if not text.strip():
                    continue

                chunks = splitter.split_text(text)

                for chunk in chunks:
                    if not chunk.strip():
                        continue

                    success = vector_store.add_text(
                        chunk,
                        document_name=str(file_path),
                        metadata={"source": str(file_path)}
                    )

                    if success:
                        docs_added += 1

                        if docs_added % 50 == 0:
                            print(f"✅ {docs_added} chunks indexed")

                        if docs_added >= max_docs:
                            print(f"\n🎉 Reached max_docs={max_docs}")
                            return docs_added

            except Exception as e:
                print(f"⚠️ Failed: {file_path}")
                print(f"   Error: {e}")

        print("\n============================")
        print(f"Files Found : {files_found}")
        print(f"Chunks Added: {docs_added}")
        print("============================")

        return docs_added

    except Exception as e:
        print(f"❌ Ingestion Error: {e}")
        return 0


if __name__ == "__main__":
    print("\n🚀 Starting RAG document ingestion...\n")

    docs_ingested = ingest_project_docs(max_docs=1000)

    print(f"\nReturned: {docs_ingested}")

    if docs_ingested > 0:
        print(f"\n✅ Successfully ingested {docs_ingested} document chunks!")
        print("🎉 RAG is ready.")
    else:
        print("\n⚠️ No documents ingested.")