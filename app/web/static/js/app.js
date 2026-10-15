// Cedar Lane Auto Detailing - AI Receptionist Frontend Controller

let conversationHistory = [];
let isVoiceMode = false;

document.addEventListener("DOMContentLoaded", () => {
  initEventListeners();
  loadCalendarEvents();
  loadContacts();
  loadVapiConfig();
});

function initEventListeners() {
  const sendBtn = document.getElementById("send-btn");
  const userInput = document.getElementById("user-input");
  const clearChatBtn = document.getElementById("clear-chat-btn");
  const refreshCalBtn = document.getElementById("refresh-cal-btn");
  const refreshSheetsBtn = document.getElementById("refresh-sheets-btn");
  const copyConfigBtn = document.getElementById("copy-config-btn");
  const textModeBtn = document.getElementById("text-mode-btn");
  const voiceModeBtn = document.getElementById("voice-mode-btn");

  sendBtn.addEventListener("click", () => handleSendMessage());
  userInput.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  });

  clearChatBtn.addEventListener("click", () => {
    conversationHistory = [];
    const chatContainer = document.getElementById("chat-messages");
    chatContainer.innerHTML = `
      <div class="message assistant">
        <div class="bubble">Thanks for calling Cedar Lane Auto Detailing! How can I help you today?</div>
        <div class="msg-meta">Cedar Lane AI • Just now</div>
      </div>
    `;
  });

  // Tab switching
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", (e) => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-content").forEach((c) => c.classList.remove("active"));

      const targetTab = btn.getAttribute("data-tab");
      btn.classList.add("active");
      document.getElementById(targetTab).classList.add("active");

      if (targetTab === "tab-calendar") loadCalendarEvents();
      if (targetTab === "tab-sheets") loadContacts();
    });
  });

  // Quick scenario prompt chips
  document.querySelectorAll(".scenario-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const prompt = chip.getAttribute("data-prompt");
      userInput.value = prompt;
      handleSendMessage();
    });
  });

  refreshCalBtn.addEventListener("click", loadCalendarEvents);
  refreshSheetsBtn.addEventListener("click", loadContacts);
  copyConfigBtn.addEventListener("click", copyVapiConfig);

  // Mode buttons
  textModeBtn.addEventListener("click", () => {
    isVoiceMode = false;
    textModeBtn.classList.add("active");
    voiceModeBtn.classList.remove("active");
    document.getElementById("agent-sub-text").textContent = "Text Chat Mode: Detailed, courteous assistance";
  });

  voiceModeBtn.addEventListener("click", () => {
    isVoiceMode = true;
    voiceModeBtn.classList.add("active");
    textModeBtn.classList.remove("active");
    document.getElementById("agent-sub-text").textContent = "Voice Mode (Vapi): Concise 1-2 sentence spoken replies (<1.2s target)";
  });

  // Microphone test using Web Speech API if supported
  const micBtn = document.getElementById("voice-speak-btn");
  if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;

    micBtn.addEventListener("click", () => {
      micBtn.style.background = "#ef4444";
      recognition.start();
    });

    recognition.onresult = (event) => {
      micBtn.style.background = "";
      const transcript = event.results[0][0].transcript;
      userInput.value = transcript;
      handleSendMessage();
    };

    recognition.onerror = () => {
      micBtn.style.background = "";
    };
  } else {
    micBtn.style.display = "none";
  }
}

async function handleSendMessage() {
  const userInput = document.getElementById("user-input");
  const text = userInput.value.trim();
  if (!text) return;

  userInput.value = "";

  // Append user bubble
  appendMessage("user", text);
  conversationHistory.push({ role: "user", content: text });

  // Show typing indicator
  const typingIndicator = appendTypingIndicator();

  try {
    const resp = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: jsonBody({
        messages: conversationHistory,
        is_voice_mode: isVoiceMode
      })
    });

    const data = await resp.json();
    typingIndicator.remove();

    conversationHistory.push({ role: "assistant", content: data.reply });
    appendMessage("assistant", data.reply, data.actions);

    // If calendar or sheets actions occurred, refresh the views
    if (data.actions && data.actions.length > 0) {
      loadCalendarEvents();
      loadContacts();
    }
  } catch (err) {
    typingIndicator.remove();
    appendMessage("assistant", "Sorry, I encountered a brief error connecting to the service. Please try again.");
    console.error(err);
  }
}

