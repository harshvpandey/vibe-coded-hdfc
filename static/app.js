// HDFC AI MailRoom Front-End Controller

// 1. SCENARIOS DEFINITIONS
const SCENARIOS = {
    1: {
        sender: "john.doe@gmail.com",
        subject: "Please share my savings balance",
        body: "Please provide my savings account balance for account number 1234567890."
    },
    2: {
        sender: "john.doe@gmail.com",
        subject: "Credit card transaction query",
        body: "Please share my last 5 credit card transactions for card 4567XXXX8901."
    },
    3: {
        sender: "john.doe@gmail.com",
        subject: "April e-statement request",
        body: "Kindly send my bank statement for April 2026."
    },
    4: {
        sender: "john.doe@gmail.com",
        subject: "Request for balance & card transactions",
        body: "Please share my account balance for account 1234567890 and also send last 3 transactions of my credit card 987654321."
    },
    5: {
        sender: "john.doe@gmail.com",
        subject: "Urgent account query",
        body: "Please provide balance for account 1234567890 and card transactions for card 999999999."
    }
};

let currentTab = 'accounts';
let latestExecutionTrace = null;
let nodeDurations = {};

// 2. ON INITIALIZATION
document.addEventListener("DOMContentLoaded", () => {
    // Start Live Clock
    updateClock();
    setInterval(updateClock, 30000);
    
    // Fetch initial database status
    fetchDatabaseState();
    
    // Fetch system logs
    fetchLogs();
    
    // Preset Scenario 1
    loadScenario(1);
});

function updateClock() {
    const clock = document.getElementById("live-clock");
    if (clock) {
        const now = new Date();
        const yyyy = now.getFullYear();
        const mm = String(now.getMonth() + 1).padStart(2, '0');
        const dd = String(now.getDate()).padStart(2, '0');
        const hh = String(now.getHours()).padStart(2, '0');
        const min = String(now.getMinutes()).padStart(2, '0');
        clock.textContent = `${yyyy}-${mm}-${dd} ${hh}:${min}`;
    }
}

// 3. SCENARIOS CONTROLLER
function loadScenario(id) {
    // Highlight button
    const buttons = document.querySelectorAll(".scenario-btn");
    buttons.forEach((btn, idx) => {
        if (idx === (id - 1)) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    const scenario = SCENARIOS[id];
    if (scenario) {
        document.getElementById("email-sender").value = scenario.sender;
        document.getElementById("email-subject").value = scenario.subject;
        document.getElementById("email-body").value = scenario.body;
        addTerminalLog(`SYSTEM`, `Loaded Scenario ${id} inbox query. ready to process.`, 'system');
    }
}

// 4. DATABASE CONTROLLER
function switchDbTab(tab) {
    currentTab = tab;
    const buttons = document.querySelectorAll(".db-tab-btn");
    const accountsPanel = document.getElementById("db-accounts-panel");
    const cardsPanel = document.getElementById("db-cards-panel");
    
    if (tab === 'accounts') {
        buttons[0].classList.add("active");
        buttons[1].classList.remove("active");
        accountsPanel.classList.add("active");
        cardsPanel.classList.remove("active");
    } else {
        buttons[0].classList.remove("active");
        buttons[1].classList.add("active");
        accountsPanel.classList.remove("active");
        cardsPanel.classList.add("active");
    }
}

async function fetchDatabaseState() {
    try {
        const accRes = await fetch("/api/db/accounts");
        const accounts = await accRes.json();
        renderAccountsTable(accounts);
        
        const cardRes = await fetch("/api/db/cards");
        const cards = await cardRes.json();
        renderCardsTable(cards);
    } catch (err) {
        addTerminalLog("SYSTEM_ERROR", `Failed to contact core database API: ${err.message}`, 'error');
    }
}

function renderAccountsTable(accounts) {
    const tbody = document.getElementById("accounts-table-body");
    tbody.innerHTML = "";
    
    Object.keys(accounts).forEach(key => {
        const acc = accounts[key];
        const statusClass = acc.status === 'ACTIVE' ? 'status-valid' : 'status-invalid';
        
        tbody.innerHTML += `
            <tr>
                <td><strong>${acc.account_number}</strong></td>
                <td>${acc.customer_name}</td>
                <td>${acc.balance.toLocaleString('en-IN', {minimumFractionDigits: 2})}</td>
                <td><span class="${statusClass}">${acc.status}</span></td>
                <td>
                    <button class="btn-xs" onclick="triggerUpdateBalance('${acc.account_number}', ${acc.balance})">
                        <i class="fa-solid fa-pen-to-square"></i>
                    </button>
                </td>
            </tr>
        `;
    });
}

function renderCardsTable(cards) {
    const tbody = document.getElementById("cards-table-body");
    tbody.innerHTML = "";
    
    Object.keys(cards).forEach(key => {
        const card = cards[key];
        const statusClass = card.status === 'ACTIVE' ? 'status-valid' : 'status-invalid';
        tbody.innerHTML += `
            <tr>
                <td><strong>${card.card_number}</strong></td>
                <td>${card.cardholder_name}</td>
                <td>${card.credit_limit.toLocaleString('en-IN')}</td>
                <td>${card.available_limit.toLocaleString('en-IN')}</td>
                <td><span class="${statusClass}">${card.status}</span></td>
            </tr>
        `;
    });
}

async function triggerUpdateBalance(accountNumber, currentBalance) {
    const rawVal = prompt(`Update Savings Account ${accountNumber} Balance (INR):`, currentBalance);
    if (rawVal === null) return;
    const newVal = parseFloat(rawVal);
    if (isNaN(newVal)) {
        alert("Please enter a valid numeric amount.");
        return;
    }
    
    try {
        const r = await fetch("/api/db/accounts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                account_number: accountNumber,
                customer_name: "Mock", // API updates fields in-place, so name is ignored for existing
                balance: newVal
            })
        });
        if (r.ok) {
            addTerminalLog("CORE_DB", `Balance for Account ${accountNumber} updated manually to INR ${newVal}`, 'system');
            fetchDatabaseState();
        }
    } catch (err) {
        alert(`Update failed: ${err.message}`);
    }
}

