# app/core/execution/rules.py

from typing import Dict, Any

def extract_contains_line(document: Dict[str, Any], keyword: str) -> str:
    """
    Retourne la ligne contenant le keyword
    """
    for line in document.get("lines", []):
        if keyword.lower() in line.lower():
            return line
    return ""

def extract_after_keyword(line: str, keyword: str) -> str:
    """
    Extrait ce qui est après le keyword dans la ligne
    """
    if keyword in line:
        return line.split(keyword, 1)[1].strip()
    return line

def line_offset(document: Dict[str, Any], start_index: int, count: int) -> str:
    """
    Prend N lignes à partir de l'index start_index
    """
    lines = document.get("lines", [])
    return "\n".join(lines[start_index:start_index + count])