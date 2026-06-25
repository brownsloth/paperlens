import type { AnnotateResponse } from "./types";

const seg1 =
  "I heard one fellow say one day that eventually intermarriage and intermixing would take place on such a vast scale that it would produce a chocolate-colored race. And Mr. Muhammad teaches us that until the black man here in America is connected or reestablished or given some knowledge of his existence prior to coming here to America, he will never feel motivated to stand on his own feet and solve his own problems.";

const seg2 =
  "I believe, for example, that one of these days, maybe tomorrow, Birmingham, Alabama, will probably blow up. The black man in Birmingham knows that he is not wanted there. He knows that the white man there will use every means at his disposal to keep him in his place.";

const seg3 =
  "The so-called Negroes who are taking part in these sit-ins are being used. They don't realize that they are being used by the very people who have kept them in a state of ignorance for four hundred years. The Black Muslims, as we are called, do not believe in begging for what is rightfully ours.";

const seg5 =
  "The question is not whether we will integrate or separate. The question is whether we will survive as a nation. And survival means facing what we have done, what we continue to do, and what we refuse to see.";

function span(text: string, spanText: string) {
  const start = text.indexOf(spanText);
  return { span_start: start, span_end: start + spanText.length, span_text: spanText };
}

/** Demo annotations so the reader UI works without an API key. */
export const SAMPLE_DOCUMENT: AnnotateResponse = {
  doc_id: "doc_sample_malcolm_baldwin",
  title: "Debate between Malcolm X and James Baldwin",
  metadata: { mode: "medium", sample: true },
  segments: [
    { segment_id: "seg_0001", speaker: "MALCOLM X", text: seg1 },
    { segment_id: "seg_0002", speaker: "MALCOLM X", text: seg2 },
    { segment_id: "seg_0003", speaker: "MALCOLM X", text: seg3 },
    {
      segment_id: "seg_0004",
      speaker: "JAMES BALDWIN",
      text: "I think that the Negro in this country has every right to be angry. But I also think that the country has every reason to be afraid. Because if the Negro is not able to achieve his freedom here, then the country itself is doomed.",
    },
    { segment_id: "seg_0005", speaker: "JAMES BALDWIN", text: seg5 },
  ],
  annotations: [
    {
      annotation_id: "ann_001",
      segment_id: "seg_0001",
      ...span(seg1, "one fellow say one day"),
      annotation_type: "quote_verification",
      annotation_text:
        "Malcolm X appears to be paraphrasing a pro-integration argument about interracial mixing. The exact speaker is uncertain; similar claims circulated in mid-20th-century civil rights debates.",
      evidence_status: "needs_verification",
      confidence: 0.42,
      sources: [],
      needs_human_review: true,
      alternative_interpretations: [
        "May refer to integrationist rhetoric rather than a single named figure.",
      ],
    },
    {
      annotation_id: "ann_002",
      segment_id: "seg_0001",
      ...span(seg1, "Mr. Muhammad teaches us"),
      annotation_type: "doctrinal_context",
      annotation_text:
        "Mr. Muhammad refers to Elijah Muhammad, leader of the Nation of Islam. Malcolm X is summarizing the NOI emphasis on knowledge of self and recovering history before enslavement in America.",
      evidence_status: "supported_general_context",
      confidence: 0.84,
      sources: [
        { title: "The Autobiography of Malcolm X", source_type: "primary", relevance: "direct" },
        { title: "Nation of Islam speeches and writings", source_type: "primary", relevance: "direct" },
      ],
      needs_human_review: false,
      alternative_interpretations: [],
    },
    {
      annotation_id: "ann_003",
      segment_id: "seg_0002",
      ...span(seg2, "Birmingham, Alabama, will probably blow up"),
      annotation_type: "historical_context",
      annotation_text:
        "Birmingham was a major civil rights flashpoint in the early 1960s — bombings, police repression, and mass protest. Malcolm X uses it as a symbol of imminent racial crisis, not necessarily a literal prediction.",
      evidence_status: "supported_general_context",
      confidence: 0.91,
      sources: [
        { title: "Birmingham campaign records", source_type: "primary", relevance: "direct" },
        { title: "Civil rights history sources", source_type: "secondary", relevance: "general" },
      ],
      needs_human_review: false,
      alternative_interpretations: ["Rhetorical warning rather than literal forecast."],
    },
    {
      annotation_id: "ann_004",
      segment_id: "seg_0003",
      ...span(seg3, "sit-ins"),
      annotation_type: "historical_context",
      annotation_text:
        "Sit-ins were nonviolent civil rights protests in which Black students and activists occupied segregated lunch counters and public spaces, especially from 1960 onward.",
      evidence_status: "supported",
      confidence: 0.95,
      sources: [{ title: "Greensboro sit-in records", source_type: "primary", relevance: "direct" }],
      needs_human_review: false,
      alternative_interpretations: [],
    },
    {
      annotation_id: "ann_005",
      segment_id: "seg_0003",
      ...span(seg3, "Black Muslims"),
      annotation_type: "entity",
      annotation_text:
        "Historical label for members of the Nation of Islam. Malcolm X uses the term while distancing his group from civil rights protest tactics he considers ineffective.",
      evidence_status: "supported_general_context",
      confidence: 0.88,
      sources: [{ title: "Malcolm X speeches", source_type: "primary", relevance: "direct" }],
      needs_human_review: false,
      alternative_interpretations: [],
    },
    {
      annotation_id: "ann_006",
      segment_id: "seg_0005",
      ...span(seg5, "integrate or separate"),
      annotation_type: "doctrinal_context",
      annotation_text:
        "Frames the central debate of the era: integration into American society vs. Black separatism/nationalism. Baldwin reframes the stakes as national survival rather than a simple policy choice.",
      evidence_status: "supported_general_context",
      confidence: 0.86,
      sources: [
        { title: "James Baldwin interviews and essays", source_type: "primary", relevance: "direct" },
      ],
      needs_human_review: false,
      alternative_interpretations: [],
    },
  ],
};