async function addAccount(e) {
    e.preventDefault();
    const accNum = document.getElementById("add-acc-num").value;
    const name = document.getElementById("add-acc-name").value;
    const bal = parseFloat(document.getElementById("add-acc-bal").value);
    
    try {
        const r = await fetch("/api/db/accounts", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ account_number: accNum, customer_name: name, balance: bal })
        });
        if (r.ok) {
            document.getElementById("add-acc-num").value = "";
            document.getElementById("add-acc-name").value = "";
            document.getElementById("add-acc-bal").value = "";
            addTerminalLog("CORE_DB", `Inserted new mock Account ${accNum} [${name}]`, 'system');
            fetchDatabaseState();
        }
    } catch (err) {
        addTerminalLog("SYSTEM_ERROR", `Failed to insert account: ${err.message}`, 'error');
    }
}

async function addCard(e) {
    e.preventDefault();
    const cardNum = document.getElementById("add-card-num").value;
    const name = document.getElementById("add-card-name").value;
    const avail = parseFloat(document.getElementById("add-card-avail").value);
    
    try {
        const r = await fetch("/api/db/cards", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ card_number: cardNum, cardholder_name: name, available_limit: avail, credit_limit: avail + 20000 })
        });
        if (r.ok) {
            document.getElementById("add-card-num").value = "";
            document.getElementById("add-card-name").value = "";
            document.getElementById("add-card-avail").value = "";
            addTerminalLog("CORE_DB", `Inserted new mock Credit Card ${cardNum} [${name}]`, 'system');
            fetchDatabaseState();
        }
    } catch (err) {
        addTerminalLog("SYSTEM_ERROR", `Failed to insert card: ${err.message}`, 'error');
    }
}

// 5. TERMINAL LOGS
function addTerminalLog(source, msg, type = 'normal') {
    const terminal = document.getElementById("log-terminal");
    if (!terminal) return;
    
    const timestamp = new Date().toISOString().substring(11, 19);
    const line = document.createElement("div");
    line.className = `log-line ${type}`;
    line.innerHTML = `[${timestamp}] <strong>${source}</strong>: ${msg}`;
    
    terminal.appendChild(line);
    terminal.scrollTop = terminal.scrollHeight;
}

function clearLogs() {
    document.getElementById("log-terminal").innerHTML = `<div class="log-line system">Terminal logs cleared. Ready...</div>`;
}

async function fetchLogs() {
    try {
        const res = await fetch("/api/logs");
        const logs = await res.json();
        const terminal = document.getElementById("log-terminal");
        terminal.innerHTML = "";
        
        logs.forEach(log => {
            let src = "SYSTEM";
            let type = "system";
            let msg = "";
            
            if (log.type === "AGENT_EXECUTION") {
                src = log.agent;
                type = "agent";
                msg = `Status: ${log.status}. Summary: ${log.outputs.summary || log.outputs.sentiment || 'Agent completed step.'}`;
            } else if (log.type === "API_CALL") {
                src = log.api;
                type = "api";
                msg = `Path ${log.endpoint} returned status ${log.status_code}`;
            } else {
                src = "CORE";
                msg = log.message || JSON.stringify(log);
            }
            
            addTerminalLog(src, msg, type);
        });
    } catch(e) {}
}

