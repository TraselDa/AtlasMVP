"""Service de génération d'embeddings vectoriels.

Ce module encapsule l'utilisation du modèle SentenceTransformer pour
transformer du texte brut (ex: profils, éléments de CV, offres) en
vecteurs denses (embeddings) utilisables pour des calculs de similarité
sémantique ou de recherche vectorielle.

Il fournit également des utilitaires pour calculer la similarité cosinus
entre deux vecteurs et normaliser ce score.
"""

import numpy as np
from sentence_transformers import SentenceTransformer

# Charger le modèle de embeddings
EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2')

def compute_embedding(text: str) -> np.ndarray:
    """
    Calcule l'embedding du texte avec SentenceTransformer
    """
    text = text[:2500]  # Limitation du texte pour embeddings
    return EMBEDDING_MODEL.encode(text, convert_to_numpy=True)

def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Similarité cosinus entre deux vecteurs
    """
    if vec1 is None or vec2 is None:
        return 0.0
    num = np.dot(vec1, vec2)
    denom = np.linalg.norm(vec1) * np.linalg.norm(vec2)
    if denom == 0:
        return 0.0
    return float(num / denom)

def normalize_score(score: float) -> float:
    """ Normalise un score entre 0 et 100 """
    return max(0.0, min(100.0, float(score)))