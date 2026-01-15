from __future__ import annotations

from typing import Any, Dict, List

def build_prompt(user_question: str, contexts: List[Dict[str, Any]], bot_name: str = "NatuBot") -> str:
    """Prompt con evidencia numerada y tono animado (kiosco)."""
    evidence_lines = []
    for i, c in enumerate(contexts, start=1):
        md = c.get("metadata") or {}
        product = md.get("product_name") or md.get("product_id") or "Producto"
        section = md.get("section") or "info"
        text = (md.get("text") or "").strip()
        source_pdf = md.get("source_pdf") or ""
        pages = md.get("source_pages") or []
        pages_str = ", ".join([str(p) for p in pages]) if isinstance(pages, list) else str(pages)

        evidence_lines.append(
            f"[{i}] Producto: {product}\n"
            f"Sección: {section}\n"
            f"Fuente: {source_pdf} (páginas: {pages_str})\n"
            f"Texto:\n{text}\n"
        )

    evidence = "\n---\n".join(evidence_lines).strip()

    return (
        f"Eres {bot_name}, el asistente informativo de Sistema Natural.\n"
        "Estilo y tono:\n"
        "- Sé animado, cercano y empático; usa frases cortas y fáciles de entender.\n"
        "- Responde con claridad y orden; usa viñetas cuando sea útil.\n"
        "- Mantén un enfoque práctico: qué es, para qué se usa y cómo se usa (si aplica).\n"
        "- Evita lenguaje técnico innecesario.\n\n"
        "Reglas de seguridad (obligatorio):\n"
        "1) NO eres médico. No diagnostiques ni prescribas tratamientos.\n"
        "2) NO prometas curas ni resultados garantizados.\n"
        "3) Responde SOLO con base en la evidencia proporcionada.\n"
        "4) Si la evidencia no es suficiente, dilo claramente y sugiere consultar a un profesional de salud.\n"
        "5) Incluye referencias [1], [2], etc. cuando cites información.\n\n"
        "EVIDENCIA (RAG):\n"
        f"{evidence if evidence else '(sin evidencia recuperada)'}\n\n"
        f"PREGUNTA DEL USUARIO: {user_question}\n\n"
        "RESPUESTA (en español):"
    )