// 6. MULTI-AGENT EXECUTION & PIPELINE ANIMATION
async function submitEmail(e) {
    e.preventDefault();
    
    const sender = document.getElementById("email-sender").value;
    const subject = document.getElementById("email-subject").value;
    const body = document.getElementById("email-body").value;
    
    const btn = document.getElementById("btn-process");
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-arrows-spin fa-spin"></i> Processing...`;
    
    // Toggle Viewports: show inspector and clear previous reply view
    document.getElementById("node-inspector").style.display = "flex";
    document.getElementById("node-inspector").scrollIntoView({behavior: "smooth"});
    document.getElementById("inspect-title").textContent = "Workflow Running...";
    document.getElementById("inspect-content").textContent = "// Orchestrator starting multi-agent pipeline...\n// Synchronizing agent system environments...";
    
    // Hide final email response panel till finished
    document.getElementById("email-reply-card").style.display = "none";
    
    // Reset Pipeline Visual Nodes
    const nodes = document.querySelectorAll(".node");
    nodes.forEach(node => {
        node.className = node.classList.contains("node-input") ? "node node-input" : 
                         node.classList.contains("node-output") ? "node node-output" : 
                         node.classList.contains("node-system") ? "node node-system" : "node node-agent";
    });
    
    addTerminalLog("ORCHESTRATOR", "Initializing multi-agent pipeline workflow...", 'system');
    
    // Trigger Server Execution asynchronously
    let responseData = null;
    let errMessage = null;
    
    try {
        const fetchPromise = fetch("/api/process-email", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ sender, subject, body })
        });
        
        // Parallel: Animate pipeline visually while request is flying (mocked flow progression)
        await animatePipelineProgress();
        
        // Wait for actual API response
        const res = await fetchPromise;
        if (res.ok) {
            responseData = await res.json();
        } else {
            const errDetail = await res.json();
            errMessage = errDetail.detail || "Server Orchestration failed.";
        }
    } catch (err) {
        errMessage = err.message;
    }
    
    btn.disabled = false;
    btn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i> Process with AI Agents`;
    
    if (errMessage) {
        addTerminalLog("SYSTEM_ERROR", `Orchestrator failed: ${errMessage}`, 'error');
        document.getElementById("inspect-content").textContent = `Error: ${errMessage}`;
        markPipelineFailed();
        return;
    }
    
    // Save state globally for Inspector clicks
    latestExecutionTrace = responseData;
    
    // Mark pipeline completed
    markPipelineSuccess(responseData);
    
    // Render Response client View
    renderResponseEmail(responseData);
    
    // Refresh Audit Log console and database state (since values could have changed!)
    fetchDatabaseState();
    fetchLogs();
}

// Visual animation sequence for processing
async function animatePipelineProgress() {
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));
    
    const setNodeActive = (id) => {
        const el = document.getElementById(id);
        if (el) el.classList.add("active");
    };
    
    const setNodeDone = (id) => {
        const el = document.getElementById(id);
        if (el) {
            el.classList.remove("active");
            el.classList.add("done");
        }
    };

    // Step 1: Input
    setNodeActive("node-email-input");
    addTerminalLog("SYSTEM", "Email input ingested successfully.", "system");
    await sleep(400);
    setNodeDone("node-email-input");

    // Step 2: Understanding
    setNodeActive("node-understanding");
    addTerminalLog("EmailUnderstandingAgent", "Reading layout and cleaning email content...", "agent");
    await sleep(600);
    setNodeDone("node-understanding");

    // Step 3: Intents, Sentiment, Extraction (Parallel)
    setNodeActive("node-intent");
    setNodeActive("node-sentiment");
    setNodeActive("node-extraction");
    addTerminalLog("IntentClassificationAgent", "Classifying user requests...", "agent");
    addTerminalLog("SentimentAnalysisAgent", "Evaluating customer frustration levels...", "agent");
    addTerminalLog("EntityExtractionAgent", "Parsing account and card credentials...", "agent");
    await sleep(800);
    setNodeDone("node-intent");
    setNodeDone("node-sentiment");
    setNodeDone("node-extraction");

    // Step 4: Validation
    setNodeActive("node-validation");
    addTerminalLog("ValidationAgent", "Running deterministic validation against Core Systems...", "agent");
    await sleep(600);
    setNodeDone("node-validation");

    // Step 5: Route selection & Core API execution (Parallel)
    setNodeActive("node-selection");
    setNodeActive("node-banking-apis");
    addTerminalLog("APISelectionAgent", "Evaluating API routing decisions based on data validation...", "agent");
    addTerminalLog("CoreBankingAPIs", "Fetching core banking records...", "api");
    await sleep(700);
    setNodeDone("node-selection");
    setNodeDone("node-banking-apis");

    // Step 6: Response Drafting
    setNodeActive("node-response");
    addTerminalLog("ResponseGenerationAgent", "Drafting corporate customer response...", "agent");
    await sleep(700);
    setNodeDone("node-response");

    // Step 7: Auditor
    setNodeActive("node-auditor");
    addTerminalLog("AuditorAgent", "Evaluating response for privacy redacts and compliance rules...", "agent");
    await sleep(500);
    setNodeDone("node-auditor");

    // Step 8: Email Output
    setNodeActive("node-email-output");
    addTerminalLog("SYSTEM", "Automated email drafted successfully.", "system");
    await sleep(300);
    setNodeDone("node-email-output");
}

function markPipelineSuccess(state) {
    // Ensure all nodes are fully flagged green
    const nodes = document.querySelectorAll(".node");
    nodes.forEach(node => {
        node.className = node.classList.contains("node-input") ? "node node-input done" : 
                         node.classList.contains("node-output") ? "node node-output done" : 
                         node.classList.contains("node-system") ? "node node-system done" : "node node-agent done";
    });
    
    // Auto-inspect the final auditor node by default
    inspectNode("AuditorAgent");
    
    addTerminalLog("ORCHESTRATOR", `Workflow execution finished successfully in ${state.execution_time_ms} ms!`, 'system');
}

function markPipelineFailed() {
    const nodes = document.querySelectorAll(".node");
    nodes.forEach(node => {
        if (node.classList.contains("active")) {
            node.classList.remove("active");
            node.classList.add("failed");
        }
    });
}

// 7. NODE INSPECTOR CONTROLLER
function inspectNode(agentName) {
    if (!latestExecutionTrace) {
        document.getElementById("inspect-title").textContent = "Inspector Idle";
        document.getElementById("inspect-content").textContent = "// Please execute a transaction to view agent payloads.";
        return;
    }
    
    // Toggle Viewports: show inspector and hide reply card
    document.getElementById("node-inspector").style.display = "flex";
    document.getElementById("email-reply-card").style.display = "none";
    
    const inspectTitle = document.getElementById("inspect-title");
    const inspectContent = document.getElementById("inspect-content");
    
    inspectTitle.textContent = `${agentName} JSON Payload`;
    
    // Find the log item corresponding to this agent name
    let logItem = null;
    
    if (agentName === "CoreBankingAPIs") {
        logItem = latestExecutionTrace.agent_logs.find(l => l.agent === "CoreBankingAPIs");
    } else {
        logItem = latestExecutionTrace.agent_logs.find(l => l.agent === agentName);
    }
    
    if (logItem) {
        inspectContent.textContent = JSON.stringify(logItem, null, 2);
    } else {
        // Fallback: construct custom visualization view for other nodes or mock validations
        if (agentName === "ValidationAgent") {
            inspectContent.textContent = JSON.stringify({
                agent: "ValidationAgent",
                inputs: { entities: latestExecutionTrace.entities },
                outputs: latestExecutionTrace.validation_results
            }, null, 2);
        } else {
            inspectContent.textContent = `// Log traces for agent ${agentName} were compacted.\n// Original state variables:\n` + JSON.stringify(latestExecutionTrace, null, 2);
        }
    }
}

