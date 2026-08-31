"""文本分块：按分隔符优先级递归切分，支持重叠窗口。

设计目标：
- chunk 不超过 chunk_size（按字符数计，中文场景友好）。
- 优先在段落（\\n\\n）、行（\\n）、句末标点、空格处切分，避免切断语义。
- 相邻 chunk 之间保留 chunk_overlap 的重叠，缓解切分边界导致的信息丢失。
"""
import re

# 分隔符优先级：从粗粒度到细粒度
_SEPARATORS = ["\n\n", "\n", "。", "！", "？", " ", ""]


def split_text(text: str, chunk_size: int = 800, chunk_overlap: int = 120) -> list[str]:
    """将长文本切分为带重叠的 chunk 列表。

    Args:
        text: 待分块文本。
        chunk_size: 单个 chunk 的最大字符数。
        chunk_overlap: 相邻 chunk 的重叠字符数。

    Returns:
        chunk 文本列表；空文本返回空列表。
    """
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须小于 chunk_size")

    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = _find_split_point(text, start, chunk_size)
        chunks.append(text[start:end].strip())
        # 下一个 chunk 起点后移 overlap，保证进度向前且保留重叠
        next_start = end - chunk_overlap
        start = next_start if next_start > start else end
    return chunks


def _find_split_point(text: str, start: int, chunk_size: int) -> int:
    """在 [start, start+chunk_size] 区间内寻找最优切分点（返回该点之后的位置）。"""
    upper = min(start + chunk_size, len(text))
    window = text[start:upper]

    for sep in _SEPARATORS:
        if sep == "":
            # 无分隔符可用：硬切
            return upper
        pos = window.rfind(sep)
        if pos == -1:
            continue
        candidate = start + pos + len(sep)
        # 句子边界分隔符（。！？）保留在上一 chunk 内，避免句号被丢弃
        if sep in {"。", "！", "？"}:
            candidate = start + pos + 1
        if candidate > start:
            return candidate

    return upper


def split_document(text: str, chunk_size: int = 800, chunk_overlap: int = 120) -> list[str]:
    """文档级分块：以空行分段为基准，逐段分块。

    段落内超过 chunk_size 的超长段落交给 split_text 处理；
    短段落保持完整，减少跨段落切分造成的语义割裂。
    """
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap 必须小于 chunk_size")

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    buffer = ""
    for para in paragraphs:
        if not buffer:
            buffer = para
        elif len(buffer) + 1 + len(para) <= chunk_size:
            buffer = f"{buffer}\n\n{para}"
        else:
            chunks.extend(split_text(buffer, chunk_size, chunk_overlap))
            buffer = para
    if buffer:
        chunks.extend(split_text(buffer, chunk_size, chunk_overlap))
    return chunks
