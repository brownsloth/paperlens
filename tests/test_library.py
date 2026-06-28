import pytest

from speechlens.library import list_sources, list_speeches, load_speech


def test_list_seeded_sources():
    sources = list_sources()
    assert any(s["source_id"] == "malcolmx" for s in sources)
    assert sources[0]["speeches_count"] == 56


def test_list_speeches_search():
    speeches = list_speeches("malcolmx", search="grassroots")
    assert len(speeches) >= 1
    assert "grassroots" in speeches[0]["slug"]


def test_load_seeded_speech_transcript():
    doc = load_speech("malcolmx", "harlem-freedom-rally-1960")
    assert doc.title == "Harlem Freedom Rally (1960)"
    assert len(doc.segments) >= 1
    assert doc.annotations == []
