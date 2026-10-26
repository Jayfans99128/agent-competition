"""
向量数据库层（ChromaDB）
提供知识库的语义检索能力，替代原有关键词匹配
"""
import logging
import os
import re

import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from chromadb.config import Settings

from backend.config import CHROMA_PERSIST_DIR, client as openai_client, EMBEDDING_MODEL

logger = logging.getLogger("zhipig")

# ChromaDB 持久化目录
PERSIST_DIR = CHROMA_PERSIST_DIR

# 各知识库的 collection 名称
COLLECTION_KB = "knowledge_base"       # 岗位知识库
COLLECTION_KAOYAN = "kaoyan_data"      # 考研数据
COLLECTION_GUOKAO = "guokao_data"      # 国考数据


class SiliconFlowEmbedding(EmbeddingFunction):
    """调用 SiliconFlow API 的 Embedding 函数"""

    def __call__(self, input: Documents) -> Embeddings:
        # input 是字符串列表
        response = openai_client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=input,
        )
        # 按 index 排序，返回嵌入向量列表
        return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


# 全局 embedding 函数实例
_embedding_fn = SiliconFlowEmbedding()

_client = None
_collections = {}


def _get_client():
    """获取 ChromaDB 客户端（单例）"""
    global _client
    if _client is None:
        os.makedirs(PERSIST_DIR, exist_ok=True)
        _client = chromadb.Client(Settings(
            chroma_db_impl="duckdb+parquet",
            persist_directory=PERSIST_DIR,
            anonymized_telemetry=False,
        ))
    return _client


