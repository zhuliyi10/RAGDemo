# 第 3 步 · 文档解析与分块

> 本章目标:把任意格式的文档变成「大小合适、语义完整、带重叠」的 chunk 列表。分块质量直接决定 RAG 检索质量,这是全项目最值得打磨的模块。

## 文档解析:`app/ingestion/loader.py`

按扩展名分派,全部基于 `BytesIO` **内存操作**,不落盘:

```python
SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".pdf", ".docx"}


def load_document(filename: str, content: bytes) -> Document:
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFormatError(
            f"不支持的文件格式: {ext},支持: {sorted(SUPPORTED_EXTENSIONS)}"
        )
    text = _parse(filename, ext, content)
    return Document(text=text, metadata={"source": filename})
```

各格式的处理细节:

| 格式 | 实现 | 细节 |
|---|---|---|
| txt / md | `content.decode("utf-8", errors="replace")` | **容错解码**:坏字节替换为 `�` 而不是抛异常,一个编码瑕疵不该让整个文档报废 |
| pdf | `pypdf.PdfReader` 逐页 `extract_text()` | 页间以 `\n\n` 拼接,保留段落边界供后续分块利用 |
| docx | `python-docx` 提取段落 | **表格按行转为 `单元格 \| 单元格` 文本**,避免表格信息静默丢失 |

不支持的格式抛 `UnsupportedFormatError(ValueError)` —— 这是个**可预期的业务异常**,在入库流水线里会被捕获并写进结果,而不是变成 500。

## 分块算法:`app/ingestion/splitter.py`

### 为什么分块是个问题

向量检索的粒度就是 chunk:块太大 → 一个块混多个主题,向量语义「糊」,检索不精确;块太小 → 上下文被切碎,答案片段孤立无据。目标:**块不超限、语义尽量完整、边界不丢信息**。

### 第一级:文档级 `split_document()` —— 段落聚合

先用空行切段,再尽量把**短段落合并**进同一个块:

```python
def split_document(text, chunk_size=800, chunk_overlap=120):
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks, buffer = [], ""
    for para in paragraphs:
        if not buffer:
            buffer = para
        elif len(buffer) + 1 + len(para) <= chunk_size:
            buffer = f"{buffer}\n\n{para}"       # 能装下就合并
        else:
            chunks.extend(split_text(buffer, chunk_size, chunk_overlap))
            buffer = para
    if buffer:
        chunks.extend(split_text(buffer, chunk_size, chunk_overlap))
    return chunks
```

短段落保持完整,避免「一个段落被拦腰切断」这种最伤语义的切法;只有超长段落才进入第二级细分。

### 第二级:文本级 `split_text()` —— 递归分隔符 + 重叠

分隔符优先级**从粗到细**:段落 → 行 → 句号 → 空格 → 硬切。

```python
_SEPARATORS = ["\n\n", "\n", "。", "!", "?", " ", ""]


def split_text(text, chunk_size=800, chunk_overlap=120):
    chunks, start = [], 0
    while start < len(text):
        end = _find_split_point(text, start, chunk_size)
        chunks.append(text[start:end].strip())
        next_start = end - chunk_overlap          # 回退重叠,保证进度向前
        start = next_start if next_start > start else end
    return chunks


def _find_split_point(text, start, chunk_size):
    upper = min(start + chunk_size, len(text))
    window = text[start:upper]
    for sep in _SEPARATORS:
        pos = window.rfind(sep)                   # 找窗口内最后一个分隔符
        if pos == -1:
            continue
        if sep in {"。", "!", "?"}:               # 句末标点切分点 = 标点后 1 字符
            candidate = start + pos + 1
        else:
            candidate = start + pos + len(sep)
        if candidate > start:
            return candidate
    return upper                                  # 无分隔符可用:硬切
```

三个精心处理的细节:

1. **`rfind` 找最后一个分隔符**:在窗口内尽量装满再切,同时保证切分点一定前进(否则死循环)
2. **句末标点保留在上一块**:`start + pos + 1`,句号跟着它的句子走,不会出现下一块开头是孤立 `。` 的尴尬
3. **重叠窗口**:`next_start = end - chunk_overlap`,相邻块共享尾部/头部内容,「答案恰好被切在边界上」时,至少有一块保有完整上下文

### 复杂度

每个 chunk 的切分点查找是 O(chunk_size × 分隔符数),与文本长度无关,整体 O(n)。

## 入库流水线:`app/ingestion/pipeline.py`

把上面三步串起来,**每步失败独立兜底**:

```python
def ingest_document(filename, content, embedding_provider, vector_store,
                    chunk_size=800, chunk_overlap=120) -> IngestionResult:
    result = IngestionResult(doc_id=uuid.uuid4().hex, source=filename)
    try:
        document = load_document(filename, content)
    except ValueError as exc:                     # 格式不支持 → 记录并返回
        result.errors.append(str(exc))
        return result

    chunks = split_document(document.text, chunk_size, chunk_overlap)
    if not chunks:
        result.errors.append("文档内容为空")
        return result

    try:
        embeddings = embedding_provider.embed(chunks)   # 批量向量化,一次请求
        vector_store.upsert_document(result.doc_id, filename, chunks, embeddings)
        result.chunks = len(chunks)
    except Exception as exc:                      # 网络/提供商异常 → 记录,不中断
        result.errors.append(str(exc))
        logger.exception("文档入库失败 %s", filename)
    return result
```

关键设计:**多文件批量入库时,单文件的任何失败只写进自己的 `errors`,不影响同请求的其他文件**。返回 `IngestionResult { doc_id, source, chunks, errors[] }`,前端能区分「格式不支持」和「提供商调用失败」。

下一步 → [第 4 步 · 向量化与存储](/guide/06-vector)
