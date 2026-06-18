from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta, datetime


class PouchForming(models.Model):
    _name = 'pouch.forming'
    _description = 'Pouch Forming Winding Tension'
    _order = "id desc"

    winding_tension_a = fields.Float()
    winding_tension_b = fields.Float()
    winding_tension_c = fields.Float()
    winding_tension_d = fields.Float()
    winding_tension_e = fields.Float()
    winding_tension_f = fields.Float()
    winding_tension_g = fields.Float()
    assembly_id = fields.Many2one('assembly.cell')


class AssemblySealing(models.Model):
    _name = 'assembly.sealing'
    _description = 'Assembly Sealing'
    _order = "id desc"

    side_seal_temp = fields.Float()
    top_seal_temperature = fields.Float()
    patch_speed = fields.Float()
    top_seal_pressure = fields.Float()
    top_side_seal_time = fields.Float()
    assembly_id = fields.Many2one('assembly.cell')


class MachineData(models.Model):
    _inherit = 'machine.parameter'

    assembly_id = fields.Many2one('assembly.cell')


class Utilities(models.Model):
    _inherit = 'utility.parameter'

    assembly_id = fields.Many2one('assembly.cell')
    assembly_utility_condition = fields.Selection([
        ('good', 'Good'),
        ('fail', 'Fail')
    ], compute='_compute_assembly_utility')

    def _compute_assembly_utility(self):
        for rec in self:
            rec.assembly_utility_condition = 'fail'
            if rec.assembly_id:
                if rec.assembly_id.operation_id.min_humidity <= rec.humidity <= rec.assembly_id.operation_id.max_humidity and rec.assembly_id.operation_id.min_temperature <= rec.temperature <= rec.assembly_id.operation_id.max_temperature:
                    rec.assembly_utility_condition = 'good'
                else:
                    rec.assembly_utility_condition = 'fail'


class QualityDetails(models.Model):
    _inherit = 'quality.parameter'

    assembly_id = fields.Many2one('assembly.cell')


class StockProductionLOt(models.Model):
    _inherit = 'stock.lot'

    assembly_id = fields.Many2one('assembly.cell')




class StockProductionLOt(models.Model):
    _inherit = 'stock.lot'

    assembly_id = fields.Many2one('assembly.cell')


class StockMove(models.Model):
    _inherit = 'stock.move'
    assembly_id = fields.Many2one('assembly.cell')


class ProductSerialNumber(models.Model):
    _inherit = 'product.serial.number'
    assembly_id = fields.Many2one('assembly.cell')


class StockMoveLIne(models.Model):
    _inherit = 'stock.move.line'
    assembly_id = fields.Many2one('assembly.cell')
    out_assembly_id = fields.Many2one('assembly.cell')


class ManufacturingComponents(models.Model):
    _inherit = 'manufacturing.component'

    assembly_id = fields.Many2one('assembly.cell')

    @api.onchange('product_id')
    def _onchange_assembly_product_id(self):
        if self.assembly_id:
            self.location_src_id = self.assembly_id.location_src_id.id
            self.location_dest_id = self.assembly_id.location_dest_id.id


