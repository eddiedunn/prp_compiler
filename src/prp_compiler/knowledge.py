from pathlib import Path
from typing import Any, Dict, List

from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings


class KnowledgeStore:
    """
    Manages the creation, loading, and querying of a vector database
    for Retrieval-Augmented Generation (RAG).
    """

    def __init__(self, persist_directory: Path):
        self.persist_directory = persist_directory
        # WHY: We use Google's embedding model for consistency with the main LLM.
        self.embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
        self.db: Chroma | None = None

    def build(self, knowledge_primitives: List[Dict[str, Any]]):
        """
        Builds the vector store from scratch by chunking and embedding knowledge files.

        # PATTERN: This is a one-time, expensive operation. The result is persisted
        # to disk so we don't have to run it every time.
        """
        print(f"Building knowledge store at {self.persist_directory}...")
        """Builds the vector store from scratch."""
        all_chunks = []
        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
        ]
        markdown_splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on
        )
        for primitive in knowledge_primitives:
            chunks_path = Path(primitive["base_path"]) / "chunks"
            if not chunks_path.is_dir():
                continue
            for md_file in chunks_path.rglob("*.md"):
                content = md_file.read_text()
                chunks = markdown_splitter.split_text(content)
                all_chunks.extend(chunks)
        self.db = Chroma.from_documents(
            documents=all_chunks,
            embedding=self.embeddings,
            persist_directory=str(self.persist_directory),
        )
        self.db.persist()
        print("Knowledge store built and persisted.")

    def load(self):
        """Loads an existing vector store from disk."""
        if not self.persist_directory.exists():
            raise FileNotFoundError(
                (
                    f"KnowledgeStore persist directory not found at "
                    f"{self.persist_directory}. "
                    f"Please run with '--build-knowledge' first."
                )
            )

        self.db = Chroma(
            persist_directory=str(self.persist_directory),
            embedding_function=self.embeddings,
        )
        print("Knowledge store loaded from disk.")

    def retrieve(self, query: str, k: int = 5) -> List[str]:
        """Retrieves the k most relevant document chunks for a given query."""
        if not self.db:
            raise RuntimeError(
                "KnowledgeStore is not built or loaded. Call .build() or .load() first."
            )
        print(f"Retrieving knowledge for query: '{query}'")
        docs = self.db.similarity_search(query, k=k)
        return [doc.page_content for doc in docs]
