from claude_voice.spoken import spoken_text


def test_spoken_block_wins():
    reply = "Long detail here.\n\n<spoken>Done. Tests pass.</spoken>"
    assert spoken_text(reply) == "Done. Tests pass."


def test_strips_markdown_and_code():
    reply = (
        "## Result\n\n**Build passed.** See [the log](https://x.test/log).\n\n"
        "```bash\nmake test\n```\n\n- Fixed `parse()` in the auth module."
    )
    assert spoken_text(reply) == "Build passed. See the log. Fixed parse() in the auth module."


def test_keeps_whole_sentences_under_cap():
    reply = "One two three. " + "word " * 40 + "end."
    assert spoken_text(reply, max_words=10) == "One two three."


def test_truncates_a_single_long_sentence():
    reply = "word " * 50
    assert spoken_text(reply, max_words=5) == "word word word word word."


def test_drops_tables_and_empty():
    assert spoken_text("| a | b |\n| --- | --- |\n| 1 | 2 |") == ""
    assert spoken_text("") == ""
