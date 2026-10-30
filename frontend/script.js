
const API = "http://127.0.0.1:8000";

const pages = ["dashboard", "validate", "history", "docs"];


// PAGE NAVIGATION
function showPage(page) {
    if (!pages.includes(page)) return;

    pages.forEach(name => {
        const section = document.getElementById(`${name}-page`);
        if (section) {
            section.classList.toggle("hidden", name !== page);
        }
    });

    document.querySelectorAll(".nav-item").forEach(button => {
        button.classList.toggle("active", button.dataset.page === page);
    });

    const titles = {
        dashboard: "Validation overview",
        validate: "Validate an API",
        history: "Validation history",
        docs: "Documentation"
    };

    document.getElementById("page-title").textContent = titles[page];
    document.getElementById("breadcrumb").textContent = titles[page];
}


// NAVIGATION BUTTONS
document.querySelectorAll("[data-page]").forEach(button => {
    button.addEventListener("click", () => {
        showPage(button.dataset.page);
        updateDashboard();
    });
});

document.querySelectorAll("[data-go]").forEach(button => {
    button.addEventListener("click", () => {
        showPage(button.dataset.go);
    });
});


// LOAD HISTORY
async function getHistory() {
    try {
        const response = await fetch(`${API}/history`);

        if (!response.ok) {
            throw new Error("Could not load history.");
        }

        return await response.json();

    } catch (error) {
        console.error("History loading failed:", error);
        return [];
    }
}


// HTML SAFETY
function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}


// FORMAT RESPONSE TIME
function formatResponseTime(value) {
    if (value === null || value === undefined) {
        return "N/A";
    }

    return `${Number(value).toFixed(2)} ms`;
}


// FORMAT DATE
function formatLocalDate(value) {
    if (!value) return "N/A";

    let date;

    if (value.includes("T")) {
        date = new Date(
            value.endsWith("Z") ? value : `${value}Z`
        );
    } else {
        date = new Date(`${value.replace(" ", "T")}Z`);
    }

    if (Number.isNaN(date.getTime())) {
        return value;
    }

    return date.toLocaleString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
        hour12: true
    });
}


// REASON FOR VALIDATION
function getReason(item) {
    if (item.status === "PASS") {
        return "API response matches the contract";
    }

    return item.message || "Validation failed. Check the validation details.";
}


// RENDER TABLE
function renderTable(elementId, history) {
    const table = document.getElementById(elementId);

    if (!table) return;

    if (!history.length) {
        table.innerHTML =
            '<tr><td colspan="7" class="empty">No validations recorded yet.</td></tr>';
        return;
    }

    table.innerHTML = history.map(item => `
        <tr>
            <td>
                <span class="status ${item.status === "PASS" ? "pass" : "fail"}">
                    ${item.status === "PASS" ? "● PASS" : "● FAIL"}
                </span>
            </td>
            <td>${escapeHTML(item.endpoint)}</td>
            <td>${escapeHTML(item.method)}</td>
            <td>${item.http_status ?? "N/A"}</td>
            <td>${escapeHTML(formatResponseTime(item.response_time_ms))}</td>
            <td class="reason-cell">${escapeHTML(getReason(item))}</td>
            <td>${escapeHTML(formatLocalDate(item.created_at || item.time))}</td>
        </tr>
    `).join("");
}


// UPDATE DASHBOARD
async function updateDashboard() {
    const history = await getHistory();

    const passed = history.filter(item => item.status === "PASS").length;
    const failed = history.filter(item => item.status === "FAIL").length;
    const total = history.length;

    const passRate = total > 0
        ? ((passed / total) * 100).toFixed(1)
        : "0.0";

    document.getElementById("total-count").textContent = total;
    document.getElementById("pass-count").textContent = passed;
    document.getElementById("fail-count").textContent = failed;
    document.getElementById("pass-rate").textContent = `${passRate}%`;

    renderTable("recent-table", history.slice(0, 5));
    renderTable("history-table", history);
}


// FEATURE 1: AUTOMATIC JSON SCHEMA GENERATION
document.getElementById("generate-schema-btn").addEventListener(
    "click",
    async (event) => {
        event.preventDefault();
        event.stopPropagation();

        const endpoint = document.getElementById("endpoint").value.trim();
        const button = document.getElementById("generate-schema-btn");
        const contractBox = document.getElementById("contract");

        if (!endpoint) {
            alert("Please enter an API endpoint URL first.");
            return;
        }

        button.disabled = true;
        button.textContent = "Generating contract...";

        try {
            const response = await fetch(
                `${API}/generate-schema?url=${encodeURIComponent(endpoint)}`,
                {
                    method: "POST",
                    headers: {
                        "Accept": "application/json"
                    }
                }
            );

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || "Could not generate the contract."
                );
            }

            contractBox.value = JSON.stringify(data.schema, null, 2);

            alert("JSON Schema generated successfully!");

        } catch (error) {
            alert(`Schema generation failed: ${error.message}`);

        } finally {
            button.disabled = false;
            button.textContent = "✨ Generate contract from endpoint";
        }
    }
);


