from utils import clean_title

def test_clean_title_removes_special_chars():
    assert clean_title("Funny Cats!!!") == "Funny Cats"

def test_clean_title_lowercases():
    assert clean_title("HELLO WORLD") == "hello world"
