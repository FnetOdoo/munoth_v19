from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta, datetime


class MachineData(models.Model):
    _inherit = 'machine.parameter'

    diaphragm_drying_id = fields.Many2one('diaphragm.drying')
    diaphragm_dry_condition = fields.Selection([
        ('good', 'Good'),
        ('fail', 'Fail')
    ], compute='_compute_diaphragm_dry_condition')

    def _compute_diaphragm_dry_condition(self):
        for rec in self:
            rec.diaphragm_dry_condition = 'fail'
            if rec.diaphragm_drying_id:
                if rec.diaphragm_drying_id.operation_id.dry_min_temperature <= rec.temperature <= rec.diaphragm_drying_id.operation_id.dry_max_temperature and abs(
                        rec.diaphragm_drying_id.operation_id.dry_min_vacuum) <= abs(rec.vacuum) <= abs(
                        rec.diaphragm_drying_id.operation_id.dry_max_vacuum):
                    rec.diaphragm_dry_condition = 'good'
                else:
                    rec.diaphragm_dry_condition = 'fail'


class Utilities(models.Model):
    _inherit = 'utility.parameter'

    diaphragm_drying_id = fields.Many2one('diaphragm.drying')
    diaphragm_utility_condition = fields.Selection([
        ('good', 'Good'),
        ('fail', 'Fail')
    ], compute='_compute_diaphragm_utility')

    def _compute_diaphragm_utility(self):
        for rec in self:
            rec.diaphragm_utility_condition = 'fail'
            if rec.diaphragm_drying_id:
                if rec.diaphragm_drying_id.operation_id.min_humidity <= rec.humidity <= rec.diaphragm_drying_id.operation_id.max_humidity and rec.diaphragm_drying_id.operation_id.min_temperature <= rec.temperature <= rec.diaphragm_drying_id.operation_id.max_temperature:
                    rec.diaphragm_utility_condition = 'good'
                else:
                    rec.diaphragm_utility_condition = 'fail'


class QualityDetails(models.Model):
    _inherit = 'quality.parameter'

    diaphragm_drying_id = fields.Many2one('diaphragm.drying')


class StockProductionLOt(models.Model):
    _inherit = 'stock.lot'

    diaphragm_drying_id = fields.Many2one('diaphragm.drying')


class StockMove(models.Model):
    _inherit = 'stock.move'
    diaphragm_drying_id = fields.Many2one('diaphragm.drying')


class ProductSerialNumber(models.Model):
    _inherit = 'product.serial.number'
    diaphragm_drying_id = fields.Many2one('diaphragm.drying')


class StockMoveLIne(models.Model):
    _inherit = 'stock.move.line'
    diaphragm_drying_id = fields.Many2one('diaphragm.drying')


class ManufacturingComponents(models.Model):
    _inherit = 'manufacturing.component'

    diaphragm_drying_id = fields.Many2one('diaphragm.drying')

    @api.onchange('product_id')
    def _onchange_diaphragm_product_id(self):
        if self.diaphragm_drying_id:
            self.location_src_id = self.diaphragm_drying_id.location_src_id.id
            self.location_dest_id = self.diaphragm_drying_id.location_dest_id.id