// FEATURE 2: RUN API VALIDATION
document.getElementById("run-btn").addEventListener(
    "click",
    async (event) => {

        // Prevent any default click or form submission behaviour.
        event.preventDefault();
        event.stopPropagation();
        event.stopImmediatePropagation();

        // Keep the user on the validation page.
        showPage("validate");

        const endpoint = document.getElementById("endpoint").value.trim();
        const method = document.getElementById("method").value;
        const scenario = document.getElementById("scenario").value;

        const resultBox = document.getElementById("validation-result");
        const runButton = document.getElementById("run-btn");

        let contract;

        try {
            contract = JSON.parse(
                document.getElementById("contract").value
            );

        } catch (error) {
            resultBox.className = "result-box fail-result";
            resultBox.classList.remove("hidden");

            resultBox.innerHTML = `
                <h3>Invalid contract JSON</h3>
                <p>Check the JSON in the contract box.</p>
            `;

            return;
        }

        if (!endpoint) {
            resultBox.className = "result-box fail-result";
            resultBox.classList.remove("hidden");
            resultBox.innerHTML = `
                <h3>Endpoint required</h3>
                <p>Please enter an API endpoint URL.</p>
            `;
            return;
        }

        runButton.disabled = true;
        runButton.textContent = "Validating...";

        resultBox.className = "result-box";
        resultBox.classList.remove("hidden");
        resultBox.textContent = "Sending request to the backend...";

        try {
            const response = await fetch(`${API}/validate/run`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    endpoint,
                    method,
                    contract,
                    scenario
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(
                    data.detail || `Backend returned HTTP ${response.status}`
                );
            }

            const status = data.status === "PASS" ? "PASS" : "FAIL";

            resultBox.className =
                `result-box ${status === "PASS" ? "pass-result" : "fail-result"}`;

            // FIELD-LEVEL ERRORS
            const errorRows = Array.isArray(data.errors) && data.errors.length
                ? `
                    <h4>Field-level errors</h4>
                    <div class="table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th>FIELD</th>
                                    <th>EXPECTED</th>
                                    <th>RECEIVED</th>
                                    <th>DETAIL</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${data.errors.map(error => `
                                    <tr>
                                        <td>${escapeHTML(error.field)}</td>
                                        <td>${escapeHTML(
                    typeof error.expected === "object"
                        ? JSON.stringify(error.expected)
                        : error.expected
                )}</td>
                                        <td>${escapeHTML(error.received)}</td>
                                        <td>${escapeHTML(error.message)}</td>
                                    </tr>
                                `).join("")}
                            </tbody>
                        </table>
                    </div>
                `
                : "";

            // PLAIN-ENGLISH EXPLANATIONS
            const explanationsBlock =
                Array.isArray(data.explanations) && data.explanations.length
                    ? `
                        <div class="diagnosis">
                            <h4>Smart error explanations</h4>
                            <ul>
                                ${data.explanations.map(explanation => `
                                    <li>${escapeHTML(explanation)}</li>
                                `).join("")}
                            </ul>
                        </div>
                    `
                    : "";

            // HTTP DIAGNOSIS
            const diagnosisBlock = data.diagnosis
                ? `
                    <div class="diagnosis">
                        <h4>Diagnosis</h4>
                        <p>${escapeHTML(data.diagnosis)}</p>
                    </div>
                `
                : "";

            const actualStatus =
                data.actual_http_status ?? data.http_status ?? "N/A";

            const simulatedStatus =
                data.actual_http_status !== undefined
                    ? `<p><strong>Simulated status:</strong> ${escapeHTML(data.http_status)}</p>`
                    : "";

            // DISPLAY RESULTS
            resultBox.innerHTML = `
                <h3>
                    ${status === "PASS"
                    ? "✓ Validation passed"
                    : "✕ Validation failed"}
                </h3>

                <p>${escapeHTML(
                        data.message || data.error || "Validation completed."
                    )}</p>

                <div class="result-metrics">
                    <p>
                        <strong>HTTP status:</strong>
                        ${escapeHTML(actualStatus)}
                    </p>

                    <p>
                        <strong>Response time:</strong>
                        ${escapeHTML(formatResponseTime(data.response_time_ms))}
                    </p>
                </div>

                ${diagnosisBlock}
                ${explanationsBlock}
                ${simulatedStatus}
                ${errorRows}

                <details>
                    <summary>View technical response</summary>
                    <pre>${escapeHTML(JSON.stringify(data, null, 2))}</pre>
                </details>
            `;

            // Refresh dashboard data without changing the current page.
            updateDashboard().catch(error => {
                console.error("Dashboard refresh failed:", error);
            });

            // Explicitly remain on Validate API.
            showPage("validate");

            // Bring the result into view.
            resultBox.scrollIntoView({
                behavior: "smooth",
                block: "nearest"
            });

        } catch (error) {
            resultBox.className = "result-box fail-result";
            resultBox.classList.remove("hidden");

            resultBox.innerHTML = `
                <h3>Could not complete validation</h3>
                <p>${escapeHTML(error.message)}</p>
                <p>Make sure the FastAPI backend is running.</p>
            `;

            showPage("validate");

        } finally {
            runButton.disabled = false;
            runButton.textContent = "▶ Run validation";
        }
    }
);


// REFRESH BUTTON
document.getElementById("refresh-btn").addEventListener(
    "click",
    () => {
        updateDashboard();
    }
);


// CLEAR HISTORY
document.getElementById("clear-history").addEventListener(
    "click",
    async () => {
        const confirmed = confirm(
            "Are you sure you want to permanently clear all validation history?"
        );

        if (!confirmed) return;

        const button = document.getElementById("clear-history");
        button.disabled = true;

        try {
            const response = await fetch(`${API}/history`, {
                method: "DELETE"
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || "Could not clear history.");
            }

            await updateDashboard();

            alert("Validation history cleared successfully!");

        } catch (error) {
            alert(`Could not clear history: ${error.message}`);

        } finally {
            button.disabled = false;
        }
    }
);


// INITIALIZE APPLICATION
document.getElementById("endpoint").value = `${API}/products`;

showPage("dashboard");
updateDashboard();
