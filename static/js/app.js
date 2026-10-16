/**
 * Ari Chat — Main Application Controller
 */

// Application State
const state = {
  user: null,
  currentConvId: null,
  conversations: [],
  webSearch: false,
  reasoningMode: false,
  isGenerating: false,
  abortController: null,
  authMode: "login" // 'login' or 'register'
};

// DOM Elements
const DOM = {
  // Sidebar
  sidebar: document.getElementById("sidebar"),
  sidebarBackdrop: document.getElementById("sidebar-backdrop"),
  openSidebarBtn: document.getElementById("open-sidebar-btn"),
  closeSidebarBtn: document.getElementById("close-sidebar-btn"),
  newChatBtn: document.getElementById("new-chat-btn"),
  modelSelect: document.getElementById("model-select"),
  searchConvInput: document.getElementById("search-conv-input"),
  conversationsList: document.getElementById("conversations-list"),
  userName: document.getElementById("user-name"),
  userAvatar: document.getElementById("user-avatar"),
  logoutBtn: document.getElementById("logout-btn"),
  memoryModalBtn: document.getElementById("memory-modal-btn"),

  // Chat Area
  chatTitle: document.getElementById("chat-title"),
  chatMeta: document.getElementById("chat-meta"),
  messagesContainer: document.getElementById("messages-container"),
  welcomeHero: document.getElementById("welcome-hero"),
  chatForm: document.getElementById("chat-form"),
  messageInput: document.getElementById("message-input"),
  sendBtn: document.getElementById("send-btn"),

  // Controls
  toggleSearchBtn: document.getElementById("toggle-search-btn"),
  searchIndicator: document.getElementById("search-indicator"),
  toggleReasoningBtn: document.getElementById("toggle-reasoning-btn"),
  reasoningIndicator: document.getElementById("reasoning-indicator"),
  btnQuickSearch: document.getElementById("btn-quick-search"),
  quickSearchLabel: document.getElementById("quick-search-label"),
  btnQuickReason: document.getElementById("btn-quick-reason"),
  quickReasonLabel: document.getElementById("quick-reason-label"),
  engineBadge: document.getElementById("engine-badge"),
  themeToggleBtn: document.getElementById("theme-toggle-btn"),
  themeIcon: document.getElementById("theme-icon"),

  // Auth Modal
  authModal: document.getElementById("auth-modal"),
  authForm: document.getElementById("auth-form"),
  authModalTitle: document.getElementById("auth-modal-title"),
  tabLogin: document.getElementById("tab-login"),
  tabRegister: document.getElementById("tab-register"),
  authUsername: document.getElementById("auth-username"),
  authEmail: document.getElementById("auth-email"),
  authEmailGroup: document.getElementById("auth-email-group"),
  authPassword: document.getElementById("auth-password"),
  authError: document.getElementById("auth-error"),
  authSubmitBtn: document.getElementById("auth-submit-btn"),
  guestBtn: document.getElementById("guest-btn"),

  // Memory Modal
  memoryModal: document.getElementById("memory-modal"),
  closeMemoryModalBtn: document.getElementById("close-memory-modal-btn"),
  memoriesContainer: document.getElementById("memories-container"),
  addMemoryForm: document.getElementById("add-memory-form"),
  newMemKey: document.getElementById("new-mem-key"),
  newMemVal: document.getElementById("new-mem-val"),
  clearAllMemoriesBtn: document.getElementById("clear-all-memories-btn")
};

// Initialize Application
document.addEventListener("DOMContentLoaded", async () => {
  initTheme();
  setupEventListeners();
  checkEngineHealth();
  await checkAuth();
});

function initTheme() {
  const saved = localStorage.getItem("ari_theme");
  const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  const isDark = saved ? saved === "dark" : prefersDark;
  setTheme(isDark);
}

function setTheme(isDark) {
  if (isDark) {
    document.documentElement.classList.add("dark");
    if (DOM.themeIcon) {
      DOM.themeIcon.className = "fa-solid fa-moon text-xs text-slate-300";
    }
    localStorage.setItem("ari_theme", "dark");
  } else {
    document.documentElement.classList.remove("dark");
    if (DOM.themeIcon) {
      DOM.themeIcon.className = "fa-solid fa-sun text-xs text-amber-500";
    }
    localStorage.setItem("ari_theme", "light");
  }
}

function toggleTheme() {
  const isCurrentlyDark = document.documentElement.classList.contains("dark");
  setTheme(!isCurrentlyDark);
}

// Configure Marked.js
if (typeof marked !== "undefined") {
  marked.setOptions({
    breaks: true,
    gfm: true
  });
}

