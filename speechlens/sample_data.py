"""Sample annotated document for UI demo without an API key."""

from speechlens.models import AnnotateResponse, Annotation, AnnotationType, EvidenceStatus, Segment, Source

_SEGMENTS = [
    Segment(
        segment_id="seg_0001",
        speaker="MALCOLM X",
        text=(
            "I heard one fellow say one day that eventually intermarriage and intermixing "
            "would take place on such a vast scale that it would produce a chocolate-colored "
            "race. And Mr. Muhammad teaches us that until the black man here in America is "
            "connected or reestablished or given some knowledge of his existence prior to "
            "coming here to America, he will never feel motivated to stand on his own feet "
            "and solve his own problems."
        ),
    ),
    Segment(
        segment_id="seg_0002",
        speaker="MALCOLM X",
        text=(
            "I believe, for example, that one of these days, maybe tomorrow, Birmingham, "
            "Alabama, will probably blow up. The black man in Birmingham knows that he is "
            "not wanted there. He knows that the white man there will use every means at his "
            "disposal to keep him in his place."
        ),
    ),
    Segment(
        segment_id="seg_0003",
        speaker="MALCOLM X",
        text=(
            "The so-called Negroes who are taking part in these sit-ins are being used. "
            "They don't realize that they are being used by the very people who have kept "
            "them in a state of ignorance for four hundred years. The Black Muslims, as we "
            "are called, do not believe in begging for what is rightfully ours."
        ),
    ),
    Segment(
        segment_id="seg_0004",
        speaker="JAMES BALDWIN",
        text=(
            "I think that the Negro in this country has every right to be angry. But I also "
            "think that the country has every reason to be afraid. Because if the Negro is "
            "not able to achieve his freedom here, then the country itself is doomed."
        ),
    ),
    Segment(
        segment_id="seg_0005",
        speaker="JAMES BALDWIN",
        text=(
            "The question is not whether we will integrate or separate. The question is "
            "whether we will survive as a nation. And survival means facing what we have "
            "done, what we continue to do, and what we refuse to see."
        ),
    ),
]

_SEGMENT_TEXT = {s.segment_id: s.text for s in _SEGMENTS}


def _ann(
    annotation_id: str,
    segment_id: str,
    span_text: str,
    annotation_type: AnnotationType,
    annotation_text: str,
    evidence_status: EvidenceStatus,
    confidence: float,
    **kwargs,
) -> Annotation:
    text = _SEGMENT_TEXT[segment_id]
    start = text.index(span_text)
    return Annotation(
        annotation_id=annotation_id,
        segment_id=segment_id,
        span_start=start,
        span_end=start + len(span_text),
        span_text=span_text,
        annotation_type=annotation_type,
        annotation_text=annotation_text,
        evidence_status=evidence_status,
        confidence=confidence,
        **kwargs,
    )


SAMPLE_DOCUMENT = AnnotateResponse(
    doc_id="doc_sample_malcolm_baldwin",
    title="Debate between Malcolm X and James Baldwin",
    metadata={"mode": "medium", "sample": True},
    segments=_SEGMENTS,
    annotations=[
        _ann(
            "ann_001",
            "seg_0001",
            "one fellow say one day",
            AnnotationType.QUOTE_VERIFICATION,
            (
                "Malcolm X appears to be paraphrasing a pro-integration argument about interracial "
                "mixing. The exact speaker is uncertain; similar claims circulated in mid-20th-century "
                "civil rights debates."
            ),
            EvidenceStatus.NEEDS_VERIFICATION,
            0.42,
            needs_human_review=True,
            alternative_interpretations=[
                "May refer to integrationist rhetoric rather than a single named figure."
            ],
        ),
        _ann(
            "ann_002",
            "seg_0001",
            "Mr. Muhammad teaches us",
            AnnotationType.DOCTRINAL_CONTEXT,
            (
                "Mr. Muhammad refers to Elijah Muhammad, leader of the Nation of Islam. Malcolm X "
                "is summarizing the NOI emphasis on knowledge of self and recovering history before "
                "enslavement in America."
            ),
            EvidenceStatus.SUPPORTED_GENERAL_CONTEXT,
            0.84,
            sources=[
                Source(title="The Autobiography of Malcolm X", source_type="primary", relevance="direct"),
                Source(title="Nation of Islam speeches and writings", source_type="primary", relevance="direct"),
            ],
        ),
        _ann(
            "ann_003",
            "seg_0002",
            "Birmingham, Alabama, will probably blow up",
            AnnotationType.HISTORICAL_CONTEXT,
            (
                "Birmingham was a major civil rights flashpoint in the early 1960s — bombings, police "
                "repression, and mass protest. Malcolm X uses it as a symbol of imminent racial "
                "crisis, not necessarily a literal prediction."
            ),
            EvidenceStatus.SUPPORTED_GENERAL_CONTEXT,
            0.91,
            sources=[
                Source(title="Birmingham campaign records", source_type="primary", relevance="direct"),
                Source(title="Civil rights history sources", source_type="secondary", relevance="general"),
            ],
            alternative_interpretations=["Rhetorical warning rather than literal forecast."],
        ),
        _ann(
            "ann_004",
            "seg_0003",
            "sit-ins",
            AnnotationType.HISTORICAL_CONTEXT,
            (
                "Sit-ins were nonviolent civil rights protests in which Black students and activists "
                "occupied segregated lunch counters and public spaces, especially from 1960 onward."
            ),
            EvidenceStatus.SUPPORTED,
            0.95,
            sources=[Source(title="Greensboro sit-in records", source_type="primary", relevance="direct")],
        ),
        _ann(
            "ann_005",
            "seg_0003",
            "Black Muslims",
            AnnotationType.ENTITY,
            (
                "Historical label for members of the Nation of Islam. Malcolm X uses the term while "
                "distancing his group from civil rights protest tactics he considers ineffective."
            ),
            EvidenceStatus.SUPPORTED_GENERAL_CONTEXT,
            0.88,
            sources=[Source(title="Malcolm X speeches", source_type="primary", relevance="direct")],
        ),
        _ann(
            "ann_006",
            "seg_0005",
            "integrate or separate",
            AnnotationType.DOCTRINAL_CONTEXT,
            (
                "Frames the central debate of the era: integration into American society vs. Black "
                "separatism/nationalism. Baldwin reframes the stakes as national survival rather "
                "than a simple policy choice."
            ),
            EvidenceStatus.SUPPORTED_GENERAL_CONTEXT,
            0.86,
            sources=[
                Source(title="James Baldwin interviews and essays", source_type="primary", relevance="direct")
            ],
        ),
    ],
)
