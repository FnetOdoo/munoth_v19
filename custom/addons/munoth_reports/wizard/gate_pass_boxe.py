from odoo import api, models, fields, _
import json
import xlsxwriter
import base64
from datetime import date, datetime, timedelta, time

class GatePassBoxes(models.Model):
    _name='gate.pass.boxes'

    boxes = fields.Char()
    stock_move_line = fields.Many2one('stock.move.line')

    def update_box_list(self):
        for rec in self:
            if rec.stock_move_line:
                rec.stock_move_line.boxes = rec.boxes



class PalletProduct(models.TransientModel):
    _name = 'pallet.product'
    _description = 'Pallet Product'

    product_ids = fields.One2many(
        'stock.move.wizard.product',
        'wizard_id'
    )
    pallet_product_ids = fields.Many2many('product.product')

    def action_confirm(self):
        for rec in self:
            pallets=self.env['stock.move.wizard.product'].search([('wizard_id','=',self.product_ids.id)])

    @api.model
    def default_get(self, fields):
        res = super(PalletProduct, self).default_get(fields)
        picking_id = self._context.get('active_id')
        if picking_id:
            picking = self.env['stock.picking'].browse(picking_id)
            move_lines = picking.move_line_ids.filtered(lambda line: line.product_id)
            product_ids = move_lines.mapped('product_id').ids
            wizard_product_records = []
            for product_id in product_ids:
                wizard_product_records.append((0, 0, {'move_line_ids': [(6, 0, [product_id])]}))

            res.update({
                'pallet_product_ids': [(6, 0, product_ids)]
            })
        return res


class StockMoveWizardProduct(models.TransientModel):
    _name = 'stock.move.wizard.product'
    _description = 'Product in Stock Move Wizard'

    wizard_id = fields.Many2one(
        'pallet.product',
        string="Wizard",
        required=True
    )

    product_uom_id = fields.Many2many(
        'uom.uom'
    )

    # pallet_products_ids = fields.Many2many('product.product')

    product_ids_domain = fields.Binary(compute='compute_product_domain', store=True)

    move_line_ids = fields.Many2many(
        'product.product',
        string="Product",
    )

    pallets = fields.Char()

    @api.depends('wizard_id')
    def compute_product_domain(self):
        for rec in self:
            rec.product_ids_domain = [('id', 'in', rec.wizard_id.pallet_product_ids.ids)]
