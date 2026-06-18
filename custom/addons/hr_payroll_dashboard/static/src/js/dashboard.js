/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onMounted, onWillUnmount } from "@odoo/owl";

// ─────────────────────────────────────────────────────────────────────────────
// ROOT CAUSE OF BLANK CHARTS ON FIRST LOAD:
//   The old code called loadChartJs() inside loadData(), which means
//   Chart.js only starts downloading AFTER the component is already mounted.
//   The CDN fetch takes ~200–800ms; in that window the canvas elements exist
//   but Chart.js isn't ready yet — so nothing draws. On refresh, the CDN
//   response is browser-cached so it resolves instantly.
//
// FIX STRATEGY:
//   1. Start loading Chart.js at MODULE EVALUATION TIME (before mount).
//   2. Use a module-level singleton Promise so parallel components share one load.
//   3. Use waitForCanvas() with a polling retry instead of trusting DOM timing.
//   4. Run data fetch + Chart.js load in parallel via Promise.all().
//   5. After state update, wait one requestAnimationFrame before drawing.
// ─────────────────────────────────────────────────────────────────────────────

// ── Chart.js Singleton Loader ────────────────────────────────────────────────
let _chartJsPromise = null;

function ensureChartJs() {
    if (_chartJsPromise) return _chartJsPromise;
    _chartJsPromise = new Promise((resolve, reject) => {
        if (window.Chart) { resolve(window.Chart); return; }
        const s = document.createElement("script");
        s.src = "https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js";
        s.async = true;
        s.onload = () => {
            if (window.Chart) resolve(window.Chart);
            else reject(new Error("Chart.js loaded but window.Chart is undefined"));
        };
        s.onerror = () => {
            _chartJsPromise = null; // allow future retry
            reject(new Error("Chart.js CDN load failed"));
        };
        document.head.appendChild(s);
    });
    return _chartJsPromise;
}

// Pre-load immediately at module parse time so it's ready before onMounted fires
ensureChartJs().catch(() => {});

// ── Canvas Poller ────────────────────────────────────────────────────────────
// OWL may still be patching the DOM when charts try to render.
// Poll up to maxMs milliseconds for the element to appear.
function waitForCanvas(id, maxMs = 2000) {
    return new Promise((resolve) => {
        const started = Date.now();
        (function check() {
            const el = document.getElementById(id);
            if (el) { resolve(el); return; }
            if (Date.now() - started > maxMs) { resolve(null); return; }
            setTimeout(check, 40);
        })();
    });
}

// ── JSON-RPC Helper (rpc service removed in Odoo 19) ─────────────────────────
async function jsonRpc(route, params = {}) {
    const res = await fetch(route, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Requested-With": "XMLHttpRequest" },
        body: JSON.stringify({ jsonrpc: "2.0", method: "call", id: Date.now(), params }),
    });
    if (!res.ok) throw new Error("HTTP " + res.status);
    const json = await res.json();
    if (json.error) throw new Error(json.error.data?.message || json.error.message || "RPC error");
    return json.result;
}

// ── Colour Palette ───────────────────────────────────────────────────────────
const PALETTE = [
    "#4ecdc4","#7c3aed","#22c55e","#3b82f6",
    "#ef4444","#eab308","#f97316","#6366f1",
    "#ec4899","#14b8a6","#84cc16","#8b5cf6",
];
const pal = (n) => PALETTE.slice(0, Math.max(n, 1));

// ─────────────────────────────────────────────────────────────────────────────
// OWL Component
// ─────────────────────────────────────────────────────────────────────────────
export class PayrollDashboard extends Component {
    static template = "hr_payroll_dashboard.Dashboard";
    static props = ["*"];

    setup() {
        this.action   = useService("action");
        this._charts  = {};
        this._version = 0;  // cancel stale renders on rapid refresh clicks

        this.state = useState({
            loading: true,
            error: false,
            today: new Date().toLocaleDateString("en-GB", {
                weekday: "long", year: "numeric", month: "long", day: "numeric",
            }),
            kpis: {},
            recent_leaves: [],
            graphs: {},
        });

        onMounted(async () => { await this.loadData(); });

        onWillUnmount(() => { this._destroyAll(); });
    }

