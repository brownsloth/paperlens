import re

from speechlens.ingestion.transcript_parser import parse_transcript_text
from speechlens.models import AnnotationDepth, EvidenceStatus


SAMPLE = """MALCOLM X:
Hello world.

JAMES BALDWIN:
Good evening.
"""


def test_parse_speaker_segments():
    doc = parse_transcript_text(SAMPLE, title="Test Debate", date="1961-04-25")
    assert doc.title == "Test Debate"
    assert doc.date == "1961-04-25"
    assert len(doc.segments) == 2
    assert doc.segments[0].speaker == "MALCOLM X"
    assert doc.segments[0].text == "Hello world."
    assert doc.segments[1].speaker == "JAMES BALDWIN"
    assert "MALCOLM X" in doc.speakers


def test_parse_paragraph_fallback():
    text = "First paragraph.\n\nSecond paragraph."
    doc = parse_transcript_text(text)
    assert len(doc.segments) == 2
    assert doc.segments[0].text == "First paragraph."


def test_evidence_status_values():
    assert EvidenceStatus.SUPPORTED.value == "supported"
    assert EvidenceStatus.NEEDS_VERIFICATION.value == "needs_verification"


def test_annotation_depth_enum():
    assert AnnotationDepth.MEDIUM.value == "medium"


def test_markdown_renderer_footnotes():
    from speechlens.annotation.renderer import render_markdown
    from speechlens.models import Annotation, AnnotationType, Segment

    transcript = parse_transcript_text(SAMPLE, title="Test")
    ann = Annotation(
        annotation_id="ann_test",
        segment_id=transcript.segments[0].segment_id,
        span_start=0,
        span_end=5,
        span_text="Hello",
        annotation_type=AnnotationType.AMBIGUOUS_PHRASE,
        annotation_text="A greeting.",
        evidence_status=EvidenceStatus.SUPPORTED_GENERAL_CONTEXT,
        confidence=0.9,
    )
    md = render_markdown(transcript, [ann])
    assert "[Hello][^1]" in md
    assert "[^1]:" in md
