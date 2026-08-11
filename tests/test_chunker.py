from src.llm.chunker import HTMLChunker


def test_clean_html_strips_scripts_and_styles():
    chunker = HTMLChunker(max_chunk_size=100)
    raw_html = """
    <html>
        <head>
            <style>body { color: red; }</style>
            <script>console.log("secret key");</script>
        </head>
        <body>
            <header><nav>Nav Links</nav></header>
            <h1>AI Product Launch</h1>
            <p>This is groundbreaking AI technology.</p>
        </body>
    </html>
    """
    clean_text = chunker.clean_html(raw_html)

    assert "color: red" not in clean_text
    assert "console.log" not in clean_text
    assert "Nav Links" not in clean_text
    assert "AI Product Launch" in clean_text
    assert "groundbreaking AI technology" in clean_text


def test_chunk_text_splits_large_document():
    chunker = HTMLChunker(max_chunk_size=50)
    text = "Paragraph 1 is here.\n\nParagraph 2 is here.\n\nParagraph 3 is here."
    chunks = chunker.chunk_text(text)

    assert len(chunks) > 1
    for chunk in chunks:
        assert len(chunk) <= 50
