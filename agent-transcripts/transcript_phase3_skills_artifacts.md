# Agent Transcript: Phase 3 – Skills & Artifacts

**Session Date**: 2026-09-14 (Afternoon – Evening)  
**Focus**: Intent Classification Router, Ship 30 for 30 Content Skill (~1,250 words) with Structural Validator, Artifact Generation (Markdown & HTML/CSS), Sandboxed Artifact Viewer UI.  

---

## 1. Objectives & Context
- Build `classify_intent` router to distinguish `grounded_qa`, `essay`, and `artifact` requests.
- Implement the Ship 30 for 30 writing framework (strong hook, punchy 1-2 sentence paragraphs, skimmable headings and bullets, bold emphasis, single core takeaway, ~1,250 words target) with an automated post-generation structural validator.
- Implement `/sessions/{id}/artifacts` endpoint for generating versioned Markdown and HTML/CSS artifacts.
- Implement server-side allowlist sanitizer (`sanitizer.py`) and frontend sandboxed `<iframe>` viewer.

---

## 2. Failed Attempts & Corrections

### Issue 1: Iframe Script Execution in Artifact Viewer
- **Failed Attempt**: Initial HTML artifact preview used `<div dangerouslySetInnerHTML={{ __html: content }} />` which exposed the main app window to malicious `<script>` or `onerror` XSS payloads.
- **Root Cause**: Direct DOM injection does not provide origin or DOM isolation.
- **Correction**: Replaced direct DOM rendering with a two-tier defense: (1) server-side HTML allowlist parsing with `html.parser` to strip scripts, event handlers, and dangerous tags; (2) client-side `<iframe>` rendering with `sandbox="allow-same-origin"` explicitly omitting `allow-scripts`.

### Issue 2: Local Model Essay Length & Heading Formatting
- **Failed Attempt**: Smaller local models (e.g. 7B/8B) occasionally generated essays under 600 words when prompted without explicit structural milestones.
- **Root Cause**: Generic "write a 1,250-word essay" prompts are often truncated by small models without explicit step-by-step section blueprints.
- **Correction**: Re-engineered `build_essay_system_prompt()` to specify exact section-by-section breakdown (Hook: 100 words, Core Problem: 250 words, 3 Tactical Frameworks: 600 words, Common Pitfalls: 200 words, Single Takeaway: 100 words) and added `validate_essay_structure()` to evaluate headings, bullets, bolding, and word count.

---

## 3. Verification & Deliverables
- Automated tests passing for router, essay validator, HTML sanitizer, and artifact endpoints.
- Artifact Viewer successfully renders both Markdown and sandboxed HTML widgets beside the chat.
