# SpeechLens: Agentic Speech Annotation Tool

SpeechLens is an agentic annotation system that takes a speech, debate, interview, sermon, lecture, or historical transcript and enriches it with source-backed contextual annotations.

The goal is simple:

> Turn hard-to-understand speeches into readable, historically grounded, evidence-linked documents.

Given a transcript like a Malcolm X–James Baldwin debate, SpeechLens identifies references, claims, people, places, historical events, ideological terms, quotations, and implied context, then attaches short annotations with citations and confidence levels.

---

## Example

Input sentence:

> I heard one fellow say one day that eventually intermarriage and intermixing would take place on such a vast scale that it would produce a chocolate-colored race.

Possible annotation:

```json
{
  "span": "one fellow say one day",
  "type": "possible_quote_reference",
  "annotation": "The speaker appears to be referring to a pro-integration or interracial-mixing argument common in mid-20th-century civil rights debates. The system should search for exact or near-exact public statements by known figures before attaching a named attribution.",
  "evidence_status": "needs_verification",
  "confidence": 0.42,
  "sources": []
}
```

Input sentence:

> And Mr. Muhammad teaches us that until the black man here in America is connected or reestablished or given some knowledge of his existence prior to coming here to America...

Possible annotation:

```json
{
  "span": "Mr. Muhammad teaches us",
  "type": "doctrinal_context",
  "annotation": "Mr. Muhammad refers to Elijah Muhammad, leader of the Nation of Islam. Malcolm X is summarizing a central Nation of Islam idea: that Black Americans had been cut off from their original history, identity, religion, and dignity through slavery and white supremacy.",
  "evidence_status": "supported_general_context",
  "confidence": 0.84,
  "sources": [
    "Nation of Islam speeches and writings",
    "Malcolm X speeches",
    "The Autobiography of Malcolm X",
    "secondary scholarly sources"
  ]
}
```

Input sentence:

> I believe, for example, that one of these days, maybe tomorrow, Birmingham, Alabama, will probably blow up.

Possible annotation:

```json
{
  "span": "Birmingham, Alabama, will probably blow up",
  "type": "historical_event_context",
  "annotation": "Birmingham was one of the major flashpoints of the civil rights struggle. In the early 1960s it was associated with violent segregationist resistance, bombings, police repression, and mass protest. A reader needs this context to understand why Birmingham is invoked as a symbol of imminent racial crisis.",
  "evidence_status": "supported_general_context",
  "confidence": 0.91,
  "sources": [
    "Civil rights history sources",
    "Birmingham campaign records",
    "contemporary newspaper archives"
  ]
}
```

---

## Why This Should Exist

Historical speeches are difficult because speakers assume shared context.

They mention:

* people by partial names
* events without dates
* slogans without explanation
* doctrines without defining them
* “everyone knows” references
* accusations that may or may not be true
* quoted claims without naming the original speaker

A modern reader often does not know the context.

SpeechLens solves this by creating an annotation layer on top of the text.

It should not rewrite the speech.

It should not “explain away” the speaker.

It should preserve the original speech and add careful, source-backed context around it.

---

## Core Product

SpeechLens has three modes.

### 1. Reader Mode

A user pastes a transcript or URL.

SpeechLens returns an annotated reading interface.

The original text stays intact. Highlighted spans can be clicked to reveal:

* who or what is being referenced
* historical background
* source-backed verification
* whether the claim is confirmed, disputed, unclear, or false
* relevant primary/secondary sources
* confidence level

### 2. Researcher Mode

The system produces a structured annotation file.

Useful for scholars, journalists, teachers, students, and documentary researchers.

Output formats:

* JSON
* Markdown
* HTML
* TEI XML
* CSV
* Obsidian-compatible notes

### 3. Classroom Mode

The system produces a more readable student-friendly version.

This includes:

* glossary
* timeline
* key people
* “what you need to know before reading”
* discussion questions
* contested claims
* suggested further reading

---

## Annotation Types

