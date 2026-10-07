/**
 * Aegis Enterprise Knowledge Copilot — Frontend Application Engine
 * Handles real-time SSE streaming, multi-agent telemetry, citation drawers,
 * and live observability updates.
 */

document.addEventListener("DOMContentLoaded", () => {
  // DOM Elements
  const chatMessages = document.getElementById("chat-messages");
  const chatForm = document.getElementById("chat-form");
  const chatInput = document.getElementById("chat-input-field");
  const btnSubmit = document.getElementById("btn-submit-query");
  const toggleStream = document.getElementById("toggle-stream");
  const toggleBypassCache = document.getElementById("toggle-bypass-cache");
  const typingStatusHint = document.getElementById("typing-status-hint");
  const welcomeHero = document.getElementById("welcome-hero");

  // Telemetry DOM Elements
  const valTotalQueries = document.getElementById("val-total-queries");
  const valAvgLatency = document.getElementById("val-avg-latency");
  const valTotalTokens = document.getElementById("val-total-tokens");
  const valTotalCost = document.getElementById("val-total-cost");
  const cacheHitPercent = document.getElementById("cache-hit-percent");
  const cacheHitBar = document.getElementById("cache-hit-bar");
  const cacheHitsCount = document.getElementById("cache-hits-count");
  const cacheMissesCount = document.getElementById("cache-misses-count");
  const cacheBackendBadge = document.getElementById("cache-backend-badge");
  const btnClearCache = document.getElementById("btn-clear-cache");
  const btnRefreshTelemetry = document.getElementById("btn-refresh-telemetry");

  // Health Elements
  const healthPostgres = document.getElementById("health-postgres-status");
  const healthQdrant = document.getElementById("health-qdrant-status");
  const healthCache = document.getElementById("health-cache-status");
  const healthJaeger = document.getElementById("health-jaeger-status");

  // Distribution Bars
  const pctRouteRag = document.getElementById("pct-route-rag");
  const barRouteRag = document.getElementById("bar-route-rag");
  const pctRouteSql = document.getElementById("pct-route-sql");
  const barRouteSql = document.getElementById("bar-route-sql");
  const pctRouteTool = document.getElementById("pct-route-tool");
  const barRouteTool = document.getElementById("bar-route-tool");
  const pctRouteBlocked = document.getElementById("pct-route-blocked");
  const barRouteBlocked = document.getElementById("bar-route-blocked");

  // Quick Prompt Chips
  document.querySelectorAll(".prompt-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const query = chip.getAttribute("data-query");
      if (query) {
        chatInput.value = query;
        chatForm.dispatchEvent(new Event("submit"));
      }
    });
  });

  // Clear Cache Button
  if (btnClearCache) {
    btnClearCache.addEventListener("click", async () => {
      try {
        btnClearCache.disabled = true;
        btnClearCache.style.opacity = "0.5";
        const res = await fetch("/api/v1/cache/clear", { method: "POST" });
        if (res.ok) {
          fetchTelemetry();
          showNotification("Query cache flushed successfully");
        }
      } catch (err) {
        console.error("Failed to clear cache:", err);
      } finally {
        btnClearCache.disabled = false;
        btnClearCache.style.opacity = "1";
      }
    });
  }

  // Refresh Telemetry Button
  if (btnRefreshTelemetry) {
    btnRefreshTelemetry.addEventListener("click", () => {
      fetchTelemetry();
      fetchHealth();
    });
  }

  // Fetch Live Telemetry
  async function fetchTelemetry() {
    try {
      const res = await fetch("/api/v1/metrics");
      if (!res.ok) return;
      const data = await res.json();
      const obs = data.observability || {};
      const cache = data.cache || {};

      // Observability stats
      if (valTotalQueries) valTotalQueries.textContent = obs.total_queries || 0;
      if (valAvgLatency) valAvgLatency.textContent = `${Math.round(obs.avg_latency_ms || 0)}ms`;
      if (valTotalTokens) valTotalTokens.textContent = (obs.total_tokens_consumed || 0).toLocaleString();
      if (valTotalCost) valTotalCost.textContent = `$${(obs.total_cost_usd || 0).toFixed(4)}`;

      // Cache stats
      const hitRatio = cache.hit_ratio !== undefined ? Math.round(cache.hit_ratio * 100) : 0;
      if (cacheHitPercent) cacheHitPercent.textContent = `${hitRatio}%`;
      if (cacheHitBar) cacheHitBar.style.width = `${hitRatio}%`;
      if (cacheHitsCount) cacheHitsCount.textContent = cache.hits || 0;
      if (cacheMissesCount) cacheMissesCount.textContent = cache.misses || 0;
      if (cacheBackendBadge && cache.backend) {
        cacheBackendBadge.textContent = cache.backend.toUpperCase();
      }

      // Routing Distribution
      const dist = obs.route_distribution || {};
      const totalRoutes = obs.total_queries || 1;
      updateRouteBar(dist.rag || 0, totalRoutes, pctRouteRag, barRouteRag);
      updateRouteBar(dist.sql || 0, totalRoutes, pctRouteSql, barRouteSql);
      updateRouteBar(dist.tool || 0, totalRoutes, pctRouteTool, barRouteTool);
      updateRouteBar(dist.blocked || 0, totalRoutes, pctRouteBlocked, barRouteBlocked);
    } catch (err) {
      console.warn("Could not retrieve system telemetry:", err);
    }
  }

  function updateRouteBar(count, total, textEl, barEl) {
    if (!textEl || !barEl) return;
    const pct = total > 0 ? Math.round((count / total) * 100) : 0;
    textEl.textContent = `${pct}% (${count})`;
    barEl.style.width = `${pct}%`;
  }

  // Fetch Subsystem Health
  async function fetchHealth() {
    try {
      const res = await fetch("/api/v1/health");
      if (!res.ok) return;
      const data = await res.json();
      const comps = data.components || {};

      if (healthPostgres) {
        const isPgOk = comps.database_postgresql === "connected";
        healthPostgres.textContent = isPgOk ? "CONNECTED" : "OFFLINE";
        healthPostgres.className = `health-status-tag ${isPgOk ? "ok" : "fallback"}`;
      }

      if (healthQdrant) {
        const isQdOk = comps.vector_store_qdrant === "ready";
        healthQdrant.textContent = isQdOk ? "READY" : "IN-MEMORY";
        healthQdrant.className = `health-status-tag ${isQdOk ? "ok" : "fallback"}`;
      }

      if (healthCache) {
        healthCache.textContent = (comps.cache_layer || "active").toUpperCase();
        healthCache.className = "health-status-tag ok";
      }

      if (healthJaeger) {
        const jaegerStatus = comps.jaeger_tracing || "unreachable";
        if (jaegerStatus === "ready") {
          healthJaeger.textContent = "READY";
          healthJaeger.className = "health-status-tag ok";
        } else if (jaegerStatus === "disabled") {
          healthJaeger.textContent = "DISABLED";
          healthJaeger.className = "health-status-tag";
        } else {
          healthJaeger.textContent = "STANDBY";
          healthJaeger.className = "health-status-tag fallback";
        }
      }
    } catch (err) {
      console.warn("Health check failed:", err);
    }
  }

  // Form Submit Handler
  chatForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = chatInput.value.trim();
    if (!query) return;

    // Hide welcome hero on first query
    if (welcomeHero) welcomeHero.style.display = "none";

    // Disable input while executing
    chatInput.value = "";
    chatInput.disabled = true;
    btnSubmit.disabled = true;
    typingStatusHint.textContent = "Agent executing...";

    // 1. Render User Message Row
    appendUserMessage(query);

    const isStreaming = toggleStream.checked;
    const bypassCache = toggleBypassCache.checked;

    if (isStreaming) {
      await handleStreamingQuery(query, bypassCache);
    } else {
      await handleSyncQuery(query, bypassCache);
    }

    // Re-enable input
    chatInput.disabled = false;
    btnSubmit.disabled = false;
    chatInput.focus();
    typingStatusHint.textContent = "Ready";

    // Refresh telemetry
    fetchTelemetry();
  });

  // Render User Message
  function appendUserMessage(text) {
    const row = document.createElement("div");
    row.className = "message-row user";
    row.innerHTML = `
      <div class="avatar user">U</div>
      <div class="message-body">
        <div class="user-bubble">${escapeHtml(text)}</div>
      </div>
    `;
    chatMessages.appendChild(row);
    scrollToBottom();
  }

  // Handle Synchronous Query
  async function handleSyncQuery(query, bypassCache) {
    const agentRow = createAgentMessageRow();
    chatMessages.appendChild(agentRow);
    const contentEl = agentRow.querySelector(".agent-content-area");
    const metaHeader = agentRow.querySelector(".agent-meta-header");
    const telemetryFooter = agentRow.querySelector(".message-telemetry");

    // Add temporary loading dots
    contentEl.innerHTML = `
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    `;
    scrollToBottom();

    try {
      const res = await fetch("/api/v1/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, bypass_cache: bypassCache }),
      });

      if (!res.ok) {
        throw new Error(`Server returned error HTTP ${res.status}`);
      }

      const data = await res.json();

      // Render Meta Badges
      renderMetaBadges(metaHeader, data.route, data.cached, data.guardrail_status);

      // Render Body Content
      contentEl.innerHTML = formatMarkdown(data.response);

      // Render SQL query if present
      if (data.sql) {
        renderSqlBox(contentEl, data.sql);
      }

      // Render Citations & Sources
      if (data.sources && data.sources.length > 0) {
        renderCitations(contentEl, data.citations || [], data.sources);
      }

      // Render Telemetry
      renderTelemetryFooter(
        telemetryFooter,
        data.trace_id,
        data.latency_ms,
        data.tokens_used,
        data.cached
      );
    } catch (err) {
      contentEl.innerHTML = `<span style="color: #FB7185;">Error executing query: ${escapeHtml(err.message)}</span>`;
    } finally {
      scrollToBottom();
    }
  }

  // Handle SSE Streaming Query
  async function handleStreamingQuery(query, bypassCache) {
    const agentRow = createAgentMessageRow();
    chatMessages.appendChild(agentRow);
    const contentEl = agentRow.querySelector(".agent-content-area");
    const metaHeader = agentRow.querySelector(".agent-meta-header");
    const telemetryFooter = agentRow.querySelector(".message-telemetry");

    contentEl.innerHTML = `
      <div class="typing-indicator" id="current-stream-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    `;
    scrollToBottom();

    let fullText = "";
    let routeCaptured = "direct";
    let isCached = false;

    try {
      const response = await fetch("/api/v1/query/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, bypass_cache: bypassCache }),
      });

      // Render's proxy can return 502/503/504 when the agent takes > 55s.
      // Fall back to the non-streaming /query endpoint to still get an answer.
      if (!response.ok && [502, 503, 504].includes(response.status)) {
        typingStatusHint.textContent = "Switching to direct mode...";
        const fallback = await fetch("/api/v1/query", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, bypass_cache: bypassCache }),
        });
        if (!fallback.ok) throw new Error(`Query failed with status: ${fallback.status}`);
        const data = await fallback.json();

        routeCaptured = data.route || "direct";
        renderMetaBadges(metaHeader, routeCaptured, !!data.cached, data.guardrail_status || "passed");

        const indicator = contentEl.querySelector("#current-stream-indicator");
        if (indicator) indicator.remove();
        contentEl.innerHTML = formatMarkdown(data.response || "");
        if (data.citations && data.citations.length > 0) renderCitationChips(contentEl, data.citations);
        renderTelemetryFooter(telemetryFooter, data.trace_id, data.latency_ms, data.tokens_used, !!data.cached);
        scrollToBottom();
        return;
      }

      if (!response.ok) {
        throw new Error(`Streaming failed with status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const events = buffer.split("\n\n");
        buffer = events.pop(); // Retain incomplete chunk

        for (const eventStr of events) {
          if (!eventStr.trim()) continue;
          // Skip SSE comment lines (keepalive pings from the server)
          if (eventStr.trimStart().startsWith(":")) continue;

          const lines = eventStr.split("\n");
          let eventType = "";
          let eventDataRaw = "";

          for (const line of lines) {
            if (line.startsWith("event: ")) {
              eventType = line.replace("event: ", "").trim();
            } else if (line.startsWith("data: ")) {
              eventDataRaw = line.replace("data: ", "").trim();
            }
          }

          if (!eventDataRaw) continue;
          let parsedData = {};
          try {
            parsedData = JSON.parse(eventDataRaw);
          } catch (e) {
            continue;
          }

          // Handle SSE Events
          if (eventType === "status") {
            typingStatusHint.textContent = parsedData.message || "Executing...";
          } else if (eventType === "route") {
            routeCaptured = parsedData.route || "direct";
            isCached = !!parsedData.cached;
            renderMetaBadges(metaHeader, routeCaptured, isCached, "passed");
          } else if (eventType === "token") {
            // Remove typing indicator on first token
            const ind = contentEl.querySelector("#current-stream-indicator");
            if (ind) ind.remove();

            fullText += parsedData.token || "";
            contentEl.innerHTML = formatMarkdown(fullText);
            scrollToBottom();
          } else if (eventType === "citations") {
            if (parsedData.citations && parsedData.citations.length > 0) {
              renderCitationChips(contentEl, parsedData.citations);
            }
          } else if (eventType === "done") {
            renderTelemetryFooter(
              telemetryFooter,
              parsedData.trace_id,
              parsedData.latency_ms,
              parsedData.tokens_used,
              parsedData.cached
            );
          } else if (eventType === "error") {
            contentEl.innerHTML = `<span style="color: #FB7185;">Error: ${escapeHtml(parsedData.error)}</span>`;
          }
        }
      }
    } catch (err) {
      contentEl.innerHTML = `<span style="color: #FB7185;">Streaming Error: ${escapeHtml(err.message)}</span>`;
    } finally {
      // Ensure typing indicator is removed
      const ind = contentEl.querySelector("#current-stream-indicator");
      if (ind) ind.remove();
      scrollToBottom();
    }
  }

  // Create Empty Agent Message Row Shell
  function createAgentMessageRow() {
    const row = document.createElement("div");
    row.className = "message-row agent";
    row.innerHTML = `
      <div class="avatar agent">AI</div>
      <div class="message-body">
        <div class="agent-bubble">
          <div class="agent-meta-header"></div>
          <div class="agent-content-area"></div>
        </div>
        <div class="message-telemetry"></div>
      </div>
    `;
    return row;
  }

  // Render Metadata Badges
  function renderMetaBadges(headerEl, route, cached, guardrailStatus) {
    headerEl.innerHTML = "";

    // Route Pill
    const routePill = document.createElement("span");
    routePill.className = `route-pill ${route || "direct"}`;
    const routeIcons = {
      rag: "HYBRID RAG",
      sql: "POSTGRES SQL",
      tool: "LIVE TOOL",
      direct: "DIRECT",
      blocked: "GUARDRAIL BLOCKED",
    };
    routePill.textContent = routeIcons[route] || (route || "DIRECT").toUpperCase();
    headerEl.appendChild(routePill);

    // Cache Pill
    const cachePill = document.createElement("span");
    cachePill.className = `cache-pill ${cached ? "hit" : ""}`;
    cachePill.innerHTML = cached ? `Cache Hit` : `Dynamic Compute`;
    headerEl.appendChild(cachePill);

    // Guardrail Status
    if (guardrailStatus === "blocked") {
      const guardPill = document.createElement("span");
      guardPill.className = "route-pill blocked";
      guardPill.textContent = "POLICY INTERCEPTION";
      headerEl.appendChild(guardPill);
    }
  }

  // Render SQL Box
  function renderSqlBox(parentEl, sql) {
    const sqlBox = document.createElement("div");
    sqlBox.className = "sql-box";
    sqlBox.innerHTML = `
      <div class="sql-header">
        <span>GENERATED POSTGRESQL (READ-ONLY)</span>
        <span>VALIDATED</span>
      </div>
      <div class="sql-code">${escapeHtml(sql)}</div>
    `;
    parentEl.appendChild(sqlBox);
  }

  // Render Citations and Source Drawer
  function renderCitations(parentEl, citations, sources) {
    const wrapper = document.createElement("div");
    wrapper.className = "citations-wrapper";
    wrapper.innerHTML = `
      <div class="citations-header">
        <span>VERIFIED CITATIONS (${citations.length || sources.length})</span>
      </div>
      <div class="citation-chips-container"></div>
      <div class="source-preview-box" id="source-preview-${Date.now()}"></div>
    `;

    const chipsContainer = wrapper.querySelector(".citation-chips-container");
    const previewBox = wrapper.querySelector(".source-preview-box");

    sources.forEach((source) => {
      const chip = document.createElement("div");
      chip.className = "citation-chip";
      chip.innerHTML = `
        <span class="citation-source-tag">[Source ${source.source_number || 1}]</span>
        <span class="citation-doc-name">${escapeHtml(source.filename || "document.pdf")} (P.${source.page || 1})</span>
      `;

      chip.addEventListener("click", () => {
        const isCurrent = previewBox.classList.contains("open") && previewBox.getAttribute("data-active") === String(source.source_number);
        if (isCurrent) {
          previewBox.classList.remove("open");
        } else {
          previewBox.setAttribute("data-active", String(source.source_number));
          previewBox.innerHTML = `
            <div style="font-weight: 600; color: #22D3EE; margin-bottom: 4px;">
              [Source ${source.source_number}] ${escapeHtml(source.filename)} — Page ${source.page || "?"}
            </div>
            <div style="color: var(--text-muted); font-size: 0.75rem; margin-bottom: 6px;">
              Chunk ID: ${escapeHtml(source.chunk_id || "N/A")} | Rerank Score: ${source.score ? source.score.toFixed(4) : "N/A"}
            </div>
            <div style="font-size: 0.8rem; line-height: 1.5; color: var(--text-secondary);">
              "${escapeHtml(source.text || source.content || "Passage verified in clinical knowledge base.")}"
            </div>
          `;
          previewBox.classList.add("open");
        }
      });

      chipsContainer.appendChild(chip);
    });

    parentEl.appendChild(wrapper);
  }

  // Render Citation Chips for Streamed Response
  function renderCitationChips(parentEl, citations) {
    let wrapper = parentEl.querySelector(".citations-wrapper");
    if (!wrapper) {
      wrapper = document.createElement("div");
      wrapper.className = "citations-wrapper";
      wrapper.innerHTML = `
        <div class="citations-header">
          <span>GROUNDED CITATIONS</span>
        </div>
        <div class="citation-chips-container"></div>
      `;
      parentEl.appendChild(wrapper);
    }

    const container = wrapper.querySelector(".citation-chips-container");
    container.innerHTML = "";
    citations.forEach((num) => {
      const chip = document.createElement("div");
      chip.className = "citation-chip";
      chip.innerHTML = `<span class="citation-source-tag">[Source ${num}]</span> <span class="citation-doc-name">Verified Document Passage</span>`;
      container.appendChild(chip);
    });
  }

  // Render Message Telemetry Footer
  function renderTelemetryFooter(footerEl, traceId, latencyMs, tokens, cached) {
    if (!footerEl) return;
    const shortTrace = traceId ? traceId.slice(0, 8) : "N/A";
    const latencyFormatted = latencyMs !== undefined ? `${latencyMs}ms` : "<10ms";
    const tokensFormatted = tokens || 0;

    footerEl.innerHTML = `
      <span class="telemetry-item" title="Distributed Trace ID">
        <span>ID:</span> ${shortTrace}
      </span>
      <span>•</span>
      <span class="telemetry-item" title="End-to-End Latency">
        <span>Latency:</span> ${latencyFormatted}
      </span>
      <span>•</span>
      <span class="telemetry-item" title="Token Consumption">
        <span>Tokens:</span> ${tokensFormatted}
      </span>
    `;
  }

  // Helpers
  function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
  }

  function escapeHtml(text) {
    if (!text) return "";
    return String(text)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatMarkdown(text) {
    if (!text) return "";
    let formatted = escapeHtml(text);

    // Bold **text**
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

    // Citations [Source N] highlighting
    formatted = formatted.replace(
      /\[Source\s*(\d+)\]/gi,
      '<span style="color: #22D3EE; font-family: var(--font-mono); font-weight: 700; background: rgba(6, 182, 212, 0.12); padding: 1px 6px; border-radius: 4px; border: 1px solid rgba(6, 182, 212, 0.25);">[Source $1]</span>'
    );

    // Bullet points
    formatted = formatted.replace(/^\s*-\s+(.*)$/gm, '<li style="margin-left: 20px;">$1</li>');
    formatted = formatted.replace(/(<li.*<\/li>)/g, '<ul style="margin: 6px 0;">$1</ul>');

    // Line breaks
    formatted = formatted.replace(/\n\n/g, "<br><br>").replace(/\n/g, "<br>");

    return formatted;
  }

  function showNotification(msg) {
    const toast = document.createElement("div");
    toast.style.cssText = `
      position: fixed;
      bottom: 24px;
      right: 24px;
      background: rgba(16, 185, 129, 0.9);
      color: white;
      padding: 10px 18px;
      border-radius: 8px;
      font-size: 0.85rem;
      font-weight: 600;
      box-shadow: 0 4px 16px rgba(0,0,0,0.4);
      z-index: 1000;
      animation: fadeIn 0.3s ease;
    `;
    toast.textContent = msg;
    document.body.appendChild(toast);
    setTimeout(() => {
      toast.remove();
    }, 2500);
  }

  // ============================================================
  // PDF UPLOAD & DOCUMENT INGESTION LOGIC
  // ============================================================
  const btnOpenUploadModal = document.getElementById("btn-open-upload-modal");
  const btnCloseUploadModal = document.getElementById("btn-close-upload-modal");
  const uploadModal = document.getElementById("upload-modal");
  const uploadDropzone = document.getElementById("upload-dropzone");
  const pdfFileInput = document.getElementById("pdf-file-input");
  const selectedFilePreview = document.getElementById("selected-file-preview");
  const previewFilename = document.getElementById("preview-filename");
  const previewFilesize = document.getElementById("preview-filesize");
  const ingestStatusBox = document.getElementById("ingest-status-box");
  const btnSubmitUpload = document.getElementById("btn-submit-upload");
  const ingestedDocsContainer = document.getElementById("ingested-docs-container");
  const docsCountBadge = document.getElementById("docs-count-badge");

  let currentSelectedFile = null;

  // Open & Close Modal
  if (btnOpenUploadModal && uploadModal) {
    btnOpenUploadModal.addEventListener("click", () => {
      uploadModal.classList.add("open");
      resetUploadModal();
    });
  }

  if (btnCloseUploadModal && uploadModal) {
    btnCloseUploadModal.addEventListener("click", () => {
      uploadModal.classList.remove("open");
    });
  }

  if (uploadModal) {
    uploadModal.addEventListener("click", (e) => {
      if (e.target === uploadModal) {
        uploadModal.classList.remove("open");
      }
    });
  }

  function resetUploadModal() {
    currentSelectedFile = null;
    if (pdfFileInput) pdfFileInput.value = "";
    if (selectedFilePreview) selectedFilePreview.style.display = "none";
    if (ingestStatusBox) {
      ingestStatusBox.className = "ingest-status-box";
      ingestStatusBox.style.display = "none";
      ingestStatusBox.innerHTML = "";
    }
    if (btnSubmitUpload) {
      btnSubmitUpload.disabled = true;
      btnSubmitUpload.textContent = "Ingest & Index Document";
    }
  }

  // Dropzone Click
  if (uploadDropzone && pdfFileInput) {
    uploadDropzone.addEventListener("click", () => {
      pdfFileInput.click();
    });

    // Drag and Drop Events
    ["dragenter", "dragover"].forEach((eventName) => {
      uploadDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadDropzone.classList.add("dragover");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      uploadDropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        uploadDropzone.classList.remove("dragover");
      });
    });

    uploadDropzone.addEventListener("drop", (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;
      if (files && files.length > 0) {
        handleFileSelection(files[0]);
      }
    });

    pdfFileInput.addEventListener("change", (e) => {
      if (e.target.files && e.target.files.length > 0) {
        handleFileSelection(e.target.files[0]);
      }
    });
  }

  function handleFileSelection(file) {
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      alert("Please select a PDF document (.pdf)");
      return;
    }
    currentSelectedFile = file;
    if (previewFilename) previewFilename.textContent = file.name;
    if (previewFilesize) {
      const kb = Math.round(file.size / 1024);
      previewFilesize.textContent = kb > 1024 ? `${(kb / 1024).toFixed(1)} MB` : `${kb} KB`;
    }
    if (selectedFilePreview) selectedFilePreview.style.display = "flex";
    if (btnSubmitUpload) btnSubmitUpload.disabled = false;
  }

  // Ingest Document Submission
  if (btnSubmitUpload) {
    btnSubmitUpload.addEventListener("click", async () => {
      if (!currentSelectedFile) return;

      btnSubmitUpload.disabled = true;
      if (ingestStatusBox) {
        ingestStatusBox.className = "ingest-status-box loading";
        ingestStatusBox.innerHTML = `
          <div class="spinner"></div>
          <span>Parsing PDF, chunking text, generating embeddings, and updating Qdrant + BM25...</span>
        `;
      }

      try {
        const formData = new FormData();
        formData.append("file", currentSelectedFile);

        const res = await fetch("/api/v1/documents/upload", {
          method: "POST",
          body: formData,
        });

        if (!res.ok) {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Upload failed with HTTP ${res.status}`);
        }

        const data = await res.json();

        if (ingestStatusBox) {
          ingestStatusBox.className = "ingest-status-box success";
          ingestStatusBox.innerHTML = `
            <strong>Document Ingestion Complete</strong>
            <div style="margin-top: 4px; font-size: 0.78rem;">
              Indexed <strong>${data.chunks_indexed}</strong> chunks from <em>${escapeHtml(data.filename)}</em> into hybrid retrieval index.
            </div>
          `;
        }

        btnSubmitUpload.textContent = "Ingested Successfully";
        showNotification(`Document ${data.filename} indexed`);

        // Refresh documents list
        fetchDocuments();

        // Optional: auto-close modal after 2.5s
        setTimeout(() => {
          if (uploadModal) uploadModal.classList.remove("open");
        }, 2200);

      } catch (err) {
        if (ingestStatusBox) {
          ingestStatusBox.className = "ingest-status-box error";
          ingestStatusBox.innerHTML = `<strong>Ingestion Error:</strong> ${escapeHtml(err.message)}`;
        }
        btnSubmitUpload.disabled = false;
      }
    });
  }

  // Fetch Ingested Documents List
  async function fetchDocuments() {
    try {
      const res = await fetch("/api/v1/documents");
      if (!res.ok) return;
      const data = await res.json();
      const docs = data.documents || [];

      if (docsCountBadge) {
        docsCountBadge.textContent = `${docs.length} ${docs.length === 1 ? "DOC" : "DOCS"}`;
      }

      if (ingestedDocsContainer) {
        if (docs.length === 0) {
          ingestedDocsContainer.innerHTML = `<div style="font-size: 0.75rem; color: var(--text-muted);">No documents ingested yet.</div>`;
        } else {
          ingestedDocsContainer.innerHTML = docs
            .map(
              (doc) => `
              <div class="doc-item">
                <div class="doc-info">
                  <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                  <span class="doc-name" title="${escapeHtml(doc.filename)}">${escapeHtml(doc.filename)}</span>
                </div>
                <span class="doc-size">${doc.size_kb} KB</span>
              </div>
            `
            )
            .join("");
        }
      }
    } catch (err) {
      console.warn("Could not fetch ingested documents:", err);
    }
  }

  // Traces Modal Elements
  const btnOpenTracesModal = document.getElementById("btn-open-traces-modal");
  const btnCloseTracesModal = document.getElementById("btn-close-traces-modal");
  const tracesModal = document.getElementById("traces-modal");
  const tracesModalList = document.getElementById("traces-modal-list");
  const tracesModalJaegerStatus = document.getElementById("traces-modal-jaeger-status");
  const tracesModalJaegerLink = document.getElementById("traces-modal-jaeger-link");

  if (btnOpenTracesModal && tracesModal) {
    btnOpenTracesModal.addEventListener("click", () => {
      tracesModal.classList.add("open");
      fetchTracesList();
    });
  }

  if (btnCloseTracesModal && tracesModal) {
    btnCloseTracesModal.addEventListener("click", () => {
      tracesModal.classList.remove("open");
    });
  }

  if (tracesModal) {
    tracesModal.addEventListener("click", (e) => {
      if (e.target === tracesModal) {
        tracesModal.classList.remove("open");
      }
    });
  }

  async function fetchTracesList() {
    if (!tracesModalList) return;
    try {
      tracesModalList.innerHTML = `<div style="text-align: center; color: var(--text-muted); font-size: 0.8rem; padding: 24px;">Loading live traces...</div>`;
      const res = await fetch("/api/v1/traces");
      if (!res.ok) throw new Error("Failed to load traces");
      const data = await res.json();
      const traces = data.traces || [];
      const jaegerStatus = data.jaeger_status || "unreachable";

      if (tracesModalJaegerStatus) {
        if (jaegerStatus === "ready") {
          tracesModalJaegerStatus.textContent = "READY";
          tracesModalJaegerStatus.style.color = "#34D399";
          if (tracesModalJaegerLink) tracesModalJaegerLink.style.display = "inline";
        } else {
          tracesModalJaegerStatus.textContent = "STANDBY";
          tracesModalJaegerStatus.style.color = "#FBBF24";
          if (tracesModalJaegerLink) tracesModalJaegerLink.style.display = "none";
        }
      }

      if (traces.length === 0) {
        tracesModalList.innerHTML = `<div style="text-align: center; color: var(--text-muted); font-size: 0.82rem; padding: 24px;">No query traces recorded yet. Ask a question in the chat to see distributed execution spans!</div>`;
        return;
      }

      tracesModalList.innerHTML = traces.map((t) => {
        const routeColor = t.route === "rag" ? "#22D3EE" : t.route === "sql" ? "#34D399" : t.route === "tool" ? "#FBBF24" : t.route === "blocked" ? "#FB7185" : "#A78BFA";
        const latencyMs = Math.round(t.total_latency_ms);
        return `
          <div style="background: rgba(255, 255, 255, 0.03); border: 1px solid var(--border-glass); border-radius: var(--radius-md); padding: 14px; display: flex; flex-direction: column; gap: 8px;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px;">
              <div style="font-size: 0.86rem; font-weight: 500; color: var(--text-primary); line-height: 1.4;">
                ${escapeHtml(t.query)}
              </div>
              <span style="font-family: var(--font-mono); font-size: 0.72rem; font-weight: 700; padding: 2px 8px; border-radius: 999px; background: rgba(255,255,255,0.06); color: ${routeColor}; border: 1px solid ${routeColor}40;">
                ${(t.route || "UNKNOWN").toUpperCase()}
              </span>
            </div>
            <div style="display: flex; flex-wrap: wrap; gap: 12px; font-size: 0.74rem; font-family: var(--font-mono); color: var(--text-muted);">
              <span>Latency: <strong style="color: var(--text-secondary);">${latencyMs}ms</strong></span>
              <span>Tokens: <strong style="color: var(--text-secondary);">${t.total_tokens || 0}</strong></span>
              <span>Cost: <strong style="color: #34D399;">$${(t.estimated_cost_usd || 0).toFixed(4)}</strong></span>
              <span>Cached: <strong style="color: ${t.cached ? '#34D399' : 'var(--text-muted)'};">${t.cached ? 'YES' : 'NO'}</strong></span>
              <span style="margin-left: auto; color: var(--text-muted); opacity: 0.7;">${t.trace_id.substring(0, 8)}...</span>
            </div>
          </div>
        `;
      }).join("");
    } catch (err) {
      tracesModalList.innerHTML = `<div style="text-align: center; color: #FB7185; font-size: 0.8rem; padding: 24px;">Failed to retrieve traces: ${escapeHtml(err.message)}</div>`;
    }
  }

  // Initial Polls & Intervals
  fetchTelemetry();
  fetchHealth();
  fetchDocuments();
  setInterval(() => {
    fetchTelemetry();
    fetchHealth();
    fetchDocuments();
  }, 10000);
});
