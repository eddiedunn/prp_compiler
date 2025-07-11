from pathlib import Path
from typing import List, Dict, Any
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import MarkdownHeaderTextSplitter
from langchain_community.vectorstores import Chroma

class KnowledgeStore:
    def __init__(self, persist_directory: Path):
        self.persist_directory = persist_directory
        self.embeddings = OpenAIEmbeddings() # Assumes OPENAI_API_KEY is in env
        self.chroma: Chroma | None = None # Will be initialized by build() or load()

    def build(self, knowledge_primitives: List[Dict[str, Any]]):
        """Builds the vector store from scratch."""
        all_chunks = []
        headers_to_split_on = [("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3")]
        markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
        for primitive in knowledge_primitives:
            chunks_path = Path(primitive['base_path']) / "chunks"
            if not chunks_path.is_dir():
                continue
            for md_file in chunks_path.rglob("*.md"):
                content = md_file.read_text()
                chunks = markdown_splitter.split_text(content)
                all_chunks.extend(chunks)
        self.chroma = Chroma.from_documents(
            documents=all_chunks,
            embedding=self.embeddings,
            persist_directory=str(self.persist_directory)
        )
        if self.chroma is not None:
            self.chroma.persist()

    def load(self):
        """Loads the vector store from disk."""
        if not self.persist_directory.exists():
            raise FileNotFoundError("KnowledgeStore persist directory not found.")
        self.chroma = Chroma(
            persist_directory=str(self.persist_directory),
            embedding_function=self.embeddings
        )
    
    def retrieve(self, query: str, k: int = 5) -> List[str]:
        """Retrieves the k most relevant document chunks for a query."""
        if not self.chroma:
            raise RuntimeError("KnowledgeStore is not built or loaded.")
        docs = self.chroma.similarity_search(query, k=k)
        return [doc.page_content for doc in docs]
