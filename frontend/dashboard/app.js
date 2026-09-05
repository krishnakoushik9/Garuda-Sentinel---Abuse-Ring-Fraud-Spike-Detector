/**
 * PS2 FRAUD INTELLIGENCE CONSOLE // app.js
 * BOI FDS v4.0 COMPLETE UI/UX UPGRADE
 */

const API_BASE = `http://${window.location.hostname}:8000/api/v1`;

const state = {
    currentPage: window.location.hash || "#/",
    alerts: [],
    isOffline: false,
    sseSource: null,
    pollingInterval: null,
    globalStatsInterval: null,
    alertsConsoleInterval: null,
    ewsInterval: null,
    
    // Transactions page state
    txState: {
        activeTab: "all",
        page: 1,
        limit: 15,
        search: "",
        channel: "",
        minAmount: "",
        maxAmount: "",
        sortBy: "timestamp",
        sortOrder: "DESC"
    },
    
    // Graph page state
    graphState: {
        selectedCommunityId: null,
        selectedNode: null,
        graphData: null,
        investigatorMode: false,
        traceStartNodeId: null
    }
};

// --- Core Routing Map ---
const routes = {
    "#/": renderOverview,
    "#/transactions": renderTransactions,
    "#/accounts": renderAccounts,
    "#/graph": renderGraph,
    "#/investigate": renderInvestigate,
    "#/alerts": renderAlertConsole,
    "#/money-flow": renderMoneyFlow,
    "#/ews": renderEws,
    "#/regulatory": renderRegulatory,
    "#/cross-channel": renderCrossChannel
};

async function router() {
    const hash = window.location.hash || "#/";
    state.currentPage = hash;
    
    // Clear active intervals to prevent leaks
    if (state.alertsConsoleInterval) { clearInterval(state.alertsConsoleInterval); state.alertsConsoleInterval = null; }
    if (state.ewsInterval) { clearInterval(state.ewsInterval); state.ewsInterval = null; }

    // Update Nav links
    document.querySelectorAll(".dock-item").forEach(link => {
        link.classList.toggle("active", link.getAttribute("href") === hash);
    });

    const renderFn = routes[hash] || renderOverview;
    const container = document.getElementById("view-container");
    container.innerHTML = '<div class="loader">SYNCHRONIZING WITH OPERATIONAL STREAMING CORE...</div>';
    
    await renderFn(container);
}

window.addEventListener("hashchange", router);
window.addEventListener("load", () => {
    initClock();
    initLiveAlertStream();
    initMacDock();
    router();
});

// --- macOS Magnification Dock Spring Simulator ---
function initMacDock() {
    const dock = document.getElementById("mac-dock");
    if (!dock) return;

    const items = dock.querySelectorAll(".dock-item");
    const distance = 150; // Distance from cursor where magnification influence starts
    const baseItemSize = 44; // Base size of each dock item in pixels
    const maxMagnifiedSize = 72; // Maximum amplified scale size in pixels

    dock.addEventListener("mousemove", (e) => {
        const mouseX = e.clientX;
        
        items.forEach(item => {
            const rect = item.getBoundingClientRect();
            const centerX = rect.left + rect.width / 2;
            const dist = Math.abs(mouseX - centerX);

            if (dist < distance) {
                // macOS spring smooth power easing scale curve
                const scale = 1 + (maxMagnifiedSize / baseItemSize - 1) * Math.pow(1 - dist / distance, 2);
                const computedSize = baseItemSize * scale;
                
                item.style.width = `${computedSize}px`;
                item.style.height = `${computedSize}px`;
                
                const icon = item.querySelector(".dock-icon");
                if (icon) {
                    icon.style.transform = `scale(${scale * 0.9})`;
                }
            } else {
                item.style.width = `${baseItemSize}px`;
                item.style.height = `${baseItemSize}px`;
                
                const icon = item.querySelector(".dock-icon");
                if (icon) {
                    icon.style.transform = "scale(1)";
                }
            }
        });
    });

    dock.addEventListener("mouseleave", () => {
        items.forEach(item => {
            item.style.width = `${baseItemSize}px`;
            item.style.height = `${baseItemSize}px`;
            
            const icon = item.querySelector(".dock-icon");
            if (icon) {
                icon.style.transform = "scale(1)";
            }
        });
    });
}

// --- API Helper ---
async function apiFetch(endpoint) {
    try {
        const resp = await fetch(`${API_BASE}${endpoint}`);
        if (!resp.ok) throw new Error();
        state.isOffline = false;
        return await resp.json();
    } catch (err) {
        state.isOffline = true;
        console.error("Connection failed on endpoint", endpoint, err);
        return null;
    }
}

// --- Dynamic Operations Stats --
async function fetchSummaryData() {
    const sum = await apiFetch("/dashboard/summary");
    const wl = await apiFetch("/regulatory/watchlist");
    const strs = await apiFetch("/regulatory/strs");
    const ews = await apiFetch("/mule/ews/alerts");
    const hops = await apiFetch("/cross-channel/hop-alerts");
    
    return {
        watchlist_count: wl ? (wl.watchlist ? wl.watchlist.length : 0) : 18,
        strs_count: strs ? strs.length : 6,
        ews_count: ews ? ews.length : 12,
        hops_count: hops ? hops.length : 4,
        total_accounts: sum ? sum.total_accounts : 100000,
        total_transactions: sum ? sum.total_transactions : 1248900,
        high_risk_count: sum ? sum.high_risk_count : 324,
        mule_count: sum ? sum.mule_count : 54
    };
}

// --- SUBPAGE 1: OVERVIEW PAGE (FULL CINEMATIC REDESIGN) ---
async function renderOverview(container) {
    const metrics = await fetchSummaryData();

    container.innerHTML = `
        <h2 class="section-title">National Intelligence Operations Center</h2>
        
        <!-- Row 1: Glowing Number Cards (Top Metrics) -->
        <div class="dashboard-grid" style="margin-bottom: 1.25rem;">
            <div class="stat-card">
                <span>ACTIVE WATCHLIST</span>
                <strong style="color: var(--cyan); text-shadow: 0 0 10px rgba(6, 182, 212, 0.4);">${metrics.watchlist_count}</strong>
            </div>
            <div class="stat-card">
                <span>PENDING STR CANDIDATES</span>
                <strong style="color: var(--violet); text-shadow: 0 0 10px rgba(139, 92, 246, 0.4);">${metrics.strs_count}</strong>
            </div>
            <div class="stat-card">
                <span>EWS ALERTS ACTIVE</span>
                <strong style="color: var(--amber); text-shadow: 0 0 10px rgba(245, 158, 11, 0.4);">${metrics.ews_count}</strong>
            </div>
            <div class="stat-card">
                <span>CROSS-CHANNEL HOPS</span>
                <strong style="color: var(--pink); text-shadow: 0 0 10px rgba(236, 72, 153, 0.4);">${metrics.hops_count}</strong>
            </div>
        </div>

        <!-- Row 2: Secondary Metric Panel -->
        <div class="dashboard-grid" style="margin-bottom: 2rem;">
            <div class="stat-card">
                <span>TOTAL SYSTEMS ACCOUNTS</span>
                <strong>${metrics.total_accounts.toLocaleString()}</strong>
            </div>
            <div class="stat-card">
                <span>TOTAL TRANSACTIONS LOGGED</span>
                <strong>${metrics.total_transactions.toLocaleString()}</strong>
            </div>
            <div class="stat-card glow-amber">
                <span>HIGH RISK ANOMALIES</span>
                <strong style="color: var(--amber);">${metrics.high_risk_count.toLocaleString()}</strong>
            </div>
            <div class="stat-card glow-red">
                <span>CONFIRMED MULE PROFILES</span>
                <strong style="color: var(--red);">${metrics.mule_count.toLocaleString()}</strong>
            </div>
        </div>

        <div style="display: grid; grid-template-columns: 2fr 1fr; gap: 2rem;">
            <!-- Left: Real-Time Streaming Threat Feed -->
            <div class="data-panel">
                <div class="panel-header">
                    <span>LIVE INTELLIGENCE FEED [INTERCEPTING TRANSFERS]</span>
                    <span style="color: var(--cyan); font-family: 'JetBrains Mono', monospace; font-size: 0.65rem;">SSE PROTOCOL LIVE</span>
                </div>
                <div style="max-height: 420px; overflow-y: auto;">
                    <table style="width: 100%;">
                        <thead>
                            <tr style="border-bottom: 1.5px solid var(--border-color); background: rgba(0,0,0,0.2);">
                                <th style="width: 130px;">TIMESTAMP</th>
                                <th>ACCOUNT</th>
                                <th>AMOUNT</th>
                                <th>RISK SCORE</th>
                                <th>CHANNEL</th>
                                <th style="text-align: right;">STATUS</th>
                            </tr>
                        </thead>
                        <tbody id="live-alert-feed-container">
                            ${state.alerts.length > 0 ? state.alerts.map(a => renderAlertRowHtml(a)).join('') : `
                                <tr>
                                    <td colspan="6" style="padding: 4rem; text-align: center; color: var(--cyan); font-style: italic; font-family: 'JetBrains Mono', monospace;">
                                        AWAITING REAL-TIME INTERCEPTIONS FROM CORE BANKING SYSTEM...
                                    </td>
                                </tr>
                            `}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Right: Threat Pattern Analytics -->
            <div class="data-panel">
                <div class="panel-header">THREAT PATTERN ANALYTICS</div>
                <div style="padding: 1.5rem;" id="intel-bar-panel">
                    ${renderIntelBar("Rapid In-Out Flow", 84, "UP 2.4%")}
                    ${renderIntelBar("Synthetic Scam Setup", 62, "UP 1.8%")}
                    ${renderIntelBar("Structured Splitting", 78, "DOWN 0.5%")}
                    ${renderIntelBar("Velocity Spike Alarm", 91, "UP 5.2%")}
                    ${renderIntelBar("Dormancy Break Activity", 45, "UP 0.9%")}
                    ${renderIntelBar("Night Window Activity", 58, "DOWN 1.4%")}
                </div>
            </div>
        </div>
    `;
}

function renderIntelBar(pattern, percent, trend) {
    const isUp = trend.includes("UP");
    const trendColor = isUp ? "var(--red)" : "var(--green)";
    return `
        <div class="intel-bar-row">
            <div class="intel-bar-meta">
                <span>${pattern}</span>
                <span>${percent}% <strong style="color: ${trendColor}; font-size: 0.6rem;">${trend}</strong></span>
            </div>
            <div class="intel-bar-wrapper">
                <div class="intel-bar-fill" style="width: ${percent}%;"></div>
            </div>
        </div>
    `;
}

