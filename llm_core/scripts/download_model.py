import os
from pathlib import Path
from huggingface_hub import hf_hub_download

MODEL_REPO = "microsoft/Phi-3-mini-4k-instruct-gguf"
MODEL_FILE = "Phi-3-mini-4k-instruct-q4.gguf"
LOCAL_DIR = Path("models/phi-3-mini")

LOCAL_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_PATH = LOCAL_DIR / MODEL_FILE

if LOCAL_PATH.exists():
    print(f"[INFO] Le modèle existe déjà : {LOCAL_PATH}")
else:
    print(f"[INFO] Téléchargement du modèle depuis HuggingFace : {MODEL_REPO}/{MODEL_FILE}")
    try:
        hf_hub_download(
            repo_id=MODEL_REPO,
            filename=MODEL_FILE,
            local_dir=str(LOCAL_DIR),
            local_dir_use_symlinks=False
        )
        print(f"[INFO] Modèle téléchargé avec succès dans : {LOCAL_PATH}")
    except Exception as e:
        print(f"[ERROR] Impossible de télécharger le modèle : {e}")