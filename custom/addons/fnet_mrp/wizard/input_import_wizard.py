from odoo import models, fields, api, _
from odoo.exceptions import UserError


class InputImportWizard(models.TransientModel):
    _name = 'input.import.wizard'
    _description = 'Input product import'

    product_id = fields.Many2one('product.product', 'Product')
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        domain="[('relative_uom_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.relative_uom_id')
    product_qty = fields.Float("Quantity")
    line_ids = fields.Many2many('manufacturing.component', string='Components')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('progress', 'In Progress'),
        ('hold', 'Hold'),
        ('done', 'Done'),
        ('close', 'Closed'),
        ('cancel', 'Cancelled')], string='State')

    def action_update_product(self):
        pass
#
# class InputImportLine(models.TransientModel):
#     _name = 'input.import.line'
#
#     input_import_id = fields.Many2one('input.import.wizard', string='Import Wizard')
#     name = fields.Char("Serial")
#     is_available = fields.Boolean("Already Available")