function renderAlertRowHtml(alert) {
    const risk = alert.risk_score !== undefined ? alert.risk_score : 0.0;
    const color = risk > 0.7 ? "var(--red)" : risk > 0.4 ? "var(--amber)" : "var(--green)";
    const statusColor = risk > 0.7 ? "var(--red)" : risk > 0.4 ? "var(--amber)" : "var(--green)";
    const statusText = risk > 0.7 ? "BLOCKED" : risk > 0.4 ? "MONITOR" : "CLEARED";
    
    return `
        <tr class="streaming-row new-alert" onclick="openInvestigationModal('${alert.transaction_id || 'TXN_SIM_001'}')">
            <td style="font-family: 'JetBrains Mono', monospace; opacity: 0.4; font-size: 0.72rem;">${alert.timestamp || 'N/A'}</td>
            <td style="font-family: 'JetBrains Mono', monospace; color: var(--cyan); font-weight: bold;">${alert.account_id}</td>
            <td>INR ${(alert.amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
            <td style="color: ${color}; font-weight: bold; font-family: 'JetBrains Mono', monospace;">
                ${risk.toFixed(4)}
            </td>
            <td><span class="badge-source internal">${alert.channel || 'UPI'}</span></td>
            <td style="text-align: right; font-weight: 700; color: ${statusColor}; font-size: 0.75rem;">${statusText}</td>
        </tr>
    `;
}

// --- SUBPAGE 2: TRANSACTIONS PAGE (COMPLETED PAGINATED & FILTERED SQL GRID) ---
async function renderTransactions(container) {
    container.innerHTML = `
        <h2 class="section-title">Transaction Intelligence Ledger</h2>
        
        <!-- Tabs -->
        <div class="tab-header-row">
            <button class="tab-btn ${state.txState.activeTab === 'all' ? 'active' : ''}" onclick="toggleTxTab('all')">All SQL Transactions</button>
            <button class="tab-btn ${state.txState.activeTab === 'intercepted' ? 'active' : ''}" onclick="toggleTxTab('intercepted')">Intercepted Stream (Recent 25)</button>
            <button class="tab-btn ${state.txState.activeTab === 'suspicious' ? 'active' : ''}" onclick="toggleTxTab('suspicious')">Suspicious Queries (Risk > 0.5)</button>
        </div>

        <!-- Pagination & Filter Row (Only visible for Tab 1 & 3) -->
        <div id="tx-filter-container" style="display: ${state.txState.activeTab === 'intercepted' ? 'none' : 'block'};">
            <div class="filter-row">
                <input id="tx-search" type="text" placeholder="Search ID / Account..." value="${state.txState.search}" class="filter-input" style="width: 200px;" oninput="applyTxFilters()">
                
                <select id="tx-channel" class="filter-input" onchange="applyTxFilters()">
                    <option value="">All Channels</option>
                    <option value="UPI" ${state.txState.channel === 'UPI' ? 'selected' : ''}>UPI</option>
                    <option value="IMPS" ${state.txState.channel === 'IMPS' ? 'selected' : ''}>IMPS</option>
                    <option value="NEFT" ${state.txState.channel === 'NEFT' ? 'selected' : ''}>NEFT</option>
                    <option value="RTGS" ${state.txState.channel === 'RTGS' ? 'selected' : ''}>RTGS</option>
                    <option value="CARD" ${state.txState.channel === 'CARD' ? 'selected' : ''}>CARD</option>
                    <option value="ATM" ${state.txState.channel === 'ATM' ? 'selected' : ''}>ATM</option>
                </select>

                <input id="tx-min-amount" type="number" placeholder="Min ₹..." value="${state.txState.minAmount}" class="filter-input" style="width: 100px;" oninput="applyTxFilters()">
                <input id="tx-max-amount" type="number" placeholder="Max ₹..." value="${state.txState.maxAmount}" class="filter-input" style="width: 100px;" oninput="applyTxFilters()">
                
                <select id="tx-sort-by" class="filter-input" onchange="applyTxFilters()">
                    <option value="timestamp" ${state.txState.sortBy === 'timestamp' ? 'selected' : ''}>Sort: Timestamp</option>
                    <option value="amount" ${state.txState.sortBy === 'amount' ? 'selected' : ''}>Sort: Amount</option>
                    <option value="risk_score" ${state.txState.sortBy === 'risk_score' ? 'selected' : ''}>Sort: Risk Score</option>
                </select>

                <select id="tx-sort-order" class="filter-input" onchange="applyTxFilters()">
                    <option value="DESC" ${state.txState.sortOrder === 'DESC' ? 'selected' : ''}>DESC</option>
                    <option value="ASC" ${state.txState.sortOrder === 'ASC' ? 'selected' : ''}>ASC</option>
                </select>
                
                <button class="btn btn-sm" style="margin-left: auto;" onclick="resetTxFilters()">Reset</button>
            </div>
        </div>

        <div class="data-panel">
            <div class="panel-header" id="tx-panel-title">LOADING LEDGER TRANSACTIONS...</div>
            <div id="tx-grid-wrapper">
                <table style="width: 100%;">
                    <thead>
                        <tr style="border-bottom: 1.5px solid var(--border-color); background: rgba(0,0,0,0.2);">
                            <th>TRANSACTION ID</th>
                            <th>SENDER</th>
                            <th>RECEIVER</th>
                            <th>AMOUNT</th>
                            <th>CHANNEL</th>
                            <th>RISK PROFILE</th>
                            <th>TIMESTAMP</th>
                        </tr>
                    </thead>
                    <tbody id="tx-table-body"></tbody>
                </table>
            </div>
            
            <!-- Pagination Controls -->
            <div id="tx-pagination-controls" style="display: flex; justify-content: space-between; padding: 1rem 1.5rem; align-items: center; border-top: 1px solid var(--border-color); background: rgba(0,0,0,0.1); font-size: 0.75rem;">
                <button class="btn btn-sm" onclick="changeTxPage(-1)" id="tx-prev-btn">Previous Page</button>
                <span id="tx-page-indicator" style="font-family: 'JetBrains Mono', monospace; font-weight: bold; color: #888;">Page 1</span>
                <button class="btn btn-sm" onclick="changeTxPage(1)" id="tx-next-btn">Next Page</button>
            </div>
        </div>
    `;

    fetchAndRenderTxLedger();
}

async function fetchAndRenderTxLedger() {
    const tbody = document.getElementById("tx-table-body");
    const titleEl = document.getElementById("tx-panel-title");
    const paginator = document.getElementById("tx-pagination-controls");
    
    if (state.txState.activeTab === "intercepted") {
        paginator.style.display = "none";
        titleEl.innerText = "STREAM INTERCEPTIONS // RECENT 25 LIVE PACKETS";
        
        const feed = await apiFetch("/regulatory/alerts/feed");
        const list = feed || [
            { transaction_id: "TXN_SIM_001", account_id: "ACC000001", amount: 125000, channel: "UPI", risk_score: 0.85, timestamp: "2026-02-02 11:42" }
        ];

        tbody.innerHTML = list.map(tx => `
            <tr style="cursor: pointer;" onclick="openInvestigationModal('${tx.transaction_id || 'TXN_SIM_001'}')">
                <td style="font-family: 'JetBrains Mono', monospace; color: var(--cyan); font-weight: bold;">${tx.transaction_id || 'TXN_SIM_001'}</td>
                <td style="font-family: 'JetBrains Mono', monospace;">${tx.account_id}</td>
                <td style="font-family: 'JetBrains Mono', monospace; opacity: 0.5;">INTERCEPT_SINK</td>
                <td>INR ${(tx.amount || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                <td><span class="badge-source internal">${tx.channel || 'UPI'}</span></td>
                <td style="font-family: 'JetBrains Mono', monospace; font-weight: bold; color: ${tx.risk_score > 0.7 ? 'var(--red)' : tx.risk_score > 0.4 ? 'var(--amber)' : 'var(--green)'};">
                    ${(tx.risk_score || 0).toFixed(4)}
                </td>
                <td style="opacity: 0.5; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;">${tx.timestamp}</td>
            </tr>
        `).join('');
    } else {
        paginator.style.display = "flex";
        const riskTier = state.txState.activeTab === "suspicious" ? "high" : "all";
        titleEl.innerText = `SQL COMPLETE BANKING LEDGER // TAB: ${state.txState.activeTab.toUpperCase()}`;
        
        let url = `/transactions?page=${state.txState.page}&limit=${state.txState.limit}&risk_tier=${riskTier}&sort_by=${state.txState.sortBy}&sort_order=${state.txState.sortOrder}`;
        
        if (state.txState.search) url += `&search=${encodeURIComponent(state.txState.search)}`;
        if (state.txState.channel) url += `&channel=${state.txState.channel}`;
        if (state.txState.minAmount) url += `&min_amount=${state.txState.minAmount}`;
        if (state.txState.maxAmount) url += `&max_amount=${state.txState.maxAmount}`;

        const list = await apiFetch(url);
        
        if (!list || list.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" style="padding: 3rem; text-align: center; color: var(--red); font-style: italic;">NO MATCHING TRANSACTIONS FOUND IN SQL DATASET</td></tr>`;
            document.getElementById("tx-page-indicator").innerText = `Page ${state.txState.page} (Empty)`;
            return;
        }

        tbody.innerHTML = list.map(tx => `
            <tr style="cursor: pointer;" onclick="openInvestigationModal('${tx.transaction_id}')">
                <td style="font-family: 'JetBrains Mono', monospace; color: var(--cyan); font-weight: bold;">${tx.transaction_id}</td>
                <td style="font-family: 'JetBrains Mono', monospace; font-weight: 500;">${tx.sender_account}</td>
                <td style="font-family: 'JetBrains Mono', monospace; font-weight: 500;">${tx.receiver_account}</td>
                <td>INR ${tx.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                <td><span class="badge-source internal">${tx.channel}</span></td>
                <td style="font-family: 'JetBrains Mono', monospace; font-weight: bold; color: ${tx.risk_score > 0.7 ? 'var(--red)' : tx.risk_score > 0.4 ? 'var(--amber)' : 'var(--green)'};">
                    ${tx.risk_score.toFixed(4)}
                </td>
                <td style="opacity: 0.5; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;">${tx.timestamp}</td>
            </tr>
        `).join('');

        document.getElementById("tx-page-indicator").innerText = `Page ${state.txState.page}`;
        document.getElementById("tx-prev-btn").disabled = state.txState.page <= 1;
        document.getElementById("tx-next-btn").disabled = list.length < state.txState.limit;
    }
}

function toggleTxTab(tab) {
    state.txState.activeTab = tab;
    state.txState.page = 1;
    router();
}

function applyTxFilters() {
    state.txState.search = document.getElementById("tx-search").value;
    state.txState.channel = document.getElementById("tx-channel").value;
    state.txState.minAmount = document.getElementById("tx-min-amount").value;
    state.txState.maxAmount = document.getElementById("tx-max-amount").value;
    state.txState.sortBy = document.getElementById("tx-sort-by").value;
    state.txState.sortOrder = document.getElementById("tx-sort-order").value;
    state.txState.page = 1;
    fetchAndRenderTxLedger();
}

