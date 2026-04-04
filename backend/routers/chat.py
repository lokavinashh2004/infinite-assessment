"""
chat.py — Flask Blueprint for chatbot endpoints.
"""

from __future__ import annotations

import json
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
    user_message = data.get("message") or ""
    # Safely get context (dict) and history (list)
    claim_context = data.get("context") if isinstance(data.get("context"), dict) else {}
    chat_history = data.get("history") if isinstance(data.get("history"), list) else []

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
    # Extract details from the claim context (FinalResponse)
    claim_dict = claim_context.get("claim_details", {}) if isinstance(claim_context, dict) else {}
    policy_dict = claim_context.get("policy_details", {}) if isinstance(claim_context, dict) else {}
    
    claim_str = json.dumps(claim_dict, indent=2)
    policy_str = json.dumps(policy_dict, indent=2)
    
    system_prompt = f"""You are an Insurance Claim Evaluation Engine with reasoning capability.

RULES:
- Be formal and precise
- No emojis, no filler, no preamble
- Base answers on Claim Data, Policy Data, and Policy Clauses below
- If exact data is missing, DO NOT say "not found" — reason from available context

MISSING DATA HANDLING (CRITICAL):
- If a specific Claim ID is not found, check if ANY claim data is provided and evaluate that
- If partial data exists, evaluate what is available and state assumptions clearly
- If no claim data exists at all, state what information is needed to proceed
- NEVER give a cold "not found" response — always provide actionable intelligence

RESPONSE MODES (auto-detect based on user query):

  [FULL EVALUATION] → User asks to "evaluate", "assess", or "process" a claim
  → Return the complete structured report

  [SPECIFIC QUESTION] → User asks a targeted question
  → Answer in 2–4 lines, cite the relevant clause, done

  [CLAIM NOT FOUND] → Claim ID not in data
  → Respond like this:

      "Claim [ID] was not located in the current dataset. Based on available policy data:
       - If this claim involves [inferred condition], it would be [covered/excluded] under [Policy].
       - To proceed, provide: [list exactly what's missing — claimant name, condition, date, amount].
       - Alternatively, confirm if this claim falls under Policy [X] or [Y]."

  [STATUS CHECK] → One line: Status + one-line reason
  [AMOUNT QUERY] → Financial figures + one-line justification

INPUT DATA:

[CLAIM DATA]
{claim_str}

[POLICY DATA]
{policy_str}

[POLICY CLAUSES]
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
