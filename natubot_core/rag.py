from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .gemini_client import GeminiClient
from .pinecone_client import PineconeClients
from .prompts import build_prompt

def retrieve_context(
    *,
    question: str,
    gemini: GeminiClient,
    pinecone: PineconeClients,
    namespace: str,
    top_k: int,
    pinecone_filter: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    qvec = gemini.embed_query(question)
    res = pinecone.query(
        namespace=namespace,
        vector=qvec,
        top_k=top_k,
        include_metadata=True,
        include_values=False,
        filter=pinecone_filter,
    )

    matches = getattr(res, "matches", []) or []
    contexts: List[Dict[str, Any]] = []
    citations: List[Dict[str, Any]] = []

    for i, m in enumerate(matches, start=1):
        md = m.metadata or {}
        contexts.append({"id": m.id, "score": m.score, "metadata": md})
        citations.append(
            {
                "rank": i,
                "product_id": md.get("product_id"),
                "product_name": md.get("product_name"),
                "section": md.get("section"),
                "source_pdf": md.get("source_pdf"),
                "source_pages": md.get("source_pages"),
                "score": float(m.score) if m.score is not None else None,
            }
        )
    return contexts, citations

def answer_with_rag(
    *,
    question: str,
    gemini: GeminiClient,
    pinecone: PineconeClients,
    namespace: str,
    top_k: int,
    bot_name: str,
    pinecone_filter: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    contexts, citations = retrieve_context(
        question=question,
        gemini=gemini,
        pinecone=pinecone,
        namespace=namespace,
        top_k=top_k,
        pinecone_filter=pinecone_filter,
    )
    prompt = build_prompt(question, contexts, bot_name=bot_name)
    answer = gemini.generate(prompt)
    return {"answer": answer, "citations": citations, "used_context": bool(contexts)}