function resetTxFilters() {
    state.txState.search = "";
    state.txState.channel = "";
    state.txState.minAmount = "";
    state.txState.maxAmount = "";
    state.txState.sortBy = "timestamp";
    state.txState.sortOrder = "DESC";
    state.txState.page = 1;
    router();
}

function changeTxPage(offset) {
    state.txState.page += offset;
    if (state.txState.page < 1) state.txState.page = 1;
    fetchAndRenderTxLedger();
}

// --- SUBPAGE 3: ACCOUNTS PAGE (ACCEPTABLE, ENHANCED VISUALIZATION & SPACING) ---
async function renderAccounts(container) {
    const accs = await apiFetch("/accounts?limit=25");
    if (!accs) return container.innerHTML = renderOffline();

    container.innerHTML = `
        <h2 class="section-title">Account Profiler Node Bank</h2>
        <div class="data-panel">
            <div class="panel-header">SECURITY PROFILE LEDGER // ENHANCED SPACING & HOVER EFFECTS</div>
            <table>
                <thead>
                    <tr>
                        <th>Account ID</th>
                        <th>Name</th>
                        <th>Segment</th>
                        <th>Geography</th>
                        <th>Status</th>
                        <th>Security Profile</th>
                        <th>Contagion PageRank</th>
                    </tr>
                </thead>
                <tbody>
                    ${accs.map(a => {
                        const score = a.pagerank || 0.0001;
                        const scorePct = Math.min(100, score * 10000000000000000000); // Visual amplification
                        const scoreColor = a.risk_profile === 'high' ? 'var(--red)' : a.risk_profile === 'medium' ? 'var(--amber)' : 'var(--green)';
                        return `
                            <tr style="cursor: pointer;" onclick="openAccountModal('${a.account_id}')">
                                <td style="font-family: 'JetBrains Mono', monospace; color: var(--cyan); font-weight: bold;">${a.account_id}</td>
                                <td>${a.name || 'Account Holder'}</td>
                                <td><span style="font-size: 0.72rem; color: #888;">${a.customer_segment}</span></td>
                                <td>${a.city}</td>
                                <td><span class="badge-source internal">${a.status}</span></td>
                                <td>
                                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                                        <span class="risk-${a.risk_profile}" style="font-weight: 700; font-size: 0.7rem; text-transform: uppercase;">${a.risk_profile}</span>
                                        <div style="background: rgba(255,255,255,0.05); width: 60px; height: 5px; border-radius: 4px; overflow: hidden;">
                                            <div style="background: ${scoreColor}; width: ${a.risk_profile === 'high' ? '90' : a.risk_profile === 'medium' ? '50' : '15'}%; height: 100%;"></div>
                                        </div>
                                    </div>
                                </td>
                                <td style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;">${score.toFixed(6)}</td>
                            </tr>
                        `;
                    }).join('')}
                </tbody>
            </table>
        </div>
    `;
}

// --- SUBPAGE 4: GRAPH PAGE (COMPLETE FORCE-DIRECTED REDESIGN WITH MONEY FLOW PATH TRACING & SIDE PANEL) ---
async function renderGraph(container) {
    const rings = await apiFetch("/graph/fraud-rings");
    
    container.innerHTML = `
        <h2 class="section-title">Personalized PageRank & Community Contagion</h2>
        
        <div class="graph-layout">
            <!-- Left: D3 Viewport with Investigator Bar -->
            <div id="graph-view-card" class="data-panel" style="display: flex; flex-direction: column;">
                <div class="panel-header" style="display: flex; justify-content: space-between; align-items: center;">
                    <span id="graph-header-title">COMMUNITY STRUCTURE VISUALIZER</span>
                    
                    <div style="display: flex; gap: 0.5rem; align-items: center;">
                        <select id="graph-ring-selector" class="filter-input" style="padding: 2px 6px; font-size: 0.65rem;" onchange="loadCommunityGraphData()">
                            ${rings && rings.length > 0 ? rings.map(r => `
                                <option value="${r.community_id}">Community #${r.community_id} (Risk: ${(r.avg_risk*100).toFixed(1)}%)</option>
                            `).join('') : `
                                <option value="COMM_001">Community #1</option>
                            `}
                        </select>
                        <button class="btn btn-sm" id="btn-trace-investigator" onclick="toggleInvestigatorMode()">INVESTIGATOR: TRACE MONEY</button>
                    </div>
                </div>
                
                <div style="flex: 1; background: #020202; position: relative;">
                    <svg id="graph-svg" style="width: 100%; height: 100%;"></svg>
                    
                    <!-- Alert bar overlay if Investigator mode is active -->
                    <div id="investigator-toast" style="display: none; position: absolute; bottom: 1.5rem; left: 1.5rem; background: rgba(6, 182, 212, 0.15); border: 1.5px solid var(--cyan); border-radius: 8px; padding: 0.75rem 1.25rem; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; color: #FFF; box-shadow: 0 0 20px rgba(6,182,212,0.2);">
                        ⚡ <strong>INVESTIGATOR MODE ENABLED</strong>: Click any node to designate the origin seed node and trace funds path!
                    </div>
                </div>
            </div>

            <!-- Right: Intelligence Side Panel -->
            <div class="data-panel intel-side-panel">
                <div class="intel-side-header">
                    <h3>Node Intelligence Report</h3>
                    <span style="font-size: 0.62rem; color: #666; letter-spacing: 0.05em;">SYSTEM LEDGER INTERIOR</span>
                </div>
                
                <div id="intel-side-body" style="font-size: 0.8rem; line-height: 1.6; color: #BBB;">
                    <div style="text-align: center; padding: 3rem 0; opacity: 0.4; font-style: italic;">
                        SELECT A SYSTEM SUSPECT NODE TO COMPILE FULL GRAPH FORENSICS
                    </div>
                </div>
            </div>
        </div>
    `;

    if (rings && rings.length > 0) {
        state.graphState.selectedCommunityId = rings[0].community_id;
    } else {
        state.graphState.selectedCommunityId = "COMM_001";
    }
    loadCommunityGraphData();
}

async function loadCommunityGraphData() {
    const selector = document.getElementById("graph-ring-selector");
    if (selector) {
        state.graphState.selectedCommunityId = selector.value;
    }
    
    const cid = state.graphState.selectedCommunityId;
    const data = await apiFetch(`/graph/community/${cid}`);
    
    // Solid fallbacks if offline
    state.graphState.graphData = data || {
        nodes: [
            { account_id: "ACC000001", name: "Dinesh Kumar", risk_profile: "high", status: "GOVT_FLAGGED", pagerank: 0.0028, propagated_risk_score: 0.94 },
            { account_id: "ACC000004", name: "Sunita Sharma", risk_profile: "high", status: "RFA", pagerank: 0.0014, propagated_risk_score: 0.76 },
            { account_id: "ACC000007", name: "Amit Patel", risk_profile: "medium", status: "WATCHLIST", pagerank: 0.0008, propagated_risk_score: 0.52 },
            { account_id: "ACC000010", name: "Vikram Singh", risk_profile: "low", status: "ACTIVE", pagerank: 0.0003, propagated_risk_score: 0.12 }
        ],
        edges: [
            { source: "ACC000001", target: "ACC000004", amount: 65000, channel: "UPI" },
            { source: "ACC000001", target: "ACC000007", amount: 60000, channel: "IMPS" },
            { source: "ACC000004", target: "ACC000010", amount: 55000, channel: "CARD" }
        ]
    };

    drawCinematicForceGraph();
}

function drawCinematicForceGraph() {
    const svg = d3.select("#graph-svg");
    svg.selectAll("*").remove();

    const viewport = document.getElementById("graph-view-card");
    const width = viewport.clientWidth - 340;
    const height = 480;
    svg.attr("width", width).attr("height", height);

    const graph = state.graphState.graphData;
    const nodes = graph.nodes.map(d => ({ ...d }));
    
    // Map links correctly
    const links = graph.edges.map(d => ({
        ...d,
        source: nodes.find(n => n.account_id === d.source) || d.source,
        target: nodes.find(n => n.account_id === d.target) || d.target
    })).filter(l => typeof l.source === 'object' && typeof l.target === 'object');

    const simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(d => d.account_id).distance(100))
        .force("charge", d3.forceManyBody().strength(-250))
        .force("center", d3.forceCenter(width / 2, height / 2))
        .force("collision", d3.forceCollide().radius(24));

    // Arrow markers
    svg.append("defs").append("marker")
        .attr("id", "arrowhead")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 18)
        .attr("refY", 0)
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M0,-5L10,0L0,5")
        .attr("fill", "rgba(255,255,255,0.15)");

    const link = svg.append("g")
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke", "rgba(255,255,255,0.08)")
        .attr("stroke-width", d => Math.max(1.5, Math.min(6, (d.amount || 1000) / 20000)))
        .attr("marker-end", "url(#arrowhead)");

    const node = svg.append("g")
        .selectAll("g")
        .data(nodes)
        .join("g")
        .style("cursor", "pointer")
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

    // Node colors: Blue (Normal), Orange (Suspicious), Red (Confirmed Mule), Purple (Watchlist)
    const nodeColor = d => {
        if (d.status === 'GOVT_FLAGGED' || d.status === 'MULE') return "var(--red)";
        if (d.status === 'WATCHLIST' || d.status === 'RFA') return "var(--violet)";
        if (d.risk_profile === 'high' || d.propagated_risk_score > 0.5) return "var(--amber)";
        return "var(--cyan)";
    };

    node.append("circle")
        .attr("r", d => 7 + (d.propagated_risk_score || 0) * 10)
        .attr("fill", nodeColor)
        .attr("stroke", "#000")
        .attr("stroke-width", 1.5)
        .attr("class", "graph-circle-node");

    node.append("text")
        .attr("dy", 20)
        .attr("text-anchor", "middle")
        .attr("fill", "#888")
        .attr("font-size", "8px")
        .attr("font-family", "JetBrains Mono, monospace")
        .text(d => d.account_id);

    node.on("click", (event, d) => {
        if (state.graphState.investigatorMode) {
            triggerInvestigatorTrace(d.account_id);
        } else {
            loadNodeForensics(d);
        }
    });

    simulation.on("tick", () => {
        link.attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);

        node.attr("transform", d => `translate(${d.x},${d.y})`);
    });

    function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
    }
    function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
    }
    function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
    }
}

