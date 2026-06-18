from odoo import models, fields, api, _


class OutgoingQualityControl(models.Model):
    _name = 'outgoing.quality.control'

    name = fields.Char(copy=False, readonly=True, default=lambda x: _('New'), tracking=True)
    rev = fields.Date()
    effective_date = fields.Date()
    date = fields.Date(default=fields.Date.today())
    stock_id = fields.Many2one('stock.picking', string="Delivery", domain=[('picking_type_id.code', '=', 'outgoing')])
    customer_name = fields.Char(related='stock_id.partner_id.name', string="Customer Name", readonly=True)
    stock_ref = fields.Char(related='stock_id.name', readonly=True)
    stock_type = fields.Selection([('regular_supply', 'Regular Supply'),
                                   ('replacement', 'Replacement'),
                                   ('sample', 'Sample')])
    lot_no = fields.Char()
    aql = fields.Char()
    material = fields.Char()
    model_id = fields.Many2one('product.model', 'Model')
    total_qty = fields.Float(compute='get_stock_qty')
    sample_size = fields.Float()
    checked_by = fields.Many2one('res.users')

    @api.depends('stock_id')
    def get_stock_qty(self):
        for rec in self:
            rec.total_qty = False
            total_qty = sum(stock.quantity for stock in rec.stock_id.move_line_ids)
            rec.total_qty = total_qty

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = seq.next_by_code('outgoing.quality') or _('New')
        return super().create(vals_list)

    def name_get(self):
        result = []
        for rec in self:
            name = (rec.stock_id.name or '')
            result.append((rec.id, name))
        return result

    weight_observation = fields.Char()
    weight_result = fields.Selection([('pass', 'PASS'), ('fail', 'FAIL')], default="pass")
    weight_remarks = fields.Char()
    cell_thickness_observation = fields.Char()
    cell_thickness_result = fields.Selection([('pass', 'PASS'), ('fail', 'FAIL')], default="pass")
    cell_thickness_remarks = fields.Char()
    cell_width_observation = fields.Char()
    cell_width_result = fields.Selection([('pass', 'PASS'), ('fail', 'FAIL')], default="pass")
    cell_width_remarks = fields.Char()
    cell_length_observation = fields.Char()
    cell_length_result = fields.Selection([('pass', 'PASS'), ('fail', 'FAIL')], default="pass")
    cell_length_remarks = fields.Char()
    ocv_observation = fields.Char()
    ocv_result = fields.Selection([('pass', 'PASS'), ('fail', 'FAIL')], default="pass")
    ocv_remarks = fields.Char()
    ir_observation = fields.Char()
    ir_result = fields.Selection([('pass', 'PASS'), ('fail', 'FAIL')], default="pass")
    ir_remarks = fields.Char()
    logo_observation = fields.Char()
    logo_result = fields.Selection([('pass', 'PASS'), ('fail', 'FAIL')], default="pass")
    logo_remarks = fields.Char()
    printing_observation = fields.Char()
    printing_result = fields.Selection([('pass', 'PASS'), ('fail', 'FAIL')], default="pass")
    printing_remarks = fields.Char()
    visual_result = fields.Selection([('pass', 'PASS'), ('fail', 'FAIL')], default="pass")
    visual_remarks = fields.Char()


