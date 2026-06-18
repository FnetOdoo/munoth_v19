from odoo import models, fields, api, _


class InspectionReportReceiving(models.Model):
    _name = 'inspection.report.receiving'

    name = fields.Char(copy=False, readonly=True, default=lambda x: _('New'), tracking=True)
    rev = fields.Date()
    stock_id = fields.Many2one('stock.picking', string="Receipt", domain=[('picking_type_id.code', '=', 'incoming')])
    supplier_name = fields.Char(related='stock_id.partner_id.name', string="Supplier's Name", readonly=True)
    part_number = fields.Char()
    part_description = fields.Char()
    materials_for = fields.Char()
    inspection_date = fields.Date(default=fields.Date.today())
    drawing_rev = fields.Char()
    received_qty = fields.Float(compute='get_stock_qty')

    @api.depends('stock_id')
    def get_stock_qty(self):
        for rec in self:
            rec.received_qty = False
            total_qty = sum(stock.quantity for stock in rec.stock_id.move_line_ids)
            rec.received_qty = total_qty

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = seq.next_by_code('inspection.report') or _('New')
        return super().create(vals_list)

    def name_get(self):
        result = []
        for rec in self:
            name = (rec.stock_id.name or '')
            result.append((rec.id, name))
        return result

    # width
    first_width_actual = fields.Float()
    second_width_actual = fields.Float()
    third_width_actual = fields.Float()
    forth_width_actual = fields.Float()
    fifth_width_actual = fields.Float()
    width_max = fields.Float(compute='compute_min_max_calc')
    width_min = fields.Float(compute='compute_min_max_calc')
    width_remarks = fields.Text()

    # thickness
    first_thick_actual = fields.Float()
    second_thick_actual = fields.Float()
    third_thick_actual = fields.Float()
    forth_thick_actual = fields.Float()
    fifth_thick_actual = fields.Float()
    thickness_max = fields.Float(compute='compute_min_max_calc')
    thickness_min = fields.Float(compute='compute_min_max_calc')
    thickness_remarks = fields.Text()

    # length
    first_length_actual = fields.Float()
    second_length_actual = fields.Float()
    third_length_actual = fields.Float()
    forth_length_actual = fields.Float()
    fifth_length_actual = fields.Float()
    length_max = fields.Float(compute='compute_min_max_calc')
    length_min = fields.Float(compute='compute_min_max_calc')
    length_remarks = fields.Text()

    # tab_length
    first_tab_length_actual = fields.Float()
    second_tab_length_actual = fields.Float()
    third_tab_length_actual = fields.Float()
    forth_tab_length_actual = fields.Float()
    fifth_tab_length_actual = fields.Float()
    tab_length_max = fields.Float(compute='compute_min_max_calc')
    tab_length_min = fields.Float(compute='compute_min_max_calc')
    tab_length_remarks = fields.Text()

    # tab_width
    first_tab_width_actual = fields.Float()
    second_tab_width_actual = fields.Float()
    third_tab_width_actual = fields.Float()
    forth_tab_width_actual = fields.Float()
    fifth_tab_width_actual = fields.Float()
    tab_width_max = fields.Float(compute='compute_min_max_calc')
    tab_width_min = fields.Float(compute='compute_min_max_calc')
    tab_width_remarks = fields.Text()

    # tab_distance
    first_tab_dist_actual = fields.Float()
    second_tab_dist_actual = fields.Float()
    third_tab_dist_actual = fields.Float()
    forth_tab_dist_actual = fields.Float()
    fifth_tab_dist_actual = fields.Float()
    tab_distance_max = fields.Float(compute='compute_min_max_calc')
    tab_distance_min = fields.Float(compute='compute_min_max_calc')
    tab_dist_remarks = fields.Text()

    # weight
    first_weight_actual = fields.Float()
    second_weight_actual = fields.Float()
    third_weight_actual = fields.Float()
    forth_weight_actual = fields.Float()
    fifth_weight_actual = fields.Float()
    weight_max = fields.Float(compute='compute_min_max_calc')
    weight_min = fields.Float(compute='compute_min_max_calc')
    weight_remarks = fields.Text()

    # visual
    visual_remarks = fields.Text()

    def compute_min_max_calc(self):
        for rec in self:
            # width
            rec.width_max = max(
                [rec.first_width_actual, rec.second_width_actual, rec.third_width_actual, rec.forth_width_actual,
                 rec.fifth_width_actual])
            rec.width_min = min(
                [rec.first_width_actual, rec.second_width_actual, rec.third_width_actual, rec.forth_width_actual,
                 rec.fifth_width_actual])
            # thickness
            rec.thickness_max = max(
                [rec.first_thick_actual, rec.second_thick_actual, rec.third_thick_actual, rec.forth_thick_actual,
                 rec.fifth_thick_actual])
            rec.thickness_min = min(
                [rec.first_thick_actual, rec.second_thick_actual, rec.third_thick_actual, rec.forth_thick_actual,
                 rec.fifth_thick_actual])
            # length
            rec.length_max = max(
                [rec.first_length_actual, rec.second_length_actual, rec.third_length_actual, rec.forth_length_actual,
                 rec.fifth_length_actual])
            rec.length_min = min(
                [rec.first_length_actual, rec.second_length_actual, rec.third_length_actual, rec.forth_length_actual,
                 rec.fifth_length_actual])
            # tab_length
            rec.tab_length_max = max(
                [rec.first_tab_length_actual, rec.second_tab_length_actual, rec.third_tab_length_actual,
                 rec.forth_tab_length_actual, rec.fifth_tab_length_actual])
            rec.tab_length_min = min(
                [rec.first_tab_length_actual, rec.second_tab_length_actual, rec.third_tab_length_actual,
                 rec.forth_tab_length_actual, rec.fifth_tab_length_actual])
            # tab_width
            rec.tab_width_max = max(
                [rec.first_tab_width_actual, rec.second_tab_width_actual, rec.third_tab_width_actual,
                 rec.forth_tab_width_actual, rec.fifth_tab_width_actual])
            rec.tab_width_min = min(
                [rec.first_tab_width_actual, rec.second_tab_width_actual, rec.third_tab_width_actual,
                 rec.forth_tab_width_actual, rec.fifth_tab_width_actual])
            # tab_dist
            rec.tab_distance_max = max(
                [rec.first_tab_dist_actual, rec.second_tab_dist_actual, rec.third_tab_dist_actual,
                 rec.forth_tab_dist_actual, rec.fifth_tab_dist_actual])
            rec.tab_distance_min = min(
                [rec.first_tab_dist_actual, rec.second_tab_dist_actual, rec.third_tab_dist_actual,
                 rec.forth_tab_dist_actual, rec.fifth_tab_dist_actual])
            # weight
            rec.weight_max = max(
                [rec.first_weight_actual, rec.second_weight_actual, rec.third_weight_actual, rec.forth_weight_actual,
                 rec.fifth_weight_actual])
            rec.weight_min = min(
                [rec.first_weight_actual, rec.second_weight_actual, rec.third_weight_actual, rec.forth_weight_actual,
                 rec.fifth_weight_actual])