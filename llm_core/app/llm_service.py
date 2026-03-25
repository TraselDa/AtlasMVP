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
        if not choice:
            logger.error("OpenRouter n'a retourné aucun choice. Response: %s", response)
            raise ValueError("OpenRouter n'a retourné aucun choice dans la réponse.")

        # Dump complet du message pour diagnostic
        msg = choice.message
        logger.info(
            "OpenRouter response: model=%s, finish_reason=%s, "
            "content_type=%s, content_len=%s, reasoning_type=%s, "
            "message_fields=%s",
            getattr(response, 'model', 'N/A'),
            choice.finish_reason,
            type(msg.content).__name__,
            len(msg.content) if msg.content else 0,
            type(getattr(msg, 'reasoning', None)).__name__,
            list(msg.model_dump().keys()) if hasattr(msg, 'model_dump') else dir(msg),
        )

        content = msg.content
        refusal = getattr(msg, 'refusal', None)

        if refusal:
            logger.error("OpenRouter a refusé la requête: %s", refusal)
            raise ValueError(f"Le LLM a refusé la requête: {refusal}")

        # Gemma 3n (thinking model) peut mettre sa réponse dans 'reasoning'
        if content is None:
            reasoning = getattr(msg, 'reasoning', None)
            # Aussi vérifier model_extra pour les champs non-standard
            extra = getattr(msg, 'model_extra', {}) or {}
            reasoning_extra = extra.get('reasoning') or extra.get('reasoning_content')

            logger.warning(
                "content=None, checking fallbacks: reasoning=%s, "
                "model_extra_keys=%s, finish_reason=%s",
                type(reasoning).__name__ if reasoning else None,
                list(extra.keys()) if extra else [],
                choice.finish_reason,
            )

            fallback = reasoning or reasoning_extra
            if fallback and isinstance(fallback, str):
                logger.info("Utilisation du champ reasoning comme fallback (%d chars)", len(fallback))
                return fallback.strip()

            # Log le dump complet pour investigation
            try:
                raw_dump = msg.model_dump() if hasattr(msg, 'model_dump') else str(msg)
                logger.error("Message complet (dump): %s", raw_dump)
            except Exception:
                logger.error("Message (repr): %r", msg)

            raise ValueError(
                f"Le LLM n'a retourné aucun contenu "
                f"(finish_reason={choice.finish_reason}). "
                f"Le modèle {settings.LLM_MODEL_NAME} ne semble pas "
                f"produire de réponse pour cette requête."
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