/**
 * Event Listeners Setup
 */
function setupEventListeners() {
  // Sidebar Mobile Toggle
  DOM.openSidebarBtn?.addEventListener("click", () => {
    DOM.sidebar.classList.remove("-translate-x-full");
    DOM.sidebarBackdrop.classList.remove("hidden");
  });
  DOM.closeSidebarBtn?.addEventListener("click", closeMobileSidebar);
  DOM.sidebarBackdrop?.addEventListener("click", closeMobileSidebar);

  // New Chat
  DOM.newChatBtn?.addEventListener("click", createNewChat);
  window.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "o") {
      e.preventDefault();
      createNewChat();
    }
  });

  // Toggles
  DOM.themeToggleBtn?.addEventListener("click", toggleTheme);
  DOM.toggleSearchBtn?.addEventListener("click", toggleWebSearch);
  DOM.btnQuickSearch?.addEventListener("click", toggleWebSearch);
  DOM.toggleReasoningBtn?.addEventListener("click", toggleReasoning);
  DOM.btnQuickReason?.addEventListener("click", toggleReasoning);

  // Input Auto-Grow, Send, and Stop on Escape
  DOM.messageInput?.addEventListener("input", handleInputChange);
  DOM.messageInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      if (state.isGenerating) {
        stopGeneration();
      } else if (DOM.messageInput.value.trim().length > 0) {
        DOM.chatForm.dispatchEvent(new Event("submit"));
      }
    } else if (e.key === "Escape" && state.isGenerating) {
      e.preventDefault();
      stopGeneration();
    }
  });

  DOM.chatForm?.addEventListener("submit", (e) => {
    e.preventDefault();
    if (state.isGenerating) {
      stopGeneration();
    } else {
      handleSendMessage(e);
    }
  });

  DOM.sendBtn?.addEventListener("click", (e) => {
    if (state.isGenerating) {
      e.preventDefault();
      e.stopPropagation();
      stopGeneration();
    }
  });

  // Search Filter in Sidebar
  DOM.searchConvInput?.addEventListener("input", filterConversations);

  // Suggestion Cards
  document.querySelectorAll(".suggestion-card").forEach((btn) => {
    btn.addEventListener("click", () => {
      const prompt = btn.getAttribute("data-prompt");
      const requiresSearch = btn.getAttribute("data-search") === "true";
      if (requiresSearch && !state.webSearch) {
        toggleWebSearch();
      }
      DOM.messageInput.value = prompt;
      handleInputChange();
      DOM.chatForm.dispatchEvent(new Event("submit"));
    });
  });

  // Auth Modal Listeners
  DOM.tabLogin?.addEventListener("click", () => switchAuthTab("login"));
  DOM.tabRegister?.addEventListener("click", () => switchAuthTab("register"));
  DOM.authForm?.addEventListener("submit", handleAuthSubmit);
  DOM.guestBtn?.addEventListener("click", handleGuestDemo);
  DOM.logoutBtn?.addEventListener("click", handleLogout);
  window.addEventListener("ari:unauthorized", () => showAuthModal());

  // Memory Modal Listeners
  DOM.memoryModalBtn?.addEventListener("click", openMemoryModal);
  DOM.closeMemoryModalBtn?.addEventListener("click", closeMemoryModal);
  DOM.addMemoryForm?.addEventListener("submit", handleAddMemory);
  DOM.clearAllMemoriesBtn?.addEventListener("click", handleClearMemories);
}

function closeMobileSidebar() {
  DOM.sidebar.classList.add("-translate-x-full");
  DOM.sidebarBackdrop.classList.add("hidden");
}

/**
 * Authentication Flow
 */
async function checkAuth() {
  const user = API.getUser();
  if (!user || !API.getToken()) {
    showAuthModal();
    return;
  }
  try {
    const me = await API.getMe();
    setUserState(me);
    await loadConversations();
  } catch (err) {
    showAuthModal();
  }
}

function setUserState(user) {
  state.user = user;
  DOM.userName.textContent = user.username;
  DOM.userAvatar.textContent = user.username.charAt(0).toUpperCase();
  DOM.authModal.classList.add("hidden");
}

function showAuthModal() {
  DOM.authModal.classList.remove("hidden");
  DOM.authUsername.focus();
}

