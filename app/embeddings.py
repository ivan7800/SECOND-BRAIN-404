import math
import httpx

class EmbeddingError(RuntimeError):
    pass

def normalize(v):
    norm = math.sqrt(sum(float(x) * float(x) for x in v))
    return [float(x) / norm for x in v] if norm else [0.0 for _ in v]

def cosine(a, b):
    if len(a) != len(b) or not a:
        return 0.0
    return sum(float(x) * float(y) for x, y in zip(a, b))

async def ollama_embed(texts, settings):
    if not texts:
        return []
    try:
        async with httpx.AsyncClient(timeout=120) as client:
            r = await client.post(
                f"{settings.ollama_base_url}/api/embed",
                json={"model": settings.ollama_embed_model, "input": texts},
            )
            r.raise_for_status()
            vectors = r.json().get("embeddings") or []
    except Exception as exc:
        raise EmbeddingError(str(exc)) from exc
    if len(vectors) != len(texts):
        raise EmbeddingError("Número inesperado de embeddings")
    return [normalize(v) for v in vectors]


async def embed(texts, settings):
    provider = settings.embedding_provider
    if provider == "none":
        raise EmbeddingError("Embeddings desactivados (EMBEDDING_PROVIDER=none)")
    if provider == "ollama":
        return await ollama_embed(texts, settings)
    raise EmbeddingError(f"Proveedor de embeddings no soportado: {provider}")
