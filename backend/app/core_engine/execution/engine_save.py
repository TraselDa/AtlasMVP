from typing import Any, Dict
import re

class ExecutionEngine:
    def __init__(self, mapping_config: Dict[str, Any]):
        self.mapping = mapping_config.get("fields", {})

    def execute(self, document: dict) -> dict:
        """
        document : dict issu de OCRAdapter.process(..., raw=True)
        """
        lines = document.get("normalized_lines", []) or document.get("lines", [])
        result = {}

        # on passe lines en texte pour _apply_rules si besoin
        line_texts = [l["text"] if isinstance(l, dict) and "text" in l else l for l in lines]

        for field_name, field_conf in self.mapping.items():
            value = self._apply_rules(lines, line_texts, field_conf.get("rules", []))
            value = self._post_process(value, field_conf.get("post_process", []))
            result[field_name] = value

        return result

    def _apply_rules(self, lines, line_texts, rules):
        current_value = None

        for rule in rules:
            if "match" in rule:
                match_type = rule["match"]

                if match_type == "contains":
                    match_val = rule["value"]
                    current_value = next((l for l in line_texts if match_val.lower() in l.lower()), None)
                elif match_type == "starts_with":
                    match_val = rule["value"]
                    current_value = next((l for l in line_texts if l.lower().startswith(match_val.lower())), None)
                elif match_type == "contains_any":
                    match_vals = rule.get("values", [])
                    current_value = next((l for l in line_texts if any(v.lower() in l.lower() for v in match_vals)), None)

            if "extract" in rule and current_value is not None:
                extract_type = rule["extract"]
                if extract_type == "after":
                    current_value = self._extract_after(current_value, rule["value"])
                elif extract_type == "line_offset":
                    start = rule.get("start", 0)
                    count = rule.get("count", 1)
                    current_value = self._extract_line_offset(line_texts, current_value, start, count)
                elif extract_type == "take_last_tokens":
                    count = rule.get("count", 1)
                    current_value = self._take_last_tokens(current_value, count)
                elif extract_type == "take_tokens_after_match":
                    # récupère les tokens de la ligne matchée
                    line_obj = next((l for l in lines if (l.get("text") == current_value if isinstance(l, dict) else l == current_value)), None)
                    if line_obj and isinstance(line_obj, dict):
                        skip_pattern = rule.get("skip_tokens_pattern")
                        take_pattern = rule.get("take_tokens_pattern")
                        count = rule.get("count", 5)
                        tokens = line_obj.get("tokens", [])
                        extracted_tokens = []
                        for token in tokens:
                            if skip_pattern and re.fullmatch(skip_pattern, token):
                                continue
                            if take_pattern and re.fullmatch(take_pattern, token):
                                extracted_tokens.append(token)
                                if len(extracted_tokens) >= count:
                                    break
                            elif not take_pattern:
                                extracted_tokens.append(token)
                                if len(extracted_tokens) >= count:
                                    break
                        current_value = extracted_tokens

        return current_value

    def _extract_after(self, text, key):
        idx = text.lower().find(key.lower())
        if idx >= 0:
            return text[idx + len(key):].strip()
        return text.strip()

    def _extract_line_offset(self, lines, match_line, start=0, count=1):
        try:
            idx = lines.index(match_line)
            selected_lines = lines[idx + start : idx + start + count]
            return "\n".join(selected_lines).strip()
        except ValueError:
            return None

    def _take_last_tokens(self, text, count=1):
        if text is None:
            return None
        tokens = text.split()
        return " ".join(tokens[-count:]) if len(tokens) >= count else text

    def _post_process(self, value, processors):
        if value is None:
            return None
        for proc in processors:
            if proc == "strip" and isinstance(value, str):
                value = value.strip()
            elif proc == "strip_spaces" and isinstance(value, str):
                value = value.replace(" ", "")
            elif proc == "join_lines" and isinstance(value, str):
                value = value.replace("\n", " ")
            elif proc == "join_tokens" and isinstance(value, list):
                value = " ".join(value)
            elif proc == "comma_to_float" and isinstance(value, str):
                parts = value.split()
                if len(parts) == 2:
                    try:
                        value = {"ht": float(parts[0].replace(",", ".")),
                                 "ttc": float(parts[1].replace(",", "."))}
                    except ValueError:
                        pass
                else:
                    try:
                        value = float(parts[-1].replace(",", "."))
                    except ValueError:
                        pass
        return value