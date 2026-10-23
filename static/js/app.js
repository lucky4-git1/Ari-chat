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
  authMode: "login", // 'login' or 'register'
  modelsData: [],
  modelPullTimer: null
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
  pullModelBtn: document.getElementById("pull-model-btn"),
  pullModelBtnText: document.getElementById("pull-model-btn-text"),
  modelPullModal: document.getElementById("model-pull-modal"),
  closePullModalBtn: document.getElementById("close-pull-modal-btn"),
  startPullBtn: document.getElementById("start-pull-btn"),
  cancelPullBtn: document.getElementById("cancel-pull-btn"),
  pullProgressSection: document.getElementById("pull-progress-section"),
  pullStatusLabel: document.getElementById("pull-status-label"),
  pullPercentLabel: document.getElementById("pull-percent-label"),
  pullProgressBar: document.getElementById("pull-progress-bar"),
  pullBytesLabel: document.getElementById("pull-bytes-label"),
  pullSpeedLabel: document.getElementById("pull-speed-label"),
  pullEtaLabel: document.getElementById("pull-eta-label"),
  searchConvInput: document.getElementById("search-conv-input"),
  conversationsList: document.getElementById("conversations-list"),
  userName: document.getElementById("user-name"),
  userAvatar: document.getElementById("user-avatar"),
  memoryModalBtn: document.getElementById("memory-modal-btn"),
  sidebarUpdateBtn: document.getElementById("sidebar-update-btn"),
  sidebarUpdateDot: document.getElementById("sidebar-update-dot"),

  // Auto-Updater
  updateBannerBtn: document.getElementById("update-banner-btn"),
  updateBannerText: document.getElementById("update-banner-text"),
  updateModal: document.getElementById("update-modal"),
  closeUpdateModalBtn: document.getElementById("close-update-modal-btn"),
  updateModalTitle: document.getElementById("update-modal-title"),
  updateModalSubtitle: document.getElementById("update-modal-subtitle"),
  updateNotesText: document.getElementById("update-notes-text"),
  updateProgressSection: document.getElementById("update-progress-section"),
  updateStatusLabel: document.getElementById("update-status-label"),
  updatePercentLabel: document.getElementById("update-percent-label"),
  updateProgressBar: document.getElementById("update-progress-bar"),
  updateSpeedLabel: document.getElementById("update-speed-label"),
  updateEtaLabel: document.getElementById("update-eta-label"),
  startUpdateBtn: document.getElementById("start-update-btn"),
  cancelUpdateBtn: document.getElementById("cancel-update-btn"),
  applyUpdateBtn: document.getElementById("apply-update-btn"),

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
  memoryCountBadge: document.getElementById("memory-count-badge"),
  memoryToastContainer: document.getElementById("memory-toast-container"),
  clearAllMemoriesBtn: document.getElementById("clear-all-memories-btn")
};