class DiaphragmDrying(models.Model):
    _name = 'diaphragm.drying'
    _description = 'Cell Drying'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id desc"

    @api.model
    def default_get(self, fields):
        defaults = super(DiaphragmDrying, self).default_get(fields)
        # operation = self.env['manufacturing.operation'].search([('type', '=', 'diaphragm_drying')], limit=1)
        # defaults['operation_id'] = operation.id
        # defaults['type'] = operation.type
        # defaults['location_src_id'] = operation.location_src_id.id
        # defaults['location_dest_id'] = operation.location_dest_id.id
        production_location = self.env['stock.location'].search([('usage', '=', 'production')], limit=1)
        defaults['production_location_id'] = production_location.id
        # defaults['product_id'] = operation.bom_id.product_tmpl_id.id
        # defaults['bom_id'] = operation.bom_id.id
        return defaults

    def _get_default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id').id

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
        ('cell_baking_formation', 'Cell Formation'),
        ('aged_formation_cell', 'Aged Formation Cell'),
        ('degas', 'Degas'),
        ('dsf', 'Double side Folding'),
        ('pad_printing', 'Pad Printing'),
        ('capacity_test', 'Capacity Test')
    ], default='diaphragm_drying')
    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        default=lambda self: self.env.company)
    location_src_id = fields.Many2one('stock.location')
    location_dest_id = fields.Many2one('stock.location')
    production_location_id = fields.Many2one('stock.location')
    lot_ids = fields.One2many('product.serial.number', 'diaphragm_drying_id', string='Serial Number')

    name = fields.Char(
        'Reference', copy=False, readonly=True, default=lambda x: _('New'))
    product_id = fields.Many2one(
        'product.product', 'Product',
        domain="""[
               ('type', 'in', ['combo', 'consu']),
               '|',
                   ('company_id', '=', False),
                   ('company_id', '=', company_id)
           ]
           """,
        check_company=True,
        )
    bom_id = fields.Many2one(
        'manufacturing.bom', 'Bill of Material')
    component_ids = fields.One2many(
        'manufacturing.component', 'diaphragm_drying_id', 'Components',
        copy=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('progress', 'In Progress'),
        ('hold', 'Hold'),
        ('done', 'Done'),
        ('close', 'Closed'),
        ('cancel', 'Cancelled')], string='State',
        copy=False, index=True, default='draft',
        store=True, tracking=True,
        help=" * Draft: The MO is not confirmed yet.\n"
             " * Confirmed: The MO is confirmed, the stock rules and the reordering of the components are trigerred.\n"
             " * In Progress: The production has started (on the MO or on the WO).\n"
             " * To Close: The production is done, the MO has to be closed.\n"
             " * Done: The MO is closed, the stock moves are posted. \n"
             " * Cancelled: The MO has been cancelled, can't be confirmed anymore.")
    product_tracking = fields.Selection(related='product_id.tracking')
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', related='product_id.product_tmpl_id')
    product_qty = fields.Float(
        'Quantity To Produce',
        default=1.0, digits='Product Unit of Measure',
         required=True, tracking=True,)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure', default=_get_default_product_uom_id,
        required=True,
        domain="[('relative_uom_id', '=', product_uom_category_id)]")

    qty_producing = fields.Float(string="Quantity Producing", digits='Product Unit of Measure', copy=False)
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.relative_uom_id')
    product_uom_qty = fields.Float(string='Total Quantity', store=True)
    user_id = fields.Many2one(
        'res.users', 'Responsible', default=lambda self: self.env.user,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    qty_produced = fields.Float(string="Quantity Produced")
    operation_id = fields.Many2one('manufacturing.operation')
    product_tray_id = fields.Many2one('product.tray')
    production_plan_id = fields.Many2one('production.plan')
    product_model_id = fields.Many2one('product.model')
    machine_data_ids = fields.One2many(
        'machine.parameter', 'diaphragm_drying_id', 'Machine Data',
        copy=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    utility_ids = fields.One2many(
        'utility.parameter', 'diaphragm_drying_id', 'Utility Parameter',
        copy=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    quality_ids = fields.One2many(
        'quality.parameter', 'diaphragm_drying_id', 'Quality',
        copy=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    machine_id = fields.Many2one('manufacturing.machine')
    start_time = fields.Datetime()
    end_time = fields.Datetime()
    breakdown_ids = fields.One2many('production.breakdown', 'diaphragm_drying_id')
    expected_end_time = fields.Datetime("Expected End", compute='compute_end_date')

    @api.depends('start_time', 'operation_id')
    def compute_end_date(self):
        for rec in self:
            if rec.start_time and rec.operation_id:
                rec.expected_end_time = rec.start_time + timedelta(hours=rec.operation_id.process_duration)
            else:
                rec.expected_end_time = False

    @api.constrains('end_time', 'expected_end_time')
    def duration_constrain(self):
        for rec in self:
            if rec.end_time < rec.expected_end_time:
                time = timedelta(hours=rec.operation_id.process_duration)
                dt = datetime(2000, 1, 1) + time
                raise UserError("Minimum duration to stop process is %s hours." % dt.strftime("%H:%M"))

    @api.onchange('state')
    def _onchange_of_state(self):
        if self.state and self.component_ids:
            for line in self.component_ids:
                line.state = self.state

    # @api.onchange('product_model_id')
    # def _onchange_of_product_model_id(self):
    #     if self.product_model_id:
    #         operation = self.env['manufacturing.operation'].search(
    #             [('type', '=', 'diaphragm_drying'), ('product_model_id', '=', self.product_model_id.id)], limit=1)
    #         if operation:
    #             self.bom_id = operation.bom_id.id
    #             self.operation_id = operation.id

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self._origin:
            if self.product_id:
                self.bom_id = False
                self.component_ids = False

    @api.onchange('production_plan_id')
    def _onchange_of_product_plan_id(self):
        if self.production_plan_id:
            production_operation = self.env['production.operation'].search(
                [('operation_type', '=', self.type), ('production_plan_id', '=', self.production_plan_id.id)], limit=1)
            self.operation_id = production_operation.operation_id.id
            self.product_model_id = self.production_plan_id.model_id.id
            self.bom_id = self.operation_id.bom_id.id
            if not self.bom_id:
                self.component_ids = False
            self._onchange_of_operation()

    @api.onchange('type')
    def _onchange_of_operation_type(self):
        if self.type:
            machine = self.env['manufacturing.machine'].search([('type', '=', self.type)], limit=1)
            if machine:
                self.machine_id = machine.id

    @api.onchange('operation_id')
    def _onchange_of_operation(self):
        if self.operation_id:
            production_location = self.env['stock.location'].search([('usage', '=', 'production')], limit=1)
            self.product_id = self.operation_id.product_id.id
            self.location_src_id = self.operation_id.location_src_id.id
            self.location_dest_id = self.operation_id.location_dest_id.id
            self.production_location_id = production_location.id
            self.bom_id = self.operation_id.bom_id.id
        else:
            self.bom_id = False
            self.component_ids =False
        if self.component_ids:
            for line in self.component_ids:
                line.location_src_id = self.location_src_id.id
                line.location_dest_id = self.production_location_id.id
        self.bom_id = self.operation_id.bom_id.id
        self._onchange_bom_id()
        self._onchange_of_operation_type()

    @api.onchange('bom_id')
    def _onchange_bom_id(self):
        if self.bom_id:
            self.component_ids = False
            child_records = []
            lines = self.env['manufacturing.bom.line'].search([('bom_id', '=', self.bom_id.id)])
            for line in lines:
                child_records.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'product_uom_id': line.product_uom_id.id,
                    'location_src_id': self.location_src_id.id,
                    'location_dest_id': self.location_dest_id.id,
                    'product_qty': line.product_qty
                }))
            self.component_ids = child_records
            self.product_qty = self.bom_id.product_qty
            self.product_uom_id = self.bom_id.product_uom_id.id
        else:
            self.component_ids = False

    @api.onchange('product_tray_id')
    def _onchnage_product_tray_id(self):
        if self.product_tray_id:
            child_records = []
            lines = self.env['product.serial.number'].search([('tray_id', '=', self.product_tray_id.id)])
            for line in lines:
                child_records.append((0, 0, {
                    'name': line.name,
                }))
            self.lot_ids = child_records

    @api.onchange('product_qty')
    def _onchange_product_qty(self):
        if self.product_qty:
            for line in self.component_ids:
                bom_line = self.bom_id.bom_line_ids.filtered(lambda x: x.product_id.id == line.product_id.id)
                if bom_line:
                    line.product_qty = (bom_line[0].product_qty / self.bom_id.product_qty) * self.product_qty

    def action_confirm(self):
        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1)
        for line in self.component_ids:
            lot = self.env['stock.lot'].search(
                [('product_id', '=', line.product_id.id), ('name', '=', line.lot_number)])
            available_quant = self.env['stock.quant'].sudo().search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', line.location_src_id.id),
                ('lot_id', '=', lot.id)
            ], limit=1)

            if not available_quant or sum(available_quant.mapped('quantity')) < line.product_qty:
                raise UserError(f"Insufficient stock for product: {line.product_id.name} "
                                f"at location: {line.location_src_id.complete_name}.\n"
                                f"Available Quantity: {sum(available_quant.mapped('quantity')) if sum(available_quant.mapped('quantity')) else 0}\n"
                                f"Required Quantity: {line.product_qty}")

        for rec in self.component_ids:
            lot = self.env['stock.lot'].search([('product_id', '=', rec.product_id.id), ('name', '=', rec.lot_number)])

            picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type_id.id,
                'location_id': rec.location_src_id.id,
                'location_dest_id': rec.diaphragm_drying_id.production_location_id.id,
                'company_id': rec.env.company.id,

                'move_type': 'direct',
                'origin': self.name,
            })
            stock_move = self.env['stock.move'].create({
                'inventory_name': self.name,
                'product_id': rec.product_id.id,
                # 'product_uom_qty': 1.0,
                'product_uom': rec.product_uom_id.id,
                'location_id': rec.location_src_id.id,
                'location_dest_id': rec.diaphragm_drying_id.production_location_id.id,
                'picking_id': picking.id,
                'company_id': rec.env.company.id,
                'diaphragm_drying_id': rec.diaphragm_drying_id.id,
                # 'production_id': self.id,
                'state': 'done',  # Set the state to 'waiting' to be done.
                'origin': self.name,
            })

            stock_move_line = self.env['stock.move.line'].create({
                'product_id': rec.product_id.id,
                # 'product_uom_qty': 1.0,
                'quantity': rec.product_qty,
                'product_uom_id': rec.product_uom_id.id,
                'location_id': rec.location_src_id.id,
                'location_dest_id': rec.diaphragm_drying_id.production_location_id.id,
                'company_id': rec.company_id.id,
                'diaphragm_drying_id': rec.diaphragm_drying_id.id,
                'lot_id': lot.id or False,
                'picking_id': picking.id,
                'move_id': stock_move.id,
                # 'production_id': self.id,
                'state': 'done',
            })
        self.state = 'confirmed'


    def _check_availability(self):
        for rec in self:
            if not self.component_ids:
                raise UserError(_("Please add at least one material to confirm the production."))
            if self.component_ids.filtered(lambda x: x.product_qty <= 0):
                raise UserError(_("Required quantity must be greater than zero for the materials."))
            for line in rec.component_ids:
                domain = [('product_id', '=', line.product_id.id), ('location_id', '=', line.location_src_id.id)]
                if line.lot_id:
                    domain.append(('lot_id', '=', line.lot_id.id))
                stock_quant = self.env['stock.quant'].search(domain)
                available_quantity = sum(stock_quant.mapped('quantity'))
                line.available_qty = available_quantity
                if line.product_qty > available_quantity:
                    raise UserError(
                        _("Required quantity is not available in the stock. Please check on %s" % self.location_src_id.name))
                line.check_available = True

    def check_available_stock(self):
        self._check_availability()

    def action_start(self):
        for rec in self:
            rec.state = 'progress'
            self.start_time = fields.Datetime.now()

    def action_view_product_move(self):
        return {
            'res_model': 'stock.move.line',
            'type': 'ir.actions.act_window',
            'name': _("Stock Move"),
            'domain': [('diaphragm_drying_id', '=', self.id)],
            'view_mode': 'list,form',
        }

    def action_close(self):

        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1)
        for rec in self:
            if rec.qty_produced < 1:
                rec.qty_produced = rec.product_qty
            picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type_id.id,
                'location_id': rec.location_src_id.id,
                'location_dest_id': rec.location_dest_id.id,
                'company_id': rec.env.company.id,

                'move_type': 'direct',
                'origin': self.name,
            })
            stock_move = self.env['stock.move'].create({
                'inventory_name': self.name,
                'product_id': rec.product_id.id,
                # 'product_uom_qty': 1.0,
                'product_uom': rec.product_id.uom_id.id,
                'location_id': rec.production_location_id.id,
                'location_dest_id': rec.location_dest_id.id,
                'picking_id': picking.id,
                'company_id': rec.env.company.id,
                'diaphragm_drying_id': rec.id,
                # 'production_id': self.id,
                'state': 'done',  # Set the state to 'waiting' to be done.
                'origin': self.name,
            })

            stock_move_line = self.env['stock.move.line'].create({
                'product_id': rec.product_id.id,
                # 'product_uom_qty': 1.0,
                'quantity': rec.qty_produced,
                'product_uom_id': rec.product_id.uom_id.id,
                'location_id': rec.production_location_id.id,
                'location_dest_id': rec.location_dest_id.id,
                'company_id': rec.company_id.id,
                'diaphragm_drying_id': rec.id,
                # 'lot_id': rec.serial_number.id,
                'picking_id': picking.id,
                'move_id': stock_move.id,
                # 'production_id': self.id,
                'state': 'done',
            })
            rec.state = 'done'
        self.end_time = fields.Datetime.now()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'manufacturing.diaphragm.drying'
                ) or _('New')
        return super().create(vals_list)

    def create_scrap_product(self):
        for rec in self:
            scrap_location_id = self.env['stock.location'].search([('usage', '=', 'inventory')], limit=1)
            return {
                'name': _('Scrap Production?'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'manufacturing.scrap',
                'target': 'new',
                'context': {
                    'default_product_id': rec.product_id.id,
                    'default_location_src_id': rec.location_dest_id.id,
                    'default_scrap_location_id': scrap_location_id.id,
                    'default_diaphragm_drying_id': rec.id,
                },
            }


    def action_break_production(self):
        for rec in self:
            view = self.env.ref('fnet_mrp.production_breakdown_form_view2')
            return {
                'name': _('Production  Breakdown'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'res_model': 'production.breakdown',
                'target': 'new',
                'context': {
                    'default_diaphragm_drying_id': rec.id,
                    'default_type': 'HOLD',
                },
            }

    def action_restart_production(self):
        for rec in self:
            view = self.env.ref('fnet_mrp.production_breakdown_form_view2')
            return {
                'name': _('Production  Breakdown'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'views': [(view.id, 'form')],
                'view_id': view.id,
                'res_model': 'production.breakdown',
                'target': 'new',
                'context': {
                    'default_diaphragm_drying_id': rec.id,
                    'default_type': 'RESTART',
                },
            }

class ManufacturingScrap(models.Model):
    _inherit = 'manufacturing.scrap'
    _description = "Manufacturing Scrp"

    diaphragm_drying_id = fields.Many2one('diaphragm.drying')
    def create_scrap_product(self):
        res = super(ManufacturingScrap, self).create_scrap_product()
        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1)
        for rec in self:
            if rec.diaphragm_drying_id:
                available_quant = self.env['stock.quant'].sudo().search([
                    ('product_id', '=', rec.product_id.id),
                    ('location_id', '=', rec.location_src_id.id), ('lot_id', '=', rec.lot_id.id)
                ], limit=1)

                if not available_quant or sum(available_quant.mapped('quantity')) < rec.scrap_qty:
                    raise UserError(f"Insufficient stock for product: {rec.product_id.name} "
                                    f"at location: {rec.location_src_id.complete_name}.\n"
                                    f"Available Quantity: {sum(available_quant.mapped('quantity')) if sum(available_quant.mapped('quantity')) else 0}\n"
                                    f"Required Quantity: {rec.scrap_qty}")
                picking = self.env['stock.picking'].create({
                    'picking_type_id': picking_type_id.id,
                    'location_id': rec.location_src_id.id,
                    'location_dest_id': rec.scrap_location_id.id,
                    'company_id': rec.env.company.id,
                    'move_type': 'direct',
                    'origin': rec.diaphragm_drying_id.name,
                })
                stock_move = self.env['stock.move'].create({
                    'inventory_name': rec.diaphragm_drying_id.name,
                    'product_id': rec.product_id.id,
                    'product_uom_qty': rec.scrap_qty,
                    'product_uom': rec.product_uom_id.id,
                    'location_id': rec.location_src_id.id,
                    'location_dest_id': rec.scrap_location_id.id,
                    'picking_id': picking.id,
                    'company_id': rec.env.company.id,
                    'diaphragm_drying_id': rec.diaphragm_drying_id.id,
                    # 'production_id': self.id,
                    'state': 'draft',  # Set the state to 'waiting' to be done.
                    'origin': rec.diaphragm_drying_id.name,
                    'manufacturing_scrap_id': rec.id,
                })

                stock_move_line = self.env['stock.move.line'].create({
                    'product_id': rec.product_id.id,
                    # 'product_uom_qty': 1.0,
                    'quantity': rec.scrap_qty,
                    'product_uom_id': rec.product_uom_id.id,
                    'location_id': rec.location_src_id.id,
                    'location_dest_id': rec.scrap_location_id.id,
                    'company_id': rec.company_id.id,
                    'diaphragm_drying_id': rec.diaphragm_drying_id.id,
                    'lot_id': rec.lot_id.id,
                    'picking_id': picking.id,
                    'move_id': stock_move.id,
                    'manufacturing_scrap_id': rec.id,
                    # 'production_id': self.id,
                    'state': 'draft',
                })
                picking.action_confirm()
                picking.button_validate()
            rec.state = 'done'
        return res


class ProductionBreakdown(models.Model):
    _inherit = 'production.breakdown'

    diaphragm_drying_id = fields.Many2one('diaphragm.drying')

    def action_done_breakdown(self):
        for rec in self:
            if rec.diaphragm_drying_id:
                if rec.type == 'HOLD':
                    rec.diaphragm_drying_id.state = 'hold'
                else:
                    rec.diaphragm_drying_id.state = 'progress'

        return super(ProductionBreakdown, self).action_done_breakdown()