function switchAuthTab(mode) {
  state.authMode = mode;
  DOM.authError.classList.add("hidden");
  if (mode === "login") {
    DOM.tabLogin.className = "flex-1 pb-2.5 text-xs font-semibold text-indigo-400 border-b-2 border-indigo-500";
    DOM.tabRegister.className = "flex-1 pb-2.5 text-xs font-semibold text-slate-400 hover:text-slate-200";
    DOM.authEmailGroup.classList.add("hidden");
    DOM.authModalTitle.textContent = "Welcome Back to Ari Chat";
    DOM.authSubmitBtn.textContent = "Sign In";
  } else {
    DOM.tabRegister.className = "flex-1 pb-2.5 text-xs font-semibold text-indigo-400 border-b-2 border-indigo-500";
    DOM.tabLogin.className = "flex-1 pb-2.5 text-xs font-semibold text-slate-400 hover:text-slate-200";
    DOM.authEmailGroup.classList.remove("hidden");
    DOM.authModalTitle.textContent = "Create an Account";
    DOM.authSubmitBtn.textContent = "Register & Continue";
  }
}

async function handleAuthSubmit(e) {
  e.preventDefault();
  DOM.authError.classList.add("hidden");
  const username = DOM.authUsername.value.trim();
  const password = DOM.authPassword.value;
  const email = DOM.authEmail.value.trim();

  try {
    let data;
    if (state.authMode === "login") {
      data = await API.login(username, password);
    } else {
      data = await API.register(username, email || `${username}@example.com`, password);
    }
    setUserState(data.user);
    await loadConversations();
  } catch (err) {
    DOM.authError.textContent = err.message;
    DOM.authError.classList.remove("hidden");
  }
}

async function handleGuestDemo() {
  const randNum = Math.floor(1000 + Math.random() * 9000);
  const username = `guest_${randNum}`;
  const password = "guest_password_123";
  try {
    const data = await API.register(username, `${username}@arichat.local`, password);
    setUserState(data.user);
    await loadConversations();
  } catch {
    const data = await API.login(username, password);
    setUserState(data.user);
    await loadConversations();
  }
}

function handleLogout() {
  API.clearAuth();
  state.user = null;
  state.currentConvId = null;
  state.conversations = [];
  DOM.conversationsList.innerHTML = "";
  DOM.messagesContainer.innerHTML = "";
  DOM.messagesContainer.appendChild(DOM.welcomeHero);
  DOM.welcomeHero.classList.remove("hidden");
  showAuthModal();
}

/**
 * Health & Dynamic Model List
 */
async function checkEngineHealth() {
  try {
    const health = await API.getHealth();
    if (health.ollama && health.ollama.models && health.ollama.models.length > 0) {
      populateModelDropdown(health.ollama.models);
    }
  } catch (err) {
    console.error("Health check error:", err);
  }
}

function populateModelDropdown(models) {
  if (!DOM.modelSelect) return;
  const currentVal = DOM.modelSelect.value;
  DOM.modelSelect.innerHTML = "";

  const allowed = [
    { id: "ari-assistant-3b", label: "Ari 3B Assistant (Recommended)" },
    { id: "ari-assistant-1.5b", label: "Ari 1.5B Assistant (Updated)" }
  ];

  allowed.forEach((item) => {
    const opt = document.createElement("option");
    opt.value = item.id;
    opt.textContent = item.label;
    if (currentVal === item.id) {
      opt.selected = true;
    } else if (!currentVal && item.id === "ari-assistant-3b") {
      opt.selected = true;
    }
    DOM.modelSelect.appendChild(opt);
  });

  if (currentVal && Array.from(DOM.modelSelect.options).some(o => o.value === currentVal)) {
    DOM.modelSelect.value = currentVal;
  }
}

/**
 * Toggle Handlers (Minimalist)
 */
function toggleWebSearch() {
  state.webSearch = !state.webSearch;
  if (DOM.btnQuickSearch) {
    if (state.webSearch) {
      DOM.btnQuickSearch.style.backgroundColor = "var(--text-primary)";
      DOM.btnQuickSearch.style.color = "var(--accent-contrast)";
      if (DOM.quickSearchLabel) DOM.quickSearchLabel.textContent = "Web On";
    } else {
      DOM.btnQuickSearch.style.backgroundColor = "";
      DOM.btnQuickSearch.style.color = "";
      if (DOM.quickSearchLabel) DOM.quickSearchLabel.textContent = "Search";
    }
  }
}

function toggleReasoning() {
  state.reasoningMode = !state.reasoningMode;
  if (DOM.btnQuickReason) {
    if (state.reasoningMode) {
      DOM.btnQuickReason.style.backgroundColor = "var(--text-primary)";
      DOM.btnQuickReason.style.color = "var(--accent-contrast)";
      if (DOM.quickReasonLabel) DOM.quickReasonLabel.textContent = "Reason On";
    } else {
      DOM.btnQuickReason.style.backgroundColor = "";
      DOM.btnQuickReason.style.color = "";
      if (DOM.quickReasonLabel) DOM.quickReasonLabel.textContent = "Reason";
    }
  }
}

