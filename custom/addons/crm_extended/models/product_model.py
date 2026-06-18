from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    state_taxes_ids = fields.Many2many('account.tax', 'productmp_taxes_rel', 'prod_id', 'tax_id', string='State Taxes', domain=[('type_tax_use', '=', 'sale')])
    product_rack = fields.Char('Rack')

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return

        company_state = self.env.company.state_id
        shipping_state = self.order_id.partner_shipping_id.state_id

        if company_state == shipping_state:
            self.tax_ids = [(6, 0, self.product_id.product_tmpl_id.taxes_id.ids)]
        else:
            self.tax_ids = [(6, 0, self.product_id.product_tmpl_id.state_taxes_ids.ids)]


class ProductModel(models.Model):
    _inherit = 'product.model'
    _description = 'Product Models'

    lead_id = fields.Many2one('crm.lead', string="Lead")