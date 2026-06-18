# -*- coding: utf-8 -*-

from odoo import models, fields, api


class MrpDelivery(models.Model):
    _name = "mrp.delivery"
    _description = 'Sales Delivery'
    _rec_name = 'model_id'

    name = fields.Char("Name")
    days_full = fields.Integer("Fully Available")
    days_partial = fields.Integer("Partially Available")
    days_no = fields.Integer("Not Available")
    model_id = fields.Many2one('product.model', string="Model")
    product_qty = fields.Float('To Produce(Qty)', digits='Product Unit of Measure', required=True)
    line_ids = fields.One2many('mrp.delivery.line', 'delivery_id', string="Lines", store=True)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id.id)


class MrpDeliveryLine(models.Model):
    _name = 'mrp.delivery.line'
    _description = 'Sales Delivery Line'

    delivery_id = fields.Many2one('mrp.delivery', string="Delivery")
    company_id = fields.Many2one('res.company', string="Company", related='delivery_id.company_id')
    product_id = fields.Many2one('product.product', 'Product', check_company=True, required=True)
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.relative_uom_id', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unity of measure', required=True, domain="[('relative_uom_id', '=', product_uom_category_id)]")
    product_qty = fields.Float('Quantity To Produce', digits='Product Unit of Measure', required=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        self.ensure_one()
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id
