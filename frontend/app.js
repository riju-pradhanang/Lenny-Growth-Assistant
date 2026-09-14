// Lenny Growth Assistant Frontend Application

const API_BASE = window.location.port === "5173" && window.location.hostname === "localhost" 
  ? "http://localhost:8000" 
  : "";

let currentSessionId = null;
let currentArtifact = null;
let isArtifactRaw = false;
let sessionsList = [];

// DOM Elements
const sessionListEl = document.getElementById("session-list");
const messagesContainerEl = document.getElementById("messages-container");
const chatFormEl = document.getElementById("chat-form");
const chatInputEl = document.getElementById("chat-input");
const btnSendEl = document.getElementById("btn-send");
const btnNewChatEl = document.getElementById("btn-new-chat");
const providerBadgeEl = document.getElementById("provider-badge");
const healthBadgeEl = document.getElementById("health-badge");
const artifactPanelEl = document.getElementById("artifact-panel");
const artifactContentEl = document.getElementById("artifact-content");
const artifactTitleEl = document.getElementById("artifact-title");
const artifactTypeTagEl = document.getElementById("artifact-type-tag");
const btnToggleRawEl = document.getElementById("btn-toggle-raw");
const btnDownloadArtifactEl = document.getElementById("btn-download-artifact");
const btnCloseArtifactEl = document.getElementById("btn-close-artifact");

// Initialize application
document.addEventListener("DOMContentLoaded", () => {
  fetchConfig();
  fetchHealth();
  loadSessions();
  setupEventListeners();
});

function setupEventListeners() {
  btnNewChatEl.addEventListener("click", () => createNewSession());
  
  chatFormEl.addEventListener("submit", (e) => {
    e.preventDefault();
    handleSendMessage();
  });

  chatInputEl.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });

  btnToggleRawEl.addEventListener("click", () => {
    isArtifactRaw = !isArtifactRaw;
    btnToggleRawEl.textContent = isArtifactRaw ? "Rendered View" : "Raw Source";
    renderArtifactView();
  });

  btnDownloadArtifactEl.addEventListener("click", () => {
    if (!currentArtifact) return;
    const ext = currentArtifact.type === "html" ? "html" : "md";
    const filename = `lenny-artifact-${currentArtifact.id.substring(0, 8)}.${ext}`;
    const blob = new Blob([currentArtifact.content], { type: currentArtifact.type === "html" ? "text/html" : "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  });

  btnCloseArtifactEl.addEventListener("click", () => {
    artifactPanelEl.classList.add("hidden");
    currentArtifact = null;
  });
}

async function fetchConfig() {
  try {
    const res = await fetch(`${API_BASE}/config`);
    if (res.ok) {
      const data = await res.json();
      providerBadgeEl.innerHTML = `Provider: <strong>${data.provider.toUpperCase()}</strong> (${data.model})`;
    }
  } catch (err) {
    providerBadgeEl.textContent = "Provider: Standalone";
  }
}

async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (res.ok) {
      healthBadgeEl.innerHTML = '<span class="status-dot"></span> System Connected';
      healthBadgeEl.classList.remove("offline");
    } else {
      healthBadgeEl.innerHTML = '<span class="status-dot"></span> Degraded';
      healthBadgeEl.classList.add("offline");
    }
  } catch (err) {
    healthBadgeEl.innerHTML = '<span class="status-dot"></span> Offline';
    healthBadgeEl.classList.add("offline");
  }
}

async function loadSessions() {
  try {
    const res = await fetch(`${API_BASE}/sessions`);
    if (res.ok) {
      sessionsList = await res.json();
      renderSessionsList();
      if (sessionsList.length > 0 && !currentSessionId) {
        selectSession(sessionsList[0].id);
      } else if (sessionsList.length === 0) {
        createNewSession("Lenny Growth Chat");
      }
    }
  } catch (err) {
    console.error("Failed to load sessions", err);
  }
}

function renderSessionsList() {
  sessionListEl.innerHTML = "";
  sessionsList.forEach((session) => {
    const li = document.createElement("li");
    li.className = `session-item ${session.id === currentSessionId ? "active" : ""}`;
    li.innerHTML = `
      <span class="session-title" title="${escapeHtml(session.label)}">${escapeHtml(session.label)}</span>
      <button class="btn-delete-session" title="Delete chat" onclick="event.stopPropagation(); deleteSession('${session.id}')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
      </button>
    `;
    li.onclick = () => selectSession(session.id);
    sessionListEl.appendChild(li);
  });
}

async function createNewSession(customLabel) {
  try {
    const label = customLabel || `Conversation #${sessionsList.length + 1}`;
    const res = await fetch(`${API_BASE}/sessions`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ label }),
    });
    if (res.ok) {
      const session = await res.json();
      sessionsList.unshift(session);
      selectSession(session.id);
    }
  } catch (err) {
    console.error("Error creating session", err);
  }
}

