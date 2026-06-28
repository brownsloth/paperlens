from __future__ import annotations

from paperlens.models import AnnotationTarget, BBox, BlockType, PaperAnnotation, PaperBlock


def resolve_quote_span(block: PaperBlock, quote: str | None) -> tuple[int | None, int | None]:
  if not quote:
    return None, None
  idx = block.text.find(quote)
  if idx < 0:
    lowered = block.text.lower()
    idx = lowered.find(quote.lower())
  if idx < 0:
    return None, None
  return idx, idx + len(quote)


def resolve_annotation_bbox(
  block: PaperBlock,
  *,
  char_start: int | None = None,
  char_end: int | None = None,
) -> BBox:
  """Map char offsets within a block to a sub-bbox (v0: whole block if offsets unknown)."""
  if char_start is None or char_end is None:
    return block.bbox

  text_len = max(len(block.text), 1)
  height = block.bbox.y1 - block.bbox.y0
  y0 = block.bbox.y0 + height * (char_start / text_len)
  y1 = block.bbox.y0 + height * (char_end / text_len)
  return BBox(x0=block.bbox.x0, y0=y0, x1=block.bbox.x1, y1=max(y1, y0 + 2))


def attach_bbox_to_annotations(
  blocks: list[PaperBlock],
  annotations: list[PaperAnnotation],
) -> list[PaperAnnotation]:
  block_map = {b.block_id: b for b in blocks}
  resolved: list[PaperAnnotation] = []

  for ann in annotations:
    block = block_map.get(ann.target.block_id)
    if not block:
      resolved.append(ann)
      continue
    if ann.bbox is not None and ann.page is not None:
      resolved.append(ann)
      continue
    start, end = ann.target.char_start, ann.target.char_end
    if start is None or end is None:
      start, end = resolve_quote_span(block, ann.target.quote)
    bbox = resolve_annotation_bbox(block, char_start=start, char_end=end)
    target = ann.target.model_copy(update={"char_start": start, "char_end": end})
    resolved.append(
      ann.model_copy(
        update={
          "target": target,
          "page": block.page,
          "bbox": bbox,
        }
      )
    )
  return resolved


def bbox_to_overlay(
  bbox: BBox,
  page_info_width: int,
  page_info_height: int,
  pdf_width: float,
  pdf_height: float,
) -> dict[str, float]:
  """Convert PDF-point bbox to pixel overlay coordinates on rendered page image."""
  scale_x = page_info_width / pdf_width
  scale_y = page_info_height / pdf_height
  return {
    "left": bbox.x0 * scale_x,
    "top": bbox.y0 * scale_y,
    "width": (bbox.x1 - bbox.x0) * scale_x,
    "height": (bbox.y1 - bbox.y0) * scale_y,
  }
