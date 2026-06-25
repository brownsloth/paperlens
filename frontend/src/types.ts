export interface Source {
  title: string;
  url?: string | null;
  source_type: string;
  quote?: string | null;
  relevance: string;
}

export interface Segment {
  segment_id: string;
  speaker?: string | null;
  start_time?: number | null;
  end_time?: number | null;
  text: string;
}

export interface Annotation {
  annotation_id: string;
  segment_id: string;
  span_start: number;
  span_end: number;
  span_text: string;
  annotation_type: string;
  annotation_text: string;
  evidence_status: string;
  confidence: number;
  sources: Source[];
  needs_human_review: boolean;
  alternative_interpretations: string[];
}

export interface AnnotateResponse {
  doc_id: string;
  title: string;
  segments: Segment[];
  annotations: Annotation[];
  metadata?: Record<string, unknown>;
}

export type AnnotationDepth = "light" | "medium" | "dense";
