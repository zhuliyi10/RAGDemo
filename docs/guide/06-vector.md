# 第 4 步 · 向量化与存储

> 本章目标:用 ChromaDB 把 chunk 与向量持久化到本地磁盘,并通过一套 ID/metadata 约定,实现「按文档整体删除」与「答案溯源」。

## 存储:`app/retrieval/vector_store.py`

### 初始化:本地持久化 + cosine 相似度

```python
COLLECTION_NAME = "rag_docs"


class VectorStore:
    def __init__(self, persist_dir: Path, collection_name: str = COLLECTION_NAME):
        persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = PersistentClient(path=str(persist_dir))
        self._collection: Collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},     # 显式指定余弦距离
        )
```

`PersistentClient` 让数据落盘到 `data/chroma/`,重启服务数据还在,零部署。`hnsw:space=cosine` 是**创建 collection 时的决定**,后期不可改 —— 文本语义检索的默认正确选择。

### 数据模型:一套约定实现文档管理

```python
def upsert_document(self, doc_id, source, chunks, embeddings) -> None:
    ids = [f"{doc_id}::{i}" for i in range(len(chunks))]
    metadatas = [
        {"doc_id": doc_id, "source": source, "chunk_index": i}
        for i in range(len(chunks))
    ]
    self._collection.upsert(ids=ids, documents=chunks,
                            embeddings=embeddings, metadatas=metadatas)
```

- **ID 约定**:`"{doc_id}::{chunk_index}"`
- **metadata**:`{doc_id, source, chunk_index}`

这一套约定换来三个能力,而无需任何额外的文档索引表:

**① 按文档整体删除**(先查后删,幂等):

```python
def delete_document(self, doc_id: str) -> None:
    hits = self._collection.get(where={"doc_id": doc_id}, include=[])
    if hits["ids"]:
        self._collection.delete(ids=hits["ids"])
```

**② 文档列表与分块计数**(内存聚合,单一数据源):

```python
def list_documents(self) -> list[dict]:
    hits = self._collection.get(include=["metadatas"])
    stats: dict[str, dict] = {}
    for meta in hits["metadatas"]:
        entry = stats.setdefault(meta["doc_id"],
                                 {"doc_id": meta["doc_id"], "source": meta["source"], "chunks": 0})
        entry["chunks"] += 1
    return sorted(stats.values(), key=lambda e: e["doc_id"])
```

**③ 来源溯源**:每个命中都自带 `source`(原始文件名),回答页可以展示「这句话出自哪个文档」。

### 查询与相似度换算

```python
def query(self, query_embedding, top_k, where=None) -> list[dict]:
    if self._collection.count() == 0:
        return []                                    # 空库快速返回
    result = self._collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
        include=["documents", "metadatas", "distances"],
    )
    return self._to_hits(result)

@staticmethod
def _to_hits(result):
    ...
    hits.append({
        "chunk_id": chunk_id, "content": doc,
        "doc_id": meta["doc_id"], "source": meta["source"],
        "chunk_index": meta["chunk_index"],
        "similarity": round(1 - distance, 4),        # cosine 距离 → 相似度
    })
```

ChromaDB 返回的是**距离**(越小越相关),对外统一转成**相似度**(越大越相关):`similarity = 1 - distance`,保留 4 位小数。所有下游(生成层、前端)面对的是同一种语义,不用各自换算。

## 检索:`app/retrieval/retriever.py`

检索器是查询侧的薄封装,只做一件事:把「字符串问题」变成「向量检索」:

```python
class Retriever:
    def __init__(self, embedding_provider: EmbeddingProvider, vector_store: VectorStore):
        self._embedding_provider = embedding_provider
        self._vector_store = vector_store

    def retrieve(self, query: str, top_k: int = 4) -> list[dict]:
        query_embedding = self._embedding_provider.embed([query])[0]
        return self._vector_store.query(query_embedding, top_k)
```

返回统一结构(按相似度降序):

```python
[{ chunk_id, content, doc_id, source, chunk_index, similarity }, ...]
```

注意 `Retriever` 依赖的是 `EmbeddingProvider` **接口** —— 换任何厂商,这一层零改动。

## 本章小结

| 设计点 | 做法 | 换来的能力 |
|---|---|---|
| 持久化 | `PersistentClient` + cosine | 重启不丢数据,语义检索 |
| ID 约定 | `{doc_id}::{chunk_index}` + metadata | 按文档删除、计数、溯源,零额外表 |
| 相似度换算 | `1 - distance` 统一出口 | 下游语义一致 |
| 检索器 | 查询侧薄封装,依赖接口 | 厂商无关、易 mock 测试 |

下一步 → [第 5 步 · 检索与生成](/guide/07-rag)
