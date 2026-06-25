from __future__ import annotations

import html
import json
from pathlib import Path

from speechlens.models import AnnotateResponse, Annotation, Segment, Transcript


def _footnote_index(annotations: list[Annotation], annotation_id: str) -> int:
    for idx, ann in enumerate(annotations, start=1):
        if ann.annotation_id == annotation_id:
            return idx
    return 0


def render_markdown(transcript: Transcript, annotations: list[Annotation]) -> str:
    by_segment: dict[str, list[Annotation]] = {}
    for ann in annotations:
        by_segment.setdefault(ann.segment_id, []).append(ann)

    lines: list[str] = [
        f"# Annotated Speech: {transcript.title}",
        "",
    ]
    if transcript.date:
        lines.append(f"**Date:** {transcript.date}")
        lines.append("")
    if transcript.source_url:
        lines.append(f"**Source:** {transcript.source_url}")
        lines.append("")

    footnotes: list[str] = []
    footnote_counter = 0

    for segment in transcript.segments:
        if segment.speaker:
            lines.append(f"## Speaker: {segment.speaker}")
            lines.append("")

        segment_anns = sorted(
            by_segment.get(segment.segment_id, []),
            key=lambda a: a.span_start,
        )
        text = segment.text
        offset = 0
        rendered_parts: list[str] = []

        for ann in segment_anns:
            footnote_counter += 1
            before = text[offset : ann.span_start]
            rendered_parts.append(before)
            rendered_parts.append(f"[{ann.span_text}][^{footnote_counter}]")
            footnotes.append(_footnote_line(footnote_counter, ann))
            offset = ann.span_end

        rendered_parts.append(text[offset:])
        lines.append("".join(rendered_parts))
        lines.append("")

    if footnotes:
        lines.append("---")
        lines.append("")
        lines.extend(footnotes)

    return "\n".join(lines).strip() + "\n"


def _footnote_line(number: int, ann: Annotation) -> str:
    sources = ", ".join(s.title for s in ann.sources) if ann.sources else "No sources listed"
    alt = ""
    if ann.alternative_interpretations:
        alt = " Alternatives: " + "; ".join(ann.alternative_interpretations)
    review = " **[needs human review]**" if ann.needs_human_review else ""
    return (
        f"[^{number}]: {ann.annotation_text} "
        f"(type: {ann.annotation_type.value}; evidence: {ann.evidence_status.value}; "
        f"confidence: {ann.confidence:.2f}; sources: {sources}){alt}{review}"
    )


def render_html(transcript: Transcript, annotations: list[Annotation]) -> str:
    by_segment: dict[str, list[Annotation]] = {}
    for ann in annotations:
        by_segment.setdefault(ann.segment_id, []).append(ann)

    body_parts: list[str] = []
    for segment in transcript.segments:
        speaker_html = (
            f'<h3 class="speaker">{html.escape(segment.speaker)}</h3>' if segment.speaker else ""
        )
        segment_anns = sorted(
            by_segment.get(segment.segment_id, []),
            key=lambda a: a.span_start,
        )
        text = segment.text
        offset = 0
        parts: list[str] = []
        for ann in segment_anns:
            parts.append(html.escape(text[offset : ann.span_start]))
            parts.append(
                f'<mark class="annotation-span" data-annotation-id="{ann.annotation_id}">'
                f"{html.escape(ann.span_text)}</mark>"
            )
            offset = ann.span_end
        parts.append(html.escape(text[offset:]))
        body_parts.append(
            f'<section class="segment" id="{segment.segment_id}">{speaker_html}'
            f'<p class="segment-text">{"".join(parts)}</p></section>'
        )

    cards = "\n".join(_annotation_card(ann) for ann in annotations)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(transcript.title)}</title>
  <style>
    body {{ font-family: Georgia, serif; max-width: 900px; margin: 2rem auto; line-height: 1.6; }}
    .speaker {{ color: #444; margin-bottom: 0.25rem; }}
    mark.annotation-span {{ background: #fff3bf; cursor: pointer; }}
    .annotations {{ margin-top: 3rem; border-top: 1px solid #ddd; padding-top: 1rem; }}
    .card {{ border: 1px solid #e5e5e5; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; }}
    .meta {{ color: #666; font-size: 0.9rem; }}
    .review {{ color: #b45309; font-weight: bold; }}
  </style>
</head>
<body>
  <h1>{html.escape(transcript.title)}</h1>
  {"".join(body_parts)}
  <aside class="annotations">
    <h2>Annotations</h2>
    {cards}
  </aside>
</body>
</html>
"""


def _annotation_card(ann: Annotation) -> str:
    sources = (
        "<ul>" + "".join(f"<li>{html.escape(s.title)}</li>" for s in ann.sources) + "</ul>"
        if ann.sources
        else "<p><em>No sources listed</em></p>"
    )
    review = '<p class="review">Needs human review</p>' if ann.needs_human_review else ""
    return f"""<article class="card" id="{ann.annotation_id}">
  <h3>{html.escape(ann.span_text)}</h3>
  <p>{html.escape(ann.annotation_text)}</p>
  <p class="meta">Type: {ann.annotation_type.value} · Evidence: {ann.evidence_status.value} · Confidence: {ann.confidence:.2f}</p>
  {review}
  {sources}
</article>"""


def export_markdown(path: str | Path, transcript: Transcript, annotations: list[Annotation]) -> None:
    Path(path).write_text(render_markdown(transcript, annotations), encoding="utf-8")


def export_html(path: str | Path, transcript: Transcript, annotations: list[Annotation]) -> None:
    Path(path).write_text(render_html(transcript, annotations), encoding="utf-8")


def export_json(path: str | Path, response: AnnotateResponse) -> None:
    Path(path).write_text(response.model_dump_json(indent=2), encoding="utf-8")