SpeechLens should support the following annotation categories.

### Entity Annotations

Identifies people, organizations, places, newspapers, books, speeches, laws, movements, parties, and institutions.

Examples:

* Mr. Muhammad → Elijah Muhammad
* Birmingham → Birmingham, Alabama, civil rights flashpoint
* Black Muslims → Nation of Islam, historical terminology
* sit-ins → civil rights protest tactic

---

### Historical Context Annotations

Explains events or background conditions necessary for comprehension.

Examples:

* Birmingham campaign
* Little Rock Nine
* Montgomery Bus Boycott
* Nation of Islam growth
* civil rights sit-ins
* desegregation battles
* Cold War race politics
* decolonization in Africa

---

### Claim Verification Annotations

Detects factual claims and attempts to verify them.

Example:

> “X person said Y.”

The system should check:

* exact phrase search
* near-quote search
* named entity search
* archive search
* books/speeches search
* newspaper archive search
* scholarly references

Output statuses:

```txt
supported
partially_supported
unsupported
contradicted
unclear
not_enough_evidence
```

---

### Quote Attribution Annotations

When a speaker says:

> “I heard someone say...”

or

> “They say...”

or

> “The white man says...”

SpeechLens should try to identify whether this is:

* a known quote
* a paraphrase
* a common public argument
* a strawman
* a rhetorical device
* unverifiable

The tool should not hallucinate attribution.

If it cannot find proof, it should say so.

---

### Ideological / Doctrinal Context Annotations

Some speeches contain worldview-specific references.

Examples:

* Nation of Islam theology
* Black nationalism
* integrationism
* separatism
* nonviolence
* civil disobedience
* Marxism
* Pan-Africanism
* anti-colonialism
* religious references

The system should explain these neutrally.

It should distinguish between:

* what the speaker believed
* what the movement taught
* what historians say
* what critics argued

---

### Rhetorical Annotations

SpeechLens can also annotate rhetorical moves.

Examples:

```json
{
  "span": "Birmingham will probably blow up",
  "type": "rhetorical_warning",
  "annotation": "This is not necessarily a literal prediction of an explosion. It is a warning that racial tensions may erupt into mass unrest or violence."
}
```

Rhetorical annotation types:

* analogy
* warning
* prophecy
* sarcasm
* accusation
* appeal to history
* appeal to dignity
* enemy construction
* moral contrast
* audience mobilization
* reframing

---

### Contested Interpretation Annotations

Some passages should not get one definitive explanation.

For example, a passage may be interpreted differently by:

* civil rights historians
* religious studies scholars
* Black nationalist thinkers
* liberal integrationists
* contemporary journalists
* the speaker’s own later writings

SpeechLens should expose competing interpretations when appropriate.

---

## System Architecture

```txt
                ┌────────────────────┐
                │ Transcript / URL     │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │ Ingestion Layer     │
                └─────────┬──────────┘
                          │
                          ▼
                ┌────────────────────┐
                │ Segmentation        │
                └─────────┬──────────┘
                          │
                          ▼
       ┌──────────────────┼──────────────────┐
       ▼                  ▼                  ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Entity Agent │   │ Claim Agent  │   │ Context Agent│
└──────┬───────┘   └──────┬───────┘   └──────┬───────┘
       │                  │                  │
       ▼                  ▼                  ▼
┌────────────────────────────────────────────────────┐
│ Retrieval + Evidence Layer                          │
│ Search, archives, books, transcripts, papers, web   │
└───────────────────────┬────────────────────────────┘
                        ▼
              ┌────────────────────┐
              │ Evidence Scorer     │
              └─────────┬──────────┘
                        ▼
              ┌────────────────────┐
              │ Annotation Writer   │
              └─────────┬──────────┘
                        ▼
              ┌────────────────────┐
              │ Human Review UI     │
              └─────────┬──────────┘
                        ▼
              ┌────────────────────┐
              │ Published Document │
              └────────────────────┘
```

---

## Agent Design

### 1. Ingestion Agent

