# UI/UX Design Specification & Guidelines

# The Lenny Growth Assistant
**Author**: Riju Pradhanang  
**Document Version**: 2.0  
**Status**: Production Ready  

---

## 1. Design Principles & Aesthetic Philosophy

The Lenny Growth Assistant is designed around three core product principles:
1. **Uncompromising Trust & Grounding**: Every answer must wear its citations proudly. The user must never wonder if an idea was fabricated; source attribution is an interactive first-class citizen.
2. **Context-Preserving Workflow**: Users should move seamlessly from asking quick questions to generating 1,250-word essays and interactive HTML artifacts without switching tabs or losing session context.
3. **Modern, Polished Aesthetics**: The interface utilizes a sleek dark-mode palette, subtle glassmorphic card borders, responsive typography, and micro-animations to deliver a delightful, state-of-the-art developer experience.

---

## 2. Information Architecture & Layout

The UI layout is divided into three primary functional columns:

```
+---------------------------------------------------------------------------------------------------------+
|                                    HEADER & PROVIDER STATUS BADGE                                       |
+--------------------+---------------------------------------------------+--------------------------------+
|  SESSION SIDEBAR   |               CHAT & STREAMING PANEL              |         ARTIFACT VIEWER        |
|                    |                                                   |                                |
|  [+ New Session]   |  [Message History]                                |  [Rendered] [Raw Code] [Export]|
|                    |  User: How do we fix activation funnels?          |  +--------------------------+  |
|  - Growth Metrics  |                                                   |  | Sandboxed Preview Iframe |  |
|  - B2B Pricing     |  Assistant (Ollama - qwen2.5:7b):                 |  |                          |  |
|  - PMF Discovery   |  Based on Elena Verna's interview [1], activation |  | [Live HTML/CSS or MD]    |  |
|                    |  requires 3 core moments: setup, aha, and habit.  |  |                          |  |
|                    |                                                   |  +--------------------------+  |
|                    |  Citations: [Elena Verna - Activation]            |  Security: Sandboxed iframe    |
|                    |                                                   |  (no scripts allowed)          |
|                    |  +---------------------------------------------+  |                                |
|                    |  | Ask a question or request an essay...       |  |                                |
|                    |  +---------------------------------------------+  |                                |
|                    |  [Send] [Generate HTML] [Generate Markdown]       |                                |
+--------------------+---------------------------------------------------+--------------------------------+
```

### 2.1 Session Sidebar
- **Purpose**: Manage independent chat sessions with persistent conversation history.
- **Controls**: **+ New Session** button, session search, session items with active indicators and last-active timestamps, and single-click delete confirmation.

### 2.2 Chat & Streaming Panel
- **Purpose**: Real-time conversational interface with token streaming and instant intent feedback.
- **Components**:
  - **Message Bubbles**: Clean distinctions between user and assistant turns.
  - **Provider Badge**: Identifies the model provider (`ollama` or `anthropic`) and model name (`qwen2.5:7b`, `claude-sonnet-4-5`) used for each response.
  - **Citation Chips & Modal**: Expandable badges linking to the podcast episode title, guest name, and source URL.
  - **Essay Structural Compliance Badge**: Displays real-time pass/fail indicators for word count, headings, bullets, and takeaway elements.

### 2.3 Artifact Viewer (Side-by-Side Panel)
- **Purpose**: Render generated Markdown documents and modern HTML/CSS card snippets without leaving the chat.
- **Features**:
  - **View Toggle**: Switch between **Rendered Preview** and **Raw Code** tabs.
  - **Sandboxed Iframe**: Isolates untrusted HTML/CSS inside `sandbox="allow-same-origin"`.
  - **Download Button**: Exports `.md` or `.html` directly to the user's filesystem.
  - **Security Banner**: Explains security constraints (stripping scripts and inline event handlers).

---

## 3. Interaction States & Transitions

### 3.1 Streaming & Loading State
- While waiting for the first token, a pulsing status badge reads `Retrieving sources...` followed by `Generating response...`.
- Tokens are streamed directly via SSE, auto-scrolling the conversation container smoothly.

### 3.2 Error & Degradation State
- In the event of an unreachable Ollama instance or missing API key, the chat panel renders an inline warning card with specific remediation steps (e.g. *"Run `ollama pull qwen2.5:7b`"* or *"Configure `ANTHROPIC_API_KEY`"*).
- When an out-of-corpus query is submitted, the assistant responds with a polite abstention banner rather than failing.

### 3.3 Artifact Generation State
- Triggering an artifact request opens the right panel with a slide-in animation.
- A loading skeleton animates while the backend synthesizes and sanitizes the content.

---

## 4. Accessibility & WCAG 2.1 AA Compliance

- **Color Contrast**: Background (`#0f172a`), surface cards (`#1e293b`), and text (`#f8fafc`) maintain a contrast ratio exceeding 7:1 (well above the 4.5:1 AA requirement).
- **Keyboard Navigation**: Full `Tab` order supported across all buttons, input fields, and tab toggles.
- **Screen Reader Support**: Semantic HTML tags (`<header>`, `<nav>`, `<main>`, `<article>`, `<button>`) with descriptive `aria-label` attributes.
- **Focus Management**: Explicit visible focus rings (`ring-2 ring-indigo-500`) on all interactive controls.

---

## 5. Design Decisions & Trade-Offs

| Decision | Rationale | Alternative Considered & Rejected |
|---|---|---|
| **Side-by-Side Artifact Viewer** | Enables users to inspect and copy generated artifacts while maintaining conversational context. | Modal dialog (obstructs chat history) or separate page (loses session continuity). |
| **Sandboxed Iframe Rendering** | Guarantees complete CSS and JavaScript isolation, preventing model-generated code from compromising the host app. | Direct `dangerouslySetInnerHTML` (severe XSS vulnerability). |
| **Inline Citation Chips** | Gives users immediate verification of sources with one-click access to source transcripts and URLs. | Raw URL links at the end of the text (clutters prose and hard to trace). |
| **Dark Mode by Default** | Optimized for developer and operator workflows in high-focus environments. | Generic unstyled light theme. |
