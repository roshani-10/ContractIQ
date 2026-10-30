const API = "http://127.0.0.1:8000";

const pages = ["dashboard", "validate", "history", "docs"];

function showPage(page) {
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

    const title = titles[page] || titles.dashboard;
    document.getElementById("page-title").textContent = title;
    document.getElementById("breadcrumb").textContent = title;
}

document.querySelectorAll("[data-page]").forEach(button => {
    button.addEventListener("click", () => {
        showPage(button.dataset.page);
    });
});

document.querySelectorAll("[data-go]").forEach(button => {
    button.addEventListener("click", () => {
        showPage(button.dataset.go);
    });
});

async function getHistory() {
    try {
        const response = await fetch(`${API}/history`);

        if (!response.ok) {
            throw new Error("Could not load validation history.");
        }

        return await response.json();
    } catch (error) {
        console.error("History loading failed:", error);
        return [];
    }
}

function escapeHTML(value) {
    return String(value ?? "").replace(/[&<>"']/g, char => ({
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;"
    })[char]);
}

function renderTable(elementId, history) {
    const table = document.getElementById(elementId);
    if (!table) return;

    if (!history.length) {
        table.innerHTML =
            '<tr><td colspan="4" class="empty">No validations recorded yet.</td></tr>';
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
            <td>${escapeHTML(item.created_at || item.time || "")}</td>
        </tr>
    `).join("");
}

async function updateDashboard() {
    const history = await getHistory();

    const passed = history.filter(item => item.status === "PASS").length;
    const failed = history.filter(item => item.status === "FAIL").length;

    document.getElementById("total-count").textContent = history.length;
    document.getElementById("pass-count").textContent = passed;
    document.getElementById("fail-count").textContent = failed;

    renderTable("recent-table", history.slice(0, 5));
    renderTable("history-table", history);
}

document.getElementById("validation-form").addEventListener(
    "submit",
    async event => {
        event.preventDefault();

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
        } catch {
            resultBox.className = "result-box fail-result";
            resultBox.classList.remove("hidden");
            resultBox.innerHTML =
                "<h3>Invalid contract JSON</h3><p>Check the JSON in the contract box.</p>";
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

            resultBox.innerHTML = `
                <h3>${status === "PASS" ? "✓ Validation passed" : "✕ Validation failed"}</h3>
                <p>${escapeHTML(data.message || data.error || "Validation completed.")}</p>
                <pre>${escapeHTML(JSON.stringify(data, null, 2))}</pre>
            `;

            // Refresh the statistics without intentionally navigating away.
            await updateDashboard();

            // Keep the user on the validation page to view the result.
            showPage("validate");

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

document.getElementById("refresh-btn").addEventListener(
    "click",
    updateDashboard
);

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

document.getElementById("endpoint").value = `${API}/products`;

updateDashboard();