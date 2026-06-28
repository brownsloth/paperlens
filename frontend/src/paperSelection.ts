import type { BBox, PageInfo, PaperBlock } from "./paperTypes";
import { bboxToOverlay } from "./paperTypes";

export type SelectMode = "text" | "region";

export interface TextLine {
  id: string;
  blockId: string;
  page: number;
  lineIndex: number;
  text: string;
  bbox: BBox;
  column: number;
}

export interface ColumnGroup {
  column: number;
  leftPct: number;
  widthPct: number;
  lines: TextLine[];
}

export interface TextSelectionPayload {
  page: number;
  quote: string;
  blockId: string;
  bbox: BBox;
}

export interface RegionSelectionPayload {
  page: number;
  bbox: BBox;
  /** Position relative to the page container element (pixels). */
  containerRect: { left: number; top: number; width: number; height: number };
}

interface LineMeta {
  text: string;
  bbox: BBox;
}

function blockColumnHint(bbox: BBox, pdfWidth: number): number {
  const split = pdfWidth / 2;
  const margin = pdfWidth * 0.02;
  if (bbox.x0 < split - margin && bbox.x1 <= split + margin) return 0;
  if (bbox.x0 >= split - margin) return 1;
  if (bbox.x0 < split * 0.6) return 0;
  if (bbox.x0 > split * 0.8) return 1;
  return lineColumnIndex(bbox, split);
}

function fallbackLines(block: PaperBlock, pdfWidth: number): LineMeta[] {
  const parts = block.text.split("\n").map((p) => p.trim()).filter(Boolean);
  if (parts.length <= 1) {
    const col = blockColumnHint(block.bbox, pdfWidth);
    return [{ text: block.text.trim(), bbox: clampLineBbox(block.bbox, col, pdfWidth) }];
  }
  const height = block.bbox.y1 - block.bbox.y0;
  const lineH = height / parts.length;
  const col = blockColumnHint(block.bbox, pdfWidth);
  return parts.map((text, i) => ({
    text,
    bbox: clampLineBbox(
      {
        x0: block.bbox.x0,
        y0: block.bbox.y0 + i * lineH,
        x1: block.bbox.x1,
        y1: block.bbox.y0 + (i + 1) * lineH,
      },
      col,
      pdfWidth,
    ),
  }));
}

function clampLineBbox(bbox: BBox, column: number, pdfWidth: number): BBox {
  const split = pdfWidth / 2;
  const margin = pdfWidth * 0.02;
  if (column === 0) {
    return { ...bbox, x1: Math.min(bbox.x1, split - margin) };
  }
  return { ...bbox, x0: Math.max(bbox.x0, split + margin) };
}

/** Detect a true two-column layout (not single-column with wide lines). */
export function columnSplitForPage(lines: Pick<TextLine, "bbox">[], pdfWidth: number): number | null {
  if (lines.length < 8) return null;

  const split = pdfWidth / 2;
  const margin = pdfWidth * 0.02;
  const spanning = lines.filter((l) => l.bbox.x0 < split && l.bbox.x1 > split);
  const leftContained = lines.filter((l) => l.bbox.x1 <= split + margin);
  const rightContained = lines.filter((l) => l.bbox.x0 >= split - margin);
  const fullWidth = lines.filter((l) => l.bbox.x1 - l.bbox.x0 > pdfWidth * 0.55);

  if (leftContained.length < 5 || rightContained.length < 5) return null;
  if (spanning.length > lines.length * 0.1) return null;
  if (fullWidth.length > lines.length * 0.2) return null;

  const overlap = leftContained.length + rightContained.length - lines.length;
  if (overlap > lines.length * 0.35) return null;

  return split;
}

export function lineColumnIndex(bbox: BBox, split: number): number {
  if (bbox.x0 >= split) return 1;
  if (bbox.x1 <= split) return 0;
  const leftExtent = Math.min(bbox.x1, split) - bbox.x0;
  const rightExtent = bbox.x1 - Math.max(bbox.x0, split);
  return leftExtent >= rightExtent ? 0 : 1;
}

