"""
chat.py — Flask Blueprint for chatbot endpoints.
"""

from __future__ import annotations

from flask import Blueprint, request, jsonify
from openai import OpenAI

from config import OPENROUTER_API_KEY, OPENROUTER_MODEL
from tools.tool3_rag_retriever import _load_vectorstore

chat_bp = Blueprint("chat", __name__, url_prefix="/chat")
_client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)

@chat_bp.route("", methods=["POST"])
def chat():
    """
    Accepts a user message and a claim context, retrieves policy rules,
    and returns an AI chatbot response.
    """
    data = request.json or {}
    user_message = data.get("message", "")
    claim_context = data.get("context", {}) # Option to pass the processed claim result
    chat_history = data.get("history", []) # List of previous messages

    if not user_message:
        return jsonify({"detail": "Message is required"}), 400

    # 1. RAG retrieval using Chroma
    rag_context = ""
    try:
        vectorstore = _load_vectorstore()
        docs = vectorstore.similarity_search(user_message, k=3)
        rag_context = "\n\n".join([doc.page_content for doc in docs])
    except Exception as e:
        print(f"[RAG WARNING]: {e}")
        rag_context = "(Could not retrieve policy guidelines from vector store)"

    # 2. Formulate system prompt
    context_str = str(claim_context) if claim_context else "No active claim context."
    system_prompt = f"""You are a helpful Medical Insurance Claim Copilot.
You assist the user in understanding their policy and the adjudication decision of their claim.
Answer nicely and seamlessly. You don't have to always mention that you found info in the policy rules. Just give the answer. 
Use markdown formatting for readability. Be very helpful.

ACTIVE CLAIM CONTEXT:
{context_str}

RELEVANT POLICY RULES RETRIEVED FROM RAG:
{rag_context}
"""

    messages = [{"role": "system", "content": system_prompt}]
    for msg in chat_history:
        # history shaped like: [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]
        messages.append(msg)
    
    messages.append({"role": "user", "content": user_message})

    try:
        chat_completion = _client.chat.completions.create(
            model=OPENROUTER_MODEL,
            max_tokens=1000,
            messages=messages
        )
        reply = chat_completion.choices[0].message.content
        return jsonify({"reply": reply}), 200
    except Exception as exc:
        return jsonify({"detail": f"Chat LLM failed: {exc}"}), 500