// Initialize Application
document.addEventListener("DOMContentLoaded", async () => {
  initTheme();
  setupEventListeners();
  loadAvailableModels();
  checkEngineHealth();
  checkAppUpdates(true);
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
  DOM.clearAllMemoriesBtn?.addEventListener("click", handleClearMemories);

  // Model Pull Listeners
  DOM.pullModelBtn?.addEventListener("click", () => openPullModelModal("ari-assistant-3b"));
  DOM.closePullModalBtn?.addEventListener("click", closePullModelModal);
  DOM.startPullBtn?.addEventListener("click", handleStartPull);
  DOM.cancelPullBtn?.addEventListener("click", handleCancelPull);
  DOM.modelSelect?.addEventListener("change", handleModelSelectChange);

  // Auto-Updater Listeners
  DOM.updateBannerBtn?.addEventListener("click", openUpdateModal);
  DOM.sidebarUpdateBtn?.addEventListener("click", () => checkAppUpdates(false));
  DOM.closeUpdateModalBtn?.addEventListener("click", closeUpdateModal);
  DOM.startUpdateBtn?.addEventListener("click", handleStartUpdate);
  DOM.cancelUpdateBtn?.addEventListener("click", handleCancelUpdate);
  DOM.applyUpdateBtn?.addEventListener("click", handleApplyUpdate);
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
  DOM.authError.classList.add("hidden");
  DOM.guestBtn.disabled = true;
  DOM.guestBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin text-xs"></i> <span>Entering as Guest...</span>`;

  try {
    const data = await API.guestLogin();
    setUserState(data.user);
    await loadConversations();
  } catch (err) {
    DOM.authError.textContent = err.message || "Failed to continue as guest";
    DOM.authError.classList.remove("hidden");
  } finally {
    DOM.guestBtn.disabled = false;
    DOM.guestBtn.innerHTML = `Continue as Guest`;
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
 * Health & Dynamic Model Management
 */
async function checkEngineHealth() {
  try {
    const health = await API.getHealth();
    await loadAvailableModels();
  } catch (err) {
    console.error("Health check error:", err);
  }
}

async function loadAvailableModels() {
  try {
    const data = await API.getModels();
    state.modelsData = data.models || [];
    populateModelDropdown(state.modelsData);

    // Check pull status in case a download is active
    if (data.pull_status && data.pull_status.status === "downloading") {
      openPullModelModal();
      startProgressPolling();
    }
  } catch (err) {
    console.warn("Could not load dynamic models, using default:", err);
  }
}

function populateModelDropdown(models) {
  if (!DOM.modelSelect) return;
  const currentVal = DOM.modelSelect.value;
  DOM.modelSelect.innerHTML = "";

  const is3bInstalled = models.some(m => m.id === "ari-assistant-3b" && m.installed);
  const is15bInstalled = models.some(m => m.id === "ari-assistant-1.5b" && m.installed);

  models.forEach((m) => {
    const opt = document.createElement("option");
    opt.value = m.id;
    let label = m.name;
    if (m.installed) {
      label += ` (${m.size_label} • Ready)`;
    } else {
      label += ` (${m.size_label} • Download Needed)`;
    }
    opt.textContent = label;
    DOM.modelSelect.appendChild(opt);
  });

  // Default to 3B if installed, unless user explicitly selected another model
  if (!state.userSelectedModel && is3bInstalled) {
    DOM.modelSelect.value = "ari-assistant-3b";
  } else if (currentVal && Array.from(DOM.modelSelect.options).some(o => o.value === currentVal)) {
    DOM.modelSelect.value = currentVal;
  } else if (is3bInstalled) {
    DOM.modelSelect.value = "ari-assistant-3b";
  } else if (is15bInstalled) {
    DOM.modelSelect.value = "ari-assistant-1.5b";
  }

  // Update header Pull button
  if (DOM.pullModelBtn) {
    if (!is3bInstalled) {
      DOM.pullModelBtn.classList.remove("hidden");
      if (DOM.pullModelBtnText) DOM.pullModelBtnText.textContent = "Pull Ari 3B (1.9 GB)";
    } else {
      DOM.pullModelBtn.classList.add("hidden");
    }
  }
}

async function handleModelSelectChange() {
  state.userSelectedModel = true;
  const selectedModelId = DOM.modelSelect.value;
  const modelInfo = state.modelsData.find(m => m.id === selectedModelId);

  if (selectedModelId === "ari-assistant-3b" && (!modelInfo || !modelInfo.installed)) {
    // Model not yet installed on disk! Prompt download modal immediately
    openPullModelModal(selectedModelId);
    // Keep dropdown on currently installed model until download completes
    DOM.modelSelect.value = "ari-assistant-1.5b";
    return;
  }

  // Model is installed: switch active engine
  try {
    await API.switchModel(selectedModelId);
  } catch (err) {
    console.error("Failed to switch model:", err);
  }
}

function openPullModelModal(modelId = "ari-assistant-3b") {
  if (!DOM.modelPullModal) return;
  DOM.modelPullModal.classList.remove("hidden");
}

function closePullModelModal() {
  if (!DOM.modelPullModal) return;
  DOM.modelPullModal.classList.add("hidden");
}

async function handleStartPull() {
  try {
    DOM.startPullBtn.disabled = true;
    DOM.startPullBtn.classList.add("opacity-50");
    DOM.cancelPullBtn.classList.remove("hidden");
    DOM.pullProgressSection.classList.remove("hidden");
    DOM.pullStatusLabel.textContent = "Connecting to Hugging Face CDN...";

    const res = await API.pullModel("ari-assistant-3b");
    if (!res.ok && res.already_installed) {
      DOM.pullStatusLabel.textContent = "Model already installed!";
      setTimeout(() => {
        closePullModelModal();
        loadAvailableModels();
      }, 1000);
      return;
    }

    startProgressPolling();
  } catch (err) {
    DOM.pullStatusLabel.textContent = `Error: ${err.message || err}`;
    DOM.startPullBtn.disabled = false;
    DOM.startPullBtn.classList.remove("opacity-50");
  }
}

function startProgressPolling() {
  if (state.modelPullTimer) clearInterval(state.modelPullTimer);

  DOM.pullProgressSection.classList.remove("hidden");
  DOM.cancelPullBtn.classList.remove("hidden");
  DOM.startPullBtn.classList.add("hidden");

  state.modelPullTimer = setInterval(async () => {
    try {
      const status = await API.getPullStatus();
      if (!status) return;

      if (status.status === "downloading") {
        const pct = status.percent || 0;
        DOM.pullProgressBar.style.width = `${pct}%`;
        DOM.pullPercentLabel.textContent = `${pct}%`;
        const mbDone = Math.round(status.bytes_downloaded / (1024 * 1024));
        const mbTotal = Math.round(status.total_bytes / (1024 * 1024));
        DOM.pullBytesLabel.textContent = `${mbDone} MB / ${mbTotal} MB`;
        DOM.pullSpeedLabel.textContent = `${status.speed_mbps || 0.0} MB/s`;

        const eta = status.eta_seconds || 0;
        if (eta > 60) {
          DOM.pullEtaLabel.textContent = `ETA: ~${Math.ceil(eta / 60)} min remaining`;
        } else if (eta > 0) {
          DOM.pullEtaLabel.textContent = `ETA: ~${eta} sec remaining`;
        } else {
          DOM.pullEtaLabel.textContent = "Estimating speed...";
        }
        DOM.pullStatusLabel.textContent = "Streaming model weights...";
      } else if (status.status === "completed") {
        clearInterval(state.modelPullTimer);
        state.modelPullTimer = null;
        DOM.pullProgressBar.style.width = "100%";
        DOM.pullPercentLabel.textContent = "100%";
        DOM.pullStatusLabel.textContent = "Download complete! Initializing Ari 3B...";
        DOM.pullEtaLabel.textContent = "Ready!";

        setTimeout(async () => {
          closePullModelModal();
          DOM.startPullBtn.classList.remove("hidden");
          DOM.startPullBtn.disabled = false;
          DOM.startPullBtn.classList.remove("opacity-50");
          DOM.cancelPullBtn.classList.add("hidden");
          DOM.pullProgressSection.classList.add("hidden");
          await loadAvailableModels();
          // Switch to Ari 3B
          if (DOM.modelSelect) {
            DOM.modelSelect.value = "ari-assistant-3b";
            await API.switchModel("ari-assistant-3b");
          }
        }, 1500);
      } else if (status.status === "error" || status.status === "cancelled") {
        clearInterval(state.modelPullTimer);
        state.modelPullTimer = null;
        DOM.pullStatusLabel.textContent = status.message || "Download stopped.";
        DOM.startPullBtn.classList.remove("hidden");
        DOM.startPullBtn.disabled = false;
        DOM.startPullBtn.classList.remove("opacity-50");
        DOM.cancelPullBtn.classList.add("hidden");
      }
    } catch (err) {
      console.warn("Pull status poll error:", err);
    }
  }, 750);
}

async function handleCancelPull() {
  try {
    DOM.pullStatusLabel.textContent = "Cancelling...";
    await API.cancelPull();
  } catch (err) {
    console.error("Cancel pull error:", err);
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

              // Smoothly transition from thinking filler to active streaming
              const filler = botBubble.querySelector(".assistant-status-filler");
              if (filler) filler.remove();
              bodyEl.classList.remove("hidden");

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
                bodyEl.innerHTML = marked.parse(fullResponse) + `<span class="cursor-blink"></span>`;
              }
              scrollToBottom();
            }

            // 3. Error
            if (data.type === "error") {
              const filler = botBubble.querySelector(".assistant-status-filler");
              if (filler) filler.remove();
              bodyEl.classList.remove("hidden");
              bodyEl.innerHTML += `<div class="text-xs text-rose-400 mt-2 p-2 bg-rose-500/10 rounded-lg">${escapeHtml(data.error)}</div>`;
            }

            // 4. Finished
            if (data.type === "done") {
              const filler = botBubble.querySelector(".assistant-status-filler");
              if (filler) filler.remove();
              bodyEl.classList.remove("hidden");

              if (data.clean_content) {
                fullResponse = data.clean_content;
              } else {
                fullResponse = stripClientRepeats(fullResponse);
              }
              bodyEl.innerHTML = marked.parse(fullResponse);
              decorateCodeBlocks(bodyEl);
              attachMessageActionBar(botBubble, fullResponse, text);
              updateConversationTitleAfterSend(text);
            }
          } catch (e) {
            console.error("SSE parse error:", e);
          }
        }
      }
    }
  } catch (err) {
    const filler = botBubble.querySelector(".assistant-status-filler");
    if (filler) filler.remove();
    bodyEl.classList.remove("hidden");

    if (err.name === "AbortError" || err.message?.includes("aborted")) {
      // Stopped cleanly by user
      if (fullResponse) {
        fullResponse = stripClientRepeats(fullResponse);
        bodyEl.innerHTML = marked.parse(fullResponse);
        attachMessageActionBar(botBubble, fullResponse, text);
      }
    } else {
      bodyEl.innerHTML += `<div class="text-xs text-rose-400 mt-2 p-2 bg-rose-500/10 rounded-lg">Error: ${escapeHtml(err.message)}</div>`;
    }
  } finally {
    setGenerationState(false);
    state.abortController = null;
    const filler = botBubble.querySelector(".assistant-status-filler");
    if (filler) filler.remove();
    bodyEl.classList.remove("hidden");
    const blinker = bodyEl.querySelector(".cursor-blink");
    if (blinker) blinker.remove();
    decorateCodeBlocks(bodyEl);
    if (fullResponse) {
      attachMessageActionBar(botBubble, fullResponse, text);
    }
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

  let spinnerText = "Thinking...";
  let spinnerIcon = `
    <span class="thinking-loader">
      <span class="thinking-dot"></span>
      <span class="thinking-dot"></span>
      <span class="thinking-dot"></span>
    </span>`;

  if (state.webSearch) {
    spinnerIcon = `<i class="fa-solid fa-compass fa-spin text-indigo-400 text-xs"></i>`;
    spinnerText = "Searching the web & gathering sources...";
  } else if (state.reasoningMode) {
    spinnerIcon = `<i class="fa-solid fa-brain text-purple-400 animate-pulse text-xs"></i>`;
    spinnerText = "Reasoning step-by-step...";
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
        <span class="text-[10px] text-zinc-400">Just now</span>
      </div>
      <div class="sources-container hidden"></div>
      <details class="reasoning-box hidden">
        <summary><i class="fa-solid fa-brain text-xs"></i> Thought process</summary>
        <div class="reasoning-text"></div>
      </details>
      <div class="assistant-status-filler">
        ${spinnerIcon}
        <span class="status-filler-text">${spinnerText}</span>
      </div>
      <div class="markdown-body text-sm select-text pt-0.5 hidden">
        <span class="cursor-blink"></span>
      </div>
    </div>
  `;
  return el;
}

function attachMessageActionBar(container, markdownText, userPrompt) {
  if (!container) return;
  if (container.querySelector(".msg-action-bar")) return; // prevent duplicate bars

  const currentModel = DOM.modelSelect?.value?.includes("3b") ? "Ari 3B • Instruct" : "Ari 1.5B • Fast";
  const actionBar = document.createElement("div");
  actionBar.className = "msg-action-bar";
  actionBar.innerHTML = `
    <button class="msg-action-btn copy-msg-btn" title="Copy response">
      <i class="fa-regular fa-copy text-xs"></i>
      <span class="text-[11px]">Copy</span>
    </button>
    ${userPrompt ? `
    <button class="msg-action-btn regen-msg-btn" title="Regenerate response">
      <i class="fa-solid fa-arrows-rotate text-xs"></i>
      <span class="text-[11px]">Regenerate</span>
    </button>` : ""}
    <button class="msg-action-btn feedback-like-btn" title="Good response">
      <i class="fa-regular fa-thumbs-up text-xs"></i>
    </button>
    <button class="msg-action-btn feedback-dislike-btn" title="Bad response">
      <i class="fa-regular fa-thumbs-down text-xs"></i>
    </button>
    <span class="text-[10px] text-zinc-500 font-mono ml-auto tracking-wider">${currentModel}</span>
  `;

  // Copy handler
  const copyBtn = actionBar.querySelector(".copy-msg-btn");
  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      navigator.clipboard.writeText(markdownText);
      copyBtn.innerHTML = `<i class="fa-solid fa-check text-emerald-400 text-xs"></i><span class="text-[11px] text-emerald-400 font-medium">Copied!</span>`;
      setTimeout(() => {
        copyBtn.innerHTML = `<i class="fa-regular fa-copy text-xs"></i><span class="text-[11px]">Copy</span>`;
      }, 2000);
    });
  }

  // Regenerate handler
  const regenBtn = actionBar.querySelector(".regen-msg-btn");
  if (regenBtn && userPrompt) {
    regenBtn.addEventListener("click", () => {
      DOM.messageInput.value = userPrompt;
      handleSendMessage();
    });
  }

  // Feedback like/dislike handlers
  const likeBtn = actionBar.querySelector(".feedback-like-btn");
  const dislikeBtn = actionBar.querySelector(".feedback-dislike-btn");
  if (likeBtn && dislikeBtn) {
    likeBtn.addEventListener("click", () => {
      likeBtn.classList.toggle("active");
      dislikeBtn.classList.remove("active");
      likeBtn.querySelector("i").className = likeBtn.classList.contains("active") ? "fa-solid fa-thumbs-up text-xs" : "fa-regular fa-thumbs-up text-xs";
    });
    dislikeBtn.addEventListener("click", () => {
      dislikeBtn.classList.toggle("active");
      likeBtn.classList.remove("active");
      dislikeBtn.querySelector("i").className = dislikeBtn.classList.contains("active") ? "fa-solid fa-thumbs-down text-xs" : "fa-regular fa-thumbs-down text-xs";
    });
  }

  const contentCol = container.querySelector(".flex-1") || container;
  contentCol.appendChild(actionBar);
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
    attachMessageActionBar(el, msg.content || "", "");
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

  // Render LaTeX math formulas if KaTeX is loaded
  if (window.renderMathInElement) {
    try {
      renderMathInElement(container, {
        delimiters: [
          { left: "$$", right: "$$", display: true },
          { left: "$", right: "$", display: false },
          { left: "\\[", right: "\\]", display: true },
          { left: "\\(", right: "\\)", display: false }
        ],
        throwOnError: false
      });
    } catch (e) {
      console.warn("KaTeX render error:", e);
    }
  }
}

function scrollToBottom() {
  DOM.messagesContainer.scrollTop = DOM.messagesContainer.scrollHeight;
}

/**
 * Memory Management & Autonomous Personalization
 */
function showMemoryToast(mem) {
  if (!DOM.memoryToastContainer) return;

  const toast = document.createElement("div");
  toast.className =
    "pointer-events-auto flex items-center gap-2.5 px-3 py-2 rounded-lg bg-zinc-900 border border-indigo-500/30 text-xs shadow-xl animate-in slide-in-from-top-2 fade-in transition-all duration-300";

  toast.innerHTML = `
    <div class="w-6 h-6 rounded-md bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-xs shrink-0">
      <i class="fa-solid fa-brain"></i>
    </div>
    <div class="flex flex-col min-w-0 pr-1 cursor-pointer" title="Click to view all memories">
      <span class="text-[10px] text-zinc-400 font-medium">Memory Updated</span>
      <span class="text-zinc-200 font-medium truncate max-w-[240px]">${escapeHtml(mem.key)}: ${escapeHtml(mem.value)}</span>
    </div>
    <button class="text-zinc-500 hover:text-zinc-300 p-1 text-xs shrink-0">
      <i class="fa-solid fa-xmark"></i>
    </button>
  `;

  // Click on toast body opens memory viewer
  toast.querySelector("div.cursor-pointer")?.addEventListener("click", () => {
    openMemoryModal();
  });

  // Close button
  const closeBtn = toast.querySelector("button");
  closeBtn?.addEventListener("click", (e) => {
    e.stopPropagation();
    toast.classList.add("opacity-0", "-translate-y-2");
    setTimeout(() => toast.remove(), 250);
  });

  DOM.memoryToastContainer.appendChild(toast);

  // Auto-dismiss after 4 seconds
  setTimeout(() => {
    if (toast.isConnected) {
      toast.classList.add("opacity-0", "-translate-y-2");
      setTimeout(() => toast.remove(), 250);
    }
  }, 4000);
}

async function openMemoryModal() {
  DOM.memoryModal.classList.remove("hidden");
  await loadMemories();
}

function closeMemoryModal() {
  DOM.memoryModal.classList.add("hidden");
}

function getMemoryCategoryIcon(cat) {
  const c = (cat || "").toLowerCase();
  if (c === "profile") return "fa-user";
  if (c === "work" || c === "tech") return "fa-code";
  if (c === "preference" || c === "instruction") return "fa-sliders";
  if (c === "project") return "fa-rocket";
  return "fa-heart";
}

async function loadMemories() {
  DOM.memoriesContainer.innerHTML = `<div class="text-center py-6 text-xs text-zinc-500"><i class="fa-solid fa-spinner fa-spin mr-1.5"></i> Loading memories...</div>`;
  try {
    const list = await API.getMemories();
    if (DOM.memoryCountBadge) {
      DOM.memoryCountBadge.textContent = `${list.length} ${list.length === 1 ? 'Memory' : 'Memories'}`;
    }

    if (list.length === 0) {
      DOM.memoriesContainer.innerHTML = `
        <div class="text-center py-8 px-4 space-y-2">
          <div class="w-10 h-10 mx-auto rounded-full bg-zinc-800/60 flex items-center justify-center text-zinc-500">
            <i class="fa-solid fa-brain text-sm"></i>
          </div>
          <p class="text-xs font-medium text-zinc-300">No memories stored yet</p>
          <p class="text-[11px] text-zinc-500 max-w-xs mx-auto">
            Just chat naturally! Tell Ari about your role, favorite languages, or instructions like <em>"Keep code concise"</em>, and Ari will learn them automatically.
          </p>
        </div>`;
      return;
    }

    DOM.memoriesContainer.innerHTML = list
      .map((m) => {
        const icon = getMemoryCategoryIcon(m.category);
        return `
        <div class="flex items-start justify-between p-3 rounded-xl border card-minimal text-xs gap-3 transition-colors group" style="border-color: var(--border-subtle)">
          <div class="flex items-start gap-2.5 min-w-0">
            <div class="w-6 h-6 rounded-md bg-indigo-500/10 text-indigo-400 flex items-center justify-center text-[11px] shrink-0 mt-0.5">
              <i class="fa-solid ${icon}"></i>
            </div>
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="font-medium text-zinc-200">${escapeHtml(m.key)}</span>
                <span class="text-[9px] uppercase tracking-wider text-zinc-500 font-mono px-1.5 py-0.5 rounded bg-zinc-800/50">${escapeHtml(m.category || 'fact')}</span>
              </div>
              <p class="text-zinc-400 text-[11px] mt-0.5 leading-relaxed break-words">${escapeHtml(m.value)}</p>
            </div>
          </div>
          <button onclick="handleDeleteMemory(${m.id})" title="Forget this memory" class="text-zinc-500 hover:text-rose-400 p-1.5 rounded-md transition-colors opacity-70 group-hover:opacity-100 shrink-0">
            <i class="fa-solid fa-trash-can text-[11px]"></i>
          </button>
        </div>`;
      })
      .join("");
  } catch (err) {
    DOM.memoriesContainer.innerHTML = `<p class="text-xs text-rose-400 text-center py-4">Error loading memories: ${err.message}</p>`;
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
  if (confirm("Are you sure you want Ari to forget all stored memories?")) {
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
  cleaned = cleaned.replace(/^```(?:markdown|md)?\s*\n([\s\S]*?)\n```\s*$/i, "$1");

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
    "Answered."
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
    /\n(?:User|Human|Question):\s*/i,
    /\n###\s*(?:User|Human|Prompt)/i,
    /<\|im_start\|>/i,
    /<\|im_end\|>/i
  ];
  for (const pat of simTurnPatterns) {
    const m = cleaned.slice(20).search(pat);
    if (m !== -1) {
      cleaned = cleaned.slice(0, 20 + m);
    }
  }

  // Universal paragraph deduplication
  const paras = cleaned.split("\n");
  const seenParas = new Set();
  const keptParas = [];
  for (const p of paras) {
    const pClean = p.trim();
    if (pClean.length >= 35) {
      const norm = pClean.replace(/[^\w\s]/g, "").toLowerCase();
      if (seenParas.has(norm)) {
        break;
      }
      seenParas.add(norm);
    }
    keptParas.push(p);
  }
  cleaned = keptParas.join("\n");

  // Strip cyclical loops (loops >= 3 chars repeated 3+ times at end)
  if (cleaned.length >= 12) {
    for (let l = 3; l <= 50; l++) {
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

/**
 * Auto-Updater Client Logic
 */
async function checkAppUpdates(silent = true) {
  try {
    const res = await API.checkUpdate();
    state.updateData = res;
    if (res && res.update_available) {
      // Show navbar update banner
      if (DOM.updateBannerBtn) {
        DOM.updateBannerBtn.classList.remove("hidden");
        if (DOM.updateBannerText) {
          DOM.updateBannerText.textContent = `Update v${res.latest_version}`;
        }
      }
      if (DOM.sidebarUpdateDot) {
        DOM.sidebarUpdateDot.classList.remove("hidden");
      }
      if (!silent) {
        openUpdateModal();
      }
    } else {
      if (!silent) {
        alert(`You're up to date! Ari Chat v${res.current_version || "1.0.0"} is the latest version.`);
      }
      if (DOM.sidebarUpdateDot) {
        DOM.sidebarUpdateDot.classList.add("hidden");
      }
    }
  } catch (err) {
    if (!silent) {
      alert(`Could not check for updates: ${err.message || err}`);
    }
  }
}