/**
 * Conversations Management
 */
async function loadConversations() {
  try {
    const list = await API.getConversations();
    state.conversations = list;
    renderConversationsList();
    if (list.length > 0 && !state.currentConvId) {
      await selectConversation(list[0].id);
    }
  } catch (err) {
    console.error("Failed to load conversations:", err);
  }
}

function renderConversationsList(filter = "") {
  DOM.conversationsList.innerHTML = "";
  const filtered = state.conversations.filter((c) =>
    c.title.toLowerCase().includes(filter.toLowerCase())
  );

  if (filtered.length === 0) {
    DOM.conversationsList.innerHTML = `
      <div class="text-center py-6 text-xs text-slate-500">
        <p>${filter ? "No matching chats" : "No conversations yet"}</p>
      </div>`;
    return;
  }

  filtered.forEach((conv) => {
    const isActive = conv.id === state.currentConvId;
    const item = document.createElement("div");
    item.className = `group flex items-center justify-between px-3 py-2 rounded-xl text-xs cursor-pointer transition-all ${
      isActive
        ? "bg-[#252938] text-white font-medium border border-indigo-500/30"
        : "text-slate-400 hover:bg-[#20232e] hover:text-slate-200"
    }`;

    item.innerHTML = `
      <div class="flex items-center gap-2.5 min-w-0 flex-1">
        <i class="fa-regular fa-message text-[11px] ${isActive ? "text-indigo-400" : "text-slate-500"}"></i>
        <span class="truncate">${escapeHtml(conv.title)}</span>
      </div>
      <div class="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button class="rename-conv-btn p-1 hover:text-indigo-400" title="Rename"><i class="fa-solid fa-pen text-[10px]"></i></button>
        <button class="delete-conv-btn p-1 hover:text-rose-400" title="Delete"><i class="fa-solid fa-trash text-[10px]"></i></button>
      </div>
    `;

    item.addEventListener("click", (e) => {
      if (!e.target.closest("button")) {
        selectConversation(conv.id);
        closeMobileSidebar();
      }
    });

    item.querySelector(".rename-conv-btn")?.addEventListener("click", (e) => {
      e.stopPropagation();
      promptRenameConversation(conv.id, conv.title);
    });

    item.querySelector(".delete-conv-btn")?.addEventListener("click", (e) => {
      e.stopPropagation();
      handleDeleteConversation(conv.id);
    });

    DOM.conversationsList.appendChild(item);
  });
}

function filterConversations(e) {
  renderConversationsList(e.target.value.trim());
}

async function createNewChat() {
  try {
    const model = DOM.modelSelect.value;
    const conv = await API.createConversation("New Chat", model);
    state.conversations.unshift(conv);
    renderConversationsList();
    await selectConversation(conv.id);
    closeMobileSidebar();
  } catch (err) {
    console.error("Error creating chat:", err);
  }
}

async function selectConversation(id) {
  state.currentConvId = id;
  renderConversationsList();
  try {
    const detail = await API.getConversation(id);
    DOM.chatTitle.textContent = detail.title;
    DOM.chatMeta.textContent = `${detail.model} (${detail.messages.length} messages)`;

    DOM.messagesContainer.innerHTML = "";
    if (detail.messages.length === 0) {
      DOM.messagesContainer.appendChild(DOM.welcomeHero);
      DOM.welcomeHero.classList.remove("hidden");
    } else {
      DOM.welcomeHero.classList.add("hidden");
      detail.messages.forEach((msg) => renderMessage(msg));
      scrollToBottom();
    }
  } catch (err) {
    console.error("Error loading chat:", err);
  }
}

async function promptRenameConversation(id, oldTitle) {
  const newTitle = prompt("Rename conversation:", oldTitle);
  if (newTitle && newTitle.trim()) {
    try {
      await API.renameConversation(id, newTitle.trim());
      const conv = state.conversations.find((c) => c.id === id);
      if (conv) conv.title = newTitle.trim();
      renderConversationsList();
      if (state.currentConvId === id) DOM.chatTitle.textContent = newTitle.trim();
    } catch (err) {
      alert("Failed to rename: " + err.message);
    }
  }
}