Responsibilities:

* accept URL, raw text, PDF, audio, or video
* extract transcript
* normalize speaker labels
* preserve paragraph boundaries
* preserve timestamps if available
* detect language
* detect source metadata

Input:

```txt
URL or transcript
```

Output:

```json
{
  "title": "Debate between Malcolm X and James Baldwin",
  "date": "1961-04-25",
  "speakers": ["Malcolm X", "James Baldwin", "Leverne McCummins"],
  "segments": [...]
}
```

---

### 2. Segmentation Agent

Splits speech into meaningful spans.

Not every sentence needs annotation.

The segmentation agent identifies candidate spans such as:

* named entities
* ambiguous references
* historical claims
* causal claims
* moral claims
* quoted/paraphrased claims
* emotionally loaded phrases
* unfamiliar terms
* place references
* institutional references

Output:

```json
{
  "segment_id": "seg_0042",
  "text": "Birmingham, Alabama, will probably blow up.",
  "candidate_spans": [
    {
      "span": "Birmingham, Alabama",
      "reason": "historical place reference"
    },
    {
      "span": "will probably blow up",
      "reason": "rhetorical prediction requiring context"
    }
  ]
}
```

---

### 3. Entity Agent

Finds entities and resolves them.

Example:

```json
{
  "mention": "Mr. Muhammad",
  "resolved_entity": "Elijah Muhammad",
  "entity_type": "person",
  "confidence": 0.96,
  "disambiguation_reason": "Malcolm X often used 'Mr. Muhammad' to refer to Elijah Muhammad, leader of the Nation of Islam."
}
```

Entity sources:

* Wikidata
* Library of Congress
* SNAC
* Wikipedia for first-pass lookup
* Britannica
* Stanford Encyclopedia of Philosophy
* civil rights archives
* university archives
* book indexes
* speech transcript collections

---

### 4. Claim Detection Agent

Extracts factual claims.

Claim examples:

```txt
Someone said intermarriage would create a chocolate-colored race.
Mr. Muhammad teaches that Black Americans need knowledge of pre-slavery existence.
Birmingham is close to violent eruption.
```

The agent classifies each claim:

```json
{
  "claim": "Someone said intermarriage would create a chocolate-colored race.",
  "claim_type": "attribution_claim",
  "requires_verification": true,
  "difficulty": "hard"
}
```

Claim types:

* attribution claim
* historical claim
* causal claim
* numerical claim
* biographical claim
* doctrinal claim
* legal claim
* quote claim
* prediction
* generalization
* rhetorical claim

---

### 5. Retrieval Agent

Searches for supporting evidence.

Retrieval strategy depends on claim type.

For exact quote claims:

```txt
exact phrase search
near phrase search
book search
newspaper archive search
speech archive search
```

For doctrinal claims:

```txt
speaker writings
organization publications
scholarly summaries
biographies
archival interviews
```

For historical context:

```txt
encyclopedia source
historical archive
scholarly article
primary newspaper source
```

Potential sources:

* Democracy Now transcripts
* Internet Archive
* Library of Congress
* FBI vault documents
* Pacifica Radio Archives
* civil rights digital archives
* BlackPast
* Stanford / Yale / Columbia archives
* JSTOR metadata
* Google Books snippets
* HathiTrust metadata
* Wikipedia/Wikidata as first-pass only
* newspaper archives
* official speech collections

---

### 6. Evidence Scoring Agent

Scores whether a source supports the annotation.

Evidence dimensions:

```txt
source_quality
directness
date_relevance
quote_match
entity_match
historical_consensus
contradiction_presence
```

Example output:

```json
{
  "claim_id": "claim_019",
  "evidence_status": "partially_supported",
  "confidence": 0.68,
  "reason": "The exact phrase was not found, but similar arguments about interracial mixing and integration were common in the period."
}
```

---

### 7. Annotation Writer Agent

Writes a short, readable annotation.

Rules:

* do not over-explain
* do not moralize
* do not erase ambiguity
* always separate fact from interpretation
* say when evidence is weak
* cite sources
* preserve the original speech

Annotation format:

```json
{
  "span": "Birmingham, Alabama",
  "annotation": "Birmingham was a major center of segregationist violence and civil rights protest. The city became nationally known for bombings, police repression, and confrontations over desegregation.",
  "type": "historical_context",
  "evidence_status": "supported",
  "confidence": 0.91,
  "sources": [...]
}
```

---

### 8. Contradiction / Bias Agent

Checks whether the annotation is too one-sided.

For sensitive historical material, the system should ask:

* Is this annotation importing modern judgment too aggressively?
* Is it softening the speaker’s actual views?
* Is it treating propaganda as fact?
* Is it treating hostile criticism as neutral fact?
* Is there a primary source?
* Is there scholarly disagreement?
* Is the annotation overconfident?

This agent should reduce confidence or request human review when needed.

---

### 9. Human Review Agent

Some annotations should require manual approval.

Human review triggers:

* low confidence
* no primary source
* politically sensitive claim
* religious doctrine claim
* quote attribution claim
* claim about violence
* claim about race, caste, religion, ethnicity, gender, or nation
* contradiction between sources
* model uncertainty

Review UI:

```txt
[approve] [edit] [reject] [needs more evidence]
```

---

## Data Model

### Transcript

```json
{
  "doc_id": "speech_001",
  "title": "Black Muslims vs. the Sit-ins",
  "date": "1961-04-25",
  "source_url": "...",
  "speakers": [...],
  "segments": [...]
}
```

### Segment

```json
{
  "segment_id": "seg_001",
  "speaker": "Malcolm X",
  "start_time": null,
  "end_time": null,
  "text": "..."
}
```

### Annotation

```json
{
  "annotation_id": "ann_001",
  "segment_id": "seg_001",
  "span_start": 128,
  "span_end": 167,
  "span_text": "Mr. Muhammad teaches us",
  "annotation_type": "doctrinal_context",
  "annotation_text": "...",
  "evidence_status": "supported_general_context",
  "confidence": 0.84,
  "sources": [
    {
      "title": "...",
      "url": "...",
      "source_type": "primary",
      "quote": "...",
      "relevance": "direct"
    }
  ],
  "needs_human_review": false
}
```

---

## MVP Scope

The first version should not try to annotate everything.

Build a narrow but useful MVP.

### MVP Input

* paste transcript
* paste URL
* upload `.txt`, `.md`, or `.pdf`

### MVP Output

* annotated HTML page
* side-panel annotations
* JSON export
* Markdown export

### MVP Annotation Types

Start with only five:

1. Person / organization references
2. Historical place/event context
3. Quote or paraphrase verification
4. Ideological/doctrinal context
5. Ambiguous phrase explanation

---

## MVP User Flow

```txt
1. User pastes speech URL or transcript.
2. System extracts transcript.
3. System splits into paragraphs/speaker turns.
4. System highlights candidate spans.
5. User chooses annotation depth:
   - light
   - medium
   - dense
6. Agents generate annotations.
7. Evidence scorer filters weak claims.
8. Human review UI shows uncertain annotations.
9. User exports annotated document.
```

---

## Annotation Depth

### Light

Only annotate things a general reader likely needs.

Example:

* Birmingham
* Mr. Muhammad
* Black Muslims
* sit-ins

### Medium

Annotate historical and ideological references.

Example:

* intermarriage
* integration
* self-knowledge before slavery
* Black nationalism
* nonviolence

### Dense

Annotate almost every meaningful claim.

Best for researchers.

Includes:

* source disputes
* quote verification
* rhetorical analysis
* historical timelines
* related speeches
* scholarly interpretation

---

## Tech Stack

### Backend

* Python
* FastAPI
* Pydantic
* PostgreSQL
* pgvector
* Redis
* Celery or Dramatiq
* Playwright for web extraction
* trafilatura / newspaper3k for article extraction
* PyMuPDF for PDFs