class AssemblyCell(models.Model):
    _name = 'assembly.cell'
    _description = 'Assembly Cell'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id desc"

    @api.model
    def default_get(self, fields):
        defaults = super(AssemblyCell, self).default_get(fields)
        production_location = self.env['stock.location'].search([('usage', '=', 'production')], limit=1)
        defaults['production_location_id'] = production_location.id
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
    ], default='assembly')
    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        default=lambda self: self.env.company)
    location_src_id = fields.Many2one('stock.location')
    location_dest_id = fields.Many2one('stock.location')
    production_location_id = fields.Many2one('stock.location')
    lot_ids = fields.One2many('product.serial.number', 'assembly_id', string='Serial Number')

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
        'manufacturing.component', 'assembly_id', 'Components',
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
    cell_drying_id = fields.Many2one('cell.drying')
    production_plan_id = fields.Many2one('production.plan')
    product_model_id = fields.Many2one('product.model')

    machine_data_ids = fields.One2many(
        'machine.parameter', 'assembly_id', 'Machine Data',
        copy=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    utility_ids = fields.One2many(
        'utility.parameter', 'assembly_id', 'Utility Parameter',
        copy=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    quality_ids = fields.One2many(
        'quality.parameter', 'assembly_id', 'Quality',
        copy=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    pouch_forming_ids = fields.One2many(
        'pouch.forming', 'assembly_id', 'Pouch Forming',
        copy=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    assembly_sealing_ids = fields.One2many(
        'assembly.sealing', 'assembly_id', 'Assembly Sealing',
        copy=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    machine_id = fields.Many2one('manufacturing.machine')
    start_time = fields.Datetime()
    end_time = fields.Datetime()
    hot_press_id = fields.Many2one('hot.press.jelly')
    breakdown_ids = fields.One2many('production.breakdown', 'assembly_id')
    hot_press_count = fields.Integer(compute='_compute_hot_press_count')
    cell_dry_count = fields.Integer(compute='_compute_cell_dry_count')
    finished_move_ids = fields.One2many('stock.move.line', 'out_assembly_id')
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

    def _compute_hot_press_count(self):
        for rec in self:
            rec.hot_press_count = self.env['hot.press.jelly'].search_count([('id', '=', rec.hot_press_id.id)])

    def _compute_cell_dry_count(self):
        for rec in self:
            rec.cell_dry_count = self.env['cell.drying'].search_count([('assembly_id', '=', rec.id)])

    def action_show_cell_drying_record(self):
        records = self.env['cell.drying'].search([('assembly_id', '=', self.id)])
        if len(records) == 1:
            return {
                'name': _('Cell Drying'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'cell.drying',
                'res_id': records.id,  # Assuming records is a single record
            }
        else:
            return {
                'name': _('Cell Drying'),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'res_model': 'cell.drying',
                'domain': [('assembly_id', '=', self.id)]
            }

    def action_create_cell_drying(self):
        cell_drying = self.env['cell.drying'].create({
            'assembly_id': self.id,
            'production_plan_id': self.production_plan_id.id,
            'product_model_id': self.product_model_id.id
        })
        cell_drying._onchange_of_product_plan_id()
        return {
            'name': _('Cell Drying'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'cell.drying',
            'res_id': cell_drying.id
        }

    def show_hot_press_record(self):
        records = self.env['hot.press.jelly'].search([('id', '=', self.hot_press_id.id)])
        if len(records) == 1:
            # If there is only one record, return the form view directly
            return {
                'name': _('Hot Press'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'hot.press.jelly',
                'res_id': records.id,  # Assuming records is a single record
            }
        else:
            # If there are multiple records, return the list and form view
            return {
                'name': _('Hot  Press'),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'res_model': 'hot.press.jelly',
                'domain': [('id', '=', self.hot_press_id.id)],
            }

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

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self._origin:
            if self.product_id:
                self.bom_id = False
                self.component_ids = False

    @api.onchange('state')
    def _onchange_of_state(self):
        if self.state and self.component_ids:
            for line in self.component_ids:
                line.state = self.state

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
        else:
            self.component_ids = False

    @api.onchange('product_qty')
    def _onchange_product_qty(self):
        if self.product_qty:
            for line in self.component_ids:
                bom_line = self.bom_id.bom_line_ids.filtered(lambda x: x.product_id.id == line.product_id.id)
                if bom_line:
                    line.product_qty = (bom_line[0].product_qty / self.bom_id.product_qty) * self.product_qty

    def action_confirm(self):
        for rec in self.component_ids:
            lot = self.env['stock.lot'].search([('product_id', '=', rec.product_id.id), ('name', '=', rec.lot_number)])
            move_id = self.env['stock.move'].create({
                'inventory_name': self.name,
                'product_id': rec.product_id.id,
                'product_uom': rec.product_uom_id.id,
                'location_id': rec.location_src_id.id,
                'location_dest_id': rec.assembly_id.production_location_id.id,
                'company_id': rec.env.company.id,
                'assembly_id': rec.assembly_id.id,
                'origin': self.name,
            })
            self.env['stock.move.line'].create({
                'product_id': rec.product_id.id,
                'quantity': rec.product_qty,
                'product_uom_id': rec.product_uom_id.id,
                'location_id': rec.location_src_id.id,
                'location_dest_id': rec.assembly_id.production_location_id.id,
                'company_id': rec.company_id.id,
                'assembly_id': rec.assembly_id.id,
                'lot_id': lot.id or False,
                'move_id': move_id.id,
            })
            move_id._action_confirm()
            move_id._action_done()
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
            rec.start_time = fields.Datetime.now()

    def action_view_product_move(self):
        return {
            'res_model': 'stock.move.line',
            'type': 'ir.actions.act_window',
            'name': _("Stock Move"),
            'domain': [('assembly_id', '=', self.id)],
            'view_mode': 'list,form',
        }

    def action_close(self):
        search_out_tray = self.finished_move_ids.filtered(lambda x: not x.out_tray_id)
        if not self.finished_move_ids:
            raise UserError(_("There is no finished product available to close this operation."))
        if search_out_tray:
            raise UserError(_('Please fill the out tray number'))
        # limit = 1
        for move_line in self.finished_move_ids:
            # if limit == 1:
            #     limit += 1
            move_line.move_id._action_confirm()
            move_line.move_id._action_done()
            child_records = []
            if move_line.out_tray_id and move_line.lot_id:
                child_records.append((0, 0, {
                    'name': move_line.lot_id.name,
                    'lot_id': move_line.lot_id.id,
                    'product_id': move_line.product_id.id,
                }))
            move_line.out_tray_id.lot_ids = child_records
        self.state = 'close'

    def action_done_production(self):
        for rec in self:
            if not rec.lot_ids:
                raise UserError(_('Please fill the serial/lot number for the "%s"' % rec.product_id.name))
            if len(rec.lot_ids) != rec.product_qty:
                raise UserError(_('Quantity to produce and number of serial number must be same'))
            lot_ids = []
            for lot in rec.lot_ids:
                product_lot = self.env['stock.lot'].create({
                    'name': lot.name,
                    'ref': rec.name,
                    'assembly_id': rec.id,
                    'product_id': rec.product_id.id,
                    'final_location_id': rec.location_dest_id.id,
                    'company_id': rec.env.company.id,
                })
                update_stock = self.env['stock.quant'].sudo().create({
                    'product_id': rec.product_id.id,
                    'location_id': rec.location_dest_id.id,
                    'lot_id': product_lot.id,
                    'inventory_quantity': 1.0,
                })
                update_stock.action_apply_inventory()
                lot_ids.append(product_lot)
                lot.lot_id = product_lot.id

            produced_qty = 0
            for lot in lot_ids:
                stock_move = self.env['stock.move'].create({
                    'inventory_name': self.name,
                    'product_id': rec.product_id.id,
                    'product_uom': rec.product_id.uom_id.id,
                    'product_uom_qty': 1,
                    'location_id': rec.production_location_id.id,
                    'location_dest_id': rec.location_dest_id.id,
                    'company_id': rec.env.company.id,
                    'assembly_id': rec.id,
                    'origin': self.name,
                })
                stock_move._action_confirm()
                stock_move._action_assign()
                existing_move_lines = self.env['stock.move.line'].search([('move_id', '=', stock_move.id)])
                if not existing_move_lines:
                    self.env['stock.move.line'].create({
                        'move_id': stock_move.id,
                        'product_id': rec.product_id.id,
                        'product_uom_id': rec.product_id.uom_id.id,
                        'quantity': 1,
                        'location_id': rec.production_location_id.id,
                        'location_dest_id': rec.location_dest_id.id,
                        'company_id': rec.company_id.id,
                        'assembly_id': rec.id,
                        'out_assembly_id': rec.id,
                        'lot_id': lot.id,
                    })
                    existing_move_lines = self.env['stock.move.line'].search([('move_id', '=', stock_move.id)])
                existing_move_lines.write({
                    'assembly_id': rec.id,
                    'out_assembly_id': rec.id,
                    'lot_id': lot.id,
                })
                for move_line in existing_move_lines:
                    move_line.write({
                        'assembly_id': rec.id,
                        'out_assembly_id': rec.id,
                        'lot_id': lot.id,
                    })
                stock_move.move_line_ids.picked = True
                # stock_move._action_done()
                produced_qty += 1
            rec.qty_produced = produced_qty
            rec.state = 'done'
            rec.end_time = fields.Datetime.now()

    def open_cell_drying_processing(self):
        return {
            'name': _('Cell Drying'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'cell.drying',
            'domain': [('id', '=', self.cell_drying_id.id)]
        }

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



    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('manufacturing.assembly') or _('New')
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
                    'default_assembly_id': rec.id,
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
                    'default_assembly_id': rec.id,
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
                    'default_assembly_id': rec.id,
                    'default_type': 'RESTART',
                },
            }


class ManufacturingScrap(models.Model):
    _inherit = 'manufacturing.scrap'
    _description = "Manufacturing Scrp"

    assembly_id = fields.Many2one('assembly.cell')

    def create_scrap_product(self):
        res = super(ManufacturingScrap, self).create_scrap_product()
        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1)
        for rec in self:
            if rec.assembly_id:
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
                    'origin': rec.assembly_id.name,
                })
                stock_move = self.env['stock.move'].create({
                    'inventory_name': rec.assembly_id.name,
                    'product_id': rec.product_id.id,
                    'product_uom_qty': rec.scrap_qty,
                    'product_uom': rec.product_uom_id.id,
                    'location_id': rec.location_src_id.id,
                    'location_dest_id': rec.scrap_location_id.id,
                    'picking_id': picking.id,
                    'company_id': rec.env.company.id,
                    'assembly_id': rec.assembly_id.id,
                    # 'production_id': self.id,
                    'state': 'draft',  # Set the state to 'waiting' to be done.
                    'origin': rec.assembly_id.name,
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
                    'assembly_id': rec.assembly_id.id,
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
#Test script added for check automation

class ProductionBreakdown(models.Model):
    _inherit = 'production.breakdown'

    assembly_id = fields.Many2one('assembly.cell')

    def action_done_breakdown(self):
        for rec in self:
            if rec.assembly_id:
                if rec.type == 'HOLD':
                    rec.assembly_id.state = 'hold'
                else:
                    rec.assembly_id.state = 'progress'

        return super(ProductionBreakdown, self).action_done_breakdown()