function openUpdateModal() {
  if (!DOM.updateModal) return;
  DOM.updateModal.classList.remove("hidden");

  const data = state.updateData || {};
  if (DOM.updateModalTitle) {
    DOM.updateModalTitle.textContent = data.release_title || `Ari Chat Update`;
  }
  if (DOM.updateModalSubtitle) {
    DOM.updateModalSubtitle.textContent = `Version ${data.latest_version || "Latest"} is available`;
  }
  if (DOM.updateNotesText) {
    DOM.updateNotesText.textContent = data.release_notes || "Includes performance enhancements and fixes.";
  }
}

function closeUpdateModal() {
  if (!DOM.updateModal) return;
  DOM.updateModal.classList.add("hidden");
}

async function handleStartUpdate() {
  try {
    DOM.startUpdateBtn.disabled = true;
    DOM.startUpdateBtn.classList.add("opacity-50");
    DOM.cancelUpdateBtn.classList.remove("hidden");
    DOM.updateProgressSection.classList.remove("hidden");
    DOM.updateStatusLabel.textContent = "Connecting to GitHub Releases...";

    const res = await API.startUpdate();
    if (!res.ok) {
      throw new Error(res.message || "Could not start download");
    }

    startUpdatePolling();
  } catch (err) {
    DOM.updateStatusLabel.textContent = `Error: ${err.message || err}`;
    DOM.startUpdateBtn.disabled = false;
    DOM.startUpdateBtn.classList.remove("opacity-50");
  }
}

