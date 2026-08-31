"""文档加载器单元测试。"""
import pytest

from app.ingestion.loader import (
    SUPPORTED_EXTENSIONS,
    Document,
    UnsupportedFormatError,
    load_document,
)


class TestLoadDocument:
    def test_txt(self):
        doc: Document = load_document("readme.txt", "你好世界".encode("utf-8"))
        assert doc.text == "你好世界"
        assert doc.metadata == {"source": "readme.txt"}

    def test_markdown(self):
        content = "# 标题\n\n正文内容".encode("utf-8")
        doc = load_document("doc.md", content)
        assert doc.text == "# 标题\n\n正文内容"

    def test_unsupported_format(self):
        with pytest.raises(UnsupportedFormatError):
            load_document("data.csv", b"a,b\n1,2")

    def test_supported_extensions(self):
        assert {".txt", ".md", ".markdown", ".pdf", ".docx"} <= SUPPORTED_EXTENSIONS
