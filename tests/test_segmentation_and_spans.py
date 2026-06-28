from pathlib import Path

from speechlens.agents.span_expander import _heuristic_expand, _reclassify_type
from speechlens.ingestion.service import IngestionService
from speechlens.ingestion.transcript_parser import (
    has_speaker_turns,
    parse_transcript_text,
    _unwrap_erroneous_speaker_wrapper,
)
from speechlens.models import AnnotationType, CandidateSpan, Segment


DECLARATION = Path("data/processed/speeches/malcolmx/a-declaration-of-independence-march-12-1964.txt")


def test_unwrap_erroneous_malcolm_wrapper():
    text = "MALCOLM X:\nFBI Agent: Hello?\n\nMalcolm X: Fine."
    unwrapped = _unwrap_erroneous_speaker_wrapper(text)
    assert unwrapped.startswith("FBI Agent:")
    assert has_speaker_turns(unwrapped)


def test_declaration_splits_interview_and_press_conference():
    if not DECLARATION.exists():
        return
    doc = IngestionService().from_file(DECLARATION)
    assert len(doc.segments) >= 20
    assert max(len(s.text) for s in doc.segments) < 800
    cassius = [s for s in doc.segments if "Cassius" in s.text]
    assert cassius
    assert "come out" in cassius[0].text
    assert cassius[0].speaker == "FBI Agent"
    # Press conference paragraphs should be separate MALCOLM X segments
    muhammad_segs = [s for s in doc.segments if "Mr. Muhammad" in s.text]
    assert muhammad_segs
    assert len(muhammad_segs[0].text) < 500


def test_heuristic_expand_cassius_uses_full_question():
    segment = Segment(
        segment_id="seg_0003",
        speaker="FBI Agent",
        text="How do you think Cassius is going to\ncome out? Is he going to win or is he going to lose?",
    )
    span = CandidateSpan(
        span_text="Cassius",
        reason="entity",
        annotation_type=AnnotationType.ENTITY,
        priority=5,
    )
    expanded = _heuristic_expand(span, segment, [], [], ["seg_0003"], "Speech", "")
    assert "Cassius" in expanded.evidence_span
    assert "come out" in expanded.evidence_span
    assert expanded.needs_web is True
    assert any("Liston" in q or "Clay" in q for q in expanded.search_queries)


def test_reclassify_father_time():
    span = CandidateSpan(
        span_text="Father Time",
        reason="x",
        annotation_type=AnnotationType.DOCTRINAL_CONTEXT,
        priority=3,
    )
    ann_type = _reclassify_type(span, "Even a monster, Father Time catches up", "Liston boxing")
    assert ann_type == AnnotationType.COMMON_METAPHOR


def test_reclassify_human_rights():
    span = CandidateSpan(
        span_text="human rights",
        reason="x",
        annotation_type=AnnotationType.DOCTRINAL_CONTEXT,
        priority=3,
    )
    ann_type = _reclassify_type(span, "struggle for human rights", "")
    assert ann_type == AnnotationType.POLITICAL_FRAMING


def test_heuristic_skip_web_for_father_time():
    segment = Segment(
        segment_id="seg_0010",
        speaker="Malcolm X",
        text="Even a monster, Father Time catches\nup with them.",
    )
    span = CandidateSpan(
        span_text="Father Time",
        reason="metaphor",
        annotation_type=AnnotationType.AMBIGUOUS_PHRASE,
        priority=2,
    )
    expanded = _heuristic_expand(span, segment, [], [], ["seg_0010"], "Speech", "Liston boxing")
    assert expanded.needs_web is False
    assert expanded.annotation_type == AnnotationType.COMMON_METAPHOR
