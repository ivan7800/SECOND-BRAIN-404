import httpx

class LLMError(RuntimeError):
    pass

async def generate(prompt, s):
    if s.chat_provider == "ollama":
        return await _ollama(prompt, s)
    if s.chat_provider == "openai":
        return await _openai(prompt, s)
    if s.chat_provider == "gemini":
        return await _gemini(prompt, s)
    raise LLMError(f"Proveedor no soportado: {s.chat_provider}")

async def _ollama(prompt, s):
    payload = {
        "model": s.ollama_chat_model,
        "stream": False,
        "messages": [
            {"role": "system", "content": "Eres el asistente de un Second Brain privado. Sé preciso y respeta las fuentes."},
            {"role": "user", "content": prompt},
        ],
    }
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(f"{s.ollama_base_url}/api/chat", json=payload)
            r.raise_for_status()
            return (r.json().get("message") or {}).get("content", "").strip()
    except Exception as exc:
        raise LLMError(f"Ollama: {exc}") from exc

async def _openai(prompt, s):
    if not s.openai_api_key:
        raise LLMError("OPENAI_API_KEY no configurada")
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {s.openai_api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": s.openai_model, "input": prompt},
            )
            r.raise_for_status()
            data = r.json()
        if isinstance(data.get("output_text"), str):
            return data["output_text"].strip()
        parts = []
        for item in data.get("output", []):
            for content in item.get("content", []):
                if isinstance(content.get("text"), str):
                    parts.append(content["text"])
        if not parts:
            raise LLMError("OpenAI no devolvió texto")
        return "\n".join(parts)
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(f"OpenAI: {exc}") from exc

async def _gemini(prompt, s):
    if not s.gemini_api_key:
        raise LLMError("GEMINI_API_KEY no configurada")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{s.gemini_model}:generateContent"
    try:
        async with httpx.AsyncClient(timeout=300) as client:
            r = await client.post(
                url,
                headers={"x-goog-api-key": s.gemini_api_key, "Content-Type": "application/json"},
                json={"contents": [{"role": "user", "parts": [{"text": prompt}]}]},
            )
            r.raise_for_status()
            data = r.json()
        parts = []
        for candidate in data.get("candidates", []):
            for part in (candidate.get("content") or {}).get("parts", []):
                if isinstance(part.get("text"), str):
                    parts.append(part["text"])
        if not parts:
            raise LLMError("Gemini no devolvió texto")
        return "\n".join(parts)
    except LLMError:
        raise
    except Exception as exc:
        raise LLMError(f"Gemini: {exc}") from exc
