"""Routes API pour la génération augmentée par la recherche (RAG).

Ce module expose les endpoints permettant de dialoguer avec le LLM
tout en le contraignant fortement à répondre strictement à partir d'un contexte
documentaire fourni (chunks). Il est conçu pour les assistants IA internes
et l'analyse de documents.
"""

import asyncio
import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.llm_service import chat

logger = logging.getLogger(__name__)

router = APIRouter(tags=["RAG"])


class RAGQuery(BaseModel):
    query: str
    context_chunks: List[str]
    system_instruction: Optional[str] = None


@router.post("/chat/rag")
async def chat_rag(payload: RAGQuery):
    """Génère une réponse LLM basée uniquement sur le contexte documentaire.
    
    Cet endpoint agrège les morceaux de texte (chunks) fournis en entrée
    pour former le contexte d'apprentissage en contexte (in-context learning).
    Le LLM reçoit l'ordre strict de ne pas extrapoler en dehors de ces chunks.
    
    Args:
        payload (RAGQuery): Contient la question, les chunks de contexte
            et éventuellement une instruction système personnalisée.
            
    Returns:
        dict: Un dictionnaire avec la réponse `answer` et la taille
            `used_context_length` du contexte utilisé.
            
    Raises:
        HTTPException 503: Si le modèle LLM est surchargé ou en timeout.
        HTTPException 500: Pour toute autre erreur de traitement interne.
    """
    context_text = "\n\n---\n\n".join(payload.context_chunks)

    system_prompt = payload.system_instruction or (
        "Tu es un assistant administratif intelligent. "
        "Utilise UNIQUEMENT les informations de CONTEXTE ci-dessous pour répondre à la question de l'utilisateur. "
        "Si la réponse ne se trouve pas dans le contexte, dis poliment que tu ne sais pas."
        "Si la question demande une synthèse (ex: total des factures), fais les calculs ou la liste demandée."
    )

    full_prompt = f"""
    CONTEXTE DOCUMENTAIRE :
    {context_text}

    QUESTION UTILISATEUR :
    {payload.query}
    """

    try:
        try:
            chat_response = await asyncio.wait_for(chat(system_prompt, full_prompt), timeout=60.0)
            print(f"[REPONSE PHI-3] :\n{chat_response}")
        except asyncio.TimeoutError:
            print("[ERR] Timeout: La file d'attente LLM est saturée.")
            raise HTTPException(status_code=503, detail="Service surchargé, veuillez réessayer")

        return {
            "answer": chat_response,
            "used_context_length": len(context_text)
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Erreur LLM: {e}")
        raise HTTPException(status_code=500, detail=str(e))
