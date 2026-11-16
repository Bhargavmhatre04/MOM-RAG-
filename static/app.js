/**
 * NEURIAAI PLATFORM - CLIENT APPLICATION
 * Vanilla JS SPA for Multi-Industry Meeting Intelligence
 */

const MeetwellApp = (function () {
  // Application State
  const state = {
    workspaces: [],
    currentWorkspaceId: null,
    currentWorkspace: null,
    industries: [],
    currentView: "landing",
    currentPane: "dashboard",
    currentSummaryLength: "standard",
    currentDecisionsTab: "confirmed",
    selectedIndustryForWizard: "it",
    wizardFiles: [],
    chatHistory: [],
    charts: {},
    actionItemsCache: []
  };

  // ---------------------------------------------------------------------------
  // SAMPLE MEETING REPOSITORY (Tailored for All Industries)
  // ---------------------------------------------------------------------------
  const SAMPLE_MEETINGS = {
    it: {
      title: "Sprint 44 Retrospective & Technical Architecture Alignment",
      content: `Meeting: Sprint 44 Retrospective & Microservices Architecture Sync
Date: 2026-11-15
Attendees: Alex Rivera (VP Engineering), Sarah Jenkins (Lead Architect), Priya Patel (QA Lead), Liam Cooper (DevOps)

Key Discussions:
- Sprint 44 team velocity completed at 46 story points vs target of 50. Microservices latency reduced by 34% following Redis cluster upgrade.
- Technical Architecture: The legacy REST API authentication gateway experiences memory spikes under peak concurrency (>12k requests/sec). Sarah Jenkins proposed migrating to an asynchronous OAuth2 Proxy.
- Critical Blocker: Two P1 bugs remain unresolved in the payment webhook callbacks affecting invoice status reconciliation.

Confirmed Decisions:
- Approved the architecture migration to the new OAuth2 Proxy Gateway for all internal microservices by end of sprint. Rationale: Eliminates memory degradation and enforces Zero-Trust authentication.
- Confirmed a temporary feature code freeze on non-critical PRs until the payment callback regression is resolved.

Action Items:
- Sarah Jenkins: Finalize OAuth2 proxy architecture blueprint and deliver to DevOps by 2026-11-25. Priority: High.
- Liam Cooper: Deploy staging environment Redis cluster failover test by 2026-11-28. Priority: Medium.
- Priya Patel: Execute end-to-end regression test suite on payment webhook service before 2026-11-22. Priority: High.
- Alex Rivera: Conduct sprint capacity review for Q1 commitments by 2026-12-05. Priority: Low.

Identified Risks:
- High Risk: Potential deployment downtime during OAuth2 gateway cutover. Mitigation: Deploy Blue-Green pipeline with canary traffic routing. Responsible team: DevOps.`
    },
    healthcare: {
      title: "Clinical Operations & Emergency Ward Triage Review",
      content: `Meeting: St. Jude Medical Center Emergency Triage & Staffing Review
Date: 2026-11-16
Attendees: Dr. Marcus Vance (Chief of Surgery), Nurse Director Clara Oswald, Ward Admin Tom Rivera

Key Discussions:
- Emergency department average patient wait times increased to 48 minutes over the weekend due to admission bed bottleneck in Ward 3.
- Medical Equipment: Ventilator maintenance in ICU Bay 2 is overdue; biomedical engineering has been notified.
- Staff Scheduling: Weekend night shift roster has two open nurse shifts requiring coverage.

Confirmed Decisions:
- Approved implementation of Fast-Track triage pathway for low-acuity admissions to reduce ED congestion.
- Confirmed emergency procurement of 4 replacement patient telemetry monitors.

Action Items:
- Dr. Marcus Vance: Sign off on fast-track clinical criteria and triage protocols by 2026-11-20. Priority: High.
- Clara Oswald: Finalize weekend shift nursing rotation roster before 2026-11-22. Priority: High.
- Tom Rivera: Schedule biomedical vendor service for ICU ventilator inspection by 2026-11-24. Priority: Medium.

Identified Risks:
- Moderate concern regarding nurse staffing fatigue during flu season. Mitigation: Engage registry nurse float pool. Responsible team: Nursing Administration.`
    },
    banking: {
      title: "Q3 Financial Audit & Capital Adequacy Review",
      content: `Meeting: Q3 Capital Reserves & Internal Compliance Audit Review
Date: 2026-11-15
Attendees: Sarah Jenkins (CFO), David Miller (Chief Risk Officer), Elena Rostova (Lead Compliance Auditor)

Key Discussions:
- Capital adequacy ratio is currently at 14.8% exceeding the 12% regulatory requirement. Operating margin held steady at 28.4%.
- Internal audit identified 3 foreign exchange reporting anomalies that require statutory disclosure.
- Liquidity reserves buffer was reviewed against macroeconomic interest rate volatility.

Confirmed Decisions:
- Approved the allocation of $15M into high-liquidity short-term treasury bills.
- Confirmed adoption of revised KYC onboarding verification workflow for international commercial accounts.

Action Items:
- David Miller: Submit formal compliance audit remediation response to the Audit Committee by 2026-11-28. Priority: High.
- Sarah Jenkins: Complete treasury allocation transfer by 2026-12-02. Priority: High.
- Elena Rostova: Draft revised international KYC audit checklist by 2026-12-10. Priority: Medium.

Identified Risks:
- Operational Risk: Foreign exchange settlement latency during European market close. Mitigation: Implement pre-funding liquidity buffers. Responsible team: Treasury.`
    },
    construction: {
      title: "Skyview Tower Site Milestones & Subcontractor Safety Review",
      content: `Meeting: Skyview Tower Project Site Progress & Safety Coordination
Date: 2026-11-16
Attendees: Robert Sterling (Project Director), Miguel Santos (Site Super), Elena Torres (Safety Officer)

Key Discussions:
- Structural concrete pour for Level 18 completed 2 days ahead of schedule.
- Material Procurement: Structural steel beam delivery delayed by 4 days due to rail freight bottleneck.
- Safety: Zero lost-time incidents recorded over the past 60 days. Open punch list items down to 14.

Confirmed Decisions:
- Approved rescheduling of electrical rough-in subcontractor to commence work on Levels 15-17.
- Decided to add weekend crane operating hours to compensate for steel delivery latency.

Action Items:
- Miguel Santos: Coordinate revised delivery schedule with steel fabricator by 2026-11-20. Priority: High.
- Elena Torres: Conduct OSHA fall protection audit on exterior staging by 2026-11-22. Priority: High.
- Robert Sterling: Review subcontractor change order for additional crane shifts by 2026-11-25. Priority: Medium.

Identified Risks:
- Weather risk: Forecasted heavy winds may impact tower crane operations next week. Mitigation: Secure rigging protocols and dynamic wind monitoring. Responsible team: Site Operations.`
    }
  };

  // ---------------------------------------------------------------------------
  // INITIALIZATION & ROUTING
  // ---------------------------------------------------------------------------
  async function init() {
    setupEventListeners();
    await checkHealth();
    await fetchIndustries();
    await fetchWorkspaces();

    // Check hash on load
    handleHashChange();
    window.addEventListener("hashchange", handleHashChange);
  }

  function setupEventListeners() {
    // Mobile navigation toggle
    const toggle = document.getElementById("mobile-menu-toggle");
    if (toggle) {
      toggle.addEventListener("click", () => {
        const panel = document.getElementById("mobile-nav-panel");
        panel.style.display = panel.style.display === "flex" ? "none" : "flex";
      });
    }

    // Close export dropdown on outside click
    document.addEventListener("click", (e) => {
      const exportWrap = document.querySelector(".app-export-menu-wrap");
      const dropdown = document.getElementById("app-export-dropdown");
      if (exportWrap && dropdown && !exportWrap.contains(e.target)) {
        dropdown.classList.add("hidden");
      }
    });
  }

  function handleHashChange() {
    const rawHash = window.location.hash.replace("#", "") || "landing";
    if (rawHash.startsWith("landing") || rawHash === "features" || rawHash === "faqs" || rawHash === "about" || rawHash === "industries") {
      showLandingView();
      if (rawHash === "landing-features" || rawHash === "features") {
        document.getElementById("landing-features")?.scrollIntoView({ behavior: "smooth" });
      } else if (rawHash === "landing-industries" || rawHash === "industries") {
        document.getElementById("landing-industries")?.scrollIntoView({ behavior: "smooth" });
      } else if (rawHash === "landing-faqs" || rawHash === "faqs") {
        document.getElementById("landing-faqs")?.scrollIntoView({ behavior: "smooth" });
      } else if (rawHash === "landing-about" || rawHash === "about") {
        document.getElementById("landing-about")?.scrollIntoView({ behavior: "smooth" });
      }
    } else {
      showAppView();
      let pane = "dashboard";
      if (rawHash.startsWith("app-")) {
        pane = rawHash.replace("app-", "");
      }
      switchPane(pane, false);
    }
  }

  // ---------------------------------------------------------------------------
  // API UTILITIES & HEALTH
  // ---------------------------------------------------------------------------
  async function apiCall(endpoint, options = {}) {
    try {
      const res = await fetch(endpoint, options);
      if (!res.ok) {
        let errorMsg = `HTTP Error ${res.status}`;
        try {
          const errData = await res.json();
          if (errData && errData.detail) errorMsg = errData.detail;
        } catch (_) {}
        throw new Error(errorMsg);
      }
      return await res.json();
    } catch (err) {
      console.error(`API Error [${endpoint}]:`, err);
      throw err;
    }
  }

  async function checkHealth() {
    try {
      const data = await apiCall("/api/health");
      const banner = document.getElementById("gemini-setup-banner");
      if (banner) {
        if (!data.has_gemini_key) {
          banner.classList.remove("hidden");
        } else {
          banner.classList.add("hidden");
        }
      }
    } catch (e) {
      console.warn("Health check failed:", e);
    }
  }

  async function fetchIndustries() {
    try {
      const data = await apiCall("/api/industries");
      state.industries = data.industries || [];
      renderLandingIndustries();
      renderWizardIndustries();
      populateIndustrySelects();
    } catch (e) {
      showToast("Failed to load industry configurations", "error");
    }
  }

  async function fetchWorkspaces() {
    try {
      const data = await apiCall("/api/workspaces");
      state.workspaces = data.workspaces || [];

      // Auto-create default workspace if none exist so user is never stranded
      if (state.workspaces.length === 0) {
        const newWs = await apiCall("/api/workspaces", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: "Neuria Intelligence Workspace", industry: "it" })
        });
        state.workspaces = [newWs];
      }

      updateWorkspaceDropdown();

      const savedWsId = localStorage.getItem("meetwell_active_ws");
      if (savedWsId && state.workspaces.some(w => w.id === savedWsId)) {
        await switchWorkspace(savedWsId, false);
      } else if (state.workspaces.length > 0) {
        await switchWorkspace(state.workspaces[0].id, false);
      }
    } catch (e) {
      console.error("Error loading workspaces:", e);
    }
  }

  // ---------------------------------------------------------------------------
  // VIEW SWITCHING (LANDING vs APP)
  // ---------------------------------------------------------------------------
  function showLandingView() {
    state.currentView = "landing";
    document.getElementById("view-landing").classList.add("active");
    document.getElementById("view-app").classList.remove("active");
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function showAppView() {
    state.currentView = "app";
    document.getElementById("view-landing").classList.remove("active");
    document.getElementById("view-app").classList.add("active");

    if (!state.currentWorkspaceId && state.workspaces.length > 0) {
      switchWorkspace(state.workspaces[0].id);
    }
  }

  function openApp() {
    window.location.hash = "#app-dashboard";
    showAppView();
    switchPane("dashboard", false);
  }

  function closeMobileMenu() {
    const panel = document.getElementById("mobile-nav-panel");
    if (panel) panel.style.display = "none";
  }

  // ---------------------------------------------------------------------------
  // WORKSPACE MANAGEMENT
  // ---------------------------------------------------------------------------
  async function switchWorkspace(wsId, refreshView = true) {
    showLoading("Loading workspace intelligence...");
    try {
      const ws = await apiCall(`/api/workspaces/${wsId}`);
      state.currentWorkspaceId = ws.id;
      state.currentWorkspace = ws;
      localStorage.setItem("meetwell_active_ws", ws.id);

      updateWorkspaceDropdown();
      updateTopBarChips(ws);
      updateSidebarDocCount(ws);

      if (refreshView) {
        await loadPaneData(state.currentPane);
      }
    } catch (err) {
      showToast(err.message || "Failed to switch workspace", "error");
    } finally {
      hideLoading();
    }
  }

  function updateWorkspaceDropdown() {
    const select = document.getElementById("app-ws-select");
    if (!select) return;
    select.innerHTML = "";

    if (state.workspaces.length === 0) {
      const opt = document.createElement("option");
      opt.value = "";
      opt.textContent = "No Workspaces";
      select.appendChild(opt);
      return;
    }

    state.workspaces.forEach(ws => {
      const opt = document.createElement("option");
      opt.value = ws.id;
      opt.textContent = ws.name;
      if (ws.id === state.currentWorkspaceId) opt.selected = true;
      select.appendChild(opt);
    });
  }

  function updateTopBarChips(ws) {
    const profile = state.industries.find(i => i.id === ws.industry) || { name: ws.industry, id: ws.industry };
    const nameEl = document.getElementById("app-industry-name");
    if (nameEl) nameEl.textContent = ws.custom_industry_name || profile.name;

    const headerChip = document.getElementById("header-ws-chip");
    const headerName = document.getElementById("header-ws-name");
    const headerInd = document.getElementById("header-ws-ind");
    if (headerChip && headerName && headerInd) {
      headerChip.classList.remove("hidden");
      headerName.textContent = ws.name;
      headerInd.textContent = (profile.id || "IT").toUpperCase();
    }

    // Isolation badge
    const isoBadge = document.getElementById("app-isolation-status");
    if (isoBadge) {
      const cross = ws.settings?.cross_workspace_enabled;
      isoBadge.textContent = cross ? "CROSS-WORKSPACE" : "ISOLATED";
      isoBadge.style.color = cross ? "#D95D39" : "#2E7D32";
      isoBadge.style.background = cross ? "#FFF0EC" : "#E8F5E9";
    }

    // Disclaimer card in dashboard
    const discCard = document.getElementById("dash-disclaimer-card");
    const discText = document.getElementById("dash-disclaimer-text");
    if (discCard && discText) {
      if (profile.disclaimer) {
        discCard.classList.remove("hidden");
        discText.textContent = profile.disclaimer;
      } else {
        discCard.classList.add("hidden");
      }
    }

    // Industry emphasis card
    const empTitle = document.getElementById("emphasis-title");
    const empDesc = document.getElementById("emphasis-desc");
    const empChips = document.getElementById("emphasis-chips");
    if (empTitle && profile.dashboard_emphasis) {
      empTitle.textContent = profile.dashboard_emphasis;
    }
    if (empDesc) {
      empDesc.textContent = profile.analysis_instructions || `Domain analysis active for ${profile.name}.`;
    }
    if (empChips) {
      empChips.innerHTML = "";
      const categories = ws.dynamic_categories && ws.dynamic_categories.length > 0 ? ws.dynamic_categories : (profile.focus_categories || []);
      categories.forEach(cat => {
        const span = document.createElement("span");
        span.className = "emphasis-chip";
        span.textContent = cat;
        empChips.appendChild(span);
      });
    }

    // Update suggested questions in Ask pane
    const qWrap = document.getElementById("suggested-questions-chips");
    if (qWrap) {
      qWrap.innerHTML = "";
      const questions = profile.suggested_questions || [
        "What key decisions were confirmed?",
        "What action items were assigned?",
        "What are the upcoming deadlines?"
      ];
      questions.forEach(q => {
        const btn = document.createElement("button");
        btn.className = "q-chip";
        btn.textContent = q;
        btn.onclick = () => {
          document.getElementById("chat-query-input").value = q;
          submitChatQuery(new Event("submit"));
        };
        qWrap.appendChild(btn);
      });
    }
  }

  function updateSidebarDocCount(ws) {
    const el = document.getElementById("sidebar-doc-count");
    if (el) el.textContent = Object.keys(ws.documents || {}).length;
  }

  function onWorkspaceSelected(id) {
    if (id && id !== state.currentWorkspaceId) {
      switchWorkspace(id);
    }
  }

  // ---------------------------------------------------------------------------
  // SUB-PANE NAVIGATION
  // ---------------------------------------------------------------------------
  function switchPane(paneId, updateHash = true) {
    state.currentPane = paneId;
    if (updateHash) {
      window.location.hash = `#app-${paneId}`;
    }

    document.querySelectorAll(".sidebar-tab").forEach(tab => {
      if (tab.getAttribute("data-pane") === `pane-${paneId}`) {
        tab.classList.add("active");
      } else {
        tab.classList.remove("active");
      }
    });

    document.querySelectorAll(".sub-pane").forEach(pane => {
      pane.classList.remove("active");
    });

    const targetPane = document.getElementById(`pane-${paneId}`);
    if (targetPane) {
      targetPane.classList.add("active");
    }

    loadPaneData(paneId);
  }

  async function loadPaneData(paneId) {
    if (!state.currentWorkspaceId) return;

    switch (paneId) {
      case "dashboard":
        await refreshDashboard();
        break;
      case "documents":
        await renderDocumentsTable();
        break;
      case "summary":
        await fetchSummary(state.currentSummaryLength);
        break;
      case "decisions":
        await fetchDecisions();
        break;
      case "actions":
        await fetchActionItems();
        break;
      case "deadlines":
        await fetchDeadlines();
        break;
      case "decision-tracker":
        await fetchDecisionTracker();
        break;
      case "task-tracker":
        await fetchTaskTracker();
        break;
      case "risks":
        await fetchRisks();
        break;
      case "timeline":
        await fetchTimeline();
        break;
      case "compare":
        break;
      case "followup":
        await fetchFollowupPrep();
        break;
      case "kpis":
        await fetchKPIs();
        break;
      case "reports":
        break;
      case "settings":
        populateSettingsPane();
        break;
    }
  }

  // ---------------------------------------------------------------------------
  // DASHBOARD & CHARTS
  // ---------------------------------------------------------------------------
  async function refreshDashboard() {
    if (!state.currentWorkspaceId) return;

    try {
      const ws = await apiCall(`/api/workspaces/${state.currentWorkspaceId}`);
      state.currentWorkspace = ws;

      const docsCount = Object.keys(ws.documents || {}).length;
      document.getElementById("metric-docs").textContent = docsCount;

      const starterCard = document.getElementById("dash-starter-card");
      if (starterCard) {
        starterCard.style.display = docsCount > 0 ? "none" : "block";
      }

      const dlData = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/deadlines`, { method: "POST" });
      const actData = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/actions`, { method: "POST" });
      const decData = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/decisions`, { method: "POST" });
      const riskData = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/risks`, { method: "POST" });

      const actions = actData.actions || [];
      const confirmedDecs = decData.confirmed || [];
      const risks = riskData.risks || [];

      const pending = actions.filter(a => a.status === "pending" || a.status === "in_progress").length;
      const completed = actions.filter(a => a.status === "completed").length;

      document.getElementById("metric-actions").textContent = actions.length;
      document.getElementById("metric-decisions").textContent = confirmedDecs.length;
      document.getElementById("metric-pending").textContent = pending;
      document.getElementById("metric-completed").textContent = completed;
      document.getElementById("metric-deadlines").textContent = (dlData.upcoming || []).length;
      document.getElementById("metric-overdue").textContent = (dlData.overdue || []).length;
      document.getElementById("metric-risks").textContent = risks.length;

      renderDashboardCharts(actions, decData, risks);
    } catch (e) {
      console.warn("Dashboard refresh error:", e);
    }
  }

  function renderDashboardCharts(actions, decisions, risks) {
    const pendingCount = actions.filter(a => a.status === "pending").length;
    const inProgCount = actions.filter(a => a.status === "in_progress").length;
    const compCount = actions.filter(a => a.status === "completed").length;

    renderChart("chartTaskStatus", {
      type: "doughnut",
      data: {
        labels: ["Pending", "In Progress", "Completed"],
        datasets: [{
          data: [pendingCount || 1, inProgCount, compCount],
          backgroundColor: ["#E2A053", "#D4954A", "#48BB78"],
          borderWidth: 2,
          borderColor: "#0D0D0D"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: "#B5B5B5", font: { family: "Inter" } }
          }
        }
      }
    });

    const teamCounts = {};
    actions.forEach(a => {
      const t = a.team || "Operations";
      teamCounts[t] = (teamCounts[t] || 0) + 1;
    });
    const teamLabels = Object.keys(teamCounts).length > 0 ? Object.keys(teamCounts) : ["Operations"];
    const teamData = Object.keys(teamCounts).length > 0 ? Object.values(teamCounts) : [0];

    renderChart("chartTeamTasks", {
      type: "bar",
      data: {
        labels: teamLabels,
        datasets: [{
          label: "Tasks",
          data: teamData,
          backgroundColor: "#D4954A",
          borderRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: { legend: { display: false } },
        scales: {
          x: { ticks: { color: "#888888" }, grid: { color: "rgba(255,255,255,0.05)" } },
          y: { beginAtZero: true, ticks: { stepSize: 1, color: "#888888" }, grid: { color: "rgba(255,255,255,0.05)" } }
        }
      }
    });

    const riskCats = {};
    risks.forEach(r => {
      const cat = r.category || "Operational";
      riskCats[cat] = (riskCats[cat] || 0) + 1;
    });
    renderChart("chartRisks", {
      type: "pie",
      data: {
        labels: Object.keys(riskCats).length > 0 ? Object.keys(riskCats) : ["General"],
        datasets: [{
          data: Object.keys(riskCats).length > 0 ? Object.values(riskCats) : [1],
          backgroundColor: ["#E53E3E", "#D4954A", "#F0B86E", "#718096"],
          borderWidth: 2,
          borderColor: "#0D0D0D"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: "#B5B5B5", font: { family: "Inter" } }
          }
        }
      }
    });

    const confCount = (decisions.confirmed || []).length;
    const sugCount = (decisions.suggestions || []).length;
    const unresCount = (decisions.unresolved || []).length;

    renderChart("chartDecisions", {
      type: "doughnut",
      data: {
        labels: ["Confirmed", "Suggestions", "Unresolved"],
        datasets: [{
          data: [confCount || 1, sugCount, unresCount],
          backgroundColor: ["#F0B86E", "#D4954A", "#4A5568"],
          borderWidth: 2,
          borderColor: "#0D0D0D"
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: "#B5B5B5", font: { family: "Inter" } }
          }
        }
      }
    });
  }

  function renderChart(canvasId, config) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    if (state.charts[canvasId]) {
      state.charts[canvasId].destroy();
    }
    state.charts[canvasId] = new Chart(canvas, config);
  }

  // ---------------------------------------------------------------------------
  // DIRECT USER INPUT & SAMPLE HELPERS
  // ---------------------------------------------------------------------------
  function switchDocInputTab(mode) {
    const uploadDropzone = document.getElementById("upload-dropzone");
    const pasteBox = document.getElementById("paste-input-box");
    const btnFile = document.getElementById("tab-btn-file-upload");
    const btnPaste = document.getElementById("tab-btn-text-paste");

    if (mode === "file") {
      uploadDropzone?.classList.remove("hidden");
      pasteBox?.classList.add("hidden");
      btnFile?.classList.add("active");
      btnPaste?.classList.remove("active");
    } else {
      uploadDropzone?.classList.add("hidden");
      pasteBox?.classList.remove("hidden");
      btnFile?.classList.remove("active");
      btnPaste?.classList.add("active");
    }
  }

  function loadSampleMeetingText(elementId) {
    const el = document.getElementById(elementId);
    if (!el) return;
    let ind = state.currentWorkspace?.industry || "it";
    if (elementId === "hero-notes-input") {
      const heroInd = document.getElementById("hero-industry-select")?.value;
      if (heroInd) ind = heroInd;
    }
    const sample = SAMPLE_MEETINGS[ind] || SAMPLE_MEETINGS.it;
    el.value = sample.content;

    if (elementId === "doc-paste-content") {
      const pasteTitle = document.getElementById("doc-paste-title");
      if (pasteTitle) pasteTitle.value = sample.title;
    } else if (elementId === "hero-notes-input") {
      const heroTitle = document.getElementById("hero-title-input");
      if (heroTitle) heroTitle.value = sample.title;
    } else if (elementId === "dash-meeting-notes") {
      const dashTitle = document.getElementById("dash-meeting-title");
      if (dashTitle) dashTitle.value = sample.title;
    } else if (elementId === "wizard-notes-input") {
      const wizTitle = document.getElementById("wizard-ws-name");
      if (wizTitle && !wizTitle.value) wizTitle.value = sample.title;
    } else {
      const repTitle = document.getElementById("report-title-input");
      if (repTitle) repTitle.value = sample.title;
    }
    showToast(`Loaded realistic sample meeting for ${ind.toUpperCase()}`, "success");
  }

  async function loadSampleIntoWorkspaceAndAnalyze() {
    if (!state.currentWorkspaceId) {
      await fetchWorkspaces();
    }
    const ws = state.currentWorkspace;
    const ind = ws?.industry || "it";
    const sample = SAMPLE_MEETINGS[ind] || SAMPLE_MEETINGS.it;

    showLoading("Ingesting sample transcript & generating full intelligence report...");
    try {
      const res = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          title: sample.title,
          content: sample.content
        })
      });

      showToast("Intelligence report generated successfully!", "success");
      await switchWorkspace(state.currentWorkspaceId, false);
      switchPane("reports");
      renderReportViewer(res.report);
    } catch (err) {
      showToast(err.message || "Failed to process sample", "error");
    } finally {
      hideLoading();
    }
  }

  async function submitPastedMeetingText() {
    const titleInput = document.getElementById("doc-paste-title");
    const contentInput = document.getElementById("doc-paste-content");
    const title = titleInput?.value.trim() || "Meeting Transcript";
    const content = contentInput?.value.trim();

    if (!content) {
      showToast("Please enter or paste meeting notes before submitting", "error");
      return;
    }

    showLoading("Chunking transcript, generating vectors & analyzing...");
    try {
      const res = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title, content: content })
      });

      titleInput.value = "";
      contentInput.value = "";
      showToast(`Meeting "${title}" ingested and analyzed!`, "success");

      await switchWorkspace(state.currentWorkspaceId, false);
      switchPane("reports");
      renderReportViewer(res.report);
    } catch (err) {
      showToast(err.message || "Failed to process text", "error");
    } finally {
      hideLoading();
    }
  }

  async function submitHeroMeetingInput() {
    const titleInput = document.getElementById("hero-title-input");
    const notesInput = document.getElementById("hero-notes-input");
    const indSelect = document.getElementById("hero-industry-select");

    const content = notesInput?.value.trim();
    if (!content) {
      showToast("Please enter or paste meeting notes first (or click '⚡ Load Example Notes')", "error");
      notesInput?.focus();
      return;
    }

    const industry = indSelect?.value || "it";
    const title = titleInput?.value.trim() || `${industry.toUpperCase()} Intelligence Review`;

    showLoading("Creating workspace, indexing vectors & generating report...");
    try {
      if (state.workspaces.length === 0) {
        await fetchWorkspaces();
      }
      let targetWs = state.workspaces.find(w => w.industry === industry);
      if (!targetWs) {
        targetWs = await apiCall("/api/workspaces", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: title, industry: industry })
        });
        state.workspaces.unshift(targetWs);
      }
      state.currentWorkspaceId = targetWs.id;
      state.currentWorkspace = targetWs;
      localStorage.setItem("meetwell_active_ws", targetWs.id);

      const res = await apiCall(`/api/workspaces/${targetWs.id}/text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title, content: content })
      });

      if (notesInput) notesInput.value = "";
      if (titleInput) titleInput.value = "";

      showToast("Meeting processed and intelligence report generated!", "success");

      openApp();
      await switchWorkspace(targetWs.id, false);
      switchPane("reports");
      renderReportViewer(res.report);
    } catch (err) {
      showToast(err.message || "Failed to analyze meeting notes", "error");
    } finally {
      hideLoading();
    }
  }

  async function submitDashboardMeetingInput() {
    if (!state.currentWorkspaceId) {
      await fetchWorkspaces();
    }
    const titleInput = document.getElementById("dash-meeting-title");
    const notesInput = document.getElementById("dash-meeting-notes");
    const content = notesInput?.value.trim();

    if (!content) {
      showToast("Please enter or paste meeting notes first (or click '⚡ Load Example Notes')", "error");
      notesInput?.focus();
      return;
    }

    const title = titleInput?.value.trim() || `${(state.currentWorkspace?.name || "Meeting")} Notes`;

    showLoading("Processing meeting minutes & synthesizing intelligence report...");
    try {
      const res = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/text`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: title, content: content })
      });

      if (notesInput) notesInput.value = "";
      if (titleInput) titleInput.value = "";

      showToast("Intelligence report generated successfully!", "success");
      await switchWorkspace(state.currentWorkspaceId, false);
      switchPane("reports");
      renderReportViewer(res.report);
    } catch (err) {
      showToast(err.message || "Failed to process meeting notes", "error");
    } finally {
      hideLoading();
    }
  }

  // ---------------------------------------------------------------------------
  // DOCUMENT MANAGEMENT & UPLOAD
  // ---------------------------------------------------------------------------
  function handleDragOver(e) {
    e.preventDefault();
    document.getElementById("upload-dropzone")?.classList.add("dragover");
  }

  function handleDragLeave(e) {
    e.preventDefault();
    document.getElementById("upload-dropzone")?.classList.remove("dragover");
  }

  function handleDrop(e) {
    e.preventDefault();
    document.getElementById("upload-dropzone")?.classList.remove("dragover");
    if (e.dataTransfer && e.dataTransfer.files.length > 0) {
      handleFileInput(e.dataTransfer.files);
    }
  }

  async function handleFileInput(fileList) {
    if (!state.currentWorkspaceId) {
      showToast("Please create or select a workspace first", "error");
      return;
    }
    if (!fileList || fileList.length === 0) return;

    const files = Array.from(fileList);
    const statusBox = document.getElementById("upload-status-box");
    const listEl = document.getElementById("upload-items-list");
    if (statusBox) statusBox.classList.remove("hidden");
    if (listEl) listEl.innerHTML = "";

    const formData = new FormData();
    files.forEach(f => {
      formData.append("files", f);
      if (listEl) {
        const item = document.createElement("div");
        item.className = "upload-item-status";
        item.id = `up-item-${f.name.replace(/[^\w]/g, "_")}`;
        item.innerHTML = `
          <span>📄 ${f.name} (${(f.size / 1024).toFixed(1)} KB)</span>
          <span class="status-tag processing">Processing...</span>
        `;
        listEl.appendChild(item);
      }
    });

    showLoading("Extracting text, chunking & creating vector embeddings...");

    try {
      const res = await fetch(`/api/workspaces/${state.currentWorkspaceId}/documents`, {
        method: "POST",
        body: formData
      });
      const data = await res.json();

      if (data.uploaded) {
        let successCount = 0;
        data.uploaded.forEach(item => {
          const el = document.getElementById(`up-item-${item.filename.replace(/[^\w]/g, "_")}`);
          if (el) {
            if (item.status === "done") {
              successCount++;
              el.innerHTML = `
                <span>✓ ${item.filename} (${item.pages} pages, ${item.chunks} vectors)</span>
                <span class="status-tag done">Embedded</span>
              `;
            } else {
              el.innerHTML = `
                <span>✕ ${item.filename}</span>
                <span class="status-tag failed" title="${item.error || 'Failed'}">${item.error || 'Failed'}</span>
              `;
            }
          }
        });

        if (successCount > 0) {
          showToast(`Successfully processed & embedded ${successCount} document(s)!`, "success");
        }
      }

      await switchWorkspace(state.currentWorkspaceId, false);
      await renderDocumentsTable();
      await refreshDashboard();
    } catch (err) {
      showToast(err.message || "Upload failed", "error");
    } finally {
      hideLoading();
    }
  }

  async function renderDocumentsTable() {
    if (!state.currentWorkspaceId) return;
    try {
      const data = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/documents`);
      const docs = data.documents || [];
      const tbody = document.getElementById("documents-table-body");
      if (!tbody) return;

      if (docs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center muted-cell">No documents uploaded yet. Drag & drop files or paste notes above.</td></tr>`;
        return;
      }

      tbody.innerHTML = "";
      docs.forEach(doc => {
        const tr = document.createElement("tr");
        const dateStr = new Date(doc.uploaded_at).toLocaleString();
        const sizeStr = (doc.size_bytes / 1024).toFixed(1) + " KB";
        tr.innerHTML = `
          <td><strong>${doc.filename}</strong></td>
          <td><span class="badge-format">${doc.file_type}</span></td>
          <td>${sizeStr}</td>
          <td>${doc.page_count}</td>
          <td>${doc.chunks_count}</td>
          <td>${dateStr}</td>
          <td>
            <button class="btn-outline-pill-small danger" onclick="MeetwellApp.deleteDocument('${doc.id}')">Delete</button>
          </td>
        `;
        tbody.appendChild(tr);
      });
    } catch (e) {
      console.warn("Failed to render documents:", e);
    }
  }

  async function deleteDocument(docId) {
    if (!confirm("Are you sure you want to remove this document and all its vector embeddings?")) return;
    showLoading("Removing document & vector embeddings...");
    try {
      await apiCall(`/api/workspaces/${state.currentWorkspaceId}/documents/${docId}`, { method: "DELETE" });
      showToast("Document and vectors successfully removed", "success");
      await switchWorkspace(state.currentWorkspaceId, false);
      await renderDocumentsTable();
      await refreshDashboard();
    } catch (err) {
      showToast(err.message || "Failed to delete document", "error");
    } finally {
      hideLoading();
    }
  }

  async function clearAllDocuments() {
    if (!confirm("Are you sure you want to clear ALL documents, vector embeddings, and derived intelligence in this workspace?")) return;
    showLoading("Clearing workspace data...");
    try {
      await apiCall(`/api/workspaces/${state.currentWorkspaceId}/documents`, { method: "DELETE" });
      showToast("All documents and vectors cleared", "success");
      await switchWorkspace(state.currentWorkspaceId);
    } catch (err) {
      showToast(err.message || "Failed to clear documents", "error");
    } finally {
      hideLoading();
    }
  }

  // ---------------------------------------------------------------------------
  // EXECUTIVE SUMMARY
  // ---------------------------------------------------------------------------
  async function fetchSummary(length = "standard", force = false) {
    state.currentSummaryLength = length;
    document.querySelectorAll(".len-btn").forEach(b => {
      b.classList.toggle("active", b.getAttribute("data-len") === length);
    });

    const wrap = document.getElementById("summary-content-wrap");
    if (!wrap || !state.currentWorkspaceId) return;

    if (!force && state.currentWorkspace?.summaries?.[length]) {
      renderSummary(state.currentWorkspace.summaries[length]);
      return;
    }

    showLoading(`Generating ${length} executive summary...`);
    try {
      const data = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/summary?length=${length}`, { method: "POST" });
      renderSummary(data);
    } catch (err) {
      wrap.innerHTML = `<div class="empty-state-card text-danger"><p>${err.message || 'Failed to generate summary'}</p></div>`;
    } finally {
      hideLoading();
    }
  }

  function renderSummary(data) {
    const wrap = document.getElementById("summary-content-wrap");
    if (!wrap) return;

    const participantsList = Array.isArray(data.participants) ? data.participants.join(", ") : data.participants;

    wrap.innerHTML = `
      <div class="summary-card-full">
        <div class="summary-top-meta">
          <span class="small-caps-label accent-orange">EXECUTIVE SUMMARY</span>
          <h3 class="summary-doc-title">${data.title || 'Meeting Review'}</h3>
          <div class="summary-meta-line">
            <span>📅 <strong>Date:</strong> ${data.date || 'Not specified'}</span>
            <span>👥 <strong>Participants:</strong> ${participantsList || 'Not specified'}</span>
          </div>
        </div>

        <div class="summary-section-block">
          <h4 class="summary-block-heading">Core Discussion Topics</h4>
          <ul class="summary-bullets">
            ${(data.topics || []).map(t => `<li>${t}</li>`).join("")}
          </ul>
        </div>

        <div class="summary-section-block">
          <h4 class="summary-block-heading">Key Insights & Discussion Points</h4>
          <ul class="summary-bullets">
            ${(data.key_points || []).map(p => `<li>${p}</li>`).join("")}
          </ul>
        </div>

        <div class="summary-section-block">
          <h4 class="summary-block-heading">Confirmed Decisions & Rationale</h4>
          <ul class="summary-bullets">
            ${(data.decisions || []).map(d => `<li><strong>Decision:</strong> ${d}</li>`).join("")}
          </ul>
        </div>

        <div class="summary-section-block">
          <h4 class="summary-block-heading">Blockers, Bottlenecks & Challenges</h4>
          <ul class="summary-bullets">
            ${(data.problems || []).map(pr => `<li>⚠️ ${pr}</li>`).join("")}
          </ul>
        </div>

        <div class="summary-section-block">
          <h4 class="summary-block-heading">Strategic Next Steps & Wrap-up</h4>
          <ul class="summary-bullets">
            ${(data.conclusions || []).map(c => `<li>${c}</li>`).join("")}
          </ul>
        </div>
      </div>
    `;
  }

  // ---------------------------------------------------------------------------
  // DISCUSSIONS & DECISIONS
  // ---------------------------------------------------------------------------
  async function fetchDecisions(force = false) {
    if (!state.currentWorkspaceId) return;
    showLoading("Extracting decisions & consensus...");
    try {
      const data = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/decisions`, { method: "POST" });
      document.getElementById("count-dec-confirmed").textContent = (data.confirmed || []).length;
      document.getElementById("count-dec-suggestions").textContent = (data.suggestions || []).length;
      document.getElementById("count-dec-unresolved").textContent = (data.unresolved || []).length;

      renderDecisionsList(data, state.currentDecisionsTab);
    } catch (err) {
      showToast(err.message || "Failed to load decisions", "error");
    } finally {
      hideLoading();
    }
  }

  function switchDecisionsTab(tabKey) {
    state.currentDecisionsTab = tabKey;
    document.querySelectorAll(".dec-tab-btn").forEach(b => {
      b.classList.toggle("active", b.getAttribute("onclick")?.includes(tabKey));
    });
    fetchDecisions();
  }

  function renderDecisionsList(data, tabKey) {
    const wrap = document.getElementById("decisions-list-wrap");
    if (!wrap) return;
    const items = data[tabKey] || [];

    if (items.length === 0) {
      wrap.innerHTML = `<div class="empty-state-card"><p>No items found under ${tabKey}.</p></div>`;
      return;
    }

    wrap.innerHTML = "";
    items.forEach(item => {
      const card = document.createElement("div");
      card.className = "decision-card";
      card.innerHTML = `
        <div class="dec-card-header">
          <span class="status-badge ${tabKey === 'confirmed' ? 'completed' : 'pending'}">${tabKey.toUpperCase()}</span>
          <span class="text-muted small">${item.date || 'Today'}</span>
        </div>
        <div class="dec-desc">${item.description}</div>
        <div class="dec-why"><strong>Rationale (The "Why"):</strong> ${item.why || 'Aligned with operational objectives'}</div>
        <div class="dec-meta-row">
          <span>🏛 <strong>Department:</strong> ${item.responsible_dept || 'Operations'}</span>
          <span>📁 <strong>Project:</strong> ${item.related_project || 'Core'}</span>
          <span>📄 <strong>Source:</strong> ${item.source || 'Transcript'} p.${item.page || 1}</span>
          <span>📌 <strong>Status:</strong> ${item.follow_up_status || 'In Effect'}</span>
        </div>
      `;
      wrap.appendChild(card);
    });
  }

  // ---------------------------------------------------------------------------
  // ACTION ITEMS TABLE & SMART TASK BOARD
  // ---------------------------------------------------------------------------
  async function fetchActionItems(force = false) {
    if (!state.currentWorkspaceId) return;
    showLoading("Extracting action items...");
    try {
      const data = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/actions`, { method: "POST" });
      state.actionItemsCache = data.actions || [];
      renderActionItemsTable(state.actionItemsCache);
      renderTaskTrackerTable(state.actionItemsCache);
    } catch (err) {
      showToast(err.message || "Failed to load action items", "error");
    } finally {
      hideLoading();
    }
  }

  function renderActionItemsTable(actions) {
    const tbody = document.getElementById("actions-table-body");
    if (!tbody) return;

    if (!actions || actions.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center muted-cell">No action items recorded yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = "";
    actions.forEach(a => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${a.task}</strong></td>
        <td>${a.person || 'Not specified'}</td>
        <td>${a.team || 'Operations'}</td>
        <td>${a.deadline || 'Not specified'}</td>
        <td><span class="status-badge ${a.status || 'pending'}">${(a.status || 'pending').replace('_', ' ')}</span></td>
        <td>
          <span class="priority-badge ${a.priority || 'Medium'}">${a.priority || 'Medium'}</span>
          ${a.priority_inferred ? '<span class="inferred-tag">(AI)</span>' : ''}
        </td>
        <td>${a.source_doc || 'Doc'} p.${a.page || 1}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  function filterActionItems() {
    const searchVal = document.getElementById("action-search-input")?.value.toLowerCase() || "";
    const statusVal = document.getElementById("action-status-filter")?.value || "all";
    const prioVal = document.getElementById("action-priority-filter")?.value || "all";

    const filtered = state.actionItemsCache.filter(item => {
      const matchSearch = item.task.toLowerCase().includes(searchVal) ||
                          (item.person || "").toLowerCase().includes(searchVal) ||
                          (item.team || "").toLowerCase().includes(searchVal);
      const matchStatus = statusVal === "all" || item.status === statusVal;
      const matchPrio = prioVal === "all" || item.priority === prioVal;
      return matchSearch && matchStatus && matchPrio;
    });

    renderActionItemsTable(filtered);
  }

  // ---------------------------------------------------------------------------
  // SMART TASK TRACKER (Direct status dropdown with PATCH API sync)
  // ---------------------------------------------------------------------------
  async function fetchTaskTracker() {
    if (state.actionItemsCache.length === 0) {
      await fetchActionItems();
    } else {
      renderTaskTrackerTable(state.actionItemsCache);
    }
  }

  function renderTaskTrackerTable(tasks) {
    const tbody = document.getElementById("task-tracker-table-body");
    if (!tbody) return;

    if (!tasks || tasks.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center muted-cell">No tasks recorded yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = "";
    tasks.forEach(t => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td><strong>${t.task}</strong></td>
        <td>${t.person || 'Not specified'}</td>
        <td>${t.team || 'Operations'}</td>
        <td>${t.deadline || 'Not specified'}</td>
        <td>
          <select class="task-status-select" onchange="MeetwellApp.updateTaskStatus('${t.id}', this.value)">
            <option value="pending" ${t.status === 'pending' ? 'selected' : ''}>Pending</option>
            <option value="in_progress" ${t.status === 'in_progress' ? 'selected' : ''}>In Progress</option>
            <option value="completed" ${t.status === 'completed' ? 'selected' : ''}>Completed</option>
          </select>
        </td>
        <td><span class="priority-badge ${t.priority || 'Medium'}">${t.priority || 'Medium'}</span></td>
      `;
      tbody.appendChild(tr);
    });
  }

  async function updateTaskStatus(taskId, newStatus) {
    try {
      await apiCall(`/api/workspaces/${state.currentWorkspaceId}/tasks/${taskId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus })
      });
      const item = state.actionItemsCache.find(x => x.id === taskId);
      if (item) item.status = newStatus;
      showToast(`Task status updated to ${newStatus}`, "success");
      await refreshDashboard();
    } catch (err) {
      showToast(err.message || "Failed to update task status", "error");
    }
  }

  // ---------------------------------------------------------------------------
  // DECISION STATUS TRACKER (PATCH API sync)
  // ---------------------------------------------------------------------------
  async function fetchDecisionTracker() {
    if (!state.currentWorkspaceId) return;
    try {
      const data = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/decisions`, { method: "POST" });
      const tbody = document.getElementById("decision-tracker-table-body");
      if (!tbody) return;

      const allDecs = [
        ...(data.confirmed || []),
        ...(data.suggestions || []),
        ...(data.unresolved || [])
      ];

      if (allDecs.length === 0) {
        tbody.innerHTML = `<tr><td colspan="6" class="text-center muted-cell">No decisions available to track.</td></tr>`;
        return;
      }

      tbody.innerHTML = "";
      allDecs.forEach(d => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
          <td><strong>${d.description}</strong></td>
          <td>${d.why || 'N/A'}</td>
          <td>${d.responsible_dept || 'Operations'}</td>
          <td>${d.date || 'Today'}</td>
          <td><span class="status-badge completed">${d.follow_up_status || 'In Effect'}</span></td>
          <td>
            <select class="task-status-select" onchange="MeetwellApp.updateDecisionStatus('${d.id}', this.value)">
              <option value="In Effect" ${d.follow_up_status === 'In Effect' ? 'selected' : ''}>In Effect</option>
              <option value="Under Review" ${d.follow_up_status === 'Under Review' ? 'selected' : ''}>Under Review</option>
              <option value="Pending Implementation" ${d.follow_up_status === 'Pending Implementation' ? 'selected' : ''}>Pending Implementation</option>
              <option value="Superseded" ${d.follow_up_status === 'Superseded' ? 'selected' : ''}>Superseded</option>
            </select>
          </td>
        `;
        tbody.appendChild(tr);
      });
    } catch (err) {
      console.warn("Failed to load decision tracker:", err);
    }
  }

  async function updateDecisionStatus(decisionId, newStatus) {
    try {
      await apiCall(`/api/workspaces/${state.currentWorkspaceId}/decisions/${decisionId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ follow_up_status: newStatus })
      });
      showToast(`Decision follow-up updated to "${newStatus}"`, "success");
      await refreshDashboard();
    } catch (err) {
      showToast(err.message || "Failed to update decision status", "error");
    }
  }

  // ---------------------------------------------------------------------------
  // DEADLINES & RESPONSIBILITIES
  // ---------------------------------------------------------------------------
  async function fetchDeadlines(force = false) {
    if (!state.currentWorkspaceId) return;
    showLoading("Auditing deadlines & responsibilities...");
    try {
      const data = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/deadlines`, { method: "POST" });

      const overdueEl = document.getElementById("overdue-items-list");
      const upcomingEl = document.getElementById("upcoming-items-list");
      const completedEl = document.getElementById("completed-items-list");

      document.getElementById("count-overdue").textContent = (data.overdue || []).length;
      document.getElementById("count-upcoming").textContent = (data.upcoming || []).length;
      document.getElementById("count-completed-dl").textContent = (data.completed || []).length;

      if (overdueEl) {
        overdueEl.innerHTML = (data.overdue || []).length > 0
          ? data.overdue.map(t => `<div class="deadline-item overdue"><strong>${t.task}</strong><br><small>Due: ${t.deadline} · Owner: ${t.person}</small></div>`).join("")
          : `<p class="text-muted small">No overdue action items.</p>`;
      }

      if (upcomingEl) {
        upcomingEl.innerHTML = (data.upcoming || []).length > 0
          ? data.upcoming.map(t => `<div class="deadline-item upcoming"><strong>${t.task}</strong><br><small>Due: ${t.deadline} · Owner: ${t.person}</small></div>`).join("")
          : `<p class="text-muted small">No upcoming deadlines.</p>`;
      }

      if (completedEl) {
        completedEl.innerHTML = (data.completed || []).length > 0
          ? data.completed.map(t => `<div class="deadline-item completed"><strong>${t.task}</strong><br><small>Owner: ${t.person}</small></div>`).join("")
          : `<p class="text-muted small">No completed items.</p>`;
      }

      const matrixWrap = document.getElementById("dept-matrix-wrap");
      if (matrixWrap && data.department_responsibilities) {
        matrixWrap.innerHTML = "";
        Object.entries(data.department_responsibilities).forEach(([dept, tasks]) => {
          const card = document.createElement("div");
          card.className = "dept-card";
          card.innerHTML = `
            <h4 class="dept-name">${dept}</h4>
            <ul class="dept-task-list">
              ${tasks.map(t => `<li>${t}</li>`).join("")}
            </ul>
          `;
          matrixWrap.appendChild(card);
        });
      }
    } catch (err) {
      showToast(err.message || "Failed to load deadlines", "error");
    } finally {
      hideLoading();
    }
  }

  // ---------------------------------------------------------------------------
  // RISKS DETECTION
  // ---------------------------------------------------------------------------
  async function fetchRisks(force = false) {
    if (!state.currentWorkspaceId) return;
    showLoading("Scanning risks & contingencies...");
    try {
      const data = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/risks`, { method: "POST" });
      const wrap = document.getElementById("risks-grid-wrap");
      if (!wrap) return;

      const risks = data.risks || [];
      if (risks.length === 0) {
        wrap.innerHTML = `<div class="empty-state-card"><p>No operational or regulatory risks detected in current records.</p></div>`;
        return;
      }

      wrap.innerHTML = "";
      risks.forEach(r => {
        const isConfirmed = (r.status || "").toLowerCase().includes("confirmed");
        const card = document.createElement("div");
        card.className = "risk-card";
        card.innerHTML = `
          <div class="risk-header">
            <span class="risk-status-tag ${isConfirmed ? 'confirmed' : 'concern'}">${r.status || 'Risk'}</span>
            <span class="priority-badge ${r.potential_impact || 'Medium'}">Impact: ${r.potential_impact || 'Medium'}</span>
          </div>
          <h4 class="risk-desc">${r.description}</h4>
          <p class="risk-mitigation mt-2"><strong>Mitigation:</strong> ${r.mitigation || 'Under investigation'}</p>
          <div class="risk-footer mt-3">
            <span>🛡 <strong>Team:</strong> ${r.responsible_team || 'Operations'}</span>
            <span>📄 <strong>Source:</strong> ${r.source || 'Doc'} p.${r.page || 1}</span>
          </div>
        `;
        wrap.appendChild(card);
      });
    } catch (err) {
      showToast(err.message || "Failed to load risks", "error");
    } finally {
      hideLoading();
    }
  }

  // ---------------------------------------------------------------------------
  // TIMELINE
  // ---------------------------------------------------------------------------
  async function fetchTimeline(force = false) {
    if (!state.currentWorkspaceId) return;
    showLoading("Synthesizing chronological timeline...");
    try {
      const data = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/timeline`, { method: "POST" });
      const wrap = document.getElementById("timeline-flow-wrap");
      if (!wrap) return;

      const events = data.events || [];
      if (events.length === 0) {
        wrap.innerHTML = `<div class="empty-state-card"><p>Upload transcripts to build a chronological timeline.</p></div>`;
        return;
      }

      wrap.innerHTML = "";
      events.forEach(e => {
        const node = document.createElement("div");
        node.className = "timeline-node";
        node.innerHTML = `
          <div class="timeline-node-dot">●</div>
          <div class="timeline-node-card">
            <div class="timeline-date-tag">${e.date} · <span class="badge-format">${(e.type || 'milestone').toUpperCase()}</span></div>
            <h4 class="timeline-title">${e.title}</h4>
            <p class="timeline-desc">${e.description}</p>
            <span class="text-muted small mt-2">Source: ${e.source}</span>
          </div>
        `;
        wrap.appendChild(node);
      });
    } catch (err) {
      showToast(err.message || "Failed to load timeline", "error");
    } finally {
      hideLoading();
    }
  }

  // ---------------------------------------------------------------------------
  // MEETING COMPARISON
  // ---------------------------------------------------------------------------
  async function fetchMeetingComparison() {
    if (!state.currentWorkspaceId) return;
    showLoading("Performing cross-meeting diff & analysis...");
    try {
      const data = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/compare`, { method: "POST" });
      const wrap = document.getElementById("compare-results-wrap");
      if (!wrap) return;

      wrap.innerHTML = `
        <div class="compare-results-card">
          <h3 class="sub-heading">Progress Summary</h3>
          <p class="section-lead">${data.progress_summary || 'Cross-meeting progress is steady.'}</p>

          <div class="compare-grid-2x2 mt-4">
            <div class="compare-box">
              <h4 class="text-forest">✨ New Decisions Confirmed</h4>
              <ul>${(data.new_decisions || []).map(d => `<li>${d}</li>`).join("")}</ul>
            </div>
            <div class="compare-box">
              <h4 class="text-orange">🔄 Changed / Superseded Decisions</h4>
              <ul>${(data.changed_decisions || []).map(d => `<li>${d}</li>`).join("")}</ul>
            </div>
            <div class="compare-box">
              <h4 class="text-danger">⚠️ Recurring / Repeated Blockers</h4>
              <ul>${(data.repeated_issues || []).map(d => `<li>${d}</li>`).join("")}</ul>
            </div>
            <div class="compare-box">
              <h4 class="text-forest">✓ Completed vs Pending Tasks</h4>
              <ul>
                <li><strong>Completed:</strong> ${(data.completed_tasks || []).join(", ") || "None verified"}</li>
                <li><strong>Pending:</strong> ${(data.pending_tasks || []).join(", ") || "None"}</li>
              </ul>
            </div>
          </div>
        </div>
      `;
    } catch (err) {
      showToast(err.message || "Comparison failed", "error");
    } finally {
      hideLoading();
    }
  }

  // ---------------------------------------------------------------------------
  // FOLLOW-UP PREP
  // ---------------------------------------------------------------------------
  async function fetchFollowupPrep(force = false) {
    if (!state.currentWorkspaceId) return;
    showLoading("Compiling follow-up executive briefing...");
    try {
      const data = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/followup`, { method: "POST" });
      const wrap = document.getElementById("followup-content-wrap");
      if (!wrap) return;

      wrap.innerHTML = `
        <div class="followup-card">
          <div class="followup-section">
            <h4 class="sub-heading">Previous Meeting Recap</h4>
            <p>${data.previous_recap}</p>
          </div>

          <div class="followup-section mt-4">
            <h4 class="sub-heading">Critical Pending Deliverables</h4>
            <ul>${(data.pending_items || []).map(i => `<li>${i}</li>`).join("")}</ul>
          </div>

          <div class="followup-section mt-4">
            <h4 class="sub-heading">Unresolved Questions to Ask Stakeholders</h4>
            <ul>${(data.questions_to_ask || []).map(q => `<li>❓ ${q}</li>`).join("")}</ul>
          </div>

          <div class="followup-section mt-4">
            <h4 class="sub-heading">Suggested Agenda <span class="badge-format">AI SUGGESTION</span></h4>
            <div class="table-responsive mt-2">
              <table class="meetwell-table">
                <thead>
                  <tr><th>TIME</th><th>AGENDA ITEM</th><th>LEAD / OWNER</th></tr>
                </thead>
                <tbody>
                  ${(data.suggested_agenda || []).map(ag => `
                    <tr><td><strong>${ag.time}</strong></td><td>${ag.item}</td><td>${ag.owner}</td></tr>
                  `).join("")}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      `;
    } catch (err) {
      showToast(err.message || "Failed to load follow-up prep", "error");
    } finally {
      hideLoading();
    }
  }

  // ---------------------------------------------------------------------------
  // KPI INSIGHTS
  // ---------------------------------------------------------------------------
  async function fetchKPIs(force = false) {
    if (!state.currentWorkspaceId) return;
    showLoading("Extracting explicit KPI targets...");
    try {
      const data = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/kpis`, { method: "POST" });
      const wrap = document.getElementById("kpi-grid-wrap");
      if (!wrap) return;

      const kpis = data.kpis || [];
      if (kpis.length === 0) {
        wrap.innerHTML = `<div class="empty-state-card"><p>No explicit numeric KPI targets found in uploaded documents.</p></div>`;
        return;
      }

      wrap.innerHTML = "";
      kpis.forEach(k => {
        const card = document.createElement("div");
        card.className = "kpi-card";
        card.innerHTML = `
          <span class="small-caps-label">${k.timeframe || 'TARGET PERIOD'}</span>
          <h3 class="kpi-metric-title">${k.metric}</h3>
          <div class="kpi-values-row">
            <div class="kpi-val-box">
              <span class="text-muted small">TARGET:</span>
              <span class="kpi-num">${k.target}</span>
            </div>
            <div class="kpi-val-box">
              <span class="text-muted small">ACTUAL:</span>
              <span class="kpi-num text-orange">${k.actual}</span>
            </div>
          </div>
          <span class="kpi-source-citation">Source: ${k.source} p.${k.page}</span>
        `;
        wrap.appendChild(card);
      });
    } catch (err) {
      showToast(err.message || "Failed to extract KPIs", "error");
    } finally {
      hideLoading();
    }
  }

  // ---------------------------------------------------------------------------
  // ASK YOUR MEETINGS (RAG Chat with Citations & History)
  // ---------------------------------------------------------------------------
  async function submitChatQuery(e) {
    if (e) e.preventDefault();
    const input = document.getElementById("chat-query-input");
    const query = input?.value.trim();
    if (!query || !state.currentWorkspaceId) return;

    appendChatMessage("user", query);
    input.value = "";

    const loadingBubble = appendChatMessage("assistant", "Retrieving relevant transcripts & formulating answer...", true);

    try {
      const res = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: query, history: state.chatHistory })
      });

      loadingBubble.remove();
      appendChatMessage("assistant", res.answer, false, res.citations);

      state.chatHistory.push({ role: "user", content: query });
      state.chatHistory.push({ role: "assistant", content: res.answer });
    } catch (err) {
      loadingBubble.remove();
      appendChatMessage("assistant", `Error: ${err.message || "Retrieval failed"}`);
    }
  }

  function appendChatMessage(role, text, isLoading = false, citations = []) {
    const wrap = document.getElementById("chat-messages-wrap");
    if (!wrap) return;

    const msgDiv = document.createElement("div");
    msgDiv.className = `chat-message ${role}`;

    let citationsHtml = "";
    if (citations && citations.length > 0) {
      citationsHtml = `
        <div class="citations-block">
          <span class="small-caps-label">CITATIONS & EXCERPTS:</span>
          ${citations.map(c => `
            <div class="citation-chip">
              <div class="citation-title">📄 ${c.document_name} (Page ${c.page_number})</div>
              <div class="citation-body">"${c.excerpt}"</div>
            </div>
          `).join("")}
        </div>
      `;
    }

    msgDiv.innerHTML = `
      <div class="chat-bubble">
        <p>${text}</p>
        ${citationsHtml}
      </div>
    `;

    wrap.appendChild(msgDiv);
    wrap.scrollTop = wrap.scrollHeight;
    return msgDiv;
  }

  function clearChatHistory() {
    state.chatHistory = [];
    const wrap = document.getElementById("chat-messages-wrap");
    if (wrap) {
      wrap.innerHTML = `
        <div class="chat-message assistant">
          <div class="chat-bubble">
            <p>Welcome to <strong>NeuriaAI Ask</strong>. Ask any question about your uploaded meeting minutes, sprint discussions, action items, or decisions.</p>
          </div>
        </div>
      `;
    }
  }

  // ---------------------------------------------------------------------------
  // INDUSTRY REPORT GENERATOR & EXPORTS
  // ---------------------------------------------------------------------------
  async function generateReport() {
    if (!state.currentWorkspaceId) {
      showToast("Select or create a workspace first", "error");
      return;
    }

    const rType = document.getElementById("report-type-select")?.value || "complete";
    const rLang = document.getElementById("report-lang-select")?.value || "English";
    const notesInput = document.getElementById("report-notes-input")?.value.trim() || "";
    const titleInput = document.getElementById("report-title-input")?.value.trim() || "";

    const cbs = document.querySelectorAll("#report-sections-checkboxes input[type='checkbox']:checked");
    const sections = Array.from(cbs).map(cb => cb.value);

    showLoading("Synthesizing executive intelligence report...");
    try {
      const report = await apiCall(`/api/workspaces/${state.currentWorkspaceId}/report`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          report_type: rType,
          language: rLang,
          sections: sections,
          notes: notesInput || undefined,
          title: titleInput || undefined
        })
      });

      renderReportViewer(report);
      showToast("Report compiled successfully!", "success");
      await switchWorkspace(state.currentWorkspaceId, false);
    } catch (err) {
      showToast(err.message || "Failed to generate report", "error");
    } finally {
      hideLoading();
    }
  }

  function renderReportViewer(report) {
    const viewerCard = document.getElementById("report-viewer-card");
    const titleEl = document.getElementById("report-viewer-title");
    const bodyEl = document.getElementById("report-viewer-body");
    if (!viewerCard || !bodyEl) return;

    viewerCard.classList.remove("hidden");
    titleEl.textContent = `${report.title} · ${report.workspace_name}`;

    const summary = report.summary || {};
    const decisions = report.decisions || {};
    const actions = report.actions || [];
    const risks = report.risks || [];

    bodyEl.innerHTML = `
      <div class="report-meta-header">
        <p><strong>Industry:</strong> ${report.industry_name} | <strong>Format:</strong> ${report.report_type.toUpperCase()} | <strong>Language:</strong> ${report.language} | <strong>Generated:</strong> ${report.generated_at}</p>
        ${report.disclaimer ? `<p class="text-danger small mt-2"><em>⚠️ Notice: ${report.disclaimer}</em></p>` : ''}
      </div>
      <hr class="mt-3 mb-4">
      <div class="report-section-content">
        <h4>1. Executive Summary & Context</h4>
        <p><strong>Title:</strong> ${summary.title || 'Executive Review'} | <strong>Date:</strong> ${summary.date || 'Current'}</p>
        <p><strong>Participants:</strong> ${Array.isArray(summary.participants) ? summary.participants.join(', ') : (summary.participants || 'Not specified')}</p>
        <h5 class="mt-3">Key Highlights:</h5>
        <ul>${(summary.key_points || []).map(p => `<li>${p}</li>`).join("")}</ul>
        <h5 class="mt-3">Conclusions & Strategic Directives:</h5>
        <ul>${(summary.conclusions || []).map(c => `<li>${c}</li>`).join("")}</ul>

        <h4 class="mt-6">2. Confirmed Decisions & Rationale</h4>
        <ul>
          ${(decisions.confirmed || []).map(d => `
            <li>
              <strong>${d.description}</strong><br>
              <span class="text-muted small">Rationale: ${d.why} | Responsible Dept: ${d.responsible_dept || 'Operations'} | Status: ${d.follow_up_status || 'In Effect'}</span>
            </li>
          `).join("")}
        </ul>

        <h4 class="mt-6">3. Action Items & Accountability Matrix</h4>
        <div class="table-responsive mt-2">
          <table class="meetwell-table">
            <thead>
              <tr><th>TASK</th><th>ASSIGNEE</th><th>TEAM</th><th>DEADLINE</th><th>STATUS</th><th>PRIORITY</th></tr>
            </thead>
            <tbody>
              ${actions.map(a => `
                <tr>
                  <td><strong>${a.task}</strong></td>
                  <td>${a.person || 'Not specified'}</td>
                  <td>${a.team || 'Operations'}</td>
                  <td>${a.deadline || 'Not specified'}</td>
                  <td><span class="status-badge ${a.status || 'pending'}">${(a.status || 'pending').replace('_', ' ')}</span></td>
                  <td><span class="priority-badge ${a.priority || 'Medium'}">${a.priority || 'Medium'}</span></td>
                </tr>
              `).join("")}
            </tbody>
          </table>
        </div>

        <h4 class="mt-6">4. Identified Risks & Contingencies</h4>
        <ul>
          ${risks.map(r => `
            <li>
              <strong>[${r.status || 'Risk'}]</strong> ${r.description} (Impact: <strong>${r.potential_impact || 'Medium'}</strong>)<br>
              <span class="text-muted small">Mitigation: ${r.mitigation || 'Under investigation'} | Responsible Team: ${r.responsible_team || 'Operations'}</span>
            </li>
          `).join("")}
        </ul>
      </div>
    `;

    viewerCard.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function toggleExportMenu() {
    const el = document.getElementById("app-export-dropdown");
    if (el) el.classList.toggle("hidden");
  }

  function triggerExport(type) {
    if (!state.currentWorkspaceId) {
      showToast("Select a workspace first", "error");
      return;
    }
    const dropdown = document.getElementById("app-export-dropdown");
    if (dropdown) dropdown.classList.add("hidden");

    showToast(`Downloading ${type.toUpperCase()} export...`, "success");
    const link = document.createElement("a");
    link.href = `/api/workspaces/${state.currentWorkspaceId}/export?type=${type}`;
    link.download = "";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  // ---------------------------------------------------------------------------
  // SETTINGS & ISOLATION
  // ---------------------------------------------------------------------------
  function populateSettingsPane() {
    const ws = state.currentWorkspace;
    if (!ws) return;

    document.getElementById("setting-ws-name").value = ws.name || "";
    document.getElementById("setting-ws-industry").value = ws.industry || "it";

    const s = ws.settings || {};
    document.getElementById("setting-chunk-size").value = s.chunk_size || 1000;
    document.getElementById("setting-chunk-overlap").value = s.chunk_overlap || 150;
    document.getElementById("setting-top-k").value = s.top_k || 6;
    document.getElementById("setting-cross-ws").checked = !!s.cross_workspace_enabled;
  }

  async function saveWorkspaceDetails() {
    const name = document.getElementById("setting-ws-name")?.value.trim();
    const ind = document.getElementById("setting-ws-industry")?.value;
    if (!name) return;

    showLoading("Saving workspace details...");
    try {
      await apiCall(`/api/workspaces/${state.currentWorkspaceId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: name, industry: ind })
      });
      showToast("Workspace updated successfully", "success");
      await fetchWorkspaces();
      await switchWorkspace(state.currentWorkspaceId);
    } catch (err) {
      showToast(err.message || "Failed to update workspace", "error");
    } finally {
      hideLoading();
    }
  }

  async function saveRAGSettings() {
    const chunkSize = parseInt(document.getElementById("setting-chunk-size")?.value, 10);
    const chunkOverlap = parseInt(document.getElementById("setting-chunk-overlap")?.value, 10);
    const topK = parseInt(document.getElementById("setting-top-k")?.value, 10);
    const cross = document.getElementById("setting-cross-ws")?.checked;

    showLoading("Updating RAG & isolation configuration...");
    try {
      await apiCall(`/api/workspaces/${state.currentWorkspaceId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          chunk_size: chunkSize,
          chunk_overlap: chunkOverlap,
          top_k: topK,
          cross_workspace_enabled: cross
        })
      });
      showToast("RAG settings saved", "success");
      await switchWorkspace(state.currentWorkspaceId, false);
    } catch (err) {
      showToast(err.message || "Failed to update RAG settings", "error");
    } finally {
      hideLoading();
    }
  }

  async function deleteCurrentWorkspace() {
    if (!confirm(`Are you sure you want to permanently delete workspace '${state.currentWorkspace?.name}' and all associated vector embeddings?`)) return;

    showLoading("Deleting workspace...");
    try {
      await apiCall(`/api/workspaces/${state.currentWorkspaceId}`, { method: "DELETE" });
      showToast("Workspace permanently deleted", "success");
      state.currentWorkspaceId = null;
      state.currentWorkspace = null;
      await fetchWorkspaces();
      if (state.workspaces.length > 0) {
        await switchWorkspace(state.workspaces[0].id);
      } else {
        showLandingView();
      }
    } catch (err) {
      showToast(err.message || "Failed to delete workspace", "error");
    } finally {
      hideLoading();
    }
  }

  // ---------------------------------------------------------------------------
  // 3-STEP ONBOARDING WIZARD
  // ---------------------------------------------------------------------------
  function startWorkspaceWizard(preselectedIndustry = null) {
    if (preselectedIndustry) {
      state.selectedIndustryForWizard = preselectedIndustry;
    }
    state.wizardFiles = [];
    document.getElementById("wizard-file-list").innerHTML = "";

    wizardNextStep(1);
    document.getElementById("modal-wizard")?.classList.remove("hidden");
  }

  function closeWizard() {
    document.getElementById("modal-wizard")?.classList.add("hidden");
  }

  function wizardNextStep(stepNum) {
    document.querySelectorAll(".wizard-step").forEach((st, idx) => {
      st.classList.toggle("active", idx === stepNum - 1);
    });
    document.querySelectorAll(".step-dot").forEach((dot, idx) => {
      dot.classList.toggle("active", idx <= stepNum - 1);
    });

    if (stepNum === 2) {
      const indObj = state.industries.find(i => i.id === state.selectedIndustryForWizard);
      const nameInput = document.getElementById("wizard-ws-name");
      if (nameInput && !nameInput.value) {
        nameInput.value = `${indObj ? indObj.name.split(" & ")[0] : "Intelligence"} Review`;
      }
    }
  }

  function wizardPrevStep(stepNum) {
    wizardNextStep(stepNum);
  }

  function selectWizardIndustry(indId) {
    state.selectedIndustryForWizard = indId;
    document.querySelectorAll(".industry-card-select").forEach(c => {
      c.classList.toggle("selected", c.getAttribute("data-ind") === indId);
    });

    const otherInputs = document.getElementById("wizard-other-inputs");
    if (otherInputs) {
      otherInputs.classList.toggle("hidden", indId !== "other");
    }
  }

  function handleWizardFiles(fileList) {
    if (!fileList || fileList.length === 0) return;
    state.wizardFiles = Array.from(fileList);
    const listEl = document.getElementById("wizard-file-list");
    if (!listEl) return;
    listEl.innerHTML = state.wizardFiles.map(f => `<div>📄 ${f.name} (${(f.size / 1024).toFixed(1)} KB)</div>`).join("");
  }

  async function finishWizard() {
    const nameInput = document.getElementById("wizard-ws-name");
    const wsName = nameInput?.value.trim() || "New Workspace";
    const ind = state.selectedIndustryForWizard || "it";

    const customName = document.getElementById("wizard-custom-name")?.value.trim() || null;
    const customDesc = document.getElementById("wizard-custom-desc")?.value.trim() || null;

    showLoading("Creating workspace & initializing in-memory Chroma vectors...");
    try {
      const ws = await apiCall("/api/workspaces", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: wsName,
          industry: ind,
          custom_industry_name: customName,
          custom_industry_desc: customDesc
        })
      });

      state.currentWorkspaceId = ws.id;
      state.currentWorkspace = ws;
      closeWizard();

      if (state.wizardFiles && state.wizardFiles.length > 0) {
        await handleFileInput(state.wizardFiles);
      }

      const pastedNotes = document.getElementById("wizard-notes-input")?.value.trim();
      let resReport = null;
      if (pastedNotes) {
        const textRes = await apiCall(`/api/workspaces/${ws.id}/text`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ title: `${ws.name} Initial Notes`, content: pastedNotes })
        });
        resReport = textRes.report;
      }

      await fetchWorkspaces();
      await switchWorkspace(ws.id);

      if (resReport) {
        openApp();
        switchPane("reports");
        renderReportViewer(resReport);
      } else {
        window.location.hash = "#app-dashboard";
        showAppView();
      }
      showToast(`Workspace "${ws.name}" created successfully!`, "success");
    } catch (err) {
      showToast(err.message || "Failed to create workspace", "error");
    } finally {
      hideLoading();
    }
  }

  function quickLaunchFromFooter() {
    const input = document.getElementById("footer-quick-ws-input");
    const val = input?.value.trim();
    if (val) {
      document.getElementById("wizard-ws-name").value = val;
    }
    startWorkspaceWizard();
  }

  // ---------------------------------------------------------------------------
  // DYNAMIC RENDERING (LANDING & WIZARD INDUSTRIES)
  // ---------------------------------------------------------------------------
  function renderLandingIndustries() {
    const container = document.getElementById("landing-industries-list");
    if (!container) return;
    container.innerHTML = "";

    state.industries.forEach((ind, idx) => {
      const numStr = (idx + 1).toString().padStart(2, "0");
      const row = document.createElement("div");
      row.className = "industry-num-row";
      row.onclick = () => {
        startWorkspaceWizard(ind.id);
      };

      row.innerHTML = `
        <span class="industry-num-label">${numStr}</span>
        <div>
          <h3 class="industry-title">${ind.name}</h3>
          <p class="industry-tagline">${ind.tagline}</p>
        </div>
        <div>
          <span class="industry-badge">${ind.focus_categories?.[0] || 'INTELLIGENCE'}</span>
        </div>
        <span class="industry-circle-arrow">↗</span>
      `;
      container.appendChild(row);
    });
  }

  function renderWizardIndustries() {
    const grid = document.getElementById("wizard-industry-grid");
    if (!grid) return;
    grid.innerHTML = "";

    state.industries.forEach(ind => {
      const card = document.createElement("div");
      card.className = `industry-card-select ${ind.id === state.selectedIndustryForWizard ? 'selected' : ''}`;
      card.setAttribute("data-ind", ind.id);
      card.onclick = () => selectWizardIndustry(ind.id);

      card.innerHTML = `
        <h4 class="ind-select-title">${ind.name}</h4>
        <p class="ind-select-tagline">${ind.tagline}</p>
      `;
      grid.appendChild(card);
    });
  }

  function populateIndustrySelects() {
    const selects = [
      document.getElementById("setting-ws-industry"),
      document.getElementById("hero-industry-select")
    ];
    selects.forEach(sel => {
      if (!sel) return;
      sel.innerHTML = "";
      state.industries.forEach(ind => {
        const opt = document.createElement("option");
        opt.value = ind.id;
        opt.textContent = ind.name;
        sel.appendChild(opt);
      });
    });
  }

  // ---------------------------------------------------------------------------
  // TOASTS & SPINNERS
  // ---------------------------------------------------------------------------
  function showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast-pill ${type}`;
    toast.innerHTML = `<span>${type === 'error' ? '✕' : '✓'}</span><span>${message}</span>`;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  function showLoading(msg = "Analyzing meeting intelligence...") {
    const overlay = document.getElementById("loading-overlay");
    const textEl = document.getElementById("loading-message");
    if (textEl) textEl.textContent = msg;
    if (overlay) overlay.classList.remove("hidden");
  }

  function hideLoading() {
    const overlay = document.getElementById("loading-overlay");
    if (overlay) overlay.classList.add("hidden");
  }

  // ---------------------------------------------------------------------------
  // PUBLIC API EXPOSURE
  // ---------------------------------------------------------------------------
  return {
    init,
    openApp,
    closeMobileMenu,
    switchPane,
    switchWorkspace,
    onWorkspaceSelected,
    startWorkspaceWizard,
    closeWizard,
    wizardNextStep,
    wizardPrevStep,
    handleWizardFiles,
    finishWizard,
    quickLaunchFromFooter,
    handleDragOver,
    handleDragLeave,
    handleDrop,
    handleFileInput,
    switchDocInputTab,
    loadSampleMeetingText,
    loadSampleIntoWorkspaceAndAnalyze,
    submitHeroMeetingInput,
    submitDashboardMeetingInput,
    submitPastedMeetingText,
    deleteDocument,
    clearAllDocuments,
    fetchSummary,
    fetchDecisions,
    switchDecisionsTab,
    fetchActionItems,
    filterActionItems,
    fetchTaskTracker,
    updateTaskStatus,
    fetchDecisionTracker,
    updateDecisionStatus,
    fetchDeadlines,
    fetchRisks,
    fetchTimeline,
    fetchMeetingComparison,
    fetchFollowupPrep,
    fetchKPIs,
    submitChatQuery,
    clearChatHistory,
    generateReport,
    renderReportViewer,
    toggleExportMenu,
    triggerExport,
    saveWorkspaceDetails,
    saveRAGSettings,
    deleteCurrentWorkspace,
    get currentSummaryLength() { return state.currentSummaryLength; }
  };
})();

// Bootstrap on DOM ready
document.addEventListener("DOMContentLoaded", () => {
  MeetwellApp.init();
});
