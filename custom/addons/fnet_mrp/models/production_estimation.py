from odoo import models, fields, api, _
from datetime import datetime, timedelta
from odoo.exceptions import UserError

class ManufacturingShift(models.Model):
    _name = 'mrp.shift'
    _description = 'Manufacturing Shift'

    name = fields.Char()
    code = fields.Char()
    start_time = fields.Float()
    end_time = fields.Float()
    total_duration = fields.Float()
    def name_get(self):
        result = []
        for rec in self:
            name_parts = []

            if rec.name:
                name_parts.append(f'{rec.name}: ')

            if rec.code:
                name_parts.append(f'{rec.code}:')

            if rec.total_duration:
                name_parts.append(f'{rec.total_duration}')
            result.append((rec.id, ' '.join(name_parts)))

        return result


class ManufacturingStage(models.Model):
    _name = 'mrp.stage'
    _description = 'Manufacturing Stage'

    name = fields.Char()
    qty = fields.Float()
    stage_ids = fields.One2many('mrp.stage.line', 'stage_id')
    product_id = fields.Many2one('product.product')
    shift_id = fields.Many2one('mrp.shift')
    choose_stage = fields.Selection([
        ('stage_0', 'Process Type 0'),
        ('stage_1', 'Process Type 1'),
        ('stage_2', 'Process Type 2'),
        ('stage_3', 'Process Type 3'),
        ('stage_4', 'Process Type 4'),
        ('stage_5', 'Process Type 5'),
        ('stage_6', 'Process Type 6')], default='stage_1', help='Choose stage of going to production')
    component_ids = fields.One2many('manufacturing.component', 'stage_id')

    def name_get(self):
        result = []
        for rec in self:
            name_parts = []

            if rec.name:
                name_parts.append(f'{rec.name}: ')

            if rec.product_id:
                name_parts.append(f'{rec.product_id.display_name} ')
            result.append((rec.id, ' '.join(name_parts)))

        return result


class ManufacturingStageLine(models.Model):
    _name = 'mrp.stage.line'
    _description = 'Manufacturing Stage Line'

    machine_id = fields.Many2many('manufacturing.machine')
    qty = fields.Float()
    stage_id = fields.Many2one('mrp.stage')
    estimation_id = fields.Many2one('mrp.estimation')
    duration = fields.Float(related='stage_id.shift_id.total_duration')
    type = fields.Selection([
        ('anode_slitting', 'Anode Slitting '),
        ('cathode_slitting', 'Cathode Slitting '),
        ('anode_drying', 'Anode Drying'),
        ('cathode_drying', 'Cathode Drying'),
        ('diaphragm_drying', 'Diaphragm Drying'),
        ('anode_electrode_making', 'Anode Electrode Making'),
        ('cathode_electrode_making', 'Cathode Electrode Making'),
        ('winding', 'Winding'),
        ('hot_press_jelly', 'Hot Press Jelly'),
        ('assembly', 'Assembly'),
        ('qr_code_print', 'QR Code Printing'),
        ('cell_drying', 'Cell Drying'),
        ('injection', 'Injection'),
        ('high_temperature', 'High Temperature'),
        ('cell_clamp_baking', 'Cell Clamp Baking'),
        ('aged_formation_cell', 'Aged Formation Cell'),
        ('degas', 'Degas'),
        ('dsf', 'Double side Folding'),
        ('pad_printing', 'Pad Printing'),
        ('capacity_test', 'Capacity Test'),
        ('voltage_test', 'Voltage Test'),
        ('packing', 'Packing')
    ])
    stage = fields.Char()
    stage_duration = fields.Float()
    based_ppm = fields.Boolean()
    required_qty = fields.Float()
    required_time = fields.Float()
    required_days = fields.Float()
    estimation_stage_id = fields.Many2one('estimation.stage.line')


