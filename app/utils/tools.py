import re

def to_safe_filename(text: str, max_len: int = 80) -> str:
    """
    Convert the sentence into a safe filename stem (without extension)
    """
    text = text.replace("\n", " ").replace("\t", " ")
    illegal_chars = r'[\\/:*?"<>|]'
    text = re.sub(illegal_chars, "", text)
    text = re.sub(r'\s+', " ", text)
    text = text.strip()
    if len(text) > max_len:
        text = text[:max_len].strip()
    if not text:
        text = "untitled"
    return text