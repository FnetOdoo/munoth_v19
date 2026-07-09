from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round



class StockReturnPickingLine(models.TransientModel):
    _inherit = "stock.return.picking.line"

    reason = fields.Text(string="Reason for Return")

class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    return_value = fields.Char()


    # return_id = fields.Char()

    def create_returns(self):
        res = super(StockReturnPicking, self).create_returns()
        for line in self.product_return_moves:
            if line.move_id and line.reason:
                line.move_id.write({'reason': line.reason})
        if self.return_value:
            original_record = self.env['mrp.material.request'].search([('id','=',self.return_value)], limit=1)
            # if original_record.exists():
            original_record.write({
                'state': 'request',
            })


        return res











