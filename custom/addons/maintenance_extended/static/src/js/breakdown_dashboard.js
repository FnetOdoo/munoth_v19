/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import {
    Component,
    onWillStart,
    onMounted,
    onWillUnmount,
    useState,
} from "@odoo/owl";

const REFRESH_INTERVAL_MS = 30000; // auto refresh every 30 s
const Y_DIVISIONS = 5; // number of horizontal grid intervals

/** yyyy-mm-dd in local time. */
function fmtDate(d) {
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${d.getFullYear()}-${m}-${day}`;
}

export class BreakdownDashboard extends Component {
    static template = "breakdown_request_dashboard.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");

        // Default range: current month (1st -> last day).
        const now = new Date();
        const monthStart = fmtDate(new Date(now.getFullYear(), now.getMonth(), 1));
        const monthEnd = fmtDate(new Date(now.getFullYear(), now.getMonth() + 1, 0));

        this.state = useState({
            loading: true,
            bars: [],
            maxValue: 1,
            lastUpdate: null,
            tooltip: null, // { x, y, label, count }
            filters: {
                start: monthStart, // on requested_time
                end: monthEnd,
            },
        });

        onWillStart(() => this.loadData());

        onMounted(() => {
            this._timer = setInterval(() => this.loadData(), REFRESH_INTERVAL_MS);
        });

        onWillUnmount(() => {
            clearInterval(this._timer);
        });
    }

    // ------------------------------------------------------------------
    // Data
    // ------------------------------------------------------------------
    async loadData() {
        const data = await this.orm.call(
            "breakdown.request",
            "get_breakdown_dashboard_data",
            [],
            { filters: { ...this.state.filters } }
        );
        this.state.bars = data.bars;
        this.state.maxValue = data.max_value || 1;
        this.state.lastUpdate = new Date().toLocaleTimeString();
        this.state.loading = false;
    }

    /** Called on any date input change: reload with the new range. */
    onFilterChange() {
        this.loadData();
    }

    /** Reset dates back to the present month. */
    resetFilters() {
        const now = new Date();
        const monthStart = fmtDate(new Date(now.getFullYear(), now.getMonth(), 1));
        const monthEnd = fmtDate(new Date(now.getFullYear(), now.getMonth() + 1, 0));
        Object.assign(this.state.filters, {
            start: monthStart,
            end: monthEnd,
        });
        this.loadData();
    }

    /** Top of the y axis: max value rounded up to a clean step multiple. */
    get axisMax() {
        const step = Math.max(1, Math.ceil(this.state.maxValue / Y_DIVISIONS));
        return step * Y_DIVISIONS;
    }

    /** Bar height in % of the plot area (relative to the axis max). */
    heightFor(count) {
        return Math.round((count / this.axisMax) * 100);
    }

    /** Y-axis tick values (top -> bottom), aligned with the gridlines. */
    get yTicks() {
        const step = this.axisMax / Y_DIVISIONS;
        const ticks = [];
        for (let v = this.axisMax; v >= 0; v -= step) {
            ticks.push(v);
        }
        return ticks;
    }

    // ------------------------------------------------------------------
    // Interactions
    // ------------------------------------------------------------------
    openRecords(bar) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: bar.label,
            res_model: "breakdown.request",
            views: [
                [false, "list"],
                [false, "form"],
            ],
            domain: bar.domain,
            target: "current",
        });
    }

    showTooltip(ev, label, count) {
        const rect = ev.currentTarget
            .closest(".o_brd_chart")
            .getBoundingClientRect();
        this.state.tooltip = {
            x: ev.clientX - rect.left + 12,
            y: ev.clientY - rect.top - 10,
            label,
            count,
        };
    }

    hideTooltip() {
        this.state.tooltip = null;
    }

    get lastUpdateLabel() {
        return this.state.lastUpdate
            ? _t("Updated at %s", this.state.lastUpdate)
            : "";
    }
}

registry
    .category("actions")
    .add("breakdown_request_dashboard.dashboard", BreakdownDashboard);