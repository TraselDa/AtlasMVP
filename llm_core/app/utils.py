"""Fonctions utilitaires génériques pour le service LLM Core.

Ce module fournit des aides pour des manipulations courantes:
- Chargement sécurisé de chaines JSON
- Troncature de textes pour limiter les coûts/contextes tokens
- Normalisation de scores (ex: pourcentage de similarité)
"""

import json
from typing import Any

def safe_json_load(text: str) -> Any:
    """Charge du JSON en toute sécurité, renvoie None si erreur"""
    try:
        return json.loads(text)
    except Exception:
        return None

def truncate_text(text: str, max_len: int) -> str:
    """Tronque le texte à max_len caractères"""
    if not text:
        return ""
    return text[:max_len]

def normalize_score(score: float) -> float:
    """S'assure que le score est entre 0 et 100"""
    if score is None:
        return 0.0
    return max(0.0, min(100.0, float(score)))