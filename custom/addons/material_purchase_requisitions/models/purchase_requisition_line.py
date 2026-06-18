# -*- coding: utf-8 -*-

from odoo import models, fields, api

class MaterialPurchaseRequisitionLine(models.Model):
    _name = "material.purchase.requisition.line"
    _description = 'Material Purchase Requisition Lines'  # Removed duplicate

    requisition_id = fields.Many2one(
        'material.purchase.requisition',
        string='Requisitions',
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )
    description = fields.Char(
        string='Description',
        required=True,
    )
    qty = fields.Float(
        string='Quantity',
        default=1,
        required=True,
    )
    uom = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True,
    )
    partner_id = fields.Many2many(
        'res.partner',
        string='Vendors',
    )
    requisition_type = fields.Selection(
        selection=[
            ('internal', 'Internal Picking'),
            ('purchase', 'Purchase Order'),
        ],
        string='Requisition Action',
        default='purchase',
        required=True,
    )

    @api.onchange('product_id')
    def onchange_product_id(self):
        for rec in self:
            rec.description = rec.product_id.display_name
            rec.uom = rec.product_id.uom_id.id

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: