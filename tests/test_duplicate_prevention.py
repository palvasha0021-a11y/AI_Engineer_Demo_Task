from src.utils.fingerprint import generate_fingerprint, normalize_url


def test_url_normalization():
    url1 = "HTTPS://OpenAI.Com/blog/chatgpt/?utm_source=twitter&ref=123/"
    url2 = "https://openai.com/blog/chatgpt"

    norm1 = normalize_url(url1)
    norm2 = normalize_url(url2)

    assert norm1 == norm2
    assert norm1 == "https://openai.com/blog/chatgpt"


def test_fingerprint_generation():
    fp1 = generate_fingerprint("https://openai.com/blog", "OpenAI")
    fp2 = generate_fingerprint("https://openai.com/blog ", "OPENAI")

    assert fp1 == fp2
