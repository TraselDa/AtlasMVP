from typing import Any, Dict, List
import re

class ExecutionEngine:
    def __init__(self, mapping_config: Dict[str, Any]):
        self.fields = mapping_config.get("fields", {})

    def execute(self, document: dict) -> dict:
        lines = document.get("lines", [])
        result = {}

        for field_name, conf in self.fields.items():
            mode = conf.get("field_mode", "replace")
            value = None

            for rule in conf.get("rules", []):
                extracted = self._apply_rule(lines, value, rule)

                if extracted is None:
                    continue

                if mode == "append":
                    if value:
                        value += " " + extracted
                    else:
                        value = extracted
                else:
                    value = extracted

            value = self._post_process(value, conf.get("post_process", []))
            result[field_name] = value

        return result

    # --------------------------------------------------
    # RULE ENGINE
    # --------------------------------------------------

    def _apply_rule(self, lines, current_value, rule):
        # MATCH
        if "match" in rule:
            return self._match(lines, rule)

        # EXTRACT
        if "extract" in rule:
            extract_type = rule["extract"]

            if extract_type == "after" and current_value:
                return self._extract_after(current_value, rule["value"])

            if extract_type == "by_index":
                return self._extract_by_index(lines, rule)

            if extract_type == "take_last_tokens" and current_value:
                return self._take_last_tokens(current_value, rule.get("count", 1))

        return None

    # --------------------------------------------------
    # MATCHERS
    # --------------------------------------------------

    def _match(self, lines, rule):
        value = rule["value"].lower()

        for line in lines:
            text = line["text"] if isinstance(line, dict) else line
            txt = text.lower()

            if rule["match"] == "contains" and value in txt:
                return text

            if rule["match"] == "starts_with" and txt.startswith(value):
                return text

        return None

    # --------------------------------------------------
    # EXTRACTORS
    # --------------------------------------------------

    def _extract_after(self, text, key):
        idx = text.lower().find(key.lower())
        return text[idx + len(key):].strip() if idx >= 0 else None

    """def _extract_by_index(self, lines, rule):
        idx = rule.get("line_index")
        if idx is None or idx >= len(lines):
            return None

        line = lines[idx]
        return line.get("text", "").strip()"""
    def _extract_by_index(self, lines, rule):
        idx = rule.get("line_index")
        if idx is None or idx >= len(lines):
            return None

        line = lines[idx]
        tokens = line.get("tokens")

        # Si tokens disponibles → slicing
        if tokens:
            start, end = rule.get("token_slice", (0, None))
            sliced = tokens[start:end]
            return " ".join(sliced).strip()

        # fallback texte brut
        return line.get("text", "").strip()

    def _take_last_tokens(self, text, count):
        tokens = text.split()
        return " ".join(tokens[-count:]) if tokens else None

    # --------------------------------------------------
    # POST PROCESS
    # --------------------------------------------------

    def _post_process(self, value, processors: List[str]):
        if not value:
            return None

        for proc in processors:
            if proc == "strip":
                value = value.strip()

            elif proc == "strip_spaces":
                value = value.replace(" ", "")

            elif proc == "normalize_spaces":
                value = re.sub(r"\s+", " ", value).strip()

            elif proc == "comma_to_float":
                parts = value.split()
                if len(parts) == 2:
                    value = {
                        "ht": float(parts[0].replace(",", ".")),
                        "ttc": float(parts[1].replace(",", "."))
                    }

        return value