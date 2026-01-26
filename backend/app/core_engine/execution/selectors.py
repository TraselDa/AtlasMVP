def contains_words(*words):
    def selector(line):
        text = line["text"].lower()
        return all(w.lower() in text for w in words)
    return selector


def next_line():
    def selector(line, document):
        idx = line["index"] + 1
        if idx < len(document["lines"]):
            return document["lines"][idx]
        return None
    return selector