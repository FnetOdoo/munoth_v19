from odoo import api, fields, models,_
from odoo.exceptions import UserError

class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         if vals.get('order_id'):
    #             order = self.env['purchase.order'].browse(vals['order_id'])
    #             if order.material_request_id:
    #                 raise UserError(_('You cannot add new lines to an order linked to a Material Request.'))
    #     return super().create(vals_list)

    # def write(self, vals):
    #     for line in self:
    #         if line.order_id.material_request_id:
    #             if 'product_qty' in vals:
    #                 request_line = line.order_id.material_request_id.request_line_ids.filtered(
    #                     lambda l: l.product_id == line.product_id
    #                 )
    #                 if request_line:
    #                     max_qty = request_line[0].purchase_qty
    #                     if vals['product_qty'] < max_qty:
    #                         raise UserError(_(
    #                             '%s: PO Quantity (%s) cannot be less than Material Requests Purchase Quantity (%s).'
    #                         ) % (line.product_id.name, vals['product_qty'], max_qty))
    #     return super().write(vals)

    def unlink(self):
        for line in self:
            if line.order_id.material_request_id:
                raise UserError(_(
                    'You cannot delete product line "%s" because it is linked to a Material Request.'
                ) % line.product_id.display_name)
        return super().unlink()

class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    material_request_id = fields.Many2one('mrp.material.request', string="Material Request")
    narration = fields.Text("Narration")
    #
    # @api.constrains('order_line')
    # def _check_products_match(self):
    #     for rec in self:
    #         if rec.material_request_id:
    #             for record in rec.material_request_id.request_line_ids:
    #                 for product in rec.order_line:
    #                     if product.product_id and record.product_id == product.product_id:
    #                         if record.quantity != product.product_qty:
    #                             raise UserError(_(
    #                                 "You cannot proceed with mismatch quantity.\n\n"
    #                                 "Product: %s\n"
    #                                 "Demand Quantity: %s\n"
    #                                 "Done Quantity: %s\n\n"
    #                                 "Both values must be equal."
    #                             ) % (
    #                                                 product.product_id.display_name,
    #                                                 record.quantity,
    #                                                 product.product_qty,
    #                                             ))

    @api.onchange('material_request_id')
    def onchange_material_request_id(self):
        if self.material_request_id:
            order_lines = []
            for line in self.material_request_id.request_line_ids:
                order_line_values = {
                        'product_id': line.product_id.id,
                        'product_qty': line.quantity,
                        'name': line.name,
                        'product_uom': line.product_uom.id,
                        'date_planned': self.date_order
                    }
                order_lines.append((0, 0, order_line_values))
            self.order_line = order_lines

    def action_view_mrp_request(self):
        self.ensure_one()

        return {
            'name': _('Material Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.material.request',  # IMPORTANT (check model name)
            'view_mode': 'form',
            'res_id': self.material_request_id.id,
            'views': [(False, 'form')],
            'target': 'current',
        }