function startUpdatePolling() {
  if (state.updatePollingInterval) clearInterval(state.updatePollingInterval);

  DOM.updateProgressSection.classList.remove("hidden");
  DOM.cancelUpdateBtn.classList.remove("hidden");
  DOM.startUpdateBtn.classList.add("hidden");

  state.updatePollingInterval = setInterval(async () => {
    try {
      const status = await API.getUpdateStatus();
      if (!status) return;

      if (status.status === "downloading") {
        const pct = status.percent || 0;
        DOM.updateProgressBar.style.width = `${pct}%`;
        DOM.updatePercentLabel.textContent = `${pct}%`;
        DOM.updateSpeedLabel.textContent = `${status.speed_mbps || 0.0} MB/s`;

        const eta = status.eta_seconds || 0;
        if (eta > 60) {
          DOM.updateEtaLabel.textContent = `ETA: ~${Math.ceil(eta / 60)} min`;
        } else if (eta > 0) {
          DOM.updateEtaLabel.textContent = `ETA: ~${eta} sec`;
        } else {
          DOM.updateEtaLabel.textContent = "Estimating speed...";
        }
        DOM.updateStatusLabel.textContent = "Downloading installer...";
      } else if (status.status === "ready_to_install") {
        clearInterval(state.updatePollingInterval);
        state.updatePollingInterval = null;

        DOM.updateProgressBar.style.width = "100%";
        DOM.updatePercentLabel.textContent = "100%";
        DOM.updateStatusLabel.textContent = "Update downloaded! Ready to install.";
        DOM.updateEtaLabel.textContent = "Ready!";

        DOM.cancelUpdateBtn.classList.add("hidden");
        DOM.applyUpdateBtn.classList.remove("hidden");
      } else if (status.status === "error") {
        clearInterval(state.updatePollingInterval);
        state.updatePollingInterval = null;
        DOM.updateStatusLabel.textContent = status.message || "Download failed.";
        DOM.startUpdateBtn.classList.remove("hidden");
        DOM.startUpdateBtn.disabled = false;
        DOM.startUpdateBtn.classList.remove("opacity-50");
      }
    } catch (e) {
      console.warn("Update status polling error:", e);
    }
  }, 800);
}

async function handleCancelUpdate() {
  try {
    await API.cancelUpdate();
    if (state.updatePollingInterval) {
      clearInterval(state.updatePollingInterval);
      state.updatePollingInterval = null;
    }
    DOM.updateProgressSection.classList.add("hidden");
    DOM.cancelUpdateBtn.classList.add("hidden");
    DOM.startUpdateBtn.classList.remove("hidden");
    DOM.startUpdateBtn.disabled = false;
    DOM.startUpdateBtn.classList.remove("opacity-50");
  } catch (err) {
    console.error("Failed to cancel update:", err);
  }
}

async function handleApplyUpdate() {
  try {
    DOM.applyUpdateBtn.disabled = true;
    DOM.applyUpdateBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Restarting...`;
    await API.applyUpdate();
  } catch (err) {
    alert("Error applying update: " + (err.message || err));
    DOM.applyUpdateBtn.disabled = false;
    DOM.applyUpdateBtn.textContent = "Restart & Apply Update";
  }
}