function appendMessage(role, content, actions = []) {
  const chatContainer = document.getElementById("chat-messages");
  const msgDiv = document.createElement("div");
  msgDiv.className = `message ${role}`;

  let actionsHtml = "";
  if (actions && actions.length > 0) {
    actions.forEach((a) => {
      const toolName = a.tool;
      let summary = toolName;
      if (toolName === "check_calendar_availability") {
        summary = `Checked Google Calendar availability: ${a.result.available ? "SLOT OPEN" : "SLOT CONFLICT/FULL"}`;
      } else if (toolName === "book_calendar_appointment") {
        summary = `Booked in Google Calendar: ${a.result.date} @ ${a.result.time} (${a.result.service})`;
      } else if (toolName === "reschedule_calendar_appointment") {
        summary = `Rescheduled in Google Calendar: ${a.result.new_date} @ ${a.result.new_time}`;
      } else if (toolName === "report_running_late") {
        summary = `Logged running late note (${a.result.delay_minutes}m) in Calendar & Sheets`;
      } else if (toolName === "log_escalation_or_inquiry") {
        summary = `Logged in Google Sheets Contacts tab: ${a.args.intent}`;
      }
      actionsHtml += `<div class="action-pill">⚡ ${summary}</div>`;
    });
  }

  msgDiv.innerHTML = `
    <div class="bubble">${escapeHtml(content)}</div>
    ${actionsHtml}
    <div class="msg-meta">${role === "user" ? "Caller" : "Cedar Lane AI"} • Just now</div>
  `;

  chatContainer.appendChild(msgDiv);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function appendTypingIndicator() {
  const chatContainer = document.getElementById("chat-messages");
  const typingDiv = document.createElement("div");
  typingDiv.className = "message assistant";
  typingDiv.innerHTML = `
    <div class="bubble" style="opacity: 0.7; font-style: italic;">Checking availability & details...</div>
  `;
  chatContainer.appendChild(typingDiv);
  chatContainer.scrollTop = chatContainer.scrollHeight;
  return typingDiv;
}

async function loadCalendarEvents() {
  const listEl = document.getElementById("events-list");
  const calIdDisplay = document.getElementById("cal-id-display");

  try {
    const res = await fetch("/api/calendar/events");
    const data = await res.json();
    if (calIdDisplay) {
      calIdDisplay.textContent = data.calendar_id || "Local Mock Calendar";
    }

    if (!data.events || data.events.length === 0) {
      listEl.innerHTML = `<div class="subtle" style="padding: 12px; text-align: center;">No upcoming events found.</div>`;
      return;
    }

    listEl.innerHTML = "";
    data.events.forEach((ev) => {
      const card = document.createElement("div");
      const isConflict = ev.summary.includes("Marcus") || ev.summary.includes("Brian");
      card.className = `event-card ${isConflict ? "conflict-event" : "new-event"}`;

      let startFormatted = ev.start;
      try {
        const d = new Date(ev.start);
        startFormatted = d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
      } catch (e) {}

      card.innerHTML = `
        <div>
          <div class="event-title">${escapeHtml(ev.summary)}</div>
          <div class="event-time">⏰ ${startFormatted}</div>
          <div class="event-desc">${escapeHtml(ev.description || "")}</div>
        </div>
      `;
      listEl.appendChild(card);
    });
  } catch (err) {
    listEl.innerHTML = `<div class="subtle" style="color: #ef4444;">Failed to load calendar events.</div>`;
    console.error(err);
  }
}

async function loadContacts() {
  const tbody = document.getElementById("contacts-body");
  try {
    const res = await fetch("/api/contacts");
    const data = await res.json();

    if (!data.contacts || data.contacts.length === 0) {
      tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: #94a3b8;">No contacts logged yet. Start a chat or booking to generate rows.</td></tr>`;
      return;
    }

    tbody.innerHTML = "";
    data.contacts.forEach((c) => {
      const tr = document.createElement("tr");

      let badgeClass = "booked";
      if (c.status.toLowerCase().includes("escalat") || c.status.toLowerCase().includes("dispute")) {
        badgeClass = "escalated";
      } else if (c.status.toLowerCase().includes("resched")) {
        badgeClass = "rescheduled";
      }

      tr.innerHTML = `
        <td><strong>${escapeHtml(c.caller_id || "")}</strong></td>
        <td>${escapeHtml(c.name || "")}</td>
        <td>${escapeHtml(c.phone || "")}</td>
        <td>${escapeHtml(c.timestamp || "")}</td>
        <td>${escapeHtml(c.intent || "")}</td>
        <td>${escapeHtml(c.service || "N/A")}</td>
        <td>${escapeHtml(c.appointment || "None")}</td>
        <td><span class="status-badge ${badgeClass}">${escapeHtml(c.status || "")}</span></td>
        <td style="${c.action_required && c.action_required.toLowerCase().includes('mike') ? 'color: #f87171; font-weight: 600;' : ''}">${escapeHtml(c.action_required || "None")}</td>
        <td>${escapeHtml(c.notes || "")}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="10" style="text-align: center; color: #ef4444;">Failed to load contacts.</td></tr>`;
    console.error(err);
  }
}

async function loadVapiConfig() {
  const pre = document.getElementById("vapi-json-display");
  const webhookDisplay = document.getElementById("webhook-url-display");

  try {
    const res = await fetch("/api/vapi/assistant-config");
    const config = await res.json();
    pre.textContent = JSON.stringify(config, null, 2);
    if (config.serverUrl) {
      webhookDisplay.textContent = config.serverUrl;
    }
  } catch (err) {
    pre.textContent = "Error loading configuration.";
    console.error(err);
  }
}

function copyVapiConfig() {
  const pre = document.getElementById("vapi-json-display");
  navigator.clipboard.writeText(pre.textContent).then(() => {
    alert("Vapi Assistant JSON Configuration copied to clipboard!");
  });
}

function copyWebhook() {
  const webhookDisplay = document.getElementById("webhook-url-display");
  navigator.clipboard.writeText(webhookDisplay.textContent).then(() => {
    alert("Webhook URL copied to clipboard!");
  });
}

function jsonBody(obj) {
  return JSON.stringify(obj);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