async function selectSession(sessionId) {
  currentSessionId = sessionId;
  renderSessionsList();
  await loadMessages(sessionId);
}

async function deleteSession(sessionId) {
  if (!confirm("Are you sure you want to delete this session?")) return;
  try {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}`, { method: "DELETE" });
    if (res.ok) {
      sessionsList = sessionsList.filter((s) => s.id !== sessionId);
      if (currentSessionId === sessionId) {
        currentSessionId = sessionsList[0]?.id || null;
        if (currentSessionId) {
          selectSession(currentSessionId);
        } else {
          createNewSession();
        }
      } else {
        renderSessionsList();
      }
    }
  } catch (err) {
    console.error("Error deleting session", err);
  }
}

async function loadMessages(sessionId) {
  try {
    const res = await fetch(`${API_BASE}/sessions/${sessionId}/messages`);
    if (res.ok) {
      const messages = await res.json();
      renderMessages(messages);
    }
  } catch (err) {
    console.error("Error loading messages", err);
  }
}

function renderMessages(messages) {
  messagesContainerEl.innerHTML = "";
  if (messages.length === 0) {
    messagesContainerEl.innerHTML = `
      <div class="welcome-screen">
        <h2 class="welcome-title">Lenny's Growth Knowledge Assistant</h2>
        <p class="welcome-desc">Ask grounded product & growth questions, generate Ship 30 for 30 essays, or create self-contained artifacts directly from Lenny's transcript library.</p>
        <div class="starters-grid">
          <div class="starter-card" onclick="sendStarter('How does Figma approach product-led growth and freemium adoption?')">
            <div class="starter-badge">Grounded Q&A</div>
            <div class="starter-text">How does Figma approach product-led growth and freemium adoption?</div>
          </div>
          <div class="starter-card" onclick="sendStarter('What is Shreyas Doshi\'s LNO framework for PM prioritization?')">
            <div class="starter-badge">Grounded Q&A</div>
            <div class="starter-text">What is Shreyas Doshi's LNO framework for PM prioritization?</div>
          </div>
          <div class="starter-card" onclick="sendStarter('Write a Ship 30 for 30 essay on finding product-market fit based on the transcripts.')">
            <div class="starter-badge">Ship 30 for 30</div>
            <div class="starter-text">Write a Ship 30 for 30 essay on finding product-market fit based on the transcripts.</div>
          </div>
          <div class="starter-card" onclick="sendStarter('Generate an HTML snippet card artifact summarizing key activation funnel levers.')">
            <div class="starter-badge">Artifact</div>
            <div class="starter-text">Generate an HTML snippet card artifact summarizing key activation funnel levers.</div>
          </div>
        </div>
      </div>
    `;
    return;
  }

  messages.forEach((msg) => appendMessageNode(msg));
  messagesContainerEl.scrollTop = messagesContainerEl.scrollHeight;
}

window.sendStarter = function(promptText) {
  chatInputEl.value = promptText;
  handleSendMessage();
};

function appendMessageNode(msg) {
  const row = document.createElement("div");
  row.className = `message-row ${msg.role}`;
  row.id = `msg-${msg.id || Date.now()}`;

  const avatar = document.createElement("div");
  avatar.className = `avatar ${msg.role}`;
  avatar.textContent = msg.role === "user" ? "You" : "LG";

  const bubble = document.createElement("div");
  bubble.className = "message-bubble";

  let bodyContent = escapeHtml(msg.content).replace(/\n/g, "<br/>");
  if (msg.role === "assistant") {
    bodyContent = formatAssistantText(msg.content);
  }

  bubble.innerHTML = bodyContent;

  if (msg.role === "assistant" && msg.citations && msg.citations.length > 0) {
    const citationsHtml = `
      <div class="citations-wrapper">
        <div class="citations-header">Sources & Citations</div>
        <div style="display: flex; flex-wrap: wrap; gap: 6px;">
          ${msg.citations.map(c => `
            <a class="citation-chip" href="${escapeHtml(c.source_url)}" target="_blank" rel="noopener noreferrer">
              📚 ${escapeHtml(c.episode_title)} ${c.guest_name ? `(${escapeHtml(c.guest_name)})` : ''}
            </a>
          `).join('')}
        </div>
      </div>
    `;
    bubble.innerHTML += citationsHtml;
  }

  if (msg.role === "assistant") {
    const actionsHtml = `
      <div class="message-actions">
        <button class="btn-action-pill" onclick="generateArtifactForMessage('${msg.id}', 'markdown')">
          📄 Generate MD Artifact
        </button>
        <button class="btn-action-pill" onclick="generateArtifactForMessage('${msg.id}', 'html')">
          🎨 Generate HTML Artifact
        </button>
        <button class="btn-action-pill" onclick="copyMessageText(this)">
          📋 Copy
        </button>
      </div>
    `;
    bubble.innerHTML += actionsHtml;
  }

  row.appendChild(avatar);
  row.appendChild(bubble);
  messagesContainerEl.appendChild(row);
  messagesContainerEl.scrollTop = messagesContainerEl.scrollHeight;
  return row;
}

async function handleSendMessage() {
  const text = chatInputEl.value.trim();
  if (!text || !currentSessionId) return;

  chatInputEl.value = "";
  btnSendEl.disabled = true;

  // Render User Message
  appendMessageNode({ role: "user", content: text });

  // Placeholder for streaming assistant message
  const assistantRow = document.createElement("div");
  assistantRow.className = "message-row assistant";
  const avatar = document.createElement("div");
  avatar.className = "avatar assistant";
  avatar.textContent = "LG";
  const bubble = document.createElement("div");
  bubble.className = "message-bubble";
  bubble.innerHTML = '<span class="status-dot"></span> Thinking & retrieving transcript sources...';
  assistantRow.appendChild(avatar);
  assistantRow.appendChild(bubble);
  messagesContainerEl.appendChild(assistantRow);
  messagesContainerEl.scrollTop = messagesContainerEl.scrollHeight;

  try {
    const response = await fetch(`${API_BASE}/sessions/${currentSessionId}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: text }),
    });

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let assistantText = "";
    let citations = [];
    let validation = null;
    let intent = "grounded_qa";
    let messageId = null;

    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop(); // keep last incomplete line

      let currentEvent = null;

      for (const line of lines) {
        if (line.startsWith("event: ")) {
          currentEvent = line.replace("event: ", "").trim();
        } else if (line.startsWith("data: ")) {
          const rawData = line.replace("data: ", "").trim();
          try {
            const parsed = JSON.parse(rawData);
            if (currentEvent === "intent") {
              intent = parsed.intent;
            } else if (currentEvent === "token") {
              assistantText += parsed.text;
              updateAssistantLiveView(bubble, assistantText, intent, validation, citations);
            } else if (currentEvent === "citations") {
              citations = parsed.items || [];
              updateAssistantLiveView(bubble, assistantText, intent, validation, citations);
            } else if (currentEvent === "validation") {
              validation = parsed;
              updateAssistantLiveView(bubble, assistantText, intent, validation, citations);
            } else if (currentEvent === "done") {
              messageId = parsed.message_id;
              if (parsed.validation) validation = parsed.validation;
            }
          } catch (e) {
            console.error("SSE parse error", e);
          }
        }
      }
    }

    // Finalize view with action buttons
    finalizeAssistantView(bubble, assistantText, intent, validation, citations, messageId);

  } catch (err) {
    bubble.innerHTML = `<span style="color: var(--accent-rose);">Error connecting to assistant: ${err.message}</span>`;
  } finally {
    btnSendEl.disabled = false;
  }
}

function updateAssistantLiveView(bubble, text, intent, validation, citations) {
  let badgeHtml = "";
  if (intent === "essay") {
    badgeHtml = '<div class="intent-badge essay">✍️ Ship 30 for 30 Essay</div>';
  } else if (intent === "artifact") {
    badgeHtml = '<div class="intent-badge artifact">📦 Artifact Request</div>';
  } else {
    badgeHtml = '<div class="intent-badge grounded_qa">🎯 Grounded Q&A</div>';
  }

  let formatted = formatAssistantText(text);
  bubble.innerHTML = badgeHtml + formatted;

  if (citations && citations.length > 0) {
    bubble.innerHTML += `
      <div class="citations-wrapper">
        <div class="citations-header">Sources & Citations</div>
        <div style="display: flex; flex-wrap: wrap; gap: 6px;">
          ${citations.map(c => `
            <a class="citation-chip" href="${escapeHtml(c.source_url)}" target="_blank" rel="noopener noreferrer">
              📚 ${escapeHtml(c.episode_title)} ${c.guest_name ? `(${escapeHtml(c.guest_name)})` : ''}
            </a>
          `).join('')}
        </div>
      </div>
    `;
  }

  messagesContainerEl.scrollTop = messagesContainerEl.scrollHeight;
}

function finalizeAssistantView(bubble, text, intent, validation, citations, messageId) {
  updateAssistantLiveView(bubble, text, intent, validation, citations);

  if (validation) {
    const valHtml = `
      <div class="structural-checkcard">
        <div class="checkcard-title">
          <span>📐 Ship 30 for 30 Structure Check</span>
          <span style="font-size: 11px; color: ${validation.is_valid ? 'var(--accent-emerald)' : 'var(--accent-amber)'};">
            ${validation.word_count} words ${validation.is_valid ? '• Compliant ✅' : '• Evaluated ⚠️'}
          </span>
        </div>
        <div class="checkcard-grid">
          <div>${validation.has_headings ? '✅' : '❌'} Headings</div>
          <div>${validation.has_bullets ? '✅' : '❌'} Bullets</div>
          <div>${validation.has_bold ? '✅' : '❌'} Bold Focus</div>
          <div>${validation.has_takeaway ? '✅' : '❌'} Takeaway</div>
          <div>${validation.word_count >= 1050 && validation.word_count <= 1450 ? '✅' : '⚠️'} Word Count</div>
        </div>
      </div>
    `;
    bubble.innerHTML += valHtml;
  }

  const actionsHtml = `
    <div class="message-actions">
      <button class="btn-action-pill" onclick="generateArtifactForMessage('${messageId}', 'markdown')">
        📄 Generate MD Artifact
      </button>
      <button class="btn-action-pill" onclick="generateArtifactForMessage('${messageId}', 'html')">
        🎨 Generate HTML Artifact
      </button>
      <button class="btn-action-pill" onclick="copyMessageText(this)">
        📋 Copy
      </button>
    </div>
  `;
  bubble.innerHTML += actionsHtml;
  messagesContainerEl.scrollTop = messagesContainerEl.scrollHeight;
}

window.generateArtifactForMessage = async function(messageId, type) {
  if (!currentSessionId) return;
  try {
    const res = await fetch(`${API_BASE}/sessions/${currentSessionId}/artifacts`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type, message_id: messageId }),
    });
    if (res.ok) {
      currentArtifact = await res.json();
      openArtifactViewer(currentArtifact);
    }
  } catch (err) {
    alert("Failed to generate artifact: " + err.message);
  }
};

function openArtifactViewer(artifact) {
  currentArtifact = artifact;
  isArtifactRaw = false;
  btnToggleRawEl.textContent = "Raw Source";
  artifactTitleEl.textContent = `Artifact v${artifact.version} (${artifact.id.substring(0, 8)})`;
  artifactTypeTagEl.textContent = artifact.type.toUpperCase();
  artifactPanelEl.classList.remove("hidden");
  renderArtifactView();
}

function renderArtifactView() {
  if (!currentArtifact) return;

  if (isArtifactRaw) {
    artifactContentEl.innerHTML = `<pre class="raw-content-view">${escapeHtml(currentArtifact.content)}</pre>`;
    return;
  }

  if (currentArtifact.type === "html") {
    artifactContentEl.innerHTML = `
      <iframe class="artifact-iframe" sandbox="allow-same-origin" srcdoc="${escapeHtml(currentArtifact.content)}"></iframe>
    `;
  } else {
    // Markdown rendering
    artifactContentEl.innerHTML = `
      <div class="markdown-rendered">${formatAssistantText(currentArtifact.content)}</div>
    `;
  }
}

window.copyMessageText = function(btn) {
  const bubble = btn.closest(".message-bubble");
  const clone = bubble.cloneNode(true);
  const actions = clone.querySelector(".message-actions");
  if (actions) actions.remove();
  const checks = clone.querySelector(".structural-checkcard");
  if (checks) checks.remove();
  const citations = clone.querySelector(".citations-wrapper");
  if (citations) citations.remove();
  
  navigator.clipboard.writeText(clone.innerText.trim()).then(() => {
    const prev = btn.textContent;
    btn.textContent = "Copied! ✓";
    setTimeout(() => { btn.textContent = prev; }, 1500);
  });
};

function formatAssistantText(text) {
  if (!text) return "";
  let html = escapeHtml(text);
  
  // Format headings ##
  html = html.replace(/^### (.*$)/gim, '<h4 style="margin: 12px 0 6px; font-weight: 600; color: var(--text-primary);">$1</h4>');
  html = html.replace(/^## (.*$)/gim, '<h3 style="margin: 16px 0 8px; font-weight: 700; color: var(--text-primary);">$1</h3>');
  html = html.replace(/^# (.*$)/gim, '<h2 style="margin: 20px 0 10px; font-weight: 700; color: var(--text-primary);">$1</h2>');
  
  // Format bold
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  
  // Format bullet items
  html = html.replace(/^\- (.*$)/gim, '<li style="margin-left: 18px;">$1</li>');
  html = html.replace(/^\* (.*$)/gim, '<li style="margin-left: 18px;">$1</li>');

  // Wrap newlines
  html = html.replace(/\n\n/g, '<p style="margin-bottom: 12px;"></p>');
  html = html.replace(/\n/g, '<br/>');

  return html;
}

function escapeHtml(str) {
  if (!str) return "";
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
