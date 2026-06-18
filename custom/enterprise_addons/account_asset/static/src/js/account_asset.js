/** @odoo-module **/

import { formView } from "@web/views/form/form_view";
import { registry } from "@web/core/registry";

/**
 * AssetFormController extends the standard FormController for the
 * account.asset form view (js_class="asset_form").
 *
 * Extend setup() here for any future asset-form-specific behaviour.
 */
class AssetFormController extends formView.Controller {
    setup() {
        super.setup();
    }
}

export const assetFormView = {
    ...formView,
    Controller: AssetFormController,
};

registry.category("views").add("asset_form", assetFormView);