class EstimationLine(models.Model):
    _name = 'estimation.stage.line'
    _description = 'Estimation Stage Line'

    stage_id = fields.Many2one('mrp.stage')
    shift_ids = fields.Many2many('mrp.shift')
    production_qty = fields.Float()
    ppm = fields.Integer(default='1')
    start_date = fields.Date()
    expected_end_date = fields.Date()
    estimation_id = fields.Many2one('mrp.estimation')
    days = fields.Float()
    row_material_stock_status = fields.Selection([('full', 'Fully Available'), ('no', 'Not Available'), ('partial', 'Partially Available')], string="Stock Status(MRP)")
    production_date_reserved = fields.Boolean(related='estimation_id.production_date_reserved')




class MrpEstimation(models.Model):
    _name = 'mrp.estimation'
    _description = 'Mrp Estimation'

    name = fields.Char(
        'Reference', copy=False, readonly=True, default=lambda x: _('New'))
    product_id = fields.Many2one('product.product')
    shift_ids = fields.Many2many('mrp.shift')
    stage_id = fields.Many2one('mrp.stage')
    qty = fields.Float()
    mrp_stage_ids = fields.One2many('mrp.stage.line', 'estimation_id')
    ppm = fields.Integer(default='1')
    total_days = fields.Float(compute='_compute_total_days_calculate')
    start_date = fields.Date()
    expected_end_date = fields.Date(compute='_compute_delivery_end_date')
    location_id = fields.Many2one('stock.location')
    fg_qty = fields.Float()
    in_process_qty = fields.Float()
    balance_required_qty = fields.Float(compute='_compute_balance_required_qty')
    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        default=lambda self: self.env.company)
    production_qty = fields.Float()
    stage_ids = fields.One2many('estimation.stage.line', 'estimation_id')
    component_ids = fields.One2many('manufacturing.component', 'estimation_id')
    stock_status = fields.Selection([('full', 'Fully Available'), ('no', 'Not Available'), ('partial', 'Partially Available')], compute='_compute_stock_status', string="Stock Status(MRP)")
    production_plan_count = fields.Integer(compute='_compute_production_plan_count')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('delivery_date_sent', 'Sent Delivery Date'),
        ('production_created', 'Production Created'),
        ('expired', 'Expired'),
        ('cancel', 'Cancel')], default='draft')
    production_date_reserved = fields.Boolean()

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = seq.next_by_code('estimation.plan') or _('New')
        return super().create(vals_list)

    def _compute_production_plan_count(self):
        for rec in self:
            rec.production_plan_count = self.env['production.plan'].search_count([('mrp_stage_estimation_id', '=', rec.id)])


    def action_view_production_pan(self):
        records = self.env['production.plan'].search([('mrp_stage_estimation_id', '=', self.id)])

        if len(records) == 1:
            return {
                'name': ('Production Plan'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'production.plan',
                'res_id': records.id,  # Assuming records is a single record
            }
        else:
            return {
                'name': ('Production Plan'),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'res_model': 'production.plan',
                'domain': [('mrp_stage_estimation_id', '=', self.id)]
            }

    @api.depends('total_days', 'start_date')
    def _compute_delivery_end_date(self):
        if self.start_date:
            self.expected_end_date = self.start_date + timedelta(days=self.total_days)
        else:
            self.expected_end_date = fields.Date.today()

    @api.depends('stage_ids', 'stage_ids.days')
    def _compute_total_days_calculate(self):
        for rec in self:
            if rec.stage_ids:
                rec.total_days = sum(rec.stage_ids.mapped('days'))
            else:
                rec.total_days = 0


    @api.depends('product_id', 'fg_qty', 'in_process_qty', 'location_id', 'qty')
    def _compute_balance_required_qty(self):
        for rec in self:
            balance_required_qty = rec.qty - (rec.fg_qty + rec.in_process_qty)
            if balance_required_qty < 0:
                rec.balance_required_qty = 0
            else:
                rec.balance_required_qty = balance_required_qty


    @api.onchange('product_id', 'location_id', 'qty')
    def _onchange_of_product_qty(self):
        if self.product_id:
            warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
            self.location_id = warehouse_id.lot_stock_id.id
            self.action_update_stock_qty()
            in_process = self.env['production.plan'].search([('product_id', '=', self.product_id.id), ('state', '=', 'in_production')])
            if in_process:
                qty = sum(in_process.mapped('expected_production_qty'))
                self.in_process_qty = qty

    @api.depends('product_id', 'fg_qty', 'in_process_qty', 'location_id', 'qty')
    def _compute_stock_status(self):
        for rec in self:
            if rec.qty < rec.fg_qty:
                rec.stock_status = 'full'
            elif rec.in_process_qty + rec.fg_qty == 0:
                rec.stock_status = 'no'
            else:
                rec.stock_status = 'partial'

    def action_update_stock_qty(self):
        for rec in self:
            stock_ids = self.env['stock.quant'].search([('location_id', '=', rec.location_id.id), ('product_id', '=', rec.product_id.id)])
            rec.fg_qty = sum(stock_ids.mapped('quantity'))
            in_process = self.env['production.plan'].search(
                [('product_id', '=', self.product_id.id), ('state', '=', 'in_production')])
            if in_process:
                qty = sum(in_process.mapped('expected_production_qty'))
                self.in_process_qty = qty

    def action_show_in_process_stock(self):
        return {
            'res_model': 'stock.quant',
            'type': 'ir.actions.act_window',
            'name': _("Stock Quantity"),
            'view_mode': 'list,form',
            'context': {
                'default_group_by': 'location_id'
            }
        }

    @api.onchange('stage_id')
    def onchange_of_stage_id(self):
        if self.stage_id:
            self.mrp_stage_ids = False
            child_records = []
            if self.product_id == self.stage_id.product_id:
                for line in self.stage_id.stage_ids:
                    child_records.append((0, 0, {
                        'type': line.type,
                        'machine_id': line.machine_id,
                        'qty': line.qty,
                        'stage_duration': line.duration,
                        'based_ppm': line.based_ppm,
                        'estimation_stage_id': line.id,
                    }))
            self.mrp_stage_ids = child_records

    def update_stage_value(self):
        self.clear_all_stage_value()
        child_records = []
        self.mrp_stage_ids = False
        self.component_ids = False
        materials = []
        for rec in self.stage_ids:
            if not rec.shift_ids:
                raise UserError(_('Please fill the shift of stage line'))
            if rec.stage_id:
                for line in rec.stage_id.stage_ids:
                    machine_ids = [(6, 0, [line.machine_id.id])] if line.machine_id else False
                    child_records.append((0, 0, {
                        'type': line.type,
                        'machine_id': machine_ids,
                        'qty': line.qty,
                        'stage_duration': line.duration,
                        'based_ppm': line.based_ppm,
                        'estimation_stage_id': rec.id,
                        'stage': line.stage_id.name,
                    }))
                for component in rec.stage_id.component_ids:
                    materials.append((0, 0, {
                        'planned_qty': rec.production_qty,
                        'product_id': component.product_id.id,
                        'product_uom_id': component.product_uom_id.id,
                        'product_uom_category_id': component.product_uom_category_id.id,
                        'company_id': component.company_id.id,
                        'plan_qty': component.stage_id.qty,
                        'stage_require_qty': component.product_qty,
                        'product_qty': 0,
                        'stage': component.stage_id.name,
                        'estimation_stage_id': rec.id,
                    }))

        self.mrp_stage_ids = child_records
        self.component_ids = materials

    def clear_all_stage_value(self):
        for rec in self.mrp_stage_ids:
            rec.unlink()
        for component in self.component_ids:
            component.unlink()
    def action_estimate_duration(self):
        self.update_stage_value()
        if not self.stage_ids:
            raise UserError(_('PLease fill the stage'))
        else:
            for line in self.stage_ids:
                production_plan_check = self.env['production.plan'].search([('date_start', '<=', line.start_date), '|', ('expected_end_date', '>=', line.start_date),('end_date', '>=', line.start_date)])
                if production_plan_check:
                    raise UserError(_('Production plan already in process for the dates -%s' % line.start_date))
                estimate = self.env['estimation.stage.line'].search(
                    [('start_date', '<=', line.start_date), ('expected_end_date', '>=', line.start_date), ('production_date_reserved', '=', True)], limit=1)
                if estimate:
                    raise UserError(_('Already sale estimation Request Created %s' % (line.start_date)))

        if not self.mrp_stage_ids:
            raise UserError(_('Please update the stage values'))
        for line in self.mrp_stage_ids:

            if line.based_ppm:
                if line.estimation_stage_id.ppm <= 0:
                    raise UserError(_('Please fill the ppm value'))
            dif_qty = line.estimation_stage_id.production_qty / line.qty
            line.required_qty = line.qty * dif_qty
            line.required_time = line.stage_duration * dif_qty
            if line.based_ppm:
                line.required_time = line.required_time / line.estimation_stage_id.ppm
            # line.required_time = line.required_time / len(line.estimation_stage_id.shift_ids)
            line.required_days = line.required_time / sum(line.estimation_stage_id.shift_ids.mapped('total_duration'))
        for rec in self.stage_ids:
            stage = self.mrp_stage_ids.filtered(lambda x: x.estimation_stage_id.id == rec.id)
            total_duration = sum(stage.mapped('required_time')) / sum(
                rec.shift_ids.mapped('total_duration'))
            rounded_days = int(total_duration + 0.5)
            if 0 < total_duration < 1:
                rounded_days = 1
            rec.days = rounded_days
            if 0 < rec.days < 1:
                rec.days = 1.0
            if rec.start_date:
                rec.expected_end_date = rec.start_date + timedelta(days=rounded_days)

        for component in self.component_ids:
            check_stock = self.env['stock.quant'].search(
                [('location_id', '=', self.location_id.id), ('product_id', '=', component.product_id.id)])
            component.available_qty = sum(check_stock.mapped('quantity'))
            diff_qty = component.stage_require_qty / component.plan_qty
            component.product_qty = component.planned_qty * diff_qty
            component.state = 'draft'
            component.check_available = True
            if component.check_available:
                if component.state == 'draft' and component.check_available != False:
                    if component.available_qty >= component.product_qty:
                        component.stock_availability = 'ok'
                    else:
                        component.stock_availability = 'not_ok'
                        if component.product_id.variant_seller_ids:
                            component.delivery_lead_days = sum(component.product_id.variant_seller_ids.mapped('delay'))
                else:
                    component.stock_availability = 'not_checked'
        for rec in self.stage_ids:
            if self.component_ids:
                stage = self.component_ids.filtered(lambda x: x.estimation_stage_id.id == rec.id)
                available_qty = sum(stage.mapped('available_qty'))
                required_qty = sum(stage.mapped('product_qty'))
                if sum(stage.mapped('delivery_lead_days')) > 0:
                    rec.days += sum(stage.mapped('delivery_lead_days'))
                    if rec.start_date:
                        rec.expected_end_date = rec.start_date + timedelta(days=rec.days)
                if sum(stage.mapped('remaining_qty')) == 0:
                    rec.row_material_stock_status = 'full'
                if sum(stage.mapped('remaining_qty')) > 0:
                    rec.row_material_stock_status = 'partial'
                if available_qty == 0:
                    rec.row_material_stock_status = 'no'


# class BomOperationType(models.Model):
#     _name = 'bom.operation.type'
#     _description = 'Manufacturing Shift'
#
#     name = fields.Char()
#     sequence = fields.Integer(index=True, default=1)