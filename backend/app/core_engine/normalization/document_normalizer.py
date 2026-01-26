from uuid import uuid4


class DocumentNormalizer:
    """
    Transforme le RAW en document structurel
    """

    def normalize(self, raw: dict) -> dict:
        lines = []

        for idx, text in enumerate(raw["lines"]):
            lines.append({
                "id": str(uuid4()),
                "index": idx,
                "text": text,
                "tokens": text.split(),
                "length": len(text)
            })

        return {
            "engine": raw["engine"],
            "source_type": raw["source_type"],
            "lines": lines,
            "stats": {
                "total_lines": len(lines)
            }
        }