def _get_collection(name: str):
    """获取或创建 collection"""
    if name not in _collections:
        client = _get_client()
        _collections[name] = client.get_or_create_collection(
            name=name,
            embedding_function=_embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
    return _collections[name]


# ===================== 数据导入 =====================

def _parse_kb_sections(filepath: str) -> list[dict]:
    """解析岗位知识库文件，返回 [{id, text, metadata}]"""
    if not os.path.exists(filepath):
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    lines = [l.strip() for l in content.split("\n")]
    sections = []

    # 找岗位标题位置
    job_indices = []
    for i, line in enumerate(lines):
        if not line:
            continue
        if line[0] in "一二三四五六七八九" and ("、" in line or "）" in line):
            continue
        if line in ("研发技术类（核心高薪方向）",):
            continue
        if len(line) > 30:
            continue
        next_line = ""
        for j in range(i + 1, min(i + 3, len(lines))):
            if lines[j].strip():
                next_line = lines[j].strip()
                break
        if "工作介绍" in next_line:
            job_indices.append(i)

    for idx, pos in enumerate(job_indices):
        job_title = lines[pos].rstrip("：:")
        end = job_indices[idx + 1] if idx + 1 < len(job_indices) else len(lines)
        segment = lines[pos: end]
        full_text = " ".join(segment)

        sections.append({
            "id": f"kb_{idx}",
            "text": full_text,
            "metadata": {"job": job_title, "source": "knowledge_base"},
        })

    return sections


def _parse_structured_data(filepath: str, source_tag: str) -> list[dict]:
    """解析【标题】+字段 格式的数据文件"""
    if not os.path.exists(filepath):
        return []

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    pattern = r"【(.+?)】\n(.*?)(?=\n【|\Z)"
    matches = re.findall(pattern, content, re.DOTALL)

    entries = []
    for i, (title, body) in enumerate(matches):
        full_text = f"【{title}】\n{body}"
        entries.append({
            "id": f"{source_tag}_{i}",
            "text": full_text,
            "metadata": {"title": title.strip(), "source": source_tag},
        })

    return entries


def build_indices():
    """构建所有向量索引（首次启动时调用）"""
    kb_dir = os.path.join(os.path.dirname(__file__), "knowledge_base")
    kb_data_path = os.path.join(os.path.dirname(__file__), "knowledge_base_data.txt")
    kaoyan_path = os.path.join(kb_dir, "kaoyan_data.txt")
    guokao_path = os.path.join(kb_dir, "guokao_data.txt")

    # 1. 岗位知识库
    sections = _parse_kb_sections(kb_data_path)
    if sections:
        col = _get_collection(COLLECTION_KB)
        # 分批写入（ChromaDB 单次上限约 41666 条）
        batch_size = 100
        for i in range(0, len(sections), batch_size):
            batch = sections[i:i + batch_size]
            col.upsert(
                ids=[s["id"] for s in batch],
                documents=[s["text"] for s in batch],
                metadatas=[s["metadata"] for s in batch],
            )
        logger.info("✅ 岗位知识库向量索引构建完成: %d 条", len(sections))

    # 2. 考研数据
    kaoyan_entries = _parse_structured_data(kaoyan_path, "kaoyan")
    if kaoyan_entries:
        col = _get_collection(COLLECTION_KAOYAN)
        batch_size = 100
        for i in range(0, len(kaoyan_entries), batch_size):
            batch = kaoyan_entries[i:i + batch_size]
            col.upsert(
                ids=[e["id"] for e in batch],
                documents=[e["text"] for e in batch],
                metadatas=[e["metadata"] for e in batch],
            )
        logger.info("✅ 考研数据向量索引构建完成: %d 条", len(kaoyan_entries))

    # 3. 国考数据
    guokao_entries = _parse_structured_data(guokao_path, "guokao")
    if guokao_entries:
        col = _get_collection(COLLECTION_GUOKAO)
        batch_size = 100
        for i in range(0, len(guokao_entries), batch_size):
            batch = guokao_entries[i:i + batch_size]
            col.upsert(
                ids=[e["id"] for e in batch],
                documents=[e["text"] for e in batch],
                metadatas=[e["metadata"] for e in batch],
            )
        logger.info("✅ 国考数据向量索引构建完成: %d 条", len(guokao_entries))


# ===================== 语义检索 =====================

def search_knowledge_base(query: str, top_n: int = 3) -> str:
    """语义检索岗位知识库"""
    col = _get_collection(COLLECTION_KB)
    if col.count() == 0:
        return "向量索引未构建，请重启服务以初始化。"

    results = col.query(query_texts=[query], n_results=top_n)
    if not results["documents"][0]:
        return "未找到相关岗位信息。"

    lines = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        job = meta.get("job", "未知岗位")
        # 取前 200 字作为摘要
        summary = doc[:200].strip()
        if len(doc) > 200:
            summary += "..."
        lines.append(f"【{job}】{summary}")

    return "\n\n".join(lines)


def search_kaoyan(query: str, top_n: int = 5) -> str:
    """语义检索考研数据"""
    col = _get_collection(COLLECTION_KAOYAN)
    if col.count() == 0:
        return "考研向量索引未构建，请重启服务以初始化。"

    results = col.query(query_texts=[query], n_results=top_n)
    if not results["documents"][0]:
        return "未找到相关考研数据。"

    lines = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        title = meta.get("title", "")
        # 压缩空白
        clean_doc = " ".join(doc.split())
        if len(clean_doc) > 300:
            clean_doc = clean_doc[:300] + "..."
        lines.append(f"【{title}】{clean_doc}")

    return "\n\n".join(lines)


def search_guokao(query: str, top_n: int = 5) -> str:
    """语义检索国考数据"""
    col = _get_collection(COLLECTION_GUOKAO)
    if col.count() == 0:
        return "国考向量索引未构建，请重启服务以初始化。"

    results = col.query(query_texts=[query], n_results=top_n)
    if not results["documents"][0]:
        return "未找到相关国考数据。"

    lines = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        title = meta.get("title", "")
        clean_doc = " ".join(doc.split())
        if len(clean_doc) > 300:
            clean_doc = clean_doc[:300] + "..."
        lines.append(f"【{title}】{clean_doc}")

    return "\n\n".join(lines)


def search_all(query: str, top_n: int = 3) -> str:
    """跨所有知识库语义检索"""
    results = []
    results.append(("岗位知识库", search_knowledge_base(query, top_n)))
    results.append(("考研数据", search_kaoyan(query, top_n)))
    results.append(("国考数据", search_guokao(query, top_n)))

    output = []
    for name, content in results:
        if "未找到" not in content and "索引未构建" not in content:
            output.append(f"=== {name} ===\n{content}")

    return "\n\n".join(output) if output else "所有知识库中均未找到相关信息。"
