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
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Le LLM n'a retourné aucun contenu (rerank).")
        return content.strip()

    except Exception as e:
        print(f"❌ Erreur OpenRouter: {e}")
        # En prod, vous pourriez vouloir retenter (retry) ou loguer l'erreur
        raise e
    


async def generate_config_chat(system_prompt: str, full_prompt: str) -> str:
    """
    Appel API dédié à la génération de config JSON.
    Température basse pour un output structuré et déterministe.
    Max tokens plus élevé car les configs peuvent être longues.
    """
    try:
        logger.info(
            "generate_config_chat: prompt system=%d chars, user=%d chars",
            len(system_prompt), len(full_prompt),
        )

        response = await client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.1,
            max_tokens=4000
        )

        # Log détaillé de la réponse OpenRouter
        choice = response.choices[0] if response.choices else None
        logger.info(
            "OpenRouter response: model=%s, finish_reason=%s, usage=%s",
            getattr(response, 'model', 'N/A'),
            getattr(choice, 'finish_reason', 'N/A') if choice else 'no_choices',
            getattr(response, 'usage', 'N/A'),
        )

        if not choice:
            logger.error("OpenRouter n'a retourné aucun choice. Response: %s", response)
            raise ValueError("OpenRouter n'a retourné aucun choice dans la réponse.")

        content = choice.message.content
        refusal = getattr(choice.message, 'refusal', None)

        if refusal:
            logger.error("OpenRouter a refusé la requête: %s", refusal)
            raise ValueError(f"Le LLM a refusé la requête: {refusal}")

        if content is None:
            logger.error(
                "OpenRouter content=None. finish_reason=%s, refusal=%s, model=%s",
                choice.finish_reason, refusal, settings.LLM_MODEL_NAME,
            )
            raise ValueError(
                f"Le LLM n'a retourné aucun contenu "
                f"(finish_reason={choice.finish_reason}). "
                f"Vérifiez la clé API et le modèle."
            )
        return content.strip()
    except Exception as e:
        print(f"❌ Erreur OpenRouter (generate_config): {e}")
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
        
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Le LLM n'a retourné aucun contenu (chat).")
        return content.strip()
    except Exception as e:
        print(f"❌ Erreur OpenRouter: {e}")
        # En prod, vous pourriez vouloir retenter (retry) ou loguer l'erreur
        raise e