export function groupLinesByColumn(lines: TextLine[], page: PageInfo): ColumnGroup[] {
  const split = columnSplitForPage(lines, page.pdf_width);
  if (split === null) {
    return [{ column: 0, leftPct: 0, widthPct: 100, lines }];
  }

  const leftLines = lines.filter((l) => l.column === 0);
  const rightLines = lines.filter((l) => l.column === 1);
  if (!leftLines.length || !rightLines.length) {
    return [{ column: 0, leftPct: 0, widthPct: 100, lines }];
  }

  const margin = page.pdf_width * 0.02;
  const leftContained = leftLines.filter((l) => l.bbox.x1 <= split + margin);
  const rightContained = rightLines.filter((l) => l.bbox.x0 >= split - margin);
  const leftEdge = leftContained.length
    ? Math.max(...leftContained.map((l) => l.bbox.x1))
    : split;
  const rightEdge = rightContained.length
    ? Math.min(...rightContained.map((l) => l.bbox.x0))
    : split;
  const gutterPct = ((leftEdge + rightEdge) / 2 / page.pdf_width) * 100;

  return [
    {
      column: 0,
      leftPct: 0,
      widthPct: gutterPct,
      lines: leftLines,
    },
    {
      column: 1,
      leftPct: gutterPct,
      widthPct: 100 - gutterPct,
      lines: rightLines,
    },
  ];
}

export function textLineStyle(
  line: TextLine,
  page: PageInfo,
  col?: ColumnGroup,
): { left: string; top: string; width: string; height: string; fontSize: string } {
  const box = bboxToPercent(line.bbox, page);
  if (!col || col.widthPct >= 99) {
    return {
      left: `${box.left}%`,
      top: `${box.top}%`,
      width: `${Math.max(box.width, 0.5)}%`,
      height: `${box.height}%`,
      fontSize: `${Math.max(box.height * 0.82, 0.4)}cqh`,
    };
  }
  const relLeft = ((box.left - col.leftPct) / col.widthPct) * 100;
  const relWidth = (box.width / col.widthPct) * 100;
  return {
    left: `${relLeft}%`,
    top: `${box.top}%`,
    width: `${Math.max(relWidth, 1)}%`,
    height: `${box.height}%`,
    fontSize: `${Math.max(box.height * 0.82, 0.4)}cqh`,
  };
}

export function linesForPage(
  blocks: PaperBlock[],
  page: number,
  pageInfo: PageInfo,
  _refStart?: number,
): TextLine[] {
  const lines: TextLine[] = [];
  for (const block of blocks) {
    if (block.page !== page) continue;
    if (!block.text.trim()) continue;
    if (block.block_type === "list_item") continue;

    const metaLines = (block.metadata?.lines as LineMeta[] | undefined) ?? fallbackLines(block, pageInfo.pdf_width);
    metaLines.forEach((line, lineIndex) => {
      if (!line.text.trim()) return;
      lines.push({
        id: `${block.block_id}_l${lineIndex}`,
        blockId: block.block_id,
        page,
        lineIndex,
        text: line.text,
        bbox: line.bbox,
        column: 0,
      });
    });
  }
  const sorted = lines.sort((a, b) => a.bbox.y0 - b.bbox.y0 || a.bbox.x0 - b.bbox.x0);
  const split = columnSplitForPage(sorted, pageInfo.pdf_width);
  const assignSplit = split ?? pageInfo.pdf_width / 2;
  return sorted.map((line) => ({
    ...line,
    column: split !== null ? lineColumnIndex(line.bbox, assignSplit) : blockColumnHint(line.bbox, pageInfo.pdf_width),
  }));
}

export function bboxToPercent(
  bbox: BBox,
  page: PageInfo,
): { left: number; top: number; width: number; height: number } {
  const o = bboxToOverlay(bbox, page);
  return {
    left: (o.left / page.width_px) * 100,
    top: (o.top / page.height_px) * 100,
    width: (o.width / page.width_px) * 100,
    height: (o.height / page.height_px) * 100,
  };
}

