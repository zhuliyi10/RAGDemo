"""分块器单元测试。"""
import pytest

from app.ingestion.splitter import split_document, split_text


class TestSplitText:
    def test_short_text_single_chunk(self):
        assert split_text("你好世界", chunk_size=50, chunk_overlap=0) == ["你好世界"]

    def test_empty_text_returns_empty(self):
        assert split_text("   ") == []

    def test_chunk_size_not_exceeded(self):
        text = "这是一段测试文本。" * 100
        chunks = split_text(text, chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 1
        assert all(len(c) <= 100 for c in chunks)

    def test_overlap_preserved(self):
        text = "段落一内容。" * 50 + "\n" + "段落二内容。" * 50
        chunks = split_text(text, chunk_size=100, chunk_overlap=30)
        assert len(chunks) > 1
        # 相邻 chunk 应存在重叠内容（字符层面）
        assert chunks[0][-30:] in chunks[1] or chunks[0][-10:] in chunks[1]

    def test_chinese_sentence_boundary_kept(self):
        # 中文句号后切分时，句号应保留在上一 chunk
        text = "第一句。" + "长内容" * 40 + "第二句。" + "长内容" * 40
        chunks = split_text(text, chunk_size=60, chunk_overlap=0)
        assert all("。" in c or len(c) == 60 for c in chunks)

    def test_invalid_overlap_raises(self):
        with pytest.raises(ValueError):
            split_text("abc", chunk_size=10, chunk_overlap=10)

    def test_long_word_hard_split(self):
        text = "x" * 200
        chunks = split_text(text, chunk_size=80, chunk_overlap=0)
        assert all(len(c) <= 80 for c in chunks)
        assert "".join(chunks) == text


class TestSplitDocument:
    def test_paragraphs_merged_under_size(self):
        text = "第一段内容。\n\n第二段内容。\n\n第三段内容。"
        chunks = split_document(text, chunk_size=200, chunk_overlap=0)
        # 全部可合并为一个 chunk
        assert chunks == [text]

    def test_long_paragraph_split(self):
        para = "很长的一句话" * 50
        text = f"短段落。\n\n{para}"
        chunks = split_document(text, chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 1
        assert all(len(c) <= 100 for c in chunks)

    def test_empty_document(self):
        assert split_document("\n\n  \n") == []
