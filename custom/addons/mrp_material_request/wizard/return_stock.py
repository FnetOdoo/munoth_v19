from odoo import models, fields

class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    return_value = fields.Char()
    # return_id = fields.Char()

    def create_returns(self):
        res = super(StockReturnPicking, self).create_returns()
        if self.return_value:
            original_record = self.env['mrp.material.request'].search([('id','=',self.return_value)], limit=1)
            if original_record.exists():
                original_record.write({
                    'state': 'request',
                })
            else:
               pass
        else:
           pass
        return res


