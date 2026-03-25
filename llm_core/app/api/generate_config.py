"""Route API pour la génération automatique de configuration d'extraction.

Ce module expose un endpoint permettant de générer automatiquement
une configuration JSON compatible avec l'ExecutionEngine à partir
de documents normalisés et d'une liste de champs à extraire.
"""

import asyncio
import json
import logging
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.llm_service import generate_config_chat

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Config Generation"])


class FieldToExtract(BaseModel):
    name: str
    type: str = "string"
    description: Optional[str] = None


class GenerateConfigRequest(BaseModel):
    normalized_documents: List[Dict[str, Any]]
    fields_to_extract: List[FieldToExtract]


SYSTEM_PROMPT = """You are an expert agent specialized in generating configuration JSON for the ExecutionEngine.
You know exactly how the ExecutionEngine works: rules, post-processors, field_mode, and token extraction.
You understand normalized documents, which contain an ordered list of lines with tokens and text.
Your task is to receive a normalized document and a list of fields to extract, and generate a valid config JSON for the engine.
You must respect the supported rules, field_mode, and post-processors.
Do not invent new rules or processors.
Do not output empty fields unless extraction is impossible.
Your output must be a single valid JSON, ready to be executed by the engine.

NORMALIZED INPUT FORMAT

You will receive normalized documents structured as:
{
  "normalized_lines": [
    {
      "id": "string",
      "index": integer,
      "text": "string",
      "tokens": ["string", "..."],
      "length": integer
    }
  ]
}

Guarantees:
- normalized_lines are ordered by index
- text is always present
- tokens may be present or absent
- tokens represent OCR word segmentation
- index corresponds to visual reading order

EXECUTION ENGINE BEHAVIOR

The engine receives a mapping configuration and a document containing normalized_lines.
For each field:
- value starts as null
- rules are executed sequentially
- each rule may return a string or null
- null results are ignored
- if field_mode is "append": concatenate results with a space
- otherwise: last non-null result replaces the value
- post_process is applied at the end

CONFIGURATION FORMAT

Top-level structure:
{
  "version": "1.1",
  "engine": ["tesseract"],
  "fields": {
    "<field_name>": FieldConfig
  }
}

FieldConfig:
{
  "type": "string | number | object",
  "rules": [Rule],
  "field_mode": "append | replace",
  "post_process": [PostProcessor]
}

Notes:
- field_mode is OPTIONAL, default is "replace"
- post_process is OPTIONAL
- mapping is OPTIONAL and currently ignored by the engine

SUPPORTED RULES

MATCH RULE
Purpose: find a line matching a condition.
Format: {"match": "contains | starts_with", "value": "string"}
Behavior: iterate over normalized_lines in order, compare lowercased text, return the FULL line text of the first match. If no match, return null.

EXTRACT RULE: after
Format: {"extract": "after", "value": "string"}
Precondition: current value must not be null.
Behavior: find value (case-insensitive) inside current value, return substring after it, trim spaces. If not found, return null.

EXTRACT RULE: by_index
Format: {"extract": "by_index", "line_index": integer, "token_slice": [start, end]}
Behavior: select normalized_lines[line_index]. If tokens exist, apply Python slicing tokens[start:end] and join with spaces. If tokens do not exist, return line.text. token_slice is OPTIONAL. If line_index is invalid, return null.

EXTRACT RULE: take_last_tokens
Format: {"extract": "take_last_tokens", "count": integer}
Precondition: current value must not be null.
Behavior: split current value by spaces, return the last N tokens joined by spaces. If empty, return null.

POST PROCESSORS (applied in order to the final value)

- strip: trim leading and trailing spaces
- strip_spaces: remove all spaces
- normalize_spaces: collapse multiple spaces into one, trim result
- comma_to_float: expects two numeric tokens separated by space, replaces commas with dots, returns {"ht": float, "ttc": float}

DESIGN RULES FOR CONFIG GENERATION

- Rules MUST be ordered correctly
- match rules MUST appear before extract rules that depend on them
- extract rules with preconditions MUST NOT be first
- field_mode "append" MUST be used only when multiple rules contribute to one field
- field_mode MUST be omitted when default replace behavior is sufficient
- Prefer semantic matching (match + extract) when labels exist
- Use by_index ONLY when document structure is stable or labels are absent
- Use token_slice to exclude noise tokens (IDs, account numbers, labels)
- Never rely on regex or keywords not supported by the engine
- Never infer missing data
- Never output empty fields unless extraction is impossible

EXAMPLES

Example 1 - Invoice number extraction:
{
  "type": "string",
  "rules": [
    {"match": "contains", "value": "N° de facture"},
    {"extract": "after", "value": "N° de facture"}
  ],
  "post_process": ["strip"]
}

Example 2 - Customer address (multi-line, append mode):
{
  "type": "string",
  "field_mode": "append",
  "rules": [
    {"extract": "by_index", "line_index": 6},
    {"extract": "by_index", "line_index": 7, "token_slice": [5, null]}
  ],
  "post_process": ["normalize_spaces"]
}

Example 3 - Amount with comma_to_float:
{
  "type": "object",
  "rules": [
    {"match": "starts_with", "value": "Montant de la facture soumis à TVA"},
    {"extract": "take_last_tokens", "count": 2}
  ],
  "mapping": {"ht": 0, "ttc": 1},
  "post_process": ["comma_to_float"]
}

IMPORTANT: Your output MUST be a single valid JSON object matching the configuration format. No explanations, no comments, no markdown, no extra text. Just the JSON."""


@router.post("/chat/generate-config")
async def generate_config(payload: GenerateConfigRequest):
    """Genere automatiquement une configuration d'extraction JSON
    compatible avec l'ExecutionEngine a partir de documents normalises.
    """

    # Construire le prompt utilisateur avec les documents normalisés et les champs
    fields_description = "\n".join(
        f"- {f.name} (type: {f.type}){f' — {f.description}' if f.description else ''}"
        for f in payload.fields_to_extract
    )

    # Inclure tous les documents normalisés pour que le LLM ait une vue complète
    docs_json = json.dumps(payload.normalized_documents, ensure_ascii=False, indent=2)

    user_prompt = f"""Here are the normalized documents to analyze:

{docs_json}

Fields to extract:
{fields_description}

Generate the extraction configuration JSON."""

    try:
        try:
            response = await asyncio.wait_for(
                generate_config_chat(SYSTEM_PROMPT, user_prompt),
                timeout=120.0
            )
        except asyncio.TimeoutError:
            logger.error("Timeout lors de la generation de config")
            raise HTTPException(
                status_code=503,
                detail="Service surchargé, veuillez réessayer"
            )

        # Parser le JSON retourné par le LLM
        try:
            # Nettoyer la réponse (enlever markdown code blocks si présents)
            cleaned = response.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
                if cleaned.endswith("```"):
                    cleaned = cleaned[:-3]
                cleaned = cleaned.strip()

            config_data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Le LLM a retourné un JSON invalide: {response[:500]}")
            raise HTTPException(
                status_code=422,
                detail={
                    "message": "Le modèle a généré un JSON invalide",
                    "raw_response": response[:1000],
                    "error": str(e)
                }
            )

        return {
            "config_data": config_data,
            "raw_response": response
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur generation config: {e}")
        raise HTTPException(status_code=500, detail=str(e))