function loadNodeForensics(node) {
    const side = document.getElementById("intel-side-body");
    if (!side) return;

    state.graphState.selectedNode = node;
    const scoreColor = node.propagated_risk_score > 0.7 ? 'var(--red)' : node.propagated_risk_score > 0.4 ? 'var(--amber)' : 'var(--green)';
    
    side.innerHTML = `
        <div class="score-display" style="margin-bottom: 1.25rem;">
            <div class="score-circle" style="border-color: ${scoreColor}; color: ${scoreColor};">
                ${Math.round(node.propagated_risk_score * 100)}%
            </div>
            <div>
                <strong>Propagated Risk Score</strong><br>
                <span style="font-size: 0.65rem; color: #666; font-family: 'JetBrains Mono', monospace;">Score: ${node.propagated_risk_score.toFixed(4)}</span>
            </div>
        </div>

        <p style="margin-bottom: 0.6rem;"><strong>ACCOUNT ID:</strong><br><span style="color: var(--cyan); font-family: 'JetBrains Mono', monospace;">${node.account_id}</span></p>
        <p style="margin-bottom: 0.6rem;"><strong>HOLDER NAME:</strong><br>${node.name}</p>
        <p style="margin-bottom: 0.6rem;"><strong>PAGERANK INDEX:</strong><br><span style="font-family: 'JetBrains Mono', monospace;">${(node.pagerank || 0.0001).toFixed(6)}</span></p>
        <p style="margin-bottom: 0.6rem;"><strong>COMMUNITY CLUSTER:</strong><br><span style="color: var(--violet);">Cluster #${node.community_id}</span></p>
        <p style="margin-bottom: 0.6rem;"><strong>SECURITY PROFILE:</strong><br><span class="risk-${node.risk_profile}" style="font-weight: 700; text-transform: uppercase;">${node.risk_profile}</span></p>
        
        <div style="border-top: 1px solid var(--border-color); padding-top: 1rem; margin-top: 1rem;">
            <strong>Suspicious Indicators:</strong>
            <ul style="margin-left: 1.2rem; margin-top: 0.4rem; list-style-type: square; font-size: 0.75rem;">
                ${node.propagated_risk_score > 0.6 ? '<li>Elevated Personal PageRank Threat</li>' : ''}
                ${node.risk_profile === 'high' ? '<li>Core Security Tabular Anomaly</li>' : ''}
                ${node.status === 'GOVT_FLAGGED' ? '<li>Government NCRP complaint flagged</li>' : ''}
                ${node.status === 'RFA' ? '<li>Red-Flagged CRILC monitoring window</li>' : ''}
                ${node.propagated_risk_score <= 0.4 && node.risk_profile !== 'high' ? '<li>Standard transactional parameters within threshold</li>' : ''}
            </ul>
        </div>

        <div style="margin-top: 1.5rem; display: flex; flex-direction: column; gap: 0.5rem;">
            <button class="btn btn-sm" onclick="openAccountModal('${node.account_id}')">Open Full Audit Profile</button>
            <button class="btn btn-sm" style="border-color: var(--red); color: var(--red);" onclick="flagAccount('${node.account_id}')">Flag Suspect Node</button>
        </div>
    `;
}

function toggleInvestigatorMode() {
    state.graphState.investigatorMode = !state.graphState.investigatorMode;
    const btn = document.getElementById("btn-trace-investigator");
    const toast = document.getElementById("investigator-toast");
    
    if (state.graphState.investigatorMode) {
        btn.innerText = "CANCEL TRACING MODE";
        btn.style.borderColor = "var(--red)";
        btn.style.color = "var(--red)";
        toast.style.display = "block";
    } else {
        btn.innerText = "INVESTIGATOR: TRACE MONEY";
        btn.style.borderColor = "var(--cyan)";
        btn.style.color = "var(--cyan)";
        toast.style.display = "none";
        
        // Remove particle tracing
        d3.select("#graph-svg").selectAll(".trace-particle").remove();
        d3.select("#graph-svg").selectAll("line").attr("stroke", "rgba(255,255,255,0.08)").attr("stroke-width", d => Math.max(1.5, Math.min(6, (d.amount || 1000) / 20000)));
        d3.selectAll(".graph-circle-node").attr("stroke", "#000").attr("stroke-width", 1.5);
    }
}

function triggerInvestigatorTrace(startNodeId) {
    state.graphState.traceStartNodeId = startNodeId;
    alert(`Investigating downstream routing from origin: ${startNodeId}`);
    
    const svg = d3.select("#graph-svg");
    const graph = state.graphState.graphData;
    
    // Run DFS/BFS money flow path highlight
    const visited = new Set();
    const highlightPath = [];
    const particles = [];
    
    const trace = (nodeId) => {
        visited.add(nodeId);
        const outputs = graph.edges.filter(e => e.source === nodeId);
        outputs.forEach(e => {
            highlightPath.push(e);
            particles.push(e);
            if (!visited.has(e.target)) {
                trace(e.target);
            }
        });
    };
    
    trace(startNodeId);
    
    // Highlight links
    svg.selectAll("line")
        .transition().duration(500)
        .attr("stroke", l => {
            const match = highlightPath.some(hp => hp.source === l.source.account_id && hp.target === l.target.account_id);
            return match ? "var(--red)" : "rgba(255,255,255,0.02)";
        })
        .attr("stroke-width", l => {
            const match = highlightPath.some(hp => hp.source === l.source.account_id && hp.target === l.target.account_id);
            return match ? 4 : 1;
        });

    // Highlight nodes
    svg.selectAll(".graph-circle-node")
        .transition().duration(500)
        .attr("stroke", n => visited.has(n.account_id) ? "var(--red)" : "#000")
        .attr("stroke-width", n => visited.has(n.account_id) ? 3 : 1.5);

    // Animate flow particles along links!
    svg.selectAll(".trace-particle").remove();
    
    particles.forEach(p => {
        const linkLine = svg.selectAll("line").filter(l => l.source.account_id === p.source && l.target.account_id === p.target);
        if (!linkLine.empty()) {
            const sourceX = linkLine.datum().source.x;
            const sourceY = linkLine.datum().source.y;
            const targetX = linkLine.datum().target.x;
            const targetY = linkLine.datum().target.y;
            
            const particle = svg.append("circle")
                .attr("class", "trace-particle")
                .attr("r", 4)
                .attr("fill", "var(--cyan)")
                .attr("cx", sourceX)
                .attr("cy", sourceY)
                .style("box-shadow", "0 0 10px var(--cyan)");

            function repeat() {
                particle
                    .attr("cx", sourceX)
                    .attr("cy", sourceY)
                    .transition()
                    .duration(1200)
                    .ease(d3.easeQuadInOut)
                    .attr("cx", targetX)
                    .attr("cy", targetY)
                    .on("end", repeat);
            }
            repeat();
        }
    });
}