async function handleDeleteConversation(id) {
  if (confirm("Are you sure you want to delete this chat?")) {
    try {
      await API.deleteConversation(id);
      state.conversations = state.conversations.filter((c) => c.id !== id);
      renderConversationsList();
      if (state.currentConvId === id) {
        if (state.conversations.length > 0) {
          selectConversation(state.conversations[0].id);
        } else {
          createNewChat();
        }
      }
    } catch (err) {
      alert("Failed to delete chat: " + err.message);
    }
  }
}

/**
 * Message Handling & Streaming with Modern Send/Stop Control
 */
function setGenerationState(isGenerating) {
  state.isGenerating = isGenerating;
  if (!DOM.sendBtn) return;

  if (isGenerating) {
    DOM.sendBtn.disabled = false;
    DOM.sendBtn.title = "Stop generating (Esc)";
    DOM.sendBtn.setAttribute("aria-label", "Stop generating");
    DOM.sendBtn.classList.add("stop-active");
    DOM.sendBtn.innerHTML = '<i class="fa-solid fa-square text-[10px]"></i>';
  } else {
    DOM.sendBtn.title = "Send message";
    DOM.sendBtn.setAttribute("aria-label", "Send message");
    DOM.sendBtn.classList.remove("stop-active");
    DOM.sendBtn.innerHTML = '<i class="fa-solid fa-arrow-up text-xs"></i>';
    DOM.sendBtn.disabled = DOM.messageInput.value.trim().length === 0;
  }
}

function stopGeneration() {
  if (state.abortController) {
    state.abortController.abort();
    state.abortController = null;
  }
  setGenerationState(false);
}

function handleInputChange() {
  DOM.messageInput.style.height = "auto";
  DOM.messageInput.style.height = `${Math.min(DOM.messageInput.scrollHeight, 140)}px`;
  if (!state.isGenerating) {
    DOM.sendBtn.disabled = DOM.messageInput.value.trim().length === 0;
  }
}

