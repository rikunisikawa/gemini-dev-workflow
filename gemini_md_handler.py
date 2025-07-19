import os

def read_gemini_md(path: str = "GEMINI.md") -> str:
    """
    Reads the content of the GEMINI.md file.

    Args:
        path: The path to the GEMINI.md file.

    Returns:
        The content of the file as a string.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    
    with open(path, "r", encoding="utf-8") as f:
        return f.read()