export function screenRectToPdfBBox(
  rect: { left: number; top: number; width: number; height: number },
  container: HTMLElement,
  page: PageInfo,
): BBox {
  const cw = container.clientWidth;
  const ch = (page.height_px / page.width_px) * cw;
  const scaleX = page.pdf_width / cw;
  const scaleY = page.pdf_height / ch;
  return {
    x0: rect.left * scaleX,
    y0: rect.top * scaleY,
    x1: (rect.left + rect.width) * scaleX,
    y1: (rect.top + rect.height) * scaleY,
  };
}

export function collectTextSelection(
  page: number,
  container: HTMLElement,
  lineEls: NodeListOf<Element>,
  columnSplit: number | null,
): TextSelectionPayload | null {
  const sel = window.getSelection();
  if (!sel || sel.isCollapsed) return null;
  const quote = sel.toString().trim();
  if (!quote) return null;

  const matched: TextLine[] = [];
  lineEls.forEach((el) => {
    const start = sel.anchorNode;
    const end = sel.focusNode;
    if (!start || !end) return;
    try {
      const anchorIn = el.contains(start) || el === start;
      const focusIn = el.contains(end) || el === end;
      const intersects = sel.containsNode(el, true) || anchorIn || focusIn;
      if (intersects) {
        matched.push({
          id: el.getAttribute("data-line-id") ?? "",
          blockId: el.getAttribute("data-block-id") ?? "",
          page,
          lineIndex: Number(el.getAttribute("data-line-index") ?? 0),
          text: el.textContent ?? "",
          bbox: {
            x0: Number(el.getAttribute("data-x0")),
            y0: Number(el.getAttribute("data-y0")),
            x1: Number(el.getAttribute("data-x1")),
            y1: Number(el.getAttribute("data-y1")),
          },
          column: Number(el.getAttribute("data-column") ?? 0),
        });
      }
    } catch {
      // ignore range errors on partial selections
    }
  });

  if (!matched.length) {
    const blockId = sel.anchorNode?.parentElement?.closest("[data-block-id]")?.getAttribute("data-block-id");
    if (!blockId) return null;
    const blockEl = container.querySelector(`[data-block-id="${blockId}"]`);
    if (!blockEl) return null;
    return {
      page,
      quote,
      blockId,
      bbox: {
        x0: Number(blockEl.getAttribute("data-x0")),
        y0: Number(blockEl.getAttribute("data-y0")),
        x1: Number(blockEl.getAttribute("data-x1")),
        y1: Number(blockEl.getAttribute("data-y1")),
      },
    };
  }

  let filtered = matched;
  if (matched.length > 1) {
    const anchorEl = sel.anchorNode?.parentElement?.closest("[data-line-id]");
    const focusEl = sel.focusNode?.parentElement?.closest("[data-line-id]");
    const anchorCol = anchorEl
      ? Number(anchorEl.getAttribute("data-column") ?? 0)
      : focusEl
        ? Number(focusEl.getAttribute("data-column") ?? 0)
        : matched[0].column;
    const mixedColumns = new Set(matched.map((m) => m.column)).size > 1;
    if (mixedColumns || columnSplit !== null) {
      filtered = matched.filter((m) => m.column === anchorCol);
      if (!filtered.length) filtered = matched;
    }
  }

  filtered.sort((a, b) => a.bbox.y0 - b.bbox.y0 || a.bbox.x0 - b.bbox.x0);
  const blockId = filtered[0].blockId;
  const mergedQuote = filtered.map((m) => m.text).join(" ").replace(/\s+/g, " ").trim();
  const x0 = Math.min(...filtered.map((m) => m.bbox.x0));
  const y0 = Math.min(...filtered.map((m) => m.bbox.y0));
  const x1 = Math.max(...filtered.map((m) => m.bbox.x1));
  const y1 = Math.max(...filtered.map((m) => m.bbox.y1));

  return { page, quote: mergedQuote || quote, blockId, bbox: { x0, y0, x1, y1 } };
}

export function selectionToolbarPosition(rect: DOMRect): { top: number; left: number } {
  return {
    top: Math.max(8, rect.top - 48),
    left: Math.max(8, rect.left),
  };
}
