import pytest
from gemini_md_handler import read_gemini_md

def test_read_gemini_md_success():
    """
    Tests that read_gemini_md successfully reads the GEMINI.md file.
    """
    content = read_gemini_md()
    assert isinstance(content, str)
    assert "GEMINI.md" in content

def test_read_gemini_md_file_not_found():
    """
    Tests that read_gemini_md raises FileNotFoundError for a non-existent file.
    """
    with pytest.raises(FileNotFoundError):
        read_gemini_md("non_existent_file.md")

def test_read_gemini_md_with_dummy_file(tmp_path):
    """
    Tests read_gemini_md with a temporary dummy file.
    """
    dummy_content = "## Dummy Title"
    d = tmp_path / "sub"
    d.mkdir()
    p = d / "test.md"
    p.write_text(dummy_content, encoding="utf-8")
    
    content = read_gemini_md(p)
    assert content == dummy_content