// --- SUBPAGE 5: ALERTS PAGE (WINDOWS 98 COMPLIANCE STYLE CARD WORKSTATION) ---
async function renderAlertConsole(container) {
    container.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
            <h2 class="section-title" style="margin-bottom: 0;">Compliance Alert Hub</h2>
            <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #888;">THEME: RETRO LEGACY WORKSTATION</span>
        </div>

        <div class="alerts-win98-grid">
            <!-- Col 1: Government Cyber complaint cases -->
            <div class="legacy-terminal" style="display: flex; flex-direction: column; height: 100%;">
                <div class="legacy-title-bar">
                    <span>NCRP_GOVT_complaint_cases.EXE</span>
                    <div style="display: flex; gap: 2px;">
                        <button class="legacy-btn-close">?</button>
                        <button class="legacy-btn-close">X</button>
                    </div>
                </div>
                <div class="legacy-content-box" style="flex: 1;" id="win98-ncrp-container"></div>
            </div>

            <!-- Col 2: High Velocity transaction monitoring alerts -->
            <div class="legacy-terminal" style="display: flex; flex-direction: column; height: 100%;">
                <div class="legacy-title-bar">
                    <span>TMS_FMS_HIGH_VELOCITY.EXE</span>
                    <div style="display: flex; gap: 2px;">
                        <button class="legacy-btn-close">?</button>
                        <button class="legacy-btn-close">X</button>
                    </div>
                </div>
                <div class="legacy-content-box" style="flex: 1;" id="win98-tms-container"></div>
            </div>

            <!-- Col 3: Cross Channel hopping trails -->
            <div class="legacy-terminal" style="display: flex; flex-direction: column; height: 100%;">
                <div class="legacy-title-bar">
                    <span>CROSS_CHANNEL_HOPPING_TRAILS.EXE</span>
                    <div style="display: flex; gap: 2px;">
                        <button class="legacy-btn-close">?</button>
                        <button class="legacy-btn-close">X</button>
                    </div>
                </div>
                <div class="legacy-content-box" style="flex: 1;" id="win98-cc-container"></div>
            </div>
        </div>
    `;

    const populateWin98Alerts = async () => {
        const feed = await apiFetch("/regulatory/alerts/feed");
        
        // High fidelity retro alerts fallback
        const alertsList = feed || [
            { id: "1", account_id: "ACC000001", fraud_type: "CYBER_FRAUD_TICKET", severity: "CRITICAL", timestamp: "2026-02-02 11:42", description: "I4C NCRP Ticket #29103 - Category: MULE_SUSPECTED" },
            { id: "2", account_id: "ACC000032", fraud_type: "VELOCITY_BREACH", severity: "HIGH", timestamp: "2026-02-02 10:15", description: "TMS Alert: Velocity breach on channel UPI - exceeds transaction limit." },
            { id: "3", account_id: "ACC000045", fraud_type: "CHANNEL_HOP", severity: "HIGH", timestamp: "2026-02-02 09:30", description: "Cross-channel hopping: rapid IMPS -> CARD_POS -> NEFT transfers." }
        ];

        const ncrp = document.getElementById("win98-ncrp-container");
        const tms = document.getElementById("win98-tms-container");
        const cc = document.getElementById("win98-cc-container");

        ncrp.innerHTML = "";
        tms.innerHTML = "";
        cc.innerHTML = "";

        alertsList.forEach(a => {
            const isGovt = a.fraud_type === "CYBER_FRAUD_TICKET" || a.source === "GOVT_CYBER" || (a.description && a.description.includes("NCRP"));
            const isCC = a.fraud_type === "CHANNEL_HOP" || a.source === "CROSS_CHANNEL" || (a.description && a.description.toLowerCase().includes("hop"));
            
            const card = document.createElement("div");
            card.className = "win98-alert-card";
            
            const isUrgent = a.severity === "CRITICAL" || a.severity === "HIGH";
            const headerClass = isUrgent ? "win98-alert-header urgent" : "win98-alert-header";
            
            card.innerHTML = `
                <div class="${headerClass}">
                    <span>${isGovt ? "GOVT_CYBER" : isCC ? "CROSS_CHANNEL" : "TMS_FMS"}</span>
                    <span>${a.severity}</span>
                </div>
                <div style="font-family: 'Courier New', Courier, monospace; font-size: 11px; font-weight: bold; color: #000; margin-bottom: 4px;">
                    ACC_ID: <span style="text-decoration: underline; cursor: pointer;" onclick="openAccountModal('${a.account_id}')">${a.account_id}</span>
                </div>
                <div style="font-family: inherit; font-size: 11px; color: #333; line-height: 1.4; margin-bottom: 6px; border: 1px solid #CCC; padding: 4px; background: #FFF;">
                    ${a.description || a.fraud_type}
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; font-size: 9px; color: #666;">
                    <span>${a.timestamp}</span>
                    <div>
                        <button class="legacy-btn" style="padding: 1px 4px; font-size: 9px;" onclick="openInvestigationModal('${a.transaction_id || 'TXN_SIM_001'}')">INV</button>
                        <button class="legacy-btn" style="padding: 1px 4px; font-size: 9px;" onclick="alert('Case Dismissed')">DISMISS</button>
                    </div>
                </div>
            `;

            if (isGovt) {
                ncrp.appendChild(card);
            } else if (isCC) {
                cc.appendChild(card);
            } else {
                tms.appendChild(card);
            }
        });
    };

    populateWin98Alerts();
    state.alertsConsoleInterval = setInterval(populateWin98Alerts, 10000);
}

// --- SUBPAGE 6: MONEY FLOW PAGE (ACCEPTABLE, ENHANCED MOTION NARRATIVE) ---
async function renderMoneyFlow(container) {
    container.innerHTML = `
        <h2 class="section-title">Money Flow Tracer</h2>
        <div style="margin-bottom: 1.5rem; display: flex; gap: 1rem; align-items: center;">
            <input id="flow-target-account" type="text" placeholder="ENTER ACCOUNT ID" value="ACC000001" style="background: #000; border: 1px solid var(--border-color); border-radius: 8px; color: #FFF; padding: 0.5rem 1rem; font-family: 'JetBrains Mono', monospace;">
            <button class="btn" onclick="executeFlowTrace()">TRACE DOWNSTREAM ROUTING</button>
        </div>
        
        <div class="money-flow-grid">
            <div id="flow-svg-viewport">
                <div class="panel-header" style="position: absolute; top:0; left:0; width:100%; z-index:10;">DOWNSTREAM FLOW PATH D3 TRACER</div>
                <svg id="flow-svg" style="width: 100%; height: 100%;"></svg>
            </div>
            
            <div class="data-panel" style="display: flex; flex-direction: column;">
                <div class="panel-header">DOWNSTREAM INTEL FORENSICS</div>
                <div style="padding: 2rem; flex: 1; display: flex; flex-direction: column; justify-content: space-between;">
                    <div id="flow-summary-text" style="font-size: 0.95rem; line-height: 1.8; color: #DDD;">
                        Awaiting money flow execution trace...
                    </div>
                    <div id="str-generation-container" style="display: none; margin-top: 2rem;">
                        <button class="btn" style="width: 100%; border-color: var(--violet); color: var(--violet);" onclick="fileStrFromFlow()">AUTO-GENERATE PENDING STR CANDIDATE</button>
                    </div>
                </div>
            </div>
        </div>
    `;

    executeFlowTrace();
}

async function executeFlowTrace() {
    const aid = document.getElementById("flow-target-account").value;
    const textEl = document.getElementById("flow-summary-text");
    const strContainer = document.getElementById("str-generation-container");
    
    textEl.innerHTML = "Tracing fund routing nodes...";
    
    const flow = await apiFetch(`/mule/trace/${aid}/downstream`);
    
    const data = flow || {
        account_id: aid,
        narrative: `₹125,000 entered via VENDOR channels. Split to 2 relay accounts. Estimated cash-out: ₹110,000 via CARD_POS.`,
        flow_graph: {
            nodes: [
                { id: aid, type: "origin" },
                { id: "ACC000004", type: "relay" },
                { id: "ACC000007", type: "relay" },
                { id: "ACC000010", type: "cashout" },
                { id: "ACC000012", type: "cashout" }
            ],
            edges: [
                { source: aid, target: "ACC000004", amount: 65000 },
                { source: aid, target: "ACC000007", amount: 60000 },
                { source: "ACC000004", target: "ACC000010", amount: 55000 },
                { source: "ACC000007", target: "ACC000012", amount: 55000 }
            ]
        }
    };

    textEl.innerHTML = `<p style="margin-bottom: 1.5rem;"><strong>DOWNSTREAM SUMMARY:</strong></p>
                        <p style="font-size: 1.15rem; color: #FFF; font-style: italic; line-height: 1.6; border-left: 2px solid var(--cyan); padding-left: 1rem;">"${data.narrative}"</p>`;
    
    if (data.narrative.includes("1,00,000") || data.narrative.includes("100,000") || data.narrative.includes("125,000") || data.narrative.includes("₹")) {
        strContainer.style.display = "block";
        strContainer.dataset.accountId = aid;
    } else {
        strContainer.style.display = "none";
    }

    drawDownstreamFlow(data.flow_graph);
}

// --- SUBPAGE 7: EWS PAGE (ACCEPTABLE, UPGRADED PROGRESS BARS & SCORING) ---
async function renderEws(container) {
    container.innerHTML = `
        <h2 class="section-title">Early Warning System Anomaly Grid</h2>
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
            <div style="font-size: 1rem; font-weight: bold; color: var(--amber);">
                <span id="ews-alerts-badge-num" style="font-family: 'JetBrains Mono', monospace; font-size: 1.2rem; color: #FFF;">--</span> accounts flagged in pre-mule state (EWS > 0.6)
            </div>
            <button class="btn btn-sm" onclick="triggerEwsScanNow()">SCAN COMPLETE SQL NETWORK NOW</button>
        </div>
        
        <div class="data-panel">
            <div class="panel-header">PRE-MULE HOT FLAGGED ALERTS</div>
            <table>
                <thead>
                    <tr>
                        <th>Account ID</th>
                        <th>EWS Composite score</th>
                        <th>Triggered Indicators</th>
                        <th>Account Age</th>
                        <th>Last Activity Time</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody id="ews-table-body"></tbody>
            </table>
        </div>
    `;

    const populateEws = async () => {
        const alerts = await apiFetch("/mule/ews/alerts");
        
        const dataList = alerts || [
            { account_id: "ACC000010", ews_score: 0.85, triggered_signals: ["NEW_DEVICE", "DORMANCY_BREAK", "HIGH_VELOCITY"], account_age_days: 120, last_active: "2026-02-02 11:15" },
            { account_id: "ACC000034", ews_score: 0.64, triggered_signals: ["NEW_BENEFICIARY", "FAN_OUT_SPIKE"], account_age_days: 45, last_active: "2026-02-02 10:42" }
        ];

        document.getElementById("ews-alerts-badge-num").innerText = dataList.filter(a => a.ews_score >= 0.6).length;

        const tbody = document.getElementById("ews-table-body");
        tbody.innerHTML = dataList.map(a => {
            const isRed = a.ews_score >= 0.6;
            const isAmber = a.ews_score >= 0.4 && a.ews_score < 0.6;
            const barClass = isRed ? "ews-pulsing-red" : "";
            const barColor = isRed ? "var(--red)" : isAmber ? "var(--amber)" : "var(--green)";
            
            return `
                <tr>
                    <td style="font-family: 'JetBrains Mono', monospace; font-weight: bold; color: var(--cyan);" onclick="openAccountModal('${a.account_id}')">
                        ${a.account_id}
                    </td>
                    <td>
                        <div style="display: flex; align-items: center; gap: 1rem; width: 150px;">
                            <div class="ews-bar-container">
                                <div class="ews-bar-fill ${barClass}" style="width: ${a.ews_score * 100}%; background: ${barColor};"></div>
                            </div>
                            <span style="font-family: 'JetBrains Mono', monospace; font-weight: bold;">${(a.ews_score).toFixed(2)}</span>
                        </div>
                    </td>
                    <td>
                        ${a.triggered_signals.map(s => `<span class="ews-tag-badge">${s}</span>`).join('')}
                    </td>
                    <td>${a.account_age_days} days</td>
                    <td style="opacity: 0.5; font-family: 'JetBrains Mono', monospace; font-size: 0.75rem;">${a.last_active}</td>
                    <td>
                        <button class="btn btn-sm" style="padding: 2px 6px; font-size: 0.65rem;" onclick="dismissEwsAlert('${a.account_id}')">DISMISS</button>
                        <button class="btn btn-sm" style="padding: 2px 6px; font-size: 0.65rem; border-color: var(--violet); color: var(--violet);" onclick="investigateEwsAccount('${a.account_id}')">INVESTIGATE</button>
                    </td>
                </tr>
            `;
        }).join('');
    };

    populateEws();
}

// --- SUBPAGE 8: REGULATORY PAGE (COMPLETE WINDOWS 98 SYSTEM HEALTH WORKSTATION) ---
async function renderRegulatory(container) {
    const strs = await apiFetch("/regulatory/strs");
    const rfa = await apiFetch("/regulatory/rfa");
    const watchlist = await apiFetch("/regulatory/watchlist");

    const pendingStrs = strs || [
        { str_id: "STR_001", account_id: "ACC000001", risk_score: 0.9254, days_since_triggered: 6 }
    ];

    const rfaList = rfa ? rfa.rfa_accounts : [
        { account_id: "ACC000001", name: "Dinesh Kumar", flagged_date: "2026-02-01", crilc_report_deadline: "2026-02-04" }
    ];

    const wlList = watchlist ? watchlist.watchlist : [
        { account_id: "ACC000001", name: "Dinesh Kumar", source: "I4C_NCRP", reason: "Accused account flagged in NCRP portal" }
    ];

    container.innerHTML = `
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
            <h2 class="section-title" style="margin-bottom: 0;">Compliance Workstation Core</h2>
            <span style="font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; color: #888;">THEME: RETRO REGULATORY OFFICE</span>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 1.5rem;">
            <!-- STR Queue (Windows 98) -->
            <div class="legacy-terminal">
                <div class="legacy-title-bar">
                    <span>STR_PENDING_QUEUE.EXE [${pendingStrs.length} ACTIVE]</span>
                    <div style="display: flex; gap: 2px;">
                        <button class="legacy-btn-close">?</button>
                        <button class="legacy-btn-close">X</button>
                    </div>
                </div>
                <div class="legacy-content-box" style="height: 250px;">
                    <table class="legacy-table">
                        <thead>
                            <tr>
                                <th>STR ID</th>
                                <th>Account</th>
                                <th>Risk Score</th>
                                <th>Window (Days)</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${pendingStrs.map(s => {
                                const age = s.days_since_triggered;
                                const isRed = age >= 6;
                                const isAmber = age >= 5 && age < 6;
                                const ageColor = isRed ? "#FF0000" : isAmber ? "#FF8000" : "#00AA00";
                                return `
                                    <tr>
                                        <td>${s.str_id}</td>
                                        <td style="font-weight: bold; text-decoration: underline; cursor: pointer;" onclick="openAccountModal('${s.account_id}')">${s.account_id}</td>
                                        <td>${(s.risk_score * 100).toFixed(1)}%</td>
                                        <td style="color: ${ageColor}; font-weight: bold;">
                                            ${age} Days ${isRed ? '🚨' : ''}
                                        </td>
                                        <td>
                                            <button class="legacy-btn" onclick="fileStr('${s.str_id}')">FILE REPORT</button>
                                        </td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- CRILC red flagged accounts (Windows 98) -->
            <div class="legacy-terminal">
                <div class="legacy-title-bar">
                    <span>CRILC_RED_FLAGGED_COMPLIANCE.EXE</span>
                    <div style="display: flex; gap: 2px;">
                        <button class="legacy-btn-close">?</button>
                        <button class="legacy-btn-close">X</button>
                    </div>
                </div>
                <div class="legacy-content-box" style="height: 250px;">
                    <table class="legacy-table">
                        <thead>
                            <tr>
                                <th>Account</th>
                                <th>CRILC Deadline</th>
                                <th>Days Left</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${rfaList.map(r => {
                                const daysLeft = Math.round((new Date(r.crilc_report_deadline) - new Date("2026-02-02")) / (1000 * 60 * 60 * 24));
                                const isUrgent = daysLeft < 2;
                                return `
                                    <tr>
                                        <td style="font-weight: bold; text-decoration: underline; cursor: pointer;" onclick="openAccountModal('${r.account_id}')">${r.account_id}</td>
                                        <td>${r.crilc_report_deadline}</td>
                                        <td style="font-weight: bold; color: ${isUrgent ? '#FF0000' : '#000000'};">
                                            ${daysLeft} Days ${isUrgent ? '⚠️' : ''}
                                        </td>
                                        <td>
                                            <button class="legacy-btn" onclick="syncCrilc('${r.account_id}')">REPORT CRILC</button>
                                        </td>
                                    </tr>
                                `;
                            }).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem;">
            <!-- Left: RBI/FIU-IND Central watchlist caution feed -->
            <div class="data-panel">
                <div class="panel-header">RBI / FIU-IND WATCHLIST feed</div>
                <div style="padding: 1rem; max-height: 240px; overflow-y: auto;">
                    ${wlList.map(w => `
                        <div class="alert-item" style="border-bottom: 1px solid rgba(255,255,255,0.03); padding: 0.6rem 0;" onclick="openAccountModal('${w.account_id}')">
                            <div>
                                <span class="badge-source govt_cyber" style="margin-right: 0.5rem;">${w.source || "NCRP"}</span>
                                <strong style="color: var(--cyan); font-family: 'JetBrains Mono', monospace;">${w.account_id}</strong>
                                <span style="font-size: 0.72rem; color: #888; margin-left: 0.4rem;">(${w.name})</span>
                            </div>
                            <div style="font-size: 0.72rem; opacity: 0.6; margin-top: 0.2rem;">
                                Reason: ${w.reason}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>

            <!-- Right: System Compliance Sync Health Console -->
            <div class="data-panel">
                <div class="panel-header">COMPLIANCE SYNC & HEALTH CONSOLE</div>
                <div style="padding: 1.25rem; display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; font-size: 0.8rem; font-family: 'JetBrains Mono', monospace;">
                    <div>☑ EWS Scanning: <strong style="color: var(--emerald);">ACTIVE</strong></div>
                    <div>☑ STR Reporting: <strong style="color: var(--emerald);">ACTIVE</strong></div>
                    <div>☑ CRILC Tracker: <strong style="color: var(--emerald);">ACTIVE</strong></div>
                    <div>☑ I4C Feed Sync: <strong style="color: var(--emerald);">ACTIVE</strong></div>
                    <div>☑ Audit Logger: <strong style="color: var(--emerald);">ACTIVE</strong></div>
                    <div>☑ Kafka Ingest: <strong style="color: ${state.isOffline ? 'var(--red)' : 'var(--emerald)'};">${state.isOffline ? 'OFFLINE' : 'LIVE'}</strong></div>
                </div>
            </div>
        </div>
    `;
}

// --- SUBPAGE 9: CHANNELS PAGE (HYBRID CLINICAL CINEMATIC / RETRO WORKSTATION) ---
async function renderCrossChannel(container) {
    const hops = await apiFetch("/cross-channel/hop-alerts");
    const hopAlerts = hops || [
        { account_id: "ACC000001", channels_involved: ["NEFT", "UPI", "ATM"], time_window_minutes: 60, unique_channels_count: 3, transactions: [] }
    ];

    container.innerHTML = `
        <h2 class="section-title">Cross-Channel Analytics</h2>
        
        <div style="display: grid; grid-template-columns: 1fr 1.2fr; gap: 1.5rem; margin-bottom: 1.5rem;">
            <!-- Left: Cinematic Volume Breakdown -->
            <div class="data-panel">
                <div class="panel-header">CHANNEL volume & FRAUD BREAKDOWN</div>
                <div class="css-chart-container">
                    ${renderChannelVolumeRow("UPI", 88, "INR 182.4 Cr", "var(--cyan)")}
                    ${renderChannelVolumeRow("IMPS", 65, "INR 94.2 Cr", "var(--violet)")}
                    ${renderChannelVolumeRow("NEFT", 48, "INR 342.1 Cr", "var(--pink)")}
                    ${renderChannelVolumeRow("RTGS", 28, "INR 512.4 Cr", "var(--emerald)")}
                    ${renderChannelVolumeRow("CARD", 35, "INR 12.8 Cr", "var(--amber)")}
                </div>
            </div>

            <!-- Right: Windows 98 suspicious hops sequence tracker -->
            <div class="legacy-terminal" style="display: flex; flex-direction: column;">
                <div class="legacy-title-bar">
                    <span>SUSPICIOUS_MULTI_CHANNEL_HOPS.EXE</span>
                    <div style="display: gap; 2px;">
                        <button class="legacy-btn-close">?</button>
                        <button class="legacy-btn-close">X</button>
                    </div>
                </div>
                <div class="legacy-content-box" style="flex: 1; max-height: 250px; overflow-y: auto;">
                    ${hopAlerts.map(h => `
                        <div style="border-bottom: 1px solid #CCC; padding-bottom: 6px; margin-bottom: 6px; font-family: 'Courier New', Courier, monospace; font-size: 11px;">
                            <strong>ALERT ACC: <span style="text-decoration: underline; cursor: pointer;" onclick="openAccountModal('${h.account_id}')">${h.account_id}</span></strong><br>
                            Hop Sequence: <span style="color: #800000; font-weight: bold;">${h.channels_involved.join(" -> ")}</span> (${h.time_window_minutes}m window)<br>
                            Status: <span style="color: #FF0000; font-weight: bold;">SUSPICIOUS HOP BLOCKED ⚠️</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>

        <!-- Top 10 Riskiest Accounts Stacked Chart (Unified Intelligence Model) -->
        <div class="data-panel">
            <div class="panel-header">UNIFIED MODEL STACKED RISK BREAKDOWN // TOP 10 SUSPECT ACCOUNTS</div>
            <div class="stacked-chart-container">
                ${[
                    { id: "ACC000001", xgb: 25, gnn: 25, lstm: 15, mule: 15, chan: 10, wl: 10 },
                    { id: "ACC000004", xgb: 20, gnn: 20, lstm: 12, mule: 15, chan: 8, wl: 10 },
                    { id: "ACC000009", xgb: 15, gnn: 25, lstm: 10, mule: 10, chan: 8, wl: 10 },
                    { id: "ACC000010", xgb: 14, gnn: 12, lstm: 20, mule: 10, chan: 10, wl: 5 },
                    { id: "ACC000015", xgb: 10, gnn: 18, lstm: 15, mule: 8, chan: 8, wl: 5 }
                ].map(r => {
                    const total = r.xgb + r.gnn + r.lstm + r.mule + r.chan + r.wl;
                    return `
                        <div class="stacked-chart-row">
                            <div class="stacked-chart-label" style="cursor: pointer; text-decoration: underline;" onclick="openAccountModal('${r.id}')">${r.id}</div>
                            <div class="stacked-chart-bar-wrapper">
                                <div class="stacked-segment" style="width: ${r.xgb}%; background: #A78BFA;" title="XGBoost: ${r.xgb}%">XGB</div>
                                <div class="stacked-segment" style="width: ${r.gnn}%; background: #8B5CF6;" title="GraphSAGE: ${r.gnn}%">GNN</div>
                                <div class="stacked-segment" style="width: ${r.lstm}%; background: #6366F1;" title="LSTM AE: ${r.lstm}%">SEQ</div>
                                <div class="stacked-segment" style="width: ${r.mule}%; background: #22D3EE;" title="Mule Patterns: ${r.mule}%">MUL</div>
                                <div class="stacked-segment" style="width: ${r.chan}%; background: #06B6D4;" title="Cross-Channel: ${r.chan}%">CHN</div>
                                <div class="stacked-segment" style="width: ${r.wl}%; background: #10B981;" title="Watchlist: ${r.wl}%">WL</div>
                            </div>
                            <div style="font-family: 'JetBrains Mono', monospace; font-size: 0.75rem; font-weight: bold; width: 40px; text-align: right;">${total}%</div>
                        </div>
                    `;
                }).join('')}
            </div>
        </div>
    `;
}

function renderChannelVolumeRow(channel, percent, volume, color) {
    return `
        <div class="css-chart-row">
            <div class="css-chart-label">${channel}</div>
            <div class="css-chart-bar-wrapper">
                <div class="css-chart-bar-fill" style="width: ${percent}%; background: ${color};">${volume}</div>
            </div>
        </div>
    `;
}

// --- SUBPAGE 10: GRAPH AGENT INVESTIGATOR CORE ---
async function renderInvestigate(container) {
    const urlParams = new URLSearchParams(window.location.search);
    const txnId = urlParams.get('txn_id') || "";

    container.innerHTML = `
        <div style="max-width: 900px; margin: 0 auto;">
            <h2 class="section-title" style="text-align: center;">Graph Multi-Agent Investigation Workstation</h2>
            
            <div class="data-panel" style="padding: 2rem;">
                <div style="display: flex; gap: 1rem; margin-bottom: 2rem;">
                    <input id="investigate-id" type="text" placeholder="ENTER ACCOUNT ID / TRANSACTION ID" value="${txnId}" style="flex: 1; background: #000; border: 1px solid var(--border-color); border-radius: 8px; color: #FFF; padding: 0.75rem 1.25rem; font-family: 'JetBrains Mono', monospace; font-size: 0.9rem;">
                    <button class="btn" onclick="startInvestigation()">INITIATE DEEP FRAUD SCOUT</button>
                </div>
                <div id="terminal-output" class="terminal-box" style="height: 420px; overflow-y: auto;">
                    <div class="terminal-line"><span class="terminal-prompt">></span> OPERATIONS SYSTEM READY. SECURE INTEL STREAM IDLE.</div>
                </div>
            </div>
        </div>
    `;
}

// --- Dynamic D3 Money Flow Tracer Diagram Render ---
function drawDownstreamFlow(graph) {
    const svg = d3.select("#flow-svg");
    svg.selectAll("*").remove();

    const viewport = document.getElementById("flow-svg-viewport");
    const width = viewport.clientWidth;
    const height = viewport.clientHeight;
    svg.attr("width", width).attr("height", height);

    const nodes = graph.nodes.map(n => ({ id: n.id, type: n.type }));
    const links = graph.edges.map(e => ({ source: e.source, target: e.target, amount: e.amount }));

    const simulation = d3.forceSimulation(nodes)
        .force("link", d3.forceLink(links).id(d => d.id).distance(120))
        .force("charge", d3.forceManyBody().strength(-200))
        .force("center", d3.forceCenter(width / 2, height / 2 + 10));

    svg.append("defs").append("marker")
        .attr("id", "arrow")
        .attr("viewBox", "0 -5 10 10")
        .attr("refX", 20)
        .attr("refY", 0)
        .attr("markerWidth", 6)
        .attr("markerHeight", 6)
        .attr("orient", "auto")
        .append("path")
        .attr("d", "M0,-5L10,0L0,5")
        .attr("fill", "#666");

    const link = svg.append("g")
        .selectAll("line")
        .data(links)
        .join("line")
        .attr("stroke", "#444")
        .attr("stroke-width", 2)
        .attr("marker-end", "url(#arrow)");

    const edgeLabels = svg.append("g")
        .selectAll("text")
        .data(links)
        .join("text")
        .attr("fill", "var(--cyan)")
        .attr("font-size", "9px")
        .attr("font-family", "JetBrains Mono, monospace")
        .attr("text-anchor", "middle")
        .text(d => `₹${d.amount.toLocaleString()}`);

    const node = svg.append("g")
        .selectAll("g")
        .data(nodes)
        .join("g")
        .style("cursor", "pointer")
        .call(d3.drag()
            .on("start", dragstarted)
            .on("drag", dragged)
            .on("end", dragended));

    node.append("circle")
        .attr("r", 12)
        .attr("fill", d => d.type === "origin" ? "var(--cyan)" : d.type === "relay" ? "var(--amber)" : "var(--red)")
        .attr("stroke", "#FFF")
        .attr("stroke-width", 1.5);

    node.append("text")
        .attr("dy", 3)
        .attr("text-anchor", "middle")
        .attr("fill", "#000")
        .attr("font-size", "9px")
        .attr("font-weight", "bold")
        .text(d => d.type === "cashout" ? "$" : "");

    node.append("text")
        .attr("dy", 26)
        .attr("text-anchor", "middle")
        .attr("fill", "#FFF")
        .attr("font-size", "9px")
        .attr("font-family", "JetBrains Mono, monospace")
        .text(d => d.id);

    node.on("click", (event, d) => openAccountModal(d.id));

    simulation.on("tick", () => {
        link.attr("x1", d => d.source.x)
            .attr("y1", d => d.source.y)
            .attr("x2", d => d.target.x)
            .attr("y2", d => d.target.y);
            
        edgeLabels
            .attr("x", d => (d.source.x + d.target.x) / 2)
            .attr("y", d => (d.source.y + d.target.y) / 2 - 4);

        node.attr("transform", d => `translate(${d.x},${d.y})`);
    });

    function dragstarted(event) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        event.subject.fx = event.subject.x;
        event.subject.fy = event.subject.y;
    }
    function dragged(event) {
        event.subject.fx = event.x;
        event.subject.fy = event.y;
    }
    function dragended(event) {
        if (!event.active) simulation.alphaTarget(0);
        event.subject.fx = null;
        event.subject.fy = null;
    }
}

// --- Investigation Multi-Agent Run Orchestrator ---
async function startInvestigation() {
    const id = document.getElementById("investigate-id").value;
    const terminal = document.getElementById("terminal-output");
    terminal.innerHTML = '';
    
    const addLine = (text, delay = 0) => {
        return new Promise(resolve => {
            setTimeout(() => {
                const div = document.createElement("div");
                div.className = "terminal-line";
                div.innerHTML = `<span class="terminal-prompt">></span> ${text}`;
                terminal.appendChild(div);
                terminal.scrollTop = terminal.scrollHeight;
                resolve();
            }, delay);
        });
    };

    if (!id) {
        await addLine(`<span class="risk-high">CRITICAL ERROR: SCAN TARGET VALUE NULL</span>`);
        return;
    }

    await addLine(`DEPLOYING DEEP FRAUD SCAN PROTOCOL TARGET: ${id}...`);
    await addLine(`SPAWNING LANGGRAPH INTELLIGENT AGENT PIE...`, 150);
    
    try {
        const resp = await fetch(`${API_BASE}/investigate?txn_id=${id}&account_id=SCANNER`, {method: 'POST'});
        if (!resp.ok) throw new Error();
        const {investigation_id} = await resp.json();
        
        await addLine(`AGENTS POOL ACTIVE. ASSIGNING TASKS... [INV_ID: ${investigation_id}]`, 200);
        
        let interval = setInterval(async () => {
            const result = await apiFetch(`/investigate/${investigation_id}`);
            if (!result) return;
            
            if (result.status === "completed") {
                clearInterval(interval);
                
                const shap = result.shap_values || {};
                
                await addLine(`▶ GNN AGENT................... ✓ PageRank contagious vectors calculated.`, 100);
                await addLine(`▶ TEMPORAL AGENT.............. ✓ Transaction hop trail parsed.`, 100);
                await addLine(`▶ ML MODEL ENGINE............. ✓ Combined risk calculated: ${(result.final_risk_score * 100).toFixed(1)}%`, 100);
                
                const verdict = result.final_verdict || "cleared";
                await addLine(`▶ FINAL VERDICT: <span style="font-weight: bold; color: ${verdict === 'mule_confirmed' ? 'var(--red)' : verdict === 'suspicious' ? 'var(--amber)' : 'var(--green)'};">${verdict.toUpperCase().replace('_', ' ')}</span>`, 100);
                
                // Explanations Table
                let tableHtml = `
                    <table style="margin-top: 1rem; width: 100%; border-collapse: collapse; font-size: 0.8rem; border: 1px solid rgba(255,255,255,0.1);">
                        <thead>
                            <tr style="border-bottom: 1.5px solid var(--cyan); background: #050505;">
                                <th style="text-align: left; padding: 6px;">Feature</th>
                                <th style="text-align: right; padding: 6px;">SHAP Metric Impact</th>
                                <th style="text-align: center; padding: 6px;">Force Direction</th>
                            </tr>
                        </thead>
                        <tbody>
                `;
                
                for (const [feat, imp] of Object.entries(shap)) {
                    const direction = imp > 0 ? `<span style="color: var(--red);">▲ INCREASE</span>` : imp < 0 ? `<span style="color: var(--green);">▼ DECREASE</span>` : "—";
                    tableHtml += `
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                            <td style="padding: 6px;">${feat}</td>
                            <td style="text-align: right; padding: 6px; color: ${imp > 0 ? 'var(--red)' : 'var(--green)'}; font-weight: bold; font-family: 'JetBrains Mono', monospace;">${imp.toFixed(4)}</td>
                            <td style="text-align: center; padding: 6px;">${direction}</td>
                        </tr>
                    `;
                }
                tableHtml += `</tbody></table>`;
                
                const div = document.createElement("div");
                div.className = "terminal-line";
                div.style.marginTop = "1rem";
                div.innerHTML = `<span class="terminal-prompt">></span> <strong>SHAP ATTRIBUTION EXPLAINABILITY:</strong><br>${tableHtml}`;
                terminal.appendChild(div);
                
                const expDiv = document.createElement("div");
                expDiv.className = "terminal-line";
                expDiv.style.marginTop = "0.5rem";
                expDiv.innerHTML = `<span class="terminal-prompt">></span> <strong>NARRATIVE FINDINGS:</strong> ${result.explanation_narrative || 'Forensic report compiled successfully.'}`;
                terminal.appendChild(expDiv);
            }
        }, 1500);

    } catch (err) {
        await addLine(`<span class="risk-high">API PORT OFFLINE. EXECUTING OFFLINE MOCKED AI RUNNER...</span>`, 100);
        await addLine(`▶ DETECTED MULTI-CHANNEL HOPPING SPIKES IN 1H WINDOW.`, 100);
        await addLine(`▶ VERDICT: <span style="font-weight: bold; color: var(--amber);">SUSPICIOUS PRE-MULE</span>`, 100);
    }
}

// --- Unified Offline / Modals / stream triggers ---
function renderOffline() {
    return `
        <div style="text-align: center; padding: 6rem; color: var(--red); font-family: 'JetBrains Mono', monospace; font-style: italic;">
            <h1 style="font-size: 3rem; font-weight: 900;">SECURE SYSTEM DISCONNECTED</h1>
            <p style="font-family: inherit; font-size: 1rem; color: #888; margin-top: 1rem;">
                UNABLE TO ESTABLISH TCP PORT 8000 STREAM CONNECTION
            </p>
        </div>
    `;
}

function openInvestigationModal(txnId) {
    const overlay = document.getElementById("modal-overlay");
    const content = document.getElementById("modal-content");
    overlay.classList.remove("hidden");
    content.innerHTML = `<div class="loader" style="font-size: 1.5rem;">RETRIEVING INTEL PROFILE FOR ${txnId}...</div>`;
    
    fetch(`${API_BASE}/transactions/${txnId}`)
        .then(r => r.json())
        .then(tx => {
            const scoreColor = tx.risk_score > 0.7 ? 'var(--red)' : tx.risk_score > 0.4 ? 'var(--amber)' : 'var(--green)';
            content.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                    <h2 style="font-weight: 900; font-size: 1.5rem; text-transform: uppercase;">Transaction Profile: ${tx.transaction_id}</h2>
                    <button class="btn btn-sm" onclick="document.getElementById('modal-overlay').classList.add('hidden')">CLOSE</button>
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; font-size: 0.85rem;">
                    <div>
                        <p style="margin: 0.5rem 0;"><strong>TIMESTAMP:</strong> ${tx.timestamp}</p>
                        <p style="margin: 0.5rem 0;"><strong>SENDER ACCOUNT:</strong> <a href="#" style="color: var(--cyan); font-weight: bold; text-decoration: underline;" onclick="document.getElementById('modal-overlay').classList.add('hidden'); setTimeout(() => openAccountModal('${tx.sender_account}'), 100); return false;">${tx.sender_account}</a></p>
                        <p style="margin: 0.5rem 0;"><strong>RECEIVER ACCOUNT:</strong> <a href="#" style="color: var(--cyan); font-weight: bold; text-decoration: underline;" onclick="document.getElementById('modal-overlay').classList.add('hidden'); setTimeout(() => openAccountModal('${tx.receiver_account}'), 100); return false;">${tx.receiver_account}</a></p>
                        <p style="margin: 0.5rem 0;"><strong>AMOUNT:</strong> INR ${tx.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</p>
                        <p style="margin: 0.5rem 0;"><strong>INGESTION CHANNEL:</strong> <span class="badge-source internal">${tx.channel}</span></p>
                        <p style="margin: 0.5rem 0;"><strong>CBS BIND STATUS:</strong> <span style="color: var(--emerald); font-weight: bold;">${tx.status}</span></p>
                    </div>
                    <div class="data-panel" style="padding: 1.5rem; border: 1.5px solid ${scoreColor}; background: #020202; border-radius: 8px;">
                        <h3 style="margin-top: 0; font-size: 0.75rem; color: #888; letter-spacing: 0.05em;">RISK EVALUATION INDEX</h3>
                        <div style="font-size: 3rem; font-weight: bold; color: ${scoreColor}; font-family: 'JetBrains Mono', monospace; line-height: 1.2;">
                            ${(tx.risk_score * 100).toFixed(1)}%
                        </div>
                        <p style="margin-top: 1rem; opacity: 0.7;">This transaction has been classified as <strong>${tx.risk_score > 0.7 ? 'HIGH THREAT MULE' : tx.risk_score > 0.4 ? 'SUSPICIOUS' : 'OPERATIONAL'}</strong> by the XGBoost tabular ML engine.</p>
                        <button class="btn btn-sm" style="width: 100%; margin-top: 1.5rem; border-color: var(--violet); color: var(--violet);" onclick="document.getElementById('modal-overlay').classList.add('hidden'); window.location.hash = '#/investigate?txn_id=${tx.transaction_id}'">DEPLOY MULTI-AGENT SCAN</button>
                    </div>
                </div>
            `;
        })
        .catch(() => {
            content.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                    <h2 style="font-weight: 900; font-size: 1.5rem; text-transform: uppercase;">Simulation: ${txnId}</h2>
                    <button class="btn btn-sm" onclick="document.getElementById('modal-overlay').classList.add('hidden')">CLOSE</button>
                </div>
                <div style="padding: 2rem; text-align: center; color: var(--red); font-style: italic;">
                    API OFFLINE fallback dataset active.
                </div>
            `;
        });
}

function openAccountModal(id) {
    const overlay = document.getElementById("modal-overlay");
    const content = document.getElementById("modal-content");
    overlay.classList.remove("hidden");
    content.innerHTML = `<div class="loader" style="font-size: 1.5rem;">LOADING SECURE PROFILE FOR ${id}...</div>`;
    
    fetch(`${API_BASE}/accounts/${id}`)
        .then(r => r.json())
        .then(data => {
            content.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                    <h2 style="font-weight: 900; font-size: 1.5rem; text-transform: uppercase;">Account Profile: ${id}</h2>
                    <button class="btn btn-sm" onclick="document.getElementById('modal-overlay').classList.add('hidden')">CLOSE</button>
                </div>
                
                <div style="display: grid; grid-template-columns: 1.2fr 2fr; gap: 2rem; font-size: 0.85rem;">
                    <div>
                        <p style="margin: 0.5rem 0;"><strong>HOLDER NAME:</strong> ${data.name || 'Unknown'}</p>
                        <p style="margin: 0.5rem 0;"><strong>CUSTOMER SEGMENT:</strong> ${data.customer_segment || 'N/A'}</p>
                        <p style="margin: 0.5rem 0;"><strong>GEOGRAPHY:</strong> ${data.city || 'N/A'}</p>
                        <p style="margin: 0.5rem 0;"><strong>CBS HASH BALANCE:</strong> INR ${(data.balance || 0).toLocaleString(undefined, {minimumFractionDigits: 2})}</p>
                        <p style="margin: 0.5rem 0;"><strong>SECURITY PROFILE:</strong> <span class="risk-${data.risk_profile}" style="font-weight: 700; text-transform: uppercase;">${data.risk_profile}</span></p>
                        <p style="margin: 0.5rem 0;"><strong>NEO4J PAGERANK:</strong> <span style="font-family: 'JetBrains Mono', monospace;">${(data.pagerank || 0).toFixed(6)}</span></p>
                        
                        <div style="margin-top: 2rem; display: flex; flex-direction: column; gap: 0.5rem;">
                            <button class="btn btn-sm" style="border-color: var(--violet); color: var(--violet);" onclick="document.getElementById('modal-overlay').classList.add('hidden'); window.location.hash = '#/money-flow?account_id=${id}'">Trace Downstream Flow</button>
                            <button class="btn btn-sm" style="border-color: var(--red); color: var(--red);" onclick="flagAccount('${id}')">Flag caution in CBS</button>
                        </div>
                    </div>
                    
                    <div class="data-panel">
                        <div class="panel-header">RECENT TRANSACTIONS AUDIT</div>
                        <div style="max-height: 300px; overflow-y: auto;">
                            ${data.recent_transactions && data.recent_transactions.length > 0 ? `
                                <table>
                                    <thead>
                                        <tr style="font-size: 0.65rem; background: rgba(0,0,0,0.2);">
                                            <th>TX ID</th>
                                            <th>Amount</th>
                                            <th>Channel</th>
                                            <th>Risk</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        ${data.recent_transactions.map(tx => `
                                            <tr style="cursor: pointer;" onclick="document.getElementById('modal-overlay').classList.add('hidden'); setTimeout(() => openInvestigationModal('${tx.transaction_id}'), 100);">
                                                <td style="font-family: 'JetBrains Mono', monospace; color: var(--cyan);">${tx.transaction_id}</td>
                                                <td>INR ${tx.amount.toLocaleString(undefined, {minimumFractionDigits: 2})}</td>
                                                <td><span class="badge-source internal">${tx.channel}</span></td>
                                                <td style="color: ${tx.risk_score > 0.7 ? 'var(--red)' : tx.risk_score > 0.4 ? 'var(--amber)' : 'var(--green)'}; font-family: 'JetBrains Mono', monospace; font-weight: bold;">
                                                    ${tx.risk_score.toFixed(4)}
                                                </td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            ` : `
                                <div style="padding: 2.5rem; text-align: center; opacity: 0.4; font-style: italic;">NO RECENT LEDGER TRANSFERS FOUND</div>
                            `}
                        </div>
                    </div>
                </div>
            `;
        })
        .catch(() => {
            content.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2rem;">
                    <h2 style="font-weight: 900; font-size: 1.5rem; text-transform: uppercase;">Simulation Account: ${id}</h2>
                    <button class="btn btn-sm" onclick="document.getElementById('modal-overlay').classList.add('hidden')">CLOSE</button>
                </div>
                <div style="padding: 2rem; text-align: center; color: var(--red); font-style: italic;">
                    API OFFLINE fallback dataset active.
                </div>
            `;
        });
}

async function fileStr(strId) {
    await apiFetch(`/regulatory/strs/${strId}/file?analyst_id=ANALYST_001`);
    alert(`STR report filed successfully with FIU-IND.`);
    router();
}

function syncCrilc(accId) {
    alert(`Reporting suspect profile ${accId} to Central Repository of Information on Large Credits (CRILC).`);
}

async function flagAccount(id) {
    try {
        await fetch(`${API_BASE}/accounts/${id}/flag`, {method: 'POST'});
        alert(`Account ${id} has been caution flagged inside Core Banking System.`);
        document.getElementById('modal-overlay').classList.add('hidden');
        router();
    } catch (err) {
        alert("CBS Action Simulated. Suspicious flag logged in security terminal.");
        document.getElementById('modal-overlay').classList.add('hidden');
    }
}

async function triggerEwsScanNow() {
    await apiFetch("/mule/ews/scan?limit=100");
    alert("Full network anomaly scan completed! Refreshing console indicators.");
    router();
}

function dismissEwsAlert(id) {
    alert(`Alert for account ${id} dismissed.`);
}

function investigateEwsAccount(id) {
    window.location.hash = `#/investigate?txn_id=${id}`;
}

async function fileStrFromFlow() {
    const aid = document.getElementById("str-generation-container").dataset.accountId;
    try {
        await fetch(`${API_BASE}/regulatory/simulate`, {method: 'POST'});
        alert(`Suspicious Transaction Report generated for suspect profile ${aid}! Filed under pending list.`);
        window.location.hash = "#/regulatory";
    } catch (e) {
        alert("STR Generation Simulated. Action recorded in console.");
    }
}

// --- Live Alert Feed SSE Stream ---
function initLiveAlertStream() {
    if (state.sseSource) {
        state.sseSource.close();
    }
    if (state.pollingInterval) {
        clearInterval(state.pollingInterval);
    }

    try {
        console.log("Connecting to live alerts ledgerstream...");
        state.sseSource = new EventSource(`${API_BASE}/alerts/stream`);
        
        state.sseSource.onmessage = (event) => {
            try {
                const alert = JSON.parse(event.data);
                handleNewAlert(alert);
            } catch (e) {
                console.error("Error parsing SSE alert", e);
            }
        };

        state.sseSource.onerror = () => {
            state.sseSource.close();
            state.sseSource = null;
            startPollingFallback();
        };

    } catch (err) {
        startPollingFallback();
    }
}

function startPollingFallback() {
    const fetchLatest = async () => {
        const alertsList = await apiFetch("/regulatory/alerts/feed");
        if (alertsList && alertsList.length > 0) {
            state.alerts = alertsList.slice(0, 50);
            updateAlertFeedDom();
        }
    };
    
    fetchLatest();
    state.pollingInterval = setInterval(fetchLatest, 4000);
}

function handleNewAlert(alert) {
    state.alerts.unshift(alert);
    if (state.alerts.length > 50) {
        state.alerts.pop();
    }
    updateAlertFeedDom();
}

function updateAlertFeedDom() {
    if (state.currentPage === "#/") {
        const container = document.getElementById("live-alert-feed-container");
        if (container) {
            if (state.alerts.length === 0) {
                container.innerHTML = `
                    <tr>
                        <td colspan="6" style="padding: 4rem; text-align: center; color: var(--cyan); font-style: italic; font-family: 'JetBrains Mono', monospace;">
                            AWAITING REAL-TIME INTERCEPTIONS FROM CORE BANKING SYSTEM...
                        </td>
                    </tr>
                `;
            } else {
                container.innerHTML = state.alerts.map(a => renderAlertRowHtml(a)).join('');
            }
        }
    }
}

// --- Live Clock ---
function initClock() {
    const clockEl = document.getElementById("live-clock");
    if (clockEl) {
        const tick = () => {
            clockEl.innerText = new Date().toLocaleTimeString('en-US', {hour12: false});
        };
        tick();
        setInterval(tick, 1000);
    }
}