// Helper to dynamically parse and render Markdown tables inside the Email Client View
function formatEmailBody(text) {
    if (!text) return "";
    
    // 1. Escape HTML tags to protect layout structure
    const escaped = text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
        
    // 2. Parse Markdown Table syntax to HTML Table structure
    const lines = escaped.split("\n");
    let inTable = false;
    let newText = [];
    let tableHtml = "";
    
    for (let i = 0; i < lines.length; i++) {
        let line = lines[i].trim();
        
        if (line.startsWith("|") && line.endsWith("|")) {
            if (line.includes("---")) {
                continue; // skip separator row (e.g. |:---|:---|)
            }
            
            // Extract column fields
            let cols = line.split("|").map(c => c.trim()).filter((c, idx, arr) => idx > 0 && idx < arr.length - 1);
            
            if (!inTable) {
                inTable = true;
                tableHtml = '<div class="table-wrapper"><table class="email-data-table">';
                tableHtml += '<thead><tr>';
                cols.forEach(col => {
                    tableHtml += `<th>${col}</th>`;
                });
                tableHtml += '</tr></thead><tbody>';
            } else {
                tableHtml += '<tr>';
                cols.forEach(col => {
                    tableHtml += `<td>${col}</td>`;
                });
                tableHtml += '</tr>';
            }
        } else {
            if (inTable) {
                inTable = false;
                tableHtml += '</tbody></table></div>';
                newText.push(tableHtml);
                tableHtml = "";
            }
            newText.push(lines[i]);
        }
    }
    
    if (inTable) {
        tableHtml += '</tbody></table></div>';
        newText.push(tableHtml);
    }
    
    return newText.join("\n");
}

