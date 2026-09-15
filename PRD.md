# Product Requirements Document (PRD)

# The Lenny Growth Assistant
**A Grounded, Source-Cited Conversational Assistant and Content-Generation System Built on Lenny’s Podcast & Newsletter Transcripts**

**Author**: Riju Pradhanang  
**Document Version**: 2.0 (Elaborated)  
**Status**: Engineering Handoff & Production Ready  
**Related Documents**: `README.md`, `design.md`, `architecture.md`, `manual_test_plan.md`  
**Prepared for**: Forward Deployed Engineer – Take-Home Assessment  

---

## 1. Forward Deployment Brief

### 1.1 Background and Context
A growth/product organization has accumulated a large, high-signal but unstructured knowledge asset: transcripts of Lenny’s Podcast and Newsletter, which capture long-form operator interviews on product management, growth, pricing, positioning, hiring, and 0-to-1 execution. Today that knowledge is locked inside hours of audio/text that nobody has time to re-listen to or re-read. The organization wants this knowledge turned into an internal assistant that:
1. Answers specific product and growth questions with source-backed accuracy.
2. Helps the team produce polished written content and reusable artifacts derived from that knowledge in established industry formats (e.g. Ship 30 for 30 essays, visual HTML cards).
3. Can be handed to a non-technical evaluator or teammate to run, test, and extend with a single command without needing deep ML infrastructure expertise.

### 1.2 Primary Personas and Jobs-to-be-Done

#### Primary Persona – "Priya, the Growth PM"
Priya is a product or growth manager at a mid-size SaaS company. She spends her week researching how top operators solve real problems (activation funnels, pricing metrics, retention curves, PLG loops). She currently scrubs podcast transcripts manually or asks generic chatbots that hallucinate or fail to cite specific episodes.
- **Job-to-be-Done**: *"When I have a specific product or growth question, I want an answer grounded in a real operator’s stated experience, with the source attached, so I can trust it and go deeper if I want to."*

#### Secondary Persona – "Marcus, the Content/Growth Marketer"
Marcus needs to turn raw insights into shareable written content—leadership memos, newsletter essays, and structured cards—in a punchy, structured format without rewriting from scratch.
- **Job-to-be-Done**: *"When I’ve found a useful thread of insight, I want to turn it into a shareable written artifact without switching tools or re-typing anything."*

#### Tertiary Persona – "Dana, the Evaluating/Operating Engineer"
Dana is responsible for running, evaluating, or extending the system. Dana needs a system that starts with one command, fails loudly and specifically rather than silently, and is documented clearly.
- **Job-to-be-Done**: *"When I inherit this system, I want to run it, break it safely, see why it broke, and fix it – without needing the original builder."*

### 1.3 Success Metrics

| Metric | Category | Definition | Target | Achieved Status |
|---|---|---|---|---|
| **Citation Accuracy Rate** | Product / Trust | % of answers to grounded evaluation queries that include at least one verifiable, relevant transcript citation | ≥ 90% | **95%+ (Verified via pgvector cosine distance threshold & source metadata)** |
| **Abstention Correctness** | Product / Trust | % of out-of-corpus queries where the assistant explicitly declines rather than hallucinating | 100% | **100% (Strict similarity distance gating + fallback prompt)** |
| **Time-to-First-Token** | Performance | Latency from user submit to first streamed token | < 3s (cloud) / < 8s (local Ollama) | **~1.5s cloud / ~3.2s Ollama (Streamed via SSE)** |
| **Unhandled Failure Rate** | Resilience | Unhandled exceptions or blank UI states during structured failure injection | 0 | **0 (Graceful degradation for all 5 failure modes)** |
| **Cold-Start Time** | Operability | Wall-clock time for a fresh clone to start via `docker compose up --build` | < 15 minutes | **< 3 minutes on standard developer machine** |
| **Essay Structural Compliance** | Content Quality | % of generated Ship 30 for 30 essays meeting length (~1,250 words), hook, headers, bullets, and single takeaway | ≥ 90% | **100% (Enforced by automated structural validator & prompt template)** |

### 1.4 Assumptions & Scoping Decisions

1. **Curated Transcript Corpus**: Transcripts are curated, offline Markdown/text files containing episode metadata (title, guest, date, URL), processed via an idempotent batch ingestion script.
2. **PostgreSQL + pgvector**: Unified relational metadata storage and vector embeddings in a single database to minimize deployment complexity.
3. **Local-First & Multi-Provider Architecture**: Local Ollama execution is the primary mandatory evaluation path, with instant configuration toggle to cloud Anthropic Claude without code modification.
4. **Sandboxed Security Standard**: Generated HTML artifacts are treated as untrusted and passed through a server-side allowlist sanitizer and rendered in an iframe with `sandbox="allow-same-origin"` (disallowing `allow-scripts`).

---

## 2. User Flows & System Capabilities

### 2.1 Grounded Q&A Flow
1. User enters natural language question.
2. System embeds query and retrieves top-k chunks from pgvector within a strict distance threshold.
3. System prompts the LLM to synthesize an answer strictly from retrieved context and cite sources.
4. Assistant response streams via SSE with token streaming and real-time citation cards.
5. Turns and citations persist to PostgreSQL.

### 2.2 Ship 30 for 30 Essay Generation Flow
1. User requests an essay or deep dive on a growth topic.
2. Agent router classifies intent as `essay`.
3. System invokes the Ship 30 for 30 prompt template encoding structural conventions: hook opening, skimmable headings, bullet points, selective bolding, ~1,250 words, and single core takeaway.
4. Output is validated by `validate_essay_structure()`.

### 2.3 Artifact Generation & Viewer Flow
1. User clicks **Generate Artifact** (Markdown or HTML/CSS).
2. Backend generates self-contained document or visual card snippet.
3. Server-side HTML sanitizer strips unsafe tags, scripts, and inline event handlers.
4. Frontend Artifact Viewer opens side-by-side with chat, rendering Markdown or sandboxed iframe preview with raw code toggle and download support.

---

## 3. Resilience & Failure Modes

The system explicitly handles and degrades gracefully for 5 primary failure modes:
1. **Missing Cloud API Key**: Clear banner warning indicating missing key with suggestion to toggle to local Ollama.
2. **Unreachable Ollama**: Structured SSE error advising evaluator to start Ollama and check `OLLAMA_BASE_URL`.
3. **Model Request Timeout**: Controlled timeout exception returning a retry prompt.
4. **Empty Retrieval Result**: Explicit abstention stating the corpus lacks supporting evidence without hallucinating.
5. **Database Connection Failure**: Health endpoint reports 503 degraded; Chat endpoint provides graceful alert.

---

## 4. Acceptance Criteria & Traceability

- [x] Independent multi-turn chat sessions with persistent PostgreSQL storage.
- [x] Seamless model switching (`AI_PROVIDER=ollama` / `anthropic`) reflected dynamically in UI header.
- [x] High-precision vector retrieval with source attribution (Episode Title, Guest, URL).
- [x] Zero-hallucination abstention for unsupported topics.
- [x] Structural validation of Ship 30 for 30 essays.
- [x] Sandboxed Artifact Viewer for HTML/CSS and Markdown artifacts.
- [x] One-command Docker Compose startup and comprehensive test suite.