### LLM Layer

Use multiple model calls with strict roles.

Recommended:

* GPT-4.1 / GPT-4o / Claude / Gemini for annotation writing
* smaller local model for entity and span candidates
* embedding model for retrieval
* reranker for evidence matching

Open-source options:

* Qwen
* Llama
* Mistral
* BGE embeddings
* Jina embeddings
* ColBERT-style retrieval
* cross-encoder reranker

### Frontend

* Next.js
* React
* Tailwind
* shadcn/ui
* TipTap or ProseMirror
* React PDF viewer
* side-panel annotation cards
* diff view for human edits

---

## Retrieval Pipeline

```txt
For each candidate span:

1. Build search queries.
2. Search trusted sources.
3. Retrieve top documents.
4. Chunk documents.
5. Rerank chunks.
6. Extract evidence snippets.
7. Score evidence.
8. Generate annotation.
9. Verify annotation against evidence.
10. Send uncertain cases to review.
```

---

## Query Generation Examples

For:

> Mr. Muhammad teaches us that...

Generated queries:

```txt
Elijah Muhammad teaching Black man knowledge of self prior to slavery
Malcolm X Mr Muhammad knowledge of self America slavery
Nation of Islam knowledge of self black man history before slavery
Elijah Muhammad black man original people knowledge of self
```

For:

> chocolate-colored race

Generated queries:

```txt
"chocolate-colored race" intermarriage
"chocolate colored race" integration
"intermarriage" "chocolate-colored race"
"intermixing" "chocolate-colored race"
"intermarriage" "chocolate colored"
```

For:

> Birmingham will probably blow up

Generated queries:

```txt
Birmingham Alabama civil rights violence 1961
Birmingham Alabama bombings civil rights movement
Malcolm X Birmingham will blow up
Birmingham campaign racial violence early 1960s
```

---

## Evidence Status Labels

Use explicit labels.

```txt
supported
supported_general_context
partially_supported
disputed
contradicted
unclear
not_enough_evidence
needs_human_review
```

Never hide uncertainty.

Bad annotation:

> Malcolm X was referring to Martin Luther King Jr.

Good annotation:

> The exact referent is uncertain. The phrase may refer to integrationist arguments common in civil rights debates. No exact source has been found yet.

---

## UI Design

The reading interface should look like this:

```txt
Original Speech
──────────────────────────────────────

MALCOLM X:
And Mr. Muhammad teaches us that until the black man here in America is
connected or reestablished or given some knowledge of his existence prior
to coming here to America...

             ┌─────────────────────────────────────┐
             │ Annotation                          │
             │ Mr. Muhammad = Elijah Muhammad      │
             │                                     │
             │ Malcolm X is referring to the       │
             │ leader of the Nation of Islam.      │
             │ This passage reflects the Nation    │
             │ of Islam emphasis on knowledge      │
             │ of self and pre-slavery history.    │
             │                                     │
             │ Evidence: supported general context │
             │ Confidence: 0.84                    │
             └─────────────────────────────────────┘
```

Annotation card fields:

```txt
Title
Short explanation
Why this matters
Evidence status
Confidence
Sources
Alternative interpretations
Human review notes
```

---

## Example Output Markdown

```md
# Annotated Speech: Malcolm X and James Baldwin Debate

## Speaker: Malcolm X

And Mr. Muhammad teaches us[^1] that until the black man here in America is connected...

[^1]: “Mr. Muhammad” refers to Elijah Muhammad, leader of the Nation of Islam. Malcolm X is summarizing a central Nation of Islam teaching around knowledge of self, pre-slavery identity, and the psychological damage caused by white supremacy. Evidence status: supported general context.
```

---

## Evaluation

The system should be evaluated on:

### 1. Span Detection Quality

Did it highlight the passages that actually need annotation?

Metrics:

* precision
* recall
* human usefulness rating

### 2. Entity Resolution Accuracy