// 8. RENDER RESPONSE CLIENT VIEW
function renderResponseEmail(state) {
    // Show reply card and hide inspector card!
    document.getElementById("email-reply-card").style.display = "flex";
    document.getElementById("node-inspector").style.display = "none";
    
    const emailPanel = document.getElementById("email-reply-card");
    emailPanel.scrollIntoView({behavior: "smooth"});
    
    // Load metadata metrics
    const sentimentLabel = document.getElementById("val-sentiment");
    sentimentLabel.textContent = state.sentiment;
    sentimentLabel.className = state.sentiment === 'NEUTRAL' ? 'neutral' : 
                               state.sentiment === 'POSITIVE' ? 'positive' : 'negative';
                               
    document.getElementById("val-confidence").textContent = `${Math.round(state.confidence_score * 100)}%`;
    document.getElementById("val-time").textContent = `${state.execution_time_ms} ms`;
    
    // Load mail fields
    document.getElementById("reply-to").textContent = state.sender;
    document.getElementById("reply-subj").textContent = `Re: ${state.subject}`;
    
    // Load text body dynamically parsing Markdown tables to HTML
    document.getElementById("reply-body").innerHTML = formatEmailBody(state.draft_response);
}

// 9. NEW INTERACTIVE CONTROLS: SAVE SCENARIO & COPY RESPONSE
function saveAsScenario() {
    const sender = document.getElementById("email-sender").value;
    const subject = document.getElementById("email-subject").value;
    const body = document.getElementById("email-body").value;
    
    if (!body || !subject) {
        alert("Please enter a subject and body in the composer first!");
        return;
    }
    
    const title = prompt("Enter a Title for your custom inbox scenario:", "Custom Balance enquiry");
    if (!title || !title.trim()) return;
    
    const newId = Object.keys(SCENARIOS).length + 1;
    SCENARIOS[newId] = { sender, subject, body };
    
    // Render button inside inbox panel
    const container = document.querySelector(".inbox-scenarios");
    if (container) {
        const btn = document.createElement("button");
        btn.className = "scenario-btn";
        btn.onclick = () => loadScenario(newId);
        btn.innerHTML = `
            <div class="scenario-meta">
                <span class="sender-name">${sender}</span>
                <span class="scenario-label">Scenario ${newId}</span>
            </div>
            <h3>${title.trim()}</h3>
            <p>${body}</p>
        `;
        container.appendChild(btn);
        
        // Scroll to the bottom of scenario container to show newly added item
        container.scrollTop = container.scrollHeight;
    }
    
    // Update scenario count badge in header
    const badge = document.querySelector(".card-inbox .badge-count");
    if (badge) {
        badge.textContent = `${newId} Scenarios`;
    }
    
    // Load it as the active scenario
    loadScenario(newId);
    addTerminalLog("SYSTEM", `Successfully created and saved custom scenario: "${title.trim()}"`, 'system');
}

function copyResponseToClipboard() {
    const replyBody = document.getElementById("reply-body");
    if (!replyBody) return;
    
    const text = replyBody.textContent || replyBody.innerText;
    if (text.includes("No email processed yet")) {
        alert("There is no generated email reply to copy yet. Process an email first!");
        return;
    }
    
    navigator.clipboard.writeText(text).then(() => {
        const btn = document.getElementById("btn-copy-email");
        if (btn) {
            const originalHTML = btn.innerHTML;
            btn.innerHTML = `<i class="fa-solid fa-check"></i> Copied!`;
            btn.style.color = "var(--accent-green)";
            btn.style.borderColor = "var(--accent-green)";
            
            setTimeout(() => {
                btn.innerHTML = originalHTML;
                btn.style.color = "";
                btn.style.borderColor = "";
            }, 2000);
        }
        addTerminalLog("SYSTEM", "Email reply copied successfully to clipboard.", 'system');
    }).catch(err => {
        addTerminalLog("SYSTEM_ERROR", `Failed to copy response to clipboard: ${err.message}`, 'error');
        alert("Clipboard copy failed. You can select and copy the text manually.");
    });
}

