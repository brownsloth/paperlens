export interface BBox {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
}

export interface PaperBlock {
  block_id: string;
  paper_id: string;
  page: number;
  block_type: string;
  text: string;
  bbox: BBox;
  reading_order: number;
  section?: string | null;
  metadata?: Record<string, unknown>;
}

export interface PageInfo {
  page: number;
  image_path: string;
  width_px: number;
  height_px: number;
  pdf_width: number;
  pdf_height: number;
}

export interface AnnotationTarget {
  block_id: string;
  quote?: string | null;
  char_start?: number | null;
  char_end?: number | null;
}

export interface PaperChatMessage {
  role: "user" | "assistant";
  content: string;
  created_at?: string;
}

export interface PaperAnnotation {
  annotation_id: string;
  paper_id: string;
  target: AnnotationTarget;
  annotation_type: string;
  annotation_text: string;
  confidence: number;
  lens: string;
  evidence_status: string;
  page?: number | null;
  bbox?: BBox | null;
  color?: string | null;
  thread?: PaperChatMessage[];
}

export interface PaperMeta {
  paper_id: string;
  title: string;
  authors: string[];
  year?: number | null;
  arxiv_id?: string | null;
  abstract?: string | null;
  pdf_status: string;
  page_count: number;
  block_count: number;
  has_annotations: boolean;
}

export interface PaperDocument {
  paper: PaperMeta;
  blocks: PaperBlock[];
  pages: PageInfo[];
  annotations: PaperAnnotation[];
  metadata?: Record<string, unknown>;
}

export type PaperLens = "beginner" | "implementation" | "math" | "historical" | "lineage";

export function bboxToOverlay(
  bbox: BBox,
  page: PageInfo,
): { left: number; top: number; width: number; height: number } {
  const scaleX = page.width_px / page.pdf_width;
  const scaleY = page.height_px / page.pdf_height;
  return {
    left: bbox.x0 * scaleX,
    top: bbox.y0 * scaleY,
    width: (bbox.x1 - bbox.x0) * scaleX,
    height: (bbox.y1 - bbox.y0) * scaleY,
  };
}