Did it correctly identify “Mr. Muhammad” as Elijah Muhammad?

Metrics:

* exact match
* top-k match
* disambiguation accuracy

### 3. Claim Verification Accuracy

Did it correctly mark claims as supported, unsupported, unclear, or disputed?

Metrics:

* label accuracy
* calibration
* false attribution rate

### 4. Annotation Usefulness

Human readers rate:

```txt
Was this annotation useful?
Was it too long?
Was it neutral?
Did it help you understand the speech?
Did it cite enough evidence?
```

### 5. Hallucination Rate

Most important metric.

The system should be punished heavily for:

* invented source attribution
* fake quotes
* overconfident claims
* wrong historical context
* unsupported “this refers to X” claims

---

## Gold Dataset

Create a small benchmark.

Start with 20 speeches.

Possible sources:

* Malcolm X speeches
* James Baldwin interviews
* Martin Luther King Jr. speeches
* Frederick Douglass speeches
* Ambedkar speeches
* Gandhi speeches
* Nehru speeches
* Lincoln speeches
* Churchill speeches
* anti-colonial speeches
* parliamentary debates

For each speech, manually annotate:

* 20 entity references
* 20 historical context references
* 10 quote claims
* 10 ambiguous references
* 10 ideological/doctrinal references

This gives a 1,400+ annotation benchmark.

---

## Project Milestones

### Milestone 1: Static Annotator

* paste transcript
* run candidate span detection
* generate annotations
* export Markdown

### Milestone 2: Evidence-Grounded Annotator

* web search
* source extraction
* source ranking
* evidence scoring
* confidence labels

### Milestone 3: Human Review UI

* approve/edit/reject annotations
* keep audit trail
* compare model annotation with human annotation

### Milestone 4: Public Reader

* beautiful annotated reading interface
* shareable annotated documents
* classroom mode
* export as HTML/PDF/Markdown

### Milestone 5: Benchmark + Paper

Write a paper or blog post:

> Can LLM Agents Produce Source-Grounded Historical Speech Annotations?

Evaluate against human annotators.

---

## Hard Problems

### 1. Quote Attribution Is Hard

A speaker may paraphrase, exaggerate, misremember, or create a strawman.

The system must not pretend certainty.

### 2. Historical Context Is Not Neutral by Default

Different historians may frame the same event differently.

The system should show major disagreements where necessary.

### 3. Sources Can Be Biased

Primary sources are valuable but not automatically true.

A newspaper article from 1961 may contain racist framing.

The system should distinguish source existence from source reliability.

### 4. LLMs Love Over-Explaining

Annotations should be short.

The user is reading a speech, not a textbook.

### 5. Too Many Highlights Ruin Reading

The system needs annotation density controls.

---

## Repository Structure

```txt
speechlens/
  README.md
  pyproject.toml
  .env.example

  backend/
    app/
      main.py
      config.py
      models.py

      ingestion/
        url_loader.py
        transcript_parser.py
        pdf_loader.py

      segmentation/
        segmenter.py
        span_detector.py

      agents/
        entity_agent.py
        claim_agent.py
        context_agent.py
        retrieval_agent.py
        evidence_agent.py
        annotation_writer.py
        bias_check_agent.py

      retrieval/
        search.py
        source_ranker.py
        chunker.py
        reranker.py

      annotation/
        schemas.py
        renderer.py
        markdown_export.py
        html_export.py

      evaluation/
        metrics.py
        gold_loader.py

  frontend/
    app/
      page.tsx
      speech-reader.tsx
      annotation-card.tsx
      review-panel.tsx

  data/
    examples/
      malcolm_baldwin_excerpt.txt
    gold/
      annotations.jsonl

  notebooks/
    annotation_debug.ipynb
    evidence_scoring.ipynb

  tests/
    test_entity_resolution.py
    test_claim_detection.py
    test_annotation_schema.py
```

---

## Minimal API

### POST `/annotate`

Request:

```json
{
  "text": "...",
  "mode": "medium",
  "require_sources": true
}
```

