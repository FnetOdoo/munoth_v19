/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { markup } from "@odoo/owl";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add('sale_subscription_tour', {
    url: "/web",
    steps: () => [{
        trigger: '.o_app[data-menu-xmlid="sale_subscription.menu_sale_subscription_root"]',
        content: _t('Want recurring billing via subscription management ? Get started by clicking here'),
        tooltipPosition: 'bottom',
    },
    {
        trigger: '.dropdown-toggle[data-menu-xmlid="sale_subscription.menu_sale_subscription_config"]',
        content: _t('Configure your subscription templates here'),
        tooltipPosition: 'bottom',
    },
    {
        trigger: '.dropdown-item[data-menu-xmlid="sale_subscription.menu_template_of_subscription"]',
        content: markup(_t('Click here to create <b>your first subscription template</b>')),
        tooltipPosition: 'top',
    },
    {
        trigger: '.o-kanban-button-new',
        content: _t('Let\'s create your first subscription template.'),
        tooltipPosition: 'bottom',
    },
    {
        trigger: 'div.oe_title input',
        content: markup(_t('Enter a name for this template.<br/><i>(e.g. eLearning Yearly)</i>')),
        tooltipPosition: 'right',
    },
    {
        trigger: 'select.field_rule_type',
        content: markup(_t('Choose the recurrence for this template.<br/><i>(e.g. 1 time per Year)</i>')),
        tooltipPosition: 'right',
    },
    {
        trigger: '.o_form_button_save',
        content: _t('Save this template and the modifications you\'ve made to it.'),
        tooltipPosition: 'bottom',
    },
    {
        trigger: '.dropdown-toggle[data-menu-xmlid="sale_subscription.menu_sale_subscription"]',
        content: _t('Let\'s go to the catalog to create our first subscription product'),
        tooltipPosition: 'bottom',
    },
    {
        trigger: '.dropdown-item[data-menu-xmlid="sale_subscription.menu_sale_subscription_product"]',
        content: _t('Create your first subscription product here'),
        tooltipPosition: 'top',
    },
    {
        trigger: '.o_list_button_add',
        content: _t('Go ahead and create a new product'),
        tooltipPosition: 'right',
    },
    {
        trigger: 'input.o_field_widget[name="name"]',
        content: markup(_t('Choose a product name.<br/><i>(e.g. eLearning Access)</i>')),
        tooltipPosition: 'right',
    },
    {
        trigger: '.o_field_widget.field_sub_template_id',
        content: _t('Select your newly created template. Every sale of this product will generate a new subscription!'),
        tooltipPosition: 'top',
    },
    {
        trigger: '.o_form_button_save',
        content: markup(_t('Save and you\'re all set!<br/>Simply sell this product to create a subscription automatically or create a subscription manually!')),
        tooltipPosition: 'right',
    },
    ],
});