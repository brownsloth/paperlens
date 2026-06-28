from speechlens.retrieval.query_builder import build_queries_from_question
from speechlens.retrieval.source_filter import is_blocked_source, source_quality_score


def test_block_imdb_and_translate():
    assert is_blocked_source("https://www.imdb.com/title/tt0118715/", "Human")
    assert is_blocked_source("https://translate.google.com/", "Translate")
    assert not is_blocked_source("https://www.blackpast.org/african-american-history/malcolm-x/", "Malcolm X")


def test_human_rights_queries_are_speech_aware():
    queries = build_queries_from_question(
        "Why does Malcolm X frame the struggle as human rights?",
        "American Negro struggle for human rights",
        "A Declaration of Independence (March 12, 1964)",
        "1964 explosive year",
    )
    assert all("Malcolm X" in q for q in queries)
    assert not any(q.strip().lower() == "human rights" for q in queries)
    assert any("civil rights" in q for q in queries)


def test_racial_front_queries():
    queries = build_queries_from_question(
        "What does racial front mean here?",
        "explosive year on the racial front",
        "Declaration of Independence",
        "1964 racial front",
    )
    assert all(len(q.split()) >= 3 for q in queries)


def test_source_quality_prefers_archives():
    assert source_quality_score("https://loc.gov/item/123", "Malcolm X speech") > 0.7
    assert source_quality_score("https://www.imdb.com/title/x", "Human") == 0.0
