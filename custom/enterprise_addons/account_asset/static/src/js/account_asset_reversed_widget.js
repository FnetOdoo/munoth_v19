/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

/**
 * OWL field widget that shows an exclamation icon on depreciation lines
 * that have been reversed (i.e., reversal_move_id is set).
 *
 * Replaces the legacy AbstractField-based widget for Odoo 16+/19.
 */
class DeprecLinesReversedWidget extends Component {
    static template = "account_asset.DeprecLinesReversedWidget";
    static props = {
        ...standardFieldProps,
    };

    get isReversed() {
        // reversal_move_id is a Many2one field; truthy when a reversal exists
        return !!this.props.record.data[this.props.name];
    }
}

registry.category("fields").add("deprec_lines_reversed", {
    component: DeprecLinesReversedWidget,
    supportedTypes: ["many2one"],
});
