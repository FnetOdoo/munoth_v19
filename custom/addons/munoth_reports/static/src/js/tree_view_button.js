/** @odoo-module **/
// Migration v15→v19:
// - odoo.define() / require() pattern removed in v17+ (replaced by @odoo-module ES modules)
// - web.ListController / web.ListView / web.view_registry removed
// - Replaced with OWL component patch using @web/views/list/list_controller
// - Original logic (open Process Status Report wizard) is fully preserved

import { ListController } from "@web/views/list/list_controller";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { registry } from "@web/core/registry";
import { listView } from "@web/views/list/list_view";

// Patch ListController to add the Download button for complaint register
patch(ListController.prototype, {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
    },

    // Original _OpenWizard logic preserved — opens Process Status Report wizard
    _OpenWizard() {
        this.action.doAction({
            name: 'Process Status Report',
            res_model: 'process.status.report',
            type: 'ir.actions.act_window',
            context: {},
            domain: [],
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'new',
        });
    },
});

// Register the custom list view variant used by complaint.register
// (js_class="button_in_tree" on the list view)
registry.category("views").add("button_in_tree", {
    ...listView,
    Controller: class ButtonInTreeListController extends ListController {
        setup() {
            super.setup(...arguments);
            this.action = useService("action");
        }
        _OpenWizard() {
            this.action.doAction({
                name: 'Process Status Report',
                res_model: 'process.status.report',
                type: 'ir.actions.act_window',
                context: {},
                domain: [],
                view_mode: 'form',
                views: [[false, 'form']],
                target: 'new',
            });
        }
    },
});
