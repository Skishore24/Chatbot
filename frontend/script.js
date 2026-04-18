// ── Session Management ────────────────────────────────────────────────────────
let sessionId = localStorage.getItem("genkit_session") || null;

// ── DOM Ready ─────────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  renderWelcome();
  addSuggestions();
  autoGrowTextarea();
});

// ── Toggle Chat ───────────────────────────────────────────────────────────────
function toggleChat() {
  const chatBox = document.getElementById("chatBox");
  const icon = document.getElementById("toggleIcon");
  const isOpen = chatBox.classList.toggle("active");
  icon.textContent = isOpen ? "close" : "chat";
  if (isOpen) setTimeout(() => document.getElementById("input").focus(), 300);
}

// ── Welcome Message ───────────────────────────────────────────────────────────
function renderWelcome() {
  const welcomeText = "👋 Hi! I'm the **Genkit AI Assistant**.\n\nAsk me anything about our services, portfolio, or how we can help your business!";
  const bubble = appendBotMessage("");
  typeWriter(welcomeText, bubble);
}

function typeWriter(text, element, speed = 15) {
  let i = 0;
  element.innerHTML = "";

  function type() {
    if (i < text.length) {
      element.innerText = text.substring(0, i + 1);
      i++;
      setTimeout(type, speed);
    } else {
      element.innerHTML = renderMarkdown(text);
      scrollToBottom();
    }
  }
  type();
}

// ── Suggestions ───────────────────────────────────────────────────────────────
function addSuggestions() {
  const msgBox = document.getElementById("messages");

  const row = document.createElement("div");
  row.className = "suggestions";

  ["What is Genkit?", "What Tools Used", "Services", "Contact"].forEach(text => {
    const btn = document.createElement("button");
    btn.className = "suggestion-btn";
    btn.innerText = text;

    btn.onclick = () => {
      document.getElementById("input").value = text;
      sendMessage();
    };

    row.appendChild(btn);
  });

  msgBox.appendChild(row);
  setTimeout(scrollToBottom, 100);
}

// ── Send Message (FIXED) ─────────────────────────────────────────────────────
async function sendMessage() {
  const input = document.getElementById("input");
  const text = input.value.trim();
  if (!text) return;

  setInputState(true);
  appendUserMessage(text);
  input.value = "";

  const typingIndicator = appendTypingIndicator();

  try {
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ q: text, session_id: sessionId || undefined })
    });

    if (!res.ok) throw new Error("Server error");

    const newSessionId = res.headers.get("X-Session-Id");
    if (newSessionId) {
      sessionId = newSessionId;
      localStorage.setItem("genkit_session", sessionId);
    }

    // ✅ FIX: ONLY use res.text()
    const responseText = await res.text();

    typingIndicator.remove();
    const bubble = appendBotMessage("");
    typeWriter(responseText, bubble);

    // ✅ Auto lead trigger
    if (responseText.includes("👉")) {
      setTimeout(showLeadForm, responseText.length * 15 + 500);
    }

  } catch (err) {
    if (typingIndicator) typingIndicator.remove();
    appendBotMessage("⚠️ Server error. Please try again.");
    console.error(err);
  } finally {
    setInputState(false);
  }
}

// ── Append Messages ───────────────────────────────────────────────────────────
function appendUserMessage(text) {
  const msgBox = document.getElementById("messages");
  const row = document.createElement("div");
  row.className = "message-row user-row";

  row.innerHTML = `
    <div class="avatar user-avatar">
      <span class="material-symbols-rounded">person</span>
    </div>
    <div class="message">${escapeHTML(text)}</div>
  `;

  msgBox.appendChild(row);
  scrollToBottom();
}

function appendBotMessage(text) {
  const msgBox = document.getElementById("messages");
  const row = document.createElement("div");
  row.className = "message-row bot-row";

  const bubble = document.createElement("div");
  bubble.className = "message";
  bubble.innerHTML = renderMarkdown(text);

  row.innerHTML = `
    <div class="avatar bot-avatar">
      <img src="./images/logo1.png" alt="Genkit Logo" class="bot-logo">
    </div>
  `;

  row.appendChild(bubble);
  msgBox.appendChild(row);
  scrollToBottom();

  return bubble;
}

// ── Typing Indicator ─────────────────────────────────────────────────────────
function appendTypingIndicator() {
  const msgBox = document.getElementById("messages");

  const row = document.createElement("div");
  row.className = "message-row bot-row";

  row.innerHTML = `
    <div class="avatar bot-avatar">
      <img src="./images/logo1.png" class="bot-logo">
    </div>
    <div class="typing-indicator">
      <span></span><span></span><span></span>
    </div>
  `;

  msgBox.appendChild(row);
  scrollToBottom();
  return row;
}

// ── Markdown Renderer ─────────────────────────────────────────────────────────
function renderMarkdown(text) {
  if (!text) return "";

  let html = escapeHTML(text);

  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");
  html = html.replace(/_(.+?)_/g, "<em>$1</em>");
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/^[-•] (.+)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>)/gs, "<ul>$1</ul>");
  html = html.replace(/\n/g, "<br>");

  return html;
}

// ── Utilities ─────────────────────────────────────────────────────────────────
function escapeHTML(str) {
  return str.replace(/[&<>"']/g, c => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;"
  }[c]));
}

function setInputState(disabled) {
  document.getElementById("input").disabled = disabled;
  document.getElementById("sendBtn").disabled = disabled;
}

function scrollToBottom() {
  const msgBox = document.getElementById("messages");
  msgBox.scrollTop = msgBox.scrollHeight;
}

// ── Auto-grow textarea ────────────────────────────────────────────────────────
function autoGrowTextarea() {
  const ta = document.getElementById("input");
  ta.addEventListener("input", () => {
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 120) + "px";
  });
}

// ── Lead Form ─────────────────────────────────────────────────────────────────
function showLeadForm() {
  const msgBox = document.getElementById("messages");

  const form = document.createElement("div");
  form.innerHTML = `
    <input id="leadName" placeholder="Your Name" />
    <input id="leadEmail" placeholder="Your Email" />
    <button onclick="submitLead()">Submit</button>
  `;

  msgBox.appendChild(form);
}

async function submitLead() {
  const name = document.getElementById("leadName").value;
  const email = document.getElementById("leadEmail").value;

  await fetch("/lead", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, email })
  });

  appendBotMessage("✅ Thanks! We'll contact you soon.");
}

// ── Keyboard Shortcut ─────────────────────────────────────────────────────────
document.addEventListener("keydown", (e) => {
  const input = document.getElementById("input");

  if (e.key === "Enter" && !e.shiftKey && document.activeElement === input) {
    e.preventDefault();
    sendMessage();
  }
});