    _destroyAll() {
        Object.values(this._charts).forEach(c => { try { c.destroy(); } catch (_) {} });
        this._charts = {};
    }

    // ── Data Load + Chart Render ─────────────────────────────────────────────
    async loadData() {
        const ver = ++this._version;
        this.state.loading = true;
        this.state.error   = false;
        this._destroyAll();

        let data;
        try {
            // Fetch data AND ensure Chart.js in parallel
            [data] = await Promise.all([
                jsonRpc("/hr_payroll_dashboard/data", {}),
                ensureChartJs(),
            ]);
        } catch (e) {
            console.error("[PayrollDashboard] data/chartjs load failed:", e);
            if (ver === this._version) { this.state.loading = false; this.state.error = true; }
            return;
        }

        if (ver !== this._version) return; // superseded by a newer loadData call

        // Push state → OWL re-renders, adding <canvas> elements to DOM
        this.state.kpis          = data.kpis          || {};
        this.state.recent_leaves = data.recent_leaves || [];
        this.state.graphs        = data.graphs        || {};
        this.state.loading       = false;

        // Wait for OWL's DOM patch to complete (one animation frame is reliable)
        await new Promise(r => requestAnimationFrame(r));
        if (ver !== this._version) return;

        await this._drawCharts(data.graphs || {}, ver);
    }

    // ── Draw All Charts ──────────────────────────────────────────────────────
    async _drawCharts(g, ver) {
        const Chart = window.Chart;
        if (!Chart) { console.warn("[PayrollDashboard] Chart.js not available"); return; }

        // Wait for all canvases concurrently, then draw each
        const specs = [
            ["monthlyExpenseChart", () => this._line(Chart, "monthlyExpenseChart",  g.monthly_expense     || [], "Net Wage",    "#7c3aed")],
            ["leaveDistChart",      () => this._pie(Chart,  "leaveDistChart",        g.leave_dist          || [])],
            ["deptChart",           () => this._bar(Chart,  "deptChart",             g.dept_data           || [], "Employees",  "#3b82f6")],
            ["attendanceChart",     () => this._line(Chart, "attendanceChart",       g.attendance_per_day  || [], "Check-ins",  "#4ecdc4")],
            ["payslipChart",        () => this._donut(Chart,"payslipChart",          g.payslip_data        || [])],
            ["contractChart",       () => this._donut(Chart,"contractChart",         g.contract_data       || [])],
            ["timeOffChart",        () => this._bar(Chart,  "timeOffChart",          g.leave_dist          || [], "Days",       "#ec4899")],
        ];

        await Promise.all(specs.map(async ([id, draw]) => {
            const canvas = await waitForCanvas(id);
            if (!canvas || ver !== this._version) return;
            if (this._charts[id]) { try { this._charts[id].destroy(); } catch (_) {} delete this._charts[id]; }
            try { draw(); } catch (e) { console.warn(`[PayrollDashboard] ${id}:`, e); }
        }));
    }

    // ── Chart Builders ───────────────────────────────────────────────────────
    _fallback(data) {
        // Always give Chart.js at least one data point so it doesn't render blank
        return data && data.length ? data : [{ label: "–", value: 0 }];
    }

