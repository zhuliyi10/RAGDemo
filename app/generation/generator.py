"""生成器：构造 RAG Prompt 并调用 LLM。"""
from app.core.base import LLMProvider

SYSTEM_PROMPT = (
    "你是一个严谨的问答助手。请仅依据下方提供的【上下文】回答用户问题，"
    "不要编造上下文之外的信息。若上下文不足以回答问题，请明确说明"
    "「根据现有资料无法回答该问题」。回答时使用与问题相同的语言，"
    "并优先给出直接结论。"
)


def build_user_prompt(question: str, contexts: list[dict]) -> str:
    """将检索片段与问题组装为用户 Prompt。"""
    sections = [
        f"[片段 {i + 1}] 来源: {hit['source']}\n{hit['content']}"
        for i, hit in enumerate(contexts)
    ]
    context_block = "\n\n".join(sections)
    return f"【上下文】\n{context_block}\n\n【问题】\n{question}"


class Generator:
    """基于检索上下文生成回答。"""

    def __init__(self, llm_provider: LLMProvider):
        self._llm = llm_provider

    def generate(self, question: str, contexts: list[dict]) -> str:
        """根据上下文片段生成回答。"""
        user_prompt = build_user_prompt(question, contexts)
        return self._llm.chat(SYSTEM_PROMPT, user_prompt)