Response:

```json
{
  "doc_id": "doc_123",
  "segments": [...],
  "annotations": [...]
}
```

### POST `/annotate_url`

Request:

```json
{
  "url": "https://example.com/transcript",
  "mode": "medium",
  "require_sources": true
}
```

### GET `/document/{doc_id}`

Returns annotated document.

### PATCH `/annotation/{annotation_id}`

Human reviewer edits annotation.

---

## Minimal Prompt Contracts

### Span Detector Prompt

```txt
You are identifying parts of a historical speech that need annotation.

Return only spans that a modern reader may not understand without context.

Do not explain yet.

Return JSON with:
- span_text
- reason
- annotation_type
- priority
```

### Evidence Agent Prompt

```txt
You are checking whether retrieved sources support a proposed annotation.

Do not use outside knowledge.

Given:
- claim
- candidate annotation
- retrieved evidence

Return:
- evidence_status
- confidence
- explanation
- whether human review is needed
```

### Annotation Writer Prompt

```txt
Write a concise annotation for a reader.

Rules:
- preserve uncertainty
- do not moralize
- do not invent attribution
- separate fact from interpretation
- mention when evidence is weak
- write in 2-4 sentences
```

---

## Example CLI

```bash
speechlens annotate \
  --url "https://www.democracynow.org/2001/2/1/james_baldwin_and_malcolm_x_debate" \
  --mode medium \
  --out annotated_malcolm_baldwin.md
```

---

## Example Python Usage

```python
from speechlens import SpeechAnnotator

annotator = SpeechAnnotator(
    mode="medium",
    require_sources=True,
    human_review_threshold=0.65,
)

doc = annotator.from_url(
    "https://www.democracynow.org/2001/2/1/james_baldwin_and_malcolm_x_debate"
)

annotated = annotator.annotate(doc)

annotated.to_markdown("annotated.md")
annotated.to_html("annotated.html")
annotated.to_json("annotations.json")
```

---

## What Makes This Different From Simple RAG?

Simple RAG answers questions.

SpeechLens creates a structured annotation layer.

It must know the difference between:

```txt
“What does this sentence mean?”
“Who is being referenced?”
“Is this quote real?”
“What historical event is behind this?”
“What doctrine is being summarized?”
“Is this a rhetorical move?”
“Is this claim disputed?”
```

That makes it more like a research assistant plus editor plus fact-checker.

---

## First Build Recommendation

Do not start with every speech ever.

Start with one hard transcript:

> Malcolm X and James Baldwin debate.

Build the whole pipeline around 30–50 selected passages.

Then expand.

First target:

```txt
Input: transcript
Output: annotated Markdown with 30 source-backed annotations
```

That is enough for a serious demo.

---

## Future Extensions

* audio-aligned annotations
* timeline view
* map view
* debate argument graph
* speaker ideology comparison
* “before reading” primer
* classroom worksheet generator
* contradiction explorer
* source reliability visualization
* annotation diff between model versions
* multilingual speeches
* Indian parliamentary speech annotations
* Ambedkar/Gandhi/Nehru speech annotation corpus

---

## Research Angle

Possible research question:

> Can agentic systems generate historically useful, source-grounded annotations for speeches without hallucinating attribution?

Possible paper/blog title:

> SpeechLens: Source-Grounded Agentic Annotation of Historical Speeches

Core contribution:

* annotation taxonomy
* evidence-grounded workflow
* human review loop
* benchmark of historical speech annotations
* hallucination/error analysis

---

## Why This Is Worth Building

This is not a toy chatbot.

It sits at the intersection of:

* NLP
* retrieval
* digital humanities
* education
* fact-checking
* historical research
* annotation interfaces
* explainable reading tools

A good version could be useful for:

* students
* teachers
* journalists
* researchers
* documentary makers
* debate readers
* political speech archives
* public history projects

The key principle:

> Do not make the model sound smart. Make the speech easier to understand, and make every annotation accountable to evidence.
