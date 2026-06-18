/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.ContractSubmit = publicWidget.Widget.extend({
    selector: '.contract-submit',
    events: {
        'click': '_onClick',
    },

    //--------------------------------------------------------------------------
    // Handlers
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _onClick: function () {
        this.$el.attr('disabled', true);
        this.$el.prepend('<i class="fa fa-refresh fa-spin"></i> ');
        this.$el.closest('form').submit();
    },
});

export default publicWidget.registry.ContractSubmit;