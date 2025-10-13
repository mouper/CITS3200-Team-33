import re

def clean_title(title: str) -> str:
    """
    Remove special characters but preserve spaces.
    If the entire string is uppercase, normalise to lowercase.
    Examples:
      "Funny Cats!!!" -> "Funny Cats"
      "HELLO WORLD"   -> "hello world"
    """
    if title is None:
        return ""
    # Keep alphanumeric and spaces
    cleaned = re.sub(r"[^0-9A-Za-z ]+", "", title)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # If the original is all-caps (ignoring non-letters), lower it
    letters = re.sub(r"[^A-Za-z]+", "", title)
    if letters and letters.isupper():
        cleaned = cleaned.lower()
    return cleaned
