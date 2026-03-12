"""Service d'intégration LLM via OpenRouter.

Ce module gère les appels asynchrones vers l'API d'OpenRouter pour
l'utilisation de modèles de langage de grande taille (LLMs). Il est conçu
pour gérer efficacement de multiples requêtes simultanées sans bloquer le
processus principal.

Fonctionnalités:
- `rerank_candidate`: Évaluation et réorganisation de candidats à l'aide
  d'une analyse par LLM.
- `chat`: Interface générique de chat pour les tâches interactives (ex: RAG).
"""

import logging
from openai import AsyncOpenAI
from app.core.config import settings

logger = logging.getLogger(__name__)

if not settings.OPENROUTER_API_KEY:
    logger.warning("OPENROUTER_API_KEY n'est pas definie dans l'environnement.")

# Configuration du client compatible OpenAI
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=settings.OPENROUTER_API_KEY,
)

async def rerank_candidate(prompt: str) -> str:
    """
    Appel API asynchrone vers OpenRouter.
    Peut encaisser 100+ requêtes simultanées sans bloquer votre serveur.
    """
    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=200,
            extra_headers={
                "HTTP-Referer": "https://slim-engine.com",
                "X-Title": "CV Reranker",
            }
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        print(f"❌ Erreur OpenRouter: {e}")
        # En prod, vous pourriez vouloir retenter (retry) ou loguer l'erreur
        raise e
    


async def chat(system_prompt: str, full_prompt: str) -> str:
    """
    Appel API asynchrone vers OpenRouter.
    Peut encaisser 100+ requêtes simultanées sans bloquer votre serveur.
    """
    try:
        response = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.3, # Assez factuel mais un peu fluide
            max_tokens=1000 
        )
        
        answer = response.choices[0].message.content.strip()
        return answer
    except Exception as e:
        print(f"❌ Erreur OpenRouter: {e}")
        # En prod, vous pourriez vouloir retenter (retry) ou loguer l'erreur
        raise e