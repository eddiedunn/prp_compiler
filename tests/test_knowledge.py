from unittest.mock import patch, MagicMock
from src.prp_compiler.knowledge import KnowledgeStore

def create_temp_knowledge_primitive(tmp_path):
    base = tmp_path / "knowledge" / "python_core" / "2.3.1" / "chunks"
    base.mkdir(parents=True)
    md_file = base / "python_basics.md"
    md_file.write_text("""
# Python Basics

## Variables

Some content about variables.

### Assignment

Details about assignment.
""")
    manifest = {
        "name": "python_core",
        "version": "2.3.1",
        "base_path": str((tmp_path / "knowledge" / "python_core" / "2.3.1").resolve()),
    }
    return manifest

def test_knowledge_store_build_and_retrieve(tmp_path):
    primitive = create_temp_knowledge_primitive(tmp_path)
    persist_dir = tmp_path / "chroma_db"
    with patch("src.prp_compiler.knowledge.OpenAIEmbeddings"), \
         patch("src.prp_compiler.knowledge.Chroma") as mock_chroma, \
         patch("src.prp_compiler.knowledge.MarkdownHeaderTextSplitter") as mock_splitter:
        mock_splitter_inst = MagicMock()
        mock_splitter.return_value = mock_splitter_inst
        mock_splitter_inst.split_text.return_value = [MagicMock(page_content="Chunk1"), MagicMock(page_content="Chunk2")]
        mock_chroma_inst = MagicMock()
        mock_chroma.from_documents.return_value = mock_chroma_inst
        store = KnowledgeStore(persist_dir)
        store.build([primitive])
        mock_splitter_inst.split_text.assert_called()
        mock_chroma.from_documents.assert_called()
        # Test retrieve
        store.db = MagicMock()
        store.db.similarity_search.return_value = [MagicMock(page_content="ChunkA"), MagicMock(page_content="ChunkB")]
        results = store.retrieve("python", k=2)
        assert results == ["ChunkA", "ChunkB"]
