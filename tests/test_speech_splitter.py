from speechlens.ingestion.speech_splitter import build_speech_entries, slugify


def test_parse_malcolm_toc():
    from speechlens.paths import DEFAULT_MALCOLM_PDF

    if not DEFAULT_MALCOLM_PDF.exists():
        return
    entries = build_speech_entries(DEFAULT_MALCOLM_PDF)
    assert len(entries) >= 50
    assert entries[0].title.startswith("Harlem Freedom Rally")
    assert entries[0].start_page == 11


def test_slugify():
    assert slugify("The Ballot or the Bullet (NY, April 3, 1964)") == "the-ballot-or-the-bullet-ny-april-3-1964"