    _line(Chart, id, rawData, label, color) {
        const canvas = document.getElementById(id);
        if (!canvas) return;
        const data = this._fallback(rawData);
        this._charts[id] = new Chart(canvas, {
            type: "line",
            data: {
                labels: data.map(d => d.label),
                datasets: [{
                    label,
                    data: data.map(d => d.value),
                    borderColor: color,
                    backgroundColor: color + "22",
                    borderWidth: 2.5,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: color,
                    pointRadius: 4,
                    pointHoverRadius: 6,
                }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                animation: { duration: 500 },
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { color: "rgba(0,0,0,0.04)" }, ticks: { font: { size: 11 } } },
                    y: { beginAtZero: true, grid: { color: "rgba(0,0,0,0.04)" }, ticks: { font: { size: 11 } } },
                },
            },
        });
    }

    _bar(Chart, id, rawData, label, color) {
        const canvas = document.getElementById(id);
        if (!canvas) return;
        const data = this._fallback(rawData);
        this._charts[id] = new Chart(canvas, {
            type: "bar",
            data: {
                labels: data.map(d => d.label),
                datasets: [{
                    label,
                    data: data.map(d => d.value),
                    backgroundColor: data.map((_, i) => PALETTE[i % PALETTE.length] + "cc"),
                    borderColor:     data.map((_, i) => PALETTE[i % PALETTE.length]),
                    borderWidth: 1.5,
                    borderRadius: 6,
                }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                animation: { duration: 500 },
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { font: { size: 11 } } },
                    y: { beginAtZero: true, grid: { color: "rgba(0,0,0,0.04)" }, ticks: { font: { size: 11 } } },
                },
            },
        });
    }

    _pie(Chart, id, rawData) {
        const canvas = document.getElementById(id);
        if (!canvas) return;
        const data = this._fallback(rawData);
        this._charts[id] = new Chart(canvas, {
            type: "pie",
            data: {
                labels: data.map(d => d.label),
                datasets: [{ data: data.map(d => d.value), backgroundColor: pal(data.length), borderWidth: 2, borderColor: "#fff" }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                animation: { duration: 500 },
                plugins: { legend: { position: "right", labels: { font: { size: 11 }, boxWidth: 13, padding: 8 } } },
            },
        });
    }

    _donut(Chart, id, rawData) {
        const canvas = document.getElementById(id);
        if (!canvas) return;
        const data = this._fallback(rawData);
        this._charts[id] = new Chart(canvas, {
            type: "doughnut",
            data: {
                labels: data.map(d => d.label),
                datasets: [{ data: data.map(d => d.value), backgroundColor: pal(data.length), borderWidth: 2, borderColor: "#fff" }],
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                cutout: "60%",
                animation: { duration: 500 },
                plugins: { legend: { position: "right", labels: { font: { size: 11 }, boxWidth: 13, padding: 8 } } },
            },
        });
    }

    // ── Navigation ───────────────────────────────────────────────────────────
    _go(opts) { this.action.doAction({ type: "ir.actions.act_window", view_mode: "list,form", views: [[false,"list"],[false,"form"]], ...opts }); }

    openAttendance()    { this._go({ name: "Attendances",       res_model: "hr.attendance" }); }
    openLeaveRequests() { this._go({ name: "Leave Requests",    res_model: "hr.leave",       domain: [["state","in",["confirm","validate1","validate"]]] }); }
    openPayslips()      { this._go({ name: "Payslips",          res_model: "hr.payslip" }); }
    openSalaryRules()   { this._go({ name: "Salary Rules",      res_model: "hr.salary.rule" }); }
    openSalaryStructures() { this._go({ name: "Salary Structures", res_model: "hr.payroll.structure" }); }
    openEmployees()     { this._go({ name: "Employees",         res_model: "hr.employee" }); }

    openRunningContracts() {
        const t = new Date().toISOString().split("T")[0];
        this._go({ name: "Running Contracts", res_model: "hr.employee",
            domain: [["contract_date_start","<=",t],"|",["contract_date_end","=",false],["contract_date_end",">=",t]] });
    }

    openExpiredContracts() {
        const t = new Date().toISOString().split("T")[0];
        this._go({ name: "Expired Contracts", res_model: "hr.employee",
            domain: [["contract_date_end","<",t],["contract_date_end","!=",false]] });
    }

    openLeave(id) {
        this.action.doAction({ type: "ir.actions.act_window", name: "Leave", res_model: "hr.leave", res_id: id, view_mode: "form", views: [[false,"form"]] });
    }
}

registry.category("actions").add("hr_payroll_dashboard", PayrollDashboard);
