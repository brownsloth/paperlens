from __future__ import annotations

from speechlens.models import Segment, Transcript


def get_context_window(
    transcript: Transcript,
    segment_id: str,
    *,
    previous: int = 1,
    next_count: int = 2,
) -> tuple[list[Segment], Segment, list[Segment]]:
    segments = transcript.segments
    idx = next(i for i, s in enumerate(segments) if s.segment_id == segment_id)
    before = segments[max(0, idx - previous) : idx]
    current = segments[idx]
    after = segments[idx + 1 : idx + 1 + next_count]
    return before, current, after


def format_context_for_search(
    before: list[Segment],
    current: Segment,
    after: list[Segment],
) -> str:
    parts: list[str] = []
    for seg in before:
        label = seg.speaker or "Speaker"
        parts.append(f"[{label}]: {seg.text}")
    label = current.speaker or "Speaker"
    parts.append(f"[{label}]: {current.text}")
    for seg in after:
        label = seg.speaker or "Speaker"
        parts.append(f"[{label}]: {seg.text}")
    return "\n\n".join(parts)