async function handleSendMessage(e) {
  if (e && e.preventDefault) e.preventDefault();
  const text = DOM.messageInput.value.trim();
  if (!text || state.isGenerating) return;

  // Make sure a conversation exists
  if (!state.currentConvId) {
    await createNewChat();
  }

  DOM.welcomeHero.classList.add("hidden");
  DOM.messageInput.value = "";
  DOM.messageInput.style.height = "auto";

  state.abortController = new AbortController();
  setGenerationState(true);

  // Render User Message
  renderMessage({ role: "user", content: text, created_at: new Date().toISOString() });
  scrollToBottom();

  // Create Assistant Message Placeholder
  const botBubble = createAssistantPlaceholder();
  DOM.messagesContainer.appendChild(botBubble);
  scrollToBottom();

  const token = API.getToken();
  const sourcesContainer = botBubble.querySelector(".sources-container");
  const reasoningBox = botBubble.querySelector(".reasoning-box");
  const reasoningText = botBubble.querySelector(".reasoning-text");
  const bodyEl = botBubble.querySelector(".markdown-body");

  let fullResponse = "";
  let insideThought = false;
  let thoughtBuffer = "";

  try {
    const response = await fetch(`/api/chat/conversations/${state.currentConvId}/messages`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`
      },
      signal: state.abortController.signal,
      body: JSON.stringify({
        content: text,
        web_search: state.webSearch,
        reasoning_mode: state.reasoningMode,
        model: DOM.modelSelect.value
      })
    });

    if (!response.ok) {
      throw new Error("Generation stream failed: " + response.statusText);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n\n");
      buffer = lines.pop(); // Keep unfinished chunk

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const jsonStr = line.slice(6).trim();
          if (!jsonStr) continue;
          try {
            const data = JSON.parse(jsonStr);

            // 0. Real-Time Memory Updated Notification
            if (data.type === "memory_updated" && data.memory) {
              showMemoryToast(data.memory);
            }

            // 1. Web Sources
            if (data.type === "sources" && data.sources) {
              sourcesContainer.classList.remove("hidden");
              sourcesContainer.innerHTML = data.sources
                .map(
                  (s, i) =>
                    `<a href="${escapeHtml(s.url)}" target="_blank" rel="noopener" class="source-pill" title="${escapeHtml(s.title)}">
                      <i class="fa-solid fa-link text-[10px]"></i>
                      <span>${escapeHtml(s.title)}</span>
                    </a>`
                )
                .join("");
            }

            // 2. Token Stream
            if (data.type === "token") {
              const tok = data.token;

              // Check reasoning tags
              if (tok.includes("<thought>")) {
                insideThought = true;
                reasoningBox.classList.remove("hidden");
              }

              if (insideThought) {
                if (tok.includes("</thought>")) {
                  insideThought = false;
                  const parts = tok.split("</thought>");
                  thoughtBuffer += parts[0].replace("<thought>", "");
                  reasoningText.textContent = thoughtBuffer;
                  fullResponse += parts[1];
                } else {
                  thoughtBuffer += tok.replace("<thought>", "");
                  reasoningText.textContent = thoughtBuffer;
                }
              } else {
                fullResponse += tok;
                // Live repetition guard
                const repCheck = stripClientRepeats(fullResponse);
                if (repCheck !== fullResponse) {
                  fullResponse = repCheck;
                  bodyEl.innerHTML = marked.parse(fullResponse);
                  break; // terminate loop
                }
                bodyEl.innerHTML = marked.parse(fullResponse) + `<span class="cursor-blink"></span>`;
              }
              scrollToBottom();
            }

            // 3. Error
            if (data.type === "error") {
              bodyEl.innerHTML += `<div class="text-xs text-rose-400 mt-2 p-2 bg-rose-500/10 rounded-lg">${escapeHtml(data.error)}</div>`;
            }

            // 4. Finished
            if (data.type === "done") {
              if (data.clean_content) {
                fullResponse = data.clean_content;
              } else {
                fullResponse = stripClientRepeats(fullResponse);
              }
              bodyEl.innerHTML = marked.parse(fullResponse);
              decorateCodeBlocks(bodyEl);
              updateConversationTitleAfterSend(text);
            }
          } catch (e) {
            console.error("SSE parse error:", e);
          }
        }
      }
    }
  } catch (err) {
    if (err.name === "AbortError" || err.message?.includes("aborted")) {
      // Stopped cleanly by user
      if (fullResponse) {
        fullResponse = stripClientRepeats(fullResponse);
        bodyEl.innerHTML = marked.parse(fullResponse);
      }
    } else {
      bodyEl.innerHTML += `<div class="text-xs text-rose-400 mt-2 p-2 bg-rose-500/10 rounded-lg">Error: ${escapeHtml(err.message)}</div>`;
    }
  } finally {
    setGenerationState(false);
    state.abortController = null;
    // Remove any trailing cursor
    const blinker = bodyEl.querySelector(".cursor-blink");
    if (blinker) blinker.remove();
    decorateCodeBlocks(bodyEl);
  }
}

function updateConversationTitleAfterSend(firstPrompt) {
  const conv = state.conversations.find((c) => c.id === state.currentConvId);
  if (conv && conv.title === "New Chat") {
    conv.title = firstPrompt.slice(0, 35) + (firstPrompt.length > 35 ? "..." : "");
    DOM.chatTitle.textContent = conv.title;
    renderConversationsList();
  }
}

function createAssistantPlaceholder() {
  const el = document.createElement("div");
  el.className = "flex gap-3 max-w-3xl mx-auto";
  el.innerHTML = `
    <div class="w-6 h-6 rounded-md border flex items-center justify-center shrink-0 text-current mt-0.5" style="border-color: var(--border-subtle)">
      <svg viewBox="0 0 64 64" fill="none" class="w-4 h-4" xmlns="http://www.w3.org/2000/svg">
        <path d="M32 8L10 52H22L32 32L42 52H54L32 8Z" fill="currentColor"/>
        <circle cx="32" cy="41" r="4.5" fill="currentColor"/>
      </svg>
    </div>
    <div class="flex-1 min-w-0">
      <div class="flex items-center gap-2 mb-1.5">
        <span class="text-xs font-semibold">Ari</span>
        <span class="text-[10px] text-zinc-400">Just now</span>
      </div>
      <div class="sources-container hidden"></div>
      <details class="reasoning-box hidden">
        <summary><i class="fa-solid fa-brain text-xs"></i> Thought process</summary>
        <div class="reasoning-text"></div>
      </details>
      <div class="markdown-body text-sm select-text pt-0.5">
        <span class="cursor-blink"></span>
      </div>
    </div>
  `;
  return el;
}

function renderMessage(msg) {
  const isUser = msg.role === "user";
  const el = document.createElement("div");
  el.className = "flex gap-3 max-w-3xl mx-auto " + (isUser ? "justify-end" : "");

  if (isUser) {
    el.innerHTML = `
      <div class="msg-bubble-user max-w-[85%] sm:max-w-[75%] rounded-2xl px-4 py-2.5 text-sm select-text">
        ${escapeHtml(msg.content)}
      </div>
    `;
  } else {
    let sourcesHtml = "";
    if (msg.sources && msg.sources.length > 0) {
      sourcesHtml = `
        <div class="sources-container">
          ${msg.sources
            .map(
              (s, i) =>
                `<a href="${escapeHtml(s.url)}" target="_blank" rel="noopener" class="source-pill" title="${escapeHtml(s.title)}">
                  <i class="fa-solid fa-link text-[10px]"></i>
                  <span>${escapeHtml(s.title)}</span>
                </a>`
            )
            .join("")}
        </div>
      `;
    }

    let reasoningHtml = "";
    if (msg.reasoning) {
      reasoningHtml = `
        <details class="reasoning-box">
          <summary><i class="fa-solid fa-brain text-xs"></i> Thought process</summary>
          <div class="reasoning-text">${escapeHtml(msg.reasoning)}</div>
        </details>
      `;
    }

    el.innerHTML = `
      <div class="w-6 h-6 rounded-md border flex items-center justify-center shrink-0 text-current mt-0.5" style="border-color: var(--border-subtle)">
        <svg viewBox="0 0 64 64" fill="none" class="w-4 h-4" xmlns="http://www.w3.org/2000/svg">
          <path d="M32 8L10 52H22L32 32L42 52H54L32 8Z" fill="currentColor"/>
          <circle cx="32" cy="41" r="4.5" fill="currentColor"/>
        </svg>
      </div>
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 mb-1.5">
          <span class="text-xs font-semibold">Ari</span>
          <span class="text-[10px] text-zinc-400">${formatDate(msg.created_at)}</span>
        </div>
        ${sourcesHtml}
        ${reasoningHtml}
        <div class="markdown-body text-sm select-text pt-0.5">
          ${marked.parse(msg.content || "")}
        </div>
      </div>
    `;
    decorateCodeBlocks(el.querySelector(".markdown-body"));
  }

  DOM.messagesContainer.appendChild(el);
}

function decorateCodeBlocks(container) {
  if (!container) return;
  container.querySelectorAll("pre code").forEach((block) => {
    hljs.highlightElement(block);
    const pre = block.parentElement;
    if (pre.querySelector(".code-header")) return; // already decorated

    const lang = block.className.match(/language-(\w+)/)?.[1] || "code";
    const header = document.createElement("div");
    header.className = "code-header";
    header.innerHTML = `
      <span class="font-mono text-[11px] uppercase tracking-wider">${lang}</span>
      <button class="copy-code-btn text-xs text-slate-400 hover:text-white flex items-center gap-1">
        <i class="fa-regular fa-copy"></i>
        <span>Copy</span>
      </button>
    `;

    header.querySelector(".copy-code-btn").addEventListener("click", () => {
      navigator.clipboard.writeText(block.innerText);
      header.querySelector(".copy-code-btn").innerHTML = `<i class="fa-solid fa-check text-emerald-400"></i><span class="text-emerald-400">Copied!</span>`;
      setTimeout(() => {
        header.querySelector(".copy-code-btn").innerHTML = `<i class="fa-regular fa-copy"></i><span>Copy</span>`;
      }, 2000);
    });

    pre.prepend(header);
  });
}

function scrollToBottom() {
  DOM.messagesContainer.scrollTop = DOM.messagesContainer.scrollHeight;
}

/**
 * Memory Management
 */
async function openMemoryModal() {
  DOM.memoryModal.classList.remove("hidden");
  await loadMemories();
}

function closeMemoryModal() {
  DOM.memoryModal.classList.add("hidden");
}

async function loadMemories() {
  DOM.memoriesContainer.innerHTML = `<div class="text-center py-4 text-xs text-slate-500"><i class="fa-solid fa-spinner fa-spin mr-1"></i> Loading memories...</div>`;
  try {
    const list = await API.getMemories();
    if (list.length === 0) {
      DOM.memoriesContainer.innerHTML = `<p class="text-xs text-slate-500 text-center py-4">No memories stored yet. Tell Ari about yourself or add one above!</p>`;
      return;
    }
    DOM.memoriesContainer.innerHTML = list
      .map(
        (m) => `
        <div class="flex items-center justify-between p-2.5 rounded-xl bg-[#222530] border border-[#2e3446] text-xs">
          <div>
            <span class="font-semibold text-indigo-400">${escapeHtml(m.key)}:</span>
            <span class="text-slate-200 ml-1">${escapeHtml(m.value)}</span>
            <span class="text-[10px] bg-[#181a22] text-slate-400 px-1.5 py-0.5 rounded ml-2">${escapeHtml(m.category)}</span>
          </div>
          <button onclick="handleDeleteMemory(${m.id})" class="text-slate-500 hover:text-rose-400 p-1">
            <i class="fa-solid fa-trash text-[11px]"></i>
          </button>
        </div>`
      )
      .join("");
  } catch (err) {
    DOM.memoriesContainer.innerHTML = `<p class="text-xs text-rose-400 text-center py-4">Error loading memories: ${err.message}</p>`;
  }
}

async function handleAddMemory(e) {
  e.preventDefault();
  const key = DOM.newMemKey.value.trim();
  const val = DOM.newMemVal.value.trim();
  if (!key || !val) return;
  try {
    await API.createMemory(key, val);
    DOM.newMemKey.value = "";
    DOM.newMemVal.value = "";
    await loadMemories();
  } catch (err) {
    alert("Failed to store memory: " + err.message);
  }
}

window.handleDeleteMemory = async function (id) {
  try {
    await API.deleteMemory(id);
    await loadMemories();
  } catch (err) {
    alert("Failed to delete memory: " + err.message);
  }
};

async function handleClearMemories() {
  if (confirm("Are you sure you want to clear all stored memories?")) {
    try {
      await API.clearMemories();
      await loadMemories();
    } catch (err) {
      alert("Failed to clear memories: " + err.message);
    }
  }
}

/**
 * Utility Helpers
 */
function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatDate(isoStr) {
  if (!isoStr) return "";
  try {
    const d = new Date(isoStr);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function stripClientRepeats(text) {
  if (!text) return "";
  let cleaned = text.replace(/^<(?:response|answer)>\s*/i, "");

  // Cut at known stop tokens or synthetic markers
  const stopMarkers = [
    "</response>",
    "</answer>",
    "<endofconversation>",
    "<startchat>",
    "<|im_end|>",
    "<|im_start|>",
    "<|endoftext|>",
    "_Static",
    "Statics",
    "⏤",
    "<nooutput>",
    "//[",
    "[iVar",
    "Intialized:",
    "Answered.",
    "<br/>"
  ];
  for (const marker of stopMarkers) {
    const idx = cleaned.toLowerCase().indexOf(marker.toLowerCase());
    if (idx !== -1) {
      cleaned = cleaned.slice(0, idx);
    }
  }

  // Remove trailing unclosed tags
  cleaned = cleaned.replace(/(?:<br\s*\/?>?|<\s*|\/\s*>|\/><end.*)$/i, "");

  // Cut at simulated turns or hallucinated user prompts
  const simTurnPatterns = [
    /\n(?:User|Human|Prompt):\s*/i,
    /\n###\s*(?:User|Human|Prompt)/i,
    /\n(?:hi\b|hello\b|hey\b).*?\?/i,
    /\n(?:what are u|what are you|who are you)\b/i,
    /\n(?:hi i am|hello i am)\b/i,
    /\nI'm Ari\b/i
  ];
  for (const pat of simTurnPatterns) {
    const m = cleaned.slice(20).search(pat);
    if (m !== -1) {
      cleaned = cleaned.slice(0, 20 + m);
    }
  }

  // Universal paragraph deduplication: truncate before the first duplicate paragraph
  const paras = cleaned.split("\n");
  const seenParas = new Set();
  const keptParas = [];
  for (const p of paras) {
    const pClean = p.trim();
    if (pClean.length >= 30) {
      const norm = pClean.replace(/[^\w\s]/g, "").toLowerCase();
      if (seenParas.has(norm)) {
        break;
      }
      seenParas.add(norm);
    }
    keptParas.push(p);
  }
  cleaned = keptParas.join("\n");

  // Universal sentence deduplication: truncate before the first duplicate sentence
  const sents = cleaned.split(/(?<=[.!?])\s+/);
  const seenSents = new Set();
  const keptSents = [];
  for (const s of sents) {
    const sClean = s.trim();
    if (sClean.length >= 25) {
      const norm = sClean.replace(/[^\w\s]/g, "").toLowerCase();
      if (seenSents.has(norm)) {
        break;
      }
      seenSents.add(norm);
    }
    keptSents.push(s);
  }
  cleaned = keptSents.join(" ");

  // Strip cyclical loops
  if (cleaned.length >= 6) {
    for (let l = 2; l <= 50; l++) {
      if (cleaned.length >= l * 3) {
        const pat = cleaned.slice(-l);
        if (!pat.trim() || !/[a-zA-Z0-9]/.test(pat)) {
          continue;
        }
        if (cleaned.endsWith(pat.repeat(3))) {
          while (cleaned.endsWith(pat)) {
            cleaned = cleaned.slice(0, -l);
          }
          break;
        }
      }
    }
  }
  return cleaned.trim();
}

