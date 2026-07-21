# -*- coding: utf-8 -*-
from odoo.exceptions import UserError, ValidationError
from odoo import models, fields, api, _


class MaterialPurchaseRequisitionLine(models.Model):
    _name = "material.purchase.requisition.line"
    _description = 'Material Purchase Requisition Lines'

    requisition_id = fields.Many2one('material.purchase.requisition', string='Requisitions')
    product_creation_id = fields.Many2one('material.purchase.requisition', string='Requisitions')

    product_id = fields.Many2one('product.product', string='Product')
    description = fields.Char(string='Description')
    qty = fields.Float(string='Quantity', default=1)
    uom = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    partner_id = fields.Many2many('res.partner', string='Vendors')
    requisition_type = fields.Selection(
        selection=[('internal', 'Internal Picking'), ('purchase', 'Purchase Order')],
        string='Requisition Action',
        default='purchase',
    )


    @api.onchange('product_id')
    def onchange_product_id(self):
        for rec in self:
            rec.description = rec.product_id.display_name
            rec.uom = rec.product_id.uom_id.id

    def unlink(self):
        for rec in self:
            parent = rec.requisition_id or rec.product_creation_id
            if parent and parent.state not in ('draft'):
                raise UserError(
                    _('You cannot delete a Purchase Requisition line which is not in draft, '
                      'cancelled, or rejected state.')
                )
        return super(MaterialPurchaseRequisitionLine, self).unlink()



class ProductCreationLine(models.Model):
    _name = "product.creation.line"
    _description = 'Product Creation Line'

    product_creation_id = fields.Many2one('material.purchase.requisition', string='Requisitions')

    product_id = fields.Many2one('product.product', string='Product')
    qty = fields.Float(string='Quantity', default=1)
    uom = fields.Many2one('uom.uom', string='Unit of Measure', required=True)
    product_name = fields.Char(string='Product Name')  # required removed - only mandatory for item-code lines
    specification = fields.Char(string='Specification')
    remarks = fields.Text(string='Remarks')
    item_code_created = fields.Boolean(string='Item Code Created', copy=False, readonly=True)


    def unlink(self):
        for rec in self:
            parent = rec.requisition_id or rec.product_creation_id
            if parent and parent.state not in ('draft'):
                raise UserError(
                    _('You cannot delete a Purchase Requisition line which is not in draft, '
                      'cancelled, or rejected state.')
                )
        return super(ProductCreationLine, self).unlink()

    def action_create_product(self):
        self.ensure_one()
        if self.product_id:
            raise UserError(_('A product is already linked to this line.'))
        if not self.product_name:
            raise UserError(_('Please enter a Product Name before creating the product.'))

        product = self.env['product.product'].sudo().create({
            'name': self.product_name,
            'description': self.specification,
            'uom_id': self.uom.id if self.uom else False,
        })
        self.write({
            'product_id': product.id,
            'item_code_created': True,
        })

        return {
            'type': 'ir.actions.act_window',
            'name': _('Product'),
            'res_model': 'product.product',
            'view_mode': 'form',
            'res_id': product.id,
            'target': 'current',  # opens in the same window; use 'new' for a popup dialog
        }