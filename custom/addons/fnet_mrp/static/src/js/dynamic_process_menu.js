/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class DynamicProcessMenu extends Component {
    static template = "manufacturing.DynamicProcessMenu";
    static props = {
        action: { type: Object, optional: true },
        actionId: { type: [Number, Boolean], optional: true },
        updateActionState: { type: Function, optional: true },
        className: { type: String, optional: true },
        "*": true,
    };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        this.state = useState({
            processTypes: [],
            loading: true,
            activeId: null,
            activeLabel: "",
            records: [],
            recordsLoading: false,
        });

        onWillStart(async () => {
            await this._loadProcessTypes();
        });
    }

    async _loadProcessTypes() {
        try {
            // ✅ No active filter — your model has no active field
            const types = await this.orm.searchRead(
                "manufacturing.process.type",
                [],
                ["id", "name"],
                { order: "name asc" }
            );
            console.log("Process types:", types);
            this.state.processTypes = types;

            if (types.length > 0) {
                await this._selectType(types[0].id, types[0].name);
            }
        } catch (e) {
            console.error("Failed to load process types:", e);
        } finally {
            this.state.loading = false;
        }
    }

    async _selectType(typeId, typeName) {
        this.state.activeId = typeId;
        this.state.activeLabel = typeName;
        this.state.recordsLoading = true;

        try {
            // ✅ Correct field: manufacturing_process_type_id (from your model)
            const records = await this.orm.searchRead(
                "manufacturing.process",
                [["manufacturing_process_type_id", "=", typeId]],
                [
                    "id",
                    "name",
                    "state",
                    "manufacturing_process_type_id",
                    "production_plan_id",
                    "product_id",
                    "product_qty",
                    "batch_id",
                ],
                { order: "id desc" }
            );
            console.log("Records for type", typeName, ":", records);
            this.state.records = records;
        } catch (e) {
            console.error("Failed to load processes:", e);
            this.state.records = [];
        } finally {
            this.state.recordsLoading = false;
        }
    }

    async _openRecord(recordId) {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name: this.state.activeLabel,
            res_model: "manufacturing.process",
            view_mode: "form",
            views: [[false, "form"]],
            res_id: recordId,
            target: "current",
        });
    }

    async _openFullList(typeId, typeName) {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name: typeName,
            res_model: "manufacturing.process",
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            // ✅ Correct field name
            domain: [["manufacturing_process_type_id", "=", typeId]],
            context: { default_manufacturing_process_type_id: typeId },
            target: "current",
        });
    }

    async _createNew() {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            name: `New ${this.state.activeLabel}`,
            res_model: "manufacturing.process",
            view_mode: "form",
            views: [[false, "form"]],
            // ✅ Correct field name
            context: { default_manufacturing_process_type_id: this.state.activeId },
            target: "current",
        });
    }

    // ✅ State badge color helper
    _getStateBadgeClass(state) {
        const map = {
            draft: "badge-secondary",
            confirmed: "badge-primary",
            progress: "badge-warning",
            hold: "badge-danger",
            done: "badge-success",
            close: "badge-dark",
            cancel: "badge-danger",
        };
        return `badge ${map[state] || "badge-secondary"}`;
    }
}

registry.category("actions").add("dynamic_process_menu", DynamicProcessMenu);