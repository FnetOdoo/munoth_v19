from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta, datetime
import base64
# from xlrd import open_workbook
import io
from openpyxl import load_workbook
import logging

_logger = logging.getLogger(__name__)


class ProductionStages(models.Model):
    _name = 'manufacturing.stages'
    _description = 'Production Stages'

    name = fields.Char(string='Name', required=True)

class ProductionProcessType(models.Model):
    _name = 'manufacturing.process.type'
    _description = 'Production Process'

    name                     = fields.Char(required=True)
    is_power_bank            = fields.Boolean()
    show_degas               = fields.Boolean("Degas")
    show_packing             = fields.Boolean("Packing")
    show_injection           = fields.Boolean("Injection")
    show_cell_drying         = fields.Boolean("Cell Drying")
    show_high_temperature    = fields.Boolean("High Temperature")
    show_cell_clamp_baking   = fields.Boolean("Cell Clamp Baking")
    show_capacity_test       = fields.Boolean("Capacity Test")
    show_voltage_test        = fields.Boolean("Voltage Test")
    show_drying_process      = fields.Boolean("Drying Process")
    show_slitting_process    = fields.Boolean("Slitting Process")
    show_pad_printing        = fields.Boolean("Pad Printing")
    show_aged_formation_1    = fields.Boolean("Aged Formation Cell 1")
    show_aged_formation_2    = fields.Boolean("Aged Formation Cell 2")
    is_anode_slitting_process = fields.Boolean("Anode Slitting Process")
    is_cathode_slitting_process = fields.Boolean("Anode Slitting Process")

    @api.constrains('is_power_bank')
    def _check_power_bank(self):
        for rec in self:
            if rec.is_power_bank:
                existing_record = self.search([
                    ('is_power_bank', '=', True),
                    ('id', '!=', rec.id)
                ], limit=1)

                if existing_record:
                    raise UserError("Only one record can be marked as Power Bank.")

#

class MachineData(models.Model):
    _inherit = 'machine.parameter'

    manufacturing_process_id = fields.Many2one('manufacturing.process')
    qr_code_printing_condition = fields.Selection([
        ('good', 'Good'),
        ('fail', 'Fail')
    ], compute='_compute_qr_code_printing_condition')

    def _compute_qr_code_printing_condition(self):
        for rec in self:
            rec.qr_code_printing_condition = 'fail'
            if rec.manufacturing_process_id:
                if rec.manufacturing_process_id.operation_id.dry_min_temperature <= rec.temperature <= rec.manufacturing_process_id.operation_id.dry_max_temperature and abs(
                        rec.manufacturing_process_id.operation_id.dry_min_vacuum) <= abs(rec.vacuum) <= abs(
                        rec.manufacturing_process_id.operation_id.dry_max_vacuum):
                    rec.qr_code_printing_condition = 'good'
                else:
                    rec.qr_code_printing_condition = 'fail'


class Utilities(models.Model):
    _inherit = 'utility.parameter'

    manufacturing_process_id = fields.Many2one('manufacturing.process')
    qr_code_printing_utility_condition = fields.Selection([
        ('good', 'Good'),
        ('fail', 'Fail')
    ], compute='_compute_qr_code_printing_utility')

    def _compute_qr_code_printing_utility(self):
        for rec in self:
            # rec.cell_drying_utility_condition = 'fail'
            if rec.manufacturing_process_id:
                if rec.manufacturing_process_id.operation_id.min_humidity <= rec.humidity <= rec.manufacturing_process_id.operation_id.max_humidity and rec.manufacturing_process_id.operation_id.min_temperature <= rec.temperature <= rec.manufacturing_process_id.operation_id.max_temperature:
                    rec.qr_code_printing_utility_condition = 'good'
                else:
                    rec.qr_code_printing_utility_condition = 'fail'


class QualityDetails(models.Model):
    _inherit = 'quality.parameter'

    manufacturing_process_id = fields.Many2one('manufacturing.process')


class StockProductionLOt(models.Model):
    _inherit = 'stock.lot'

    manufacturing_process_id = fields.Many2one('manufacturing.process')


class StockMove(models.Model):
    _inherit = 'stock.move'

    manufacturing_process_id = fields.Many2one('manufacturing.process')


class ProductSerialNumber(models.Model):
    _inherit = 'product.serial.number'

    manufacturing_process_id = fields.Many2one('manufacturing.process')
    batch_id = fields.Many2one('manufacturing.batch', string='Batch',related='manufacturing_process_id.batch_id')
    cell_weight = fields.Float(string='Cell Weight (g)', digits=(16, 4))  # ✅ was Char

class StockMoveLIne(models.Model):
    _inherit = 'stock.move.line'

    manufacturing_process_id = fields.Many2one('manufacturing.process')
    out_manufacturing_process_id = fields.Many2one('manufacturing.process')
    out_tray_id = fields.Many2one('product.tray')


class ManufacturingComponents(models.Model):
    _inherit = 'manufacturing.component'

    manufacturing_process_id = fields.Many2one('manufacturing.process')

    @api.onchange('product_id')
    def _onchange_product_manufacturing_process_id(self):
        if self.manufacturing_process_id:
            self.location_src_id = self.manufacturing_process_id.location_src_id.id
            self.location_dest_id = self.manufacturing_process_id.location_dest_id.id


class MaterialLine(models.Model):
    _inherit = 'material.line'

    manufacturing_process_id = fields.Many2one('manufacturing.process')
#
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # If manufacturing_process_id is set but production_plan_id is not, auto-fill it
            if vals.get('manufacturing_process_id') and not vals.get('production_plan_id'):
                process = self.env['manufacturing.process'].browse(vals['manufacturing_process_id'])
                if process.production_plan_id:
                    vals['production_plan_id'] = process.production_plan_id.id
        return super().create(vals_list)

class ProductionProcess(models.Model):
    _name = 'manufacturing.process'
    _description = 'Production Process Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id desc"

    @api.model
    def default_get(self, fields):
        defaults = super(ProductionProcess, self).default_get(fields)
        production_location = self.env['stock.location'].search([('usage', '=', 'production')], limit=1)
        defaults['production_location_id'] = production_location.id
        return defaults

    def _get_default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id').id
    company_id = fields.Many2one( 'res.company', 'Company', index=True, default=lambda self: self.env.company)
    location_src_id = fields.Many2one('stock.location')
    location_dest_id = fields.Many2one('stock.location')
    production_location_id = fields.Many2one('stock.location')
    lot_ids = fields.One2many('product.serial.number', 'manufacturing_process_id', string='Serial Number')

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
        check_company=True,)
    bom_id = fields.Many2one(
        'manufacturing.bom', 'Bill of Material')
    component_ids = fields.One2many('manufacturing.component', 'manufacturing_process_id', string='Components', copy=False)
    finished_lines = fields.One2many('mrp.finished.line', 'manufacturing_process_id', string="Finished Lines", copy=False)
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
             " * Close: The production is done, the MO has to be closed.\n"
             " * Done: The MO is closed, the stock moves are posted. \n"
             " * Cancelled: The MO has been cancelled, can't be confirmed anymore.")
    product_tracking = fields.Selection(related='product_id.tracking')
    product_tmpl_id = fields.Many2one('product.template', 'Product Template', related='product_id.product_tmpl_id')
    product_qty = fields.Float(
        'Quantity To Produce',
        default=1.0, digits='Product Unit of Measure',
        required=True, tracking=True,
       )
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure', default=_get_default_product_uom_id,
        readonly=True, required=True,
       domain="[('relative_uom_id', '=', product_uom_category_id)]")

    qty_producing = fields.Float(string="Quantity Producing", digits='Product Unit of Measure', copy=False)
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.relative_uom_id')
    product_uom_qty = fields.Float(string='Total Quantity', store=True)
    user_id = fields.Many2one(
        'res.users', 'Responsible', default=lambda self: self.env.user,
        states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    qty_produced = fields.Float(string="Quantity Produced")
    operation_id = fields.Many2one('manufacturing.operation')
    production_plan_id = fields.Many2one('production.plan')
    injection_id= fields.Many2one('cell.injection')
    cell_drying_id= fields.Many2one('cell.drying')

    product_model_id = fields.Many2one('product.model')

    machine_data_ids = fields.One2many(
        'machine.parameter', 'manufacturing_process_id', 'Machine Data',
        copy=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    utility_ids = fields.One2many(
        'utility.parameter', 'manufacturing_process_id', 'Utility Parameter',
        copy=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    quality_ids = fields.One2many(
        'quality.parameter', 'manufacturing_process_id', 'Quality',
        copy=False, states={'done': [('readonly', True)], 'cancel': [('readonly', True)]})
    machine_id = fields.Many2one('manufacturing.machine')
    start_time = fields.Datetime()
    end_time = fields.Datetime()
    # product_tray_id = fields.Many2one('product.tray')
    assembly_id = fields.Many2one('assembly.cell')
    breakdown_ids = fields.One2many('production.breakdown', 'manufacturing_process_id')
    # injection_count = fields.Integer(compute='_compute_injection_count')
    finished_move_ids = fields.One2many('stock.move.line', 'out_manufacturing_process_id')
    expected_end_time = fields.Datetime("Expected End", compute='compute_end_date')
    out_file_name = fields.Char("Serial File")
    out_file = fields.Binary("Serials")
    input_material_lines = fields.One2many('material.line', 'manufacturing_process_id')
    remaining_hours = fields.Float("Remaining Time", compute='_get_remaining_time')
    process_status_check = fields.Boolean(compute='_compute_process_status_check')

    manufacturing_process_id = fields.Many2one('manufacturing.process')
    manufacturing_process_type_id = fields.Many2one('manufacturing.process.type')

    before_manufacturing_process_id = fields.Many2one('manufacturing.process')
    before_manufacturing_process_type_id = fields.Many2one('manufacturing.process.type')
    before_manufacturing_process_type_name = fields.Char(related='before_manufacturing_process_type_id.name')

    next_manufacturing_process_id = fields.Many2one('manufacturing.process')
    next_manufacturing_process_type_id = fields.Many2one('manufacturing.process.type')

    is_first_process = fields.Boolean(copy=False)
    next_process_count = fields.Integer(compute='_compute_next_process_count')
    next_manufacturing_process_type_name = fields.Char(string="Next Process Type",compute='_compute_next_process_type_name', store=True )
    next_manufacturing_process_type_name_2 = fields.Char(string="Next Process Type",compute='_compute_next_process_type_name', store=True )
    is_next_process_created = fields.Boolean(copy=False)
    done_lot = fields.Boolean('')
    remaining_qty = fields.Integer(compute='_compute_remaining_qty')
    batch_id = fields.Many2one('manufacturing.batch', related='production_plan_id.batch_id', string='Batch',store=True)

    def _compute_remaining_qty(self):
        for rec in self:
            if rec.lot_ids:
                rec.remaining_qty = len(rec.lot_ids)
            else:
                rec.remaining_qty = rec.product_qty

    # def action_view_lots(self):
    #     lot_ids = []
    #     production_plans = self.env['production.plan'].search([('state', '=', 'in_production')])
    #     lot_ids += self.env['stock.lot'].search([('production_plan_id', 'in', production_plans.ids),
    #                                              ('final_location_id', '=', self.locatio  n_src_id.id)]).mapped('id')
    #     return {
    #         'name': _('Available Lots'),
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'list,form',
    #         'res_model': 'stock.lot',
    #         'domain': [('id', 'in', lot_ids), ('location_id.usage', '!=', 'inventory')],
    #         'context': {'group_by': ['production_plan_id', 'final_location_id']},
    #     }

    def action_view_lots(self):
        self.ensure_one()

        return {
            'name': _('Available Lots'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'stock.lot',
            'domain': [
                ('production_plan_id', '=', self.production_plan_id.id),
            ],
            'context': {
                'group_by': ['production_plan_id']
            },
        }

    def lot_creation(self):
        if not self.lot_ids:
            raise UserError(_("Please upload the Lot/Serial Number in the Serial Number tab."))
        if self.product_id:
            print("Updating product tracking to serial")
            self.product_id.write({
                'tracking': 'serial',
            })

        for lot in self.lot_ids:
            if lot.lot_id:
                available_qty = self.env['stock.quant']._get_available_quantity(
                    self.product_id,
                    self.production_location_id,
                    lot_id=lot.lot_id
                )
                if available_qty == 0:
                    print("Lot Not Available")
                    _logger.error(_("Lot not available in %s" % self.production_location_id.name))

        if self.product_id.tracking != 'none':
            for serial in self.lot_ids:
                if not serial.lot_id:
                    if not self.operation_id.allow_lot_create:
                        print("Lot Creation Not Allowed")
                        _logger.error(
                            _("The lot %s is not available and The current operation is not allowed to create new lot number.\n Please enable lot creation or check the inventory." % serial.name))
                    lot_id = self.env['stock.lot'].sudo().create({
                        'name': serial.name,
                        'ref': serial.name,
                        'product_id': self.product_id.id,
                        'company_id': self.env.company.id,
                        'production_plan_id': self.production_plan_id.id,
                        'final_location_id': self.location_src_id.id
                    })
                    serial.write({'lot_id': lot_id.id})
                    update_stock = self.env['stock.quant'].sudo().create({
                        'product_id': self.product_id.id,
                        'location_id': self.location_src_id.id,  # ✅ source location
                        'lot_id': lot_id.id,
                        'inventory_quantity': 1.0,
                        'cell_weight': serial.cell_weight,  # ✅ from serial line
                    })

                    update_stock.action_apply_inventory()
                    self.env['stock.quant'].invalidate_model()
                    print("Inventory Applied Successfully")

                    # ✅ Also create quant in location_dest_id so finished move works
                    dest_quant_check = self.env['stock.quant'].sudo().search([
                        ('product_id', '=', self.product_id.id),
                        ('location_id', '=', self.location_dest_id.id),
                        ('lot_id', '=', lot_id.id),
                    ])
                    # No need to pre-create dest quant — Odoo creates it on _action_done
                    # But we DO need to ensure component lines use the right location

                else:
                    # ✅ lot already exists — update cell_weight and batch_id on existing quant
                    existing_quant = self.env['stock.quant'].sudo().search([
                        ('product_id', '=', self.product_id.id),
                        ('location_id', '=', self.location_src_id.id),
                        ('lot_id', '=', serial.lot_id.id),
                    ], limit=1)
                    if existing_quant:
                        existing_quant.write({
                            'cell_weight': serial.cell_weight,  # ✅ update cell_weight
                        })
                        print("Updated existing quant cell_weight:", serial.cell_weight)

        # ✅ Sync component line locations with the process source location
        for comp in self.component_ids:
            if comp.product_id.id == self.product_id.id:
                comp.write({'location_src_id': self.location_src_id.id})
        self.done_lot = True

    @api.depends('next_manufacturing_process_type_id')
    def _compute_next_process_type_name(self):
        for rec in self:
            if rec.next_manufacturing_process_type_id:
                rec.next_manufacturing_process_type_name = f"Create {rec.next_manufacturing_process_type_id.name}"
                rec.next_manufacturing_process_type_name_2 = f"Open {rec.next_manufacturing_process_type_id.name}"
            else:
                rec.next_manufacturing_process_type_name = ''
                rec.next_manufacturing_process_type_name_2 = ''

    def _compute_next_process_count(self):
        for rec in self:
            rec.next_process_count = self.env['manufacturing.process'].search_count([
                ('before_manufacturing_process_id', '=', rec.id),
            ])

    # @api.depends('pa_count')
    def _compute_process_status_check(self):
        for rec in self:
            process = self.env['first.article.inspection'].search(
                [('origin', '=', rec.name), ('state', '=', 'done'), ('inspection_type', '=', 'process')])
            if process:
                rec.process_status_check = True
            else:
                rec.process_status_check = False

    @api.onchange('location_src_id')
    def onchange_line(self):
        for rec in self.component_ids:
            rec.location_src_id = self.location_src_id

    def action_view_quality(self):
        return {
            'res_model': 'mrp.quality',
            'type': 'ir.actions.act_window',
            'name': _("Quality Check"),
            'domain': [('manufacturing_process_id', '=', self.id)],
            'view_mode': 'list,form',
        }

    def action_view_in_process_quality(self):
        in_process_records = self.env['process.quality.check'].search([('opt_id', '=', self.operation_id.id), ('origin', '=', self.name)])
        return {
            'res_model': 'process.quality.check',
            'type': 'ir.actions.act_window',
            'name': _("In Process Quality Check"),
            'domain': [('id', 'in', in_process_records.ids if in_process_records else [])],
            'view_mode': 'list,form',
        }

    def _get_remaining_time(self):
        for rec in self:
            hr_remain = 0
            if rec.start_time and rec.operation_id.process_duration:
                end = rec.start_time + timedelta(hours=rec.operation_id.process_duration)
                hr_remain = ((end - fields.Datetime.now()).seconds / 3600)
            rec.remaining_hours = hr_remain

    def action_remove_line(self):
        self.component_ids.unlink()

    def action_download_sample(self):
        return {
            "type": "ir.actions.act_url",
            "url": '/fnet_mrp/static/Sample_Serials.xlsx',
            "target": "new",
        }

    def action_upload_serial(self):
        if not self.out_file:
            raise UserError(_("Please upload the serial number updated file."))

        file_data = base64.b64decode(self.out_file)
        wb = load_workbook(filename=io.BytesIO(file_data))
        sheet = wb.active

        serial_data = []  # list of (serial_no, cell_weight)

        for row_idx, row in enumerate(sheet.iter_rows(min_row=2, values_only=True), start=2):
            row_values = list(row)
            if not row_values or not row_values[0]:
                continue

            serial_no = str(row_values[0])

            # ── read cell_weight from column B (index 1) ─────────────────────
            cell_weight = 0.0
            if len(row_values) > 1 and row_values[1] is not None:
                try:
                    cell_weight = float(row_values[1])
                except (ValueError, TypeError):
                    cell_weight = 0.0

            serial_data.append((serial_no, cell_weight))

        if len(serial_data) != self.product_qty:
            raise UserError(_(
                "The uploaded file contains %s serial numbers, but the required quantity is %s."
            ) % (len(serial_data), self.product_qty))

        for serial_no, cell_weight in serial_data:
            self.env['product.serial.number'].create({
                'product_id': self.product_id.id,
                'name': serial_no,
                'product_uom_id': self.product_uom_id.id,
                'cell_weight': cell_weight,  # ← from column B
                'batch_id': self.production_plan_id.batch_id.id if self.production_plan_id.batch_id else False,
                'manufacturing_process_id': self.id,
            })

    @api.depends('start_time', 'operation_id')
    def compute_end_date(self):
        for rec in self:
            if rec.start_time and rec.operation_id:
                rec.expected_end_time = rec.start_time + timedelta(hours=rec.operation_id.process_duration)
            else:
                rec.expected_end_time = False

    # @api.constrains('end_time', 'expected_end_time')
    def duration_constrain(self):
        for rec in self:
            if rec.end_time < rec.expected_end_time:
                time = timedelta(hours=rec.operation_id.process_duration)
                dt = datetime(2000, 1, 1) + time
                raise UserError("Minimum duration to stop process is %s hours." % dt.strftime("%H:%M"))

    def action_open_production_plan(self):
        self.ensure_one()

        return {
            'name': _('Production Plan'),
            'type': 'ir.actions.act_window',
            'res_model': 'production.plan',
            'view_mode': 'form',
            'res_id': self.production_plan_id.id,
            'target': 'current',
        }

    def action_open_before_cell_process(self):
        self.ensure_one()

        return {
            'name': self.before_manufacturing_process_type_name or _('Previous Process'),
            'type': 'ir.actions.act_window',
            'res_model': 'manufacturing.process',
            'view_mode': 'form',
            'res_id': self.before_manufacturing_process_id.id,
            'target': 'current',
        }


    def action_open_next_cell_process(self):
        return {
            'name': self.next_manufacturing_process_type_name_2,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'manufacturing.process',
            'res_id': self.next_manufacturing_process_id.id,  # Assuming records is a single record
        }

    def action_create_next_cell_process(self):
        get_quality = self.env['quality.check'].search([
            ('manufacturing_process_id', '=', self.id)
        ])

        for qc in get_quality:
            if qc.state != 'done':
                raise UserError(
                    _("Please complete all Quality Checks before proceeding. Complete them as Rework or Scrap.")
                )
        all_lines = self.production_plan_id.operation_ids.sorted('sequence')
        current_line = all_lines.filtered(
            lambda x: x.manufacturing_process_type_id == self.manufacturing_process_type_id
        )[:1]
        next_line = all_lines.filtered(
            lambda x: not x.is_process_completed
                      and x.sequence > current_line.sequence
        )[:1]
        # Step 1: create WITHOUT lot_ids
        next_process = self.env['manufacturing.process'].create({
            'before_manufacturing_process_id': self.id,
            'before_manufacturing_process_type_id': self.manufacturing_process_type_id.id,
            'manufacturing_process_type_id': next_line.manufacturing_process_type_id.id,
            'production_plan_id': self.production_plan_id.id,
            'product_model_id': self.product_model_id.id,
            'is_first_process': False,
            'done_lot': False,
        })
        self.write({'next_manufacturing_process_id': next_process.id})
        next_process._onchange_of_product_plan_id()
        next_process.write({
            'lot_ids': [(4, lot_id) for lot_id in self.lot_ids.ids],
        })
        next_process.lot_creation()
        return {
            'name': next_line.manufacturing_process_type_id.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'manufacturing.process',
            'res_id': next_process.id,
        }

    @api.onchange('state')
    def _onchange_of_state(self):
        if self.state and self.component_ids:
            for line in self.component_ids:
                line.state = self.state

    @api.onchange('production_plan_id')
    def _onchange_of_product_plan_id(self):
        if self.production_plan_id:
            if self.is_first_process:
                self.manufacturing_process_type_id = self.production_plan_id.first_process_type_id  # fix 1: removed .id
                production_operation = self.env['production.operation'].search(
                    [('manufacturing_process_type_id', '=', self.manufacturing_process_type_id.id),
                     ('production_plan_id', '=', self.production_plan_id.id)], limit=1)
                self.operation_id = production_operation.operation_id  # fix 3: removed .id
                self.product_model_id = self.production_plan_id.model_id  # fix 4: removed .id
                self.bom_id = production_operation.operation_id.bom_id  # fix 5: use production_operation directly, not self.operation_id
                self.product_qty = self.production_plan_id.expected_production_qty
                if not self.bom_id:
                    self.component_ids = False
            else:
                production_operation = self.env['production.operation'].search(
                    [
                        ('manufacturing_process_type_id', '=', self.manufacturing_process_type_id.id),
                        ('production_plan_id', '=', self.production_plan_id.id),
                        ('is_process_completed', '=', False),
                    ],
                    order='sequence asc',
                    limit=1
                )
                self.before_manufacturing_process_id.is_next_process_created = True
                self.manufacturing_process_type_id = production_operation.manufacturing_process_type_id  # fix 1: was self.next_manufacturing_process_id
                self.operation_id = production_operation.operation_id
                self.product_model_id = self.production_plan_id.model_id
                self.bom_id = production_operation.operation_id.bom_id  # fix 2: removed .id, use next_line directly
                self.product_qty = self.before_manufacturing_process_id.remaining_qty
            self._onchange_of_operation()

    @api.onchange('manufacturing_process_type_id')
    def _onchange_of_operation_type(self):
        if self.manufacturing_process_type_id:
            machine = self.env['manufacturing.machine'].search([('manufacturing_process_type_id', '=', self.manufacturing_process_type_id)], limit=1)
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
            self.product_id.write({
                'tracking': 'none',
            })
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

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self._origin:
            if self.product_id:
                self.bom_id = False  # ← remove the trailing comma
                self.component_ids = False

    @api.onchange('bom_id', 'product_qty')
    def _onchange_bom_id(self):
        self.input_material_lines = False
        self.component_ids = False

        if not self.bom_id:
            return

        child_records = []

        if self.is_first_process:
            for line in self.bom_id.bom_line_ids:
                child_records.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_category_id': line.product_uom_category_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'location_src_id': self.location_src_id.id,
                    'location_dest_id': self.location_dest_id.id,
                    'name': line.product_id.name,
                    'product_qty': (line.product_qty / self.bom_id.product_qty) * self.product_qty,
                    'production_plan_id': self.production_plan_id.id,
                    'manufacturing_process_id': self._origin.id or False,
                }))
        else:
            # Use remaining_qty from before process instead of product_qty ratio
            remaining_qty = self.before_manufacturing_process_id.remaining_qty
            for line in self.bom_id.bom_line_ids:
                child_records.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_category_id': line.product_uom_category_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'location_src_id': self.location_src_id.id,
                    'location_dest_id': self.location_dest_id.id,
                    'name': line.product_id.name,
                    'product_qty': remaining_qty,
                    'production_plan_id': self.production_plan_id.id,
                    'manufacturing_process_id': self._origin.id or False,
                }))

        self.input_material_lines = child_records

    @api.onchange('location_src_id')
    def onchange_location_src_id(self):
        for rec in self.input_material_lines:
            rec.location_src_id = self.location_src_id.id

    def get_serial_numbers(self):
        available_inputs = self.component_ids.filtered(lambda x: x.product_id.id == self.product_id.id and x.lot_id)
        child_records = []
        for line in available_inputs:
            child_records.append((0, 0, {
                'product_id': line.product_id.id,
                'product_uom_id': line.product_uom_id.id,
                'name': line.lot_id.name,
            }))
        self.lot_ids = child_records

    def clear_serial_numbers(self):
        self.lot_ids = False

    def check_available_stock(self):
        for line in self.component_ids:
            available_qty = line.product_id.get_available_quantity(line.location_src_id, line.lot_id)
            qty = line.product_uom_id._compute_quantity(line.product_qty, line.product_id.uom_id)
            line.available_qty = float(available_qty)
            if qty > available_qty:
                raise UserError(
                    _("Required quantity is not available in the stock for %s. Please check on %s" % (
                    line.product_id.name, self.location_src_id.name)))
            line.check_available = True
        for line in self.input_material_lines:
            if line.product_qty != line.qty_done:
                raise UserError(_("Required materials and reserved materials are not same."))
        # for line in self.component_ids:
        #     available_qty = line.product_id.get_available_quantity(line.location_src_id, line.lot_id)
        #     qty = line.product_uom_id._compute_quantity(line.product_qty, line.product_id.uom_id)
        #     line.available_qty = available_qty
        #     if qty > available_qty:
        #         raise UserError(
        #             _("Required quantity is not available in the stock for %s. Please check on %s" % (
        #             line.product_id.name, self.location_src_id.name)))
        #     line.check_available = True

    def action_start(self):
        for rec in self:
            if rec.is_first_process:
                existing_qty = sum(self.search(
                    [('production_plan_id', '=', rec.production_plan_id.id), ('id', '!=', rec.id), ]).mapped(
                    'product_qty'))
                total_qty = existing_qty + rec.product_qty
                if total_qty > rec.production_plan_id.expected_production_qty:
                    raise UserError(
                        _("Total Quantity (%s) cannot be greater than the Expected Production Quantity (%s).") % (
                            total_qty, rec.production_plan_id.expected_production_qty))
            else:
                before_process = rec.before_manufacturing_process_id
                if rec.product_qty > before_process.remaining_qty:  # ✅ rec not self
                    raise UserError(
                        _("Total Quantity (%s) cannot be greater than the remaining quantity of the previous process (%s).") % (
                            rec.product_qty,  # ✅ rec not self
                            before_process.remaining_qty,
                        )
                    )
            if rec.operation_id.allow_lot_create and not rec.lot_ids:
                raise UserError(
                    _("This is a lot-enabled product. Please upload the Lot/Serial Number in the Serial Number tab.")
                )

            for lot in rec.lot_ids:
                if not lot.lot_id and not lot.is_available:
                    raise UserError(
                        _("This product requires a Lot/Serial Number. Please create or select a Lot/Serial Number.")
                    )

            rec.check_available_stock()

            rec.write({
                'state': 'progress',
                'start_time': fields.Datetime.now(),
            })

    # def action_done_production(self):
    #     self.with_delay(eta=10)._action_done_production()

    def action_done_production(self):
        for rec in self:
            rec.check_available_stock()
            stock_moves = []
            for line in rec.component_ids:
                stock_move_vals = {
                    'inventory_name': rec.name,
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom_id.id,
                    'product_uom_qty': line.product_qty,
                    'location_id': line.location_src_id.id,
                    'location_dest_id': rec.production_location_id.id,
                    'manufacturing_process_id': rec.id,
                    'move_line_ids': [(0, 0, {
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_id.uom_id.id,
                        'quantity': line.product_qty,
                        'location_id': line.location_src_id.id,
                        'location_dest_id': rec.production_location_id.id,
                        'company_id': rec.company_id.id,
                        'lot_id': line.lot_id.id if line.lot_id else False,
                        'manufacturing_process_id': rec.id,
                    })],
                }
                stock_moves.append(stock_move_vals)
            created_stock_moves = self.env['stock.move'].create(stock_moves)
            created_stock_moves._action_confirm()
            created_stock_moves._action_assign()
            for move, line in zip(created_stock_moves, rec.component_ids):
                if move.move_line_ids:
                    move.move_line_ids.write({
                        'quantity': line.product_qty,
                        'lot_id': line.lot_id.id if line.lot_id else False,
                        'manufacturing_process_id': rec.id,
                    })
                else:
                    self.env['stock.move.line'].create({
                        'move_id': move.id,
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_uom_id.id,
                        'quantity': line.product_qty,
                        'location_id': line.location_src_id.id,
                        'location_dest_id': rec.production_location_id.id,
                        'company_id': rec.company_id.id,
                        'lot_id': line.lot_id.id if line.lot_id else False,
                        'manufacturing_process_id': rec.id,
                    })
                move.move_line_ids.picked = True
            created_stock_moves._action_done()

        for lot in self.lot_ids:
            if lot.lot_id:
                available_qty = self.env['stock.quant']._get_available_quantity(
                    self.product_id,
                    self.location_src_id,
                    lot_id=lot.lot_id
                )
                if available_qty == 0:
                    _logger.error(_("Lot not available in %s" % self.location_src_id.name))

        if self.product_id.tracking == 'none':
            stock_move = self.env['stock.move'].create({
                'inventory_name': self.name,
                'product_id': self.product_id.id,
                'product_uom': self.product_uom_id.id,
                'product_uom_qty': self.product_qty,
                'location_id': self.production_location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'manufacturing_process_id': self.id,
            })
            stock_move._action_confirm()
            stock_move._action_assign()
            existing_move_lines = self.env['stock.move.line'].search([
                ('move_id', '=', stock_move.id)
            ])
            if not existing_move_lines:
                self.env['stock.move.line'].create({
                    'move_id': stock_move.id,
                    'product_id': self.product_id.id,
                    'product_uom_id': self.product_uom_id.id,
                    'quantity': self.product_qty,
                    'location_id': self.production_location_id.id,
                    'location_dest_id': self.location_dest_id.id,
                    'company_id': self.company_id.id,
                    'manufacturing_process_id': self.id,
                    'out_manufacturing_process_id': self.id,
                })
                existing_move_lines = self.env['stock.move.line'].search([
                    ('move_id', '=', stock_move.id)
                ])
            existing_move_lines.write({
                'manufacturing_process_id': self.id,
                'out_manufacturing_process_id': self.id,
            })
            stock_move.move_line_ids.picked = True

            # ✅ Update dest quant with batch_id for tracking == 'none'
            dest_quant = self.env['stock.quant'].sudo().search([
                ('product_id', '=', self.product_id.id),
                ('location_id', '=', self.location_dest_id.id),
            ], limit=1)
            if dest_quant:
                dest_quant.write({
                    'batch_id': self.batch_id.id if self.batch_id else False,
                })
            else:
                self.env['stock.quant'].sudo().create({
                    'product_id': self.product_id.id,
                    'location_id': self.location_dest_id.id,
                    'inventory_quantity': self.product_qty,
                    'batch_id': self.batch_id.id if self.batch_id else False,
                })

        else:
            for serial in self.lot_ids:
                lot_id = serial.lot_id

                if not serial.lot_id:
                    if not self.operation_id.allow_lot_create:
                        _logger.error(_(
                            "The lot %s is not available and The current operation "
                            "is not allowed to create new lot number.\n "
                            "Please enable lot creation or check the inventory." % serial.name
                        ))
                    lot_id = self.env['stock.lot'].sudo().create({
                        'name': serial.name,
                        'ref': serial.name,
                        'product_id': self.product_id.id,
                        'company_id': self.env.company.id,
                        'production_plan_id': self.production_plan_id.id,
                    })
                    # ✅ Create quant with cell_weight + batch_id
                    update_stock = self.env['stock.quant'].sudo().create({
                        'product_id': self.product_id.id,
                        'location_id': self.production_location_id.id,
                        'lot_id': lot_id.id,
                        'inventory_quantity': 1.0,
                        'cell_weight': serial.cell_weight,
                        'batch_id': serial.batch_id.id if serial.batch_id else False,  # ✅ batch_id
                    })
                    update_stock.action_apply_inventory()
                    serial.write({'lot_id': lot_id.id})

                else:
                    # ✅ Lot exists — update existing quant cell_weight + batch_id
                    existing_quant = self.env['stock.quant'].sudo().search([
                        ('product_id', '=', self.product_id.id),
                        ('location_id', '=', self.production_location_id.id),
                        ('lot_id', '=', lot_id.id),
                    ], limit=1)
                    if existing_quant:
                        existing_quant.write({
                            'cell_weight': serial.cell_weight,
                            'batch_id': serial.batch_id.id if serial.batch_id else False,  # ✅ batch_id
                        })
                    else:
                        # ✅ No quant found — create one with batch_id
                        self.env['stock.quant'].sudo().create({
                            'product_id': self.product_id.id,
                            'location_id': self.production_location_id.id,
                            'lot_id': lot_id.id,
                            'inventory_quantity': 1.0,
                            'cell_weight': serial.cell_weight,
                            'batch_id': serial.batch_id.id if serial.batch_id else False,  # ✅ batch_id
                        })

                stock_move = self.env['stock.move'].sudo().create({
                    'inventory_name': self.name,
                    'product_id': self.product_id.id,
                    'product_uom': self.product_uom_id.id,
                    'product_uom_qty': 1,
                    'location_id': self.production_location_id.id,
                    'location_dest_id': self.location_dest_id.id,
                    'manufacturing_process_id': self.id,
                })
                stock_move._action_confirm()
                stock_move._action_assign()
                existing_move_lines = self.env['stock.move.line'].search([
                    ('move_id', '=', stock_move.id)
                ])
                if not existing_move_lines:
                    self.env['stock.move.line'].sudo().create({
                        'move_id': stock_move.id,
                        'product_id': self.product_id.id,
                        'product_uom_id': self.product_uom_id.id,
                        'quantity': 1,
                        'location_id': self.production_location_id.id,
                        'location_dest_id': self.location_dest_id.id,
                        'company_id': self.company_id.id,
                        'lot_id': lot_id.id,
                        'manufacturing_process_id': self.id,
                        'out_manufacturing_process_id': self.id,
                    })
                    existing_move_lines = self.env['stock.move.line'].search([
                        ('move_id', '=', stock_move.id)
                    ])
                existing_move_lines.write({
                    'manufacturing_process_id': self.id,
                    'out_manufacturing_process_id': self.id,
                    'lot_id': lot_id.id,
                })
                stock_move.move_line_ids.picked = True
                stock_move._action_done()  # ✅ Moved here so dest quant exists before search below

                # ✅ Update dest location quant cell_weight + batch_id after move done
                dest_quant = self.env['stock.quant'].sudo().search([
                    ('product_id', '=', self.product_id.id),
                    ('location_id', '=', self.location_dest_id.id),
                    ('lot_id', '=', lot_id.id),
                ], limit=1)
                if dest_quant:
                    dest_quant.write({
                        'cell_weight': serial.cell_weight,
                        'batch_id': serial.batch_id.id if serial.batch_id else False,  # ✅ batch_id
                    })
                else:
                    # ✅ Dest quant missing — create it with batch_id
                    self.env['stock.quant'].sudo().create({
                        'product_id': self.product_id.id,
                        'location_id': self.location_dest_id.id,
                        'lot_id': lot_id.id,
                        'inventory_quantity': 1.0,
                        'cell_weight': serial.cell_weight,
                        'batch_id': serial.batch_id.id if serial.batch_id else False,  # ✅ batch_id
                    })

        self.state = 'done'
        self.end_time = fields.Datetime.now()

    def action_close(self):
        for move_line in self.finished_move_ids:
            exist_serial = self.lot_ids.filtered(
                lambda x: x.name == move_line.lot_id.name
            )
            if exist_serial:
                exist_serial[0].write({'tray_id': move_line.out_tray_id.id})
            else:
                if move_line.out_tray_id and move_line.lot_id:
                    self.env['product.serial.number'].create({
                        'product_id': move_line.product_id.id,
                        'product_uom_id': move_line.product_uom_id.id,
                        'lot_id': move_line.lot_id.id,
                        'name': move_line.lot_id.name,
                        'tray_id': move_line.out_tray_id.id,
                    })

        stock_moves = self.finished_move_ids.mapped('move_id')
        stock_moves._action_done()

        for rec in self:
            all_lines = rec.production_plan_id.operation_ids.sorted('sequence')
            current_line = all_lines.filtered(
                lambda x: x.manufacturing_process_type_id == rec.manufacturing_process_type_id
            )[:1]
            if current_line:
                current_line.is_process_completed = True

            next_line = all_lines.filtered(
                lambda x: not x.is_process_completed
                          and x.sequence > current_line.sequence
            )[:1]

            if next_line:
                rec.next_manufacturing_process_type_id = next_line.manufacturing_process_type_id
                rec.next_manufacturing_process_id = rec.id
            else:
                rec.next_manufacturing_process_id = False
                rec.next_manufacturing_process_type_id = False

            for serial in rec.lot_ids:
                if serial.lot_id:
                    quants = self.env['stock.quant'].sudo().search([
                        ('product_id', '=', rec.product_id.id),
                        ('lot_id', '=', serial.lot_id.id),
                    ])
                    if quants:
                        quants.write({
                            'cell_weight': serial.cell_weight,
                            'batch_id': serial.batch_id.id if serial.batch_id else False,  # ✅ batch_id
                        })
                    else:
                        # ✅ No quants at all — create with batch_id
                        self.env['stock.quant'].sudo().create({
                            'product_id': rec.product_id.id,
                            'location_id': rec.location_dest_id.id,
                            'lot_id': serial.lot_id.id,
                            'inventory_quantity': 1.0,
                            'cell_weight': serial.cell_weight,
                            'batch_id': serial.batch_id.id if serial.batch_id else False,  # ✅ batch_id
                        })

        self.state = 'close'

    def action_view_product_move(self):
        # Get move lines directly linked to this process
        direct_lines = self.env['stock.move.line'].search([
            ('manufacturing_process_id', '=', self.id),
        ]).ids

        # Get move lines created from quality checks of this process
        quality_line_ids = self.env['stock.move.line'].search([
            ('quality_id.manufacturing_process_id', '=', self.id),
        ]).ids

        all_line_ids = list(set(direct_lines + quality_line_ids))

        return {
            'res_model': 'stock.move.line',
            'type': 'ir.actions.act_window',
            'name': _("Stock Move"),
            'domain': [('id', 'in', all_line_ids)],
            'view_mode': 'list,form',
        }

    @api.constrains('product_qty', 'production_plan_id')
    def _check_product_qty(self):
        for rec in self:
            if not rec.production_plan_id:
                continue

            if rec.is_first_process:
                existing_qty = sum(
                    self.search([
                        ('production_plan_id', '=', rec.production_plan_id.id),
                        ('is_first_process', '=', True),  # ✅ only compare with other first processes
                        ('id', '!=', rec.id),
                    ]).mapped('product_qty')
                )
                total_qty = existing_qty + rec.product_qty
                if total_qty > rec.production_plan_id.expected_production_qty:
                    raise UserError(
                        _("Total Quantity (%s) cannot be greater than the Expected Production Quantity (%s).") % (
                            total_qty,
                            rec.production_plan_id.expected_production_qty
                        )
                    )
            else:
                if not rec.before_manufacturing_process_id:
                    continue
                before_process = rec.before_manufacturing_process_id
                if rec.product_qty > before_process.remaining_qty:  # ✅ rec not self
                    raise UserError(
                        _("Total Quantity (%s) cannot be greater than the remaining quantity of the previous process (%s).") % (
                            rec.product_qty,  # ✅ rec not self
                            before_process.remaining_qty,
                        )
                    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('qr.code.printing') or _('New')
        records = super().create(vals_list)
        return records

    def create_scrap_product(self):
        for rec in self:
            location_reject_id = self.env['stock.location'].search([('usage', '=', 'inventory')], limit=1)
            if rec.operation_id.location_reject_id:
                location_reject_id = rec.operation_id.location_reject_id
            lot_ids = self.finished_move_ids.filtered(lambda x: x.lot_id).mapped('lot_id')
            return {
                'name': _('Scrap Production?'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'manufacturing.scrap',
                'target': 'new',
                'context': {
                    'default_mrp_lot_ids': lot_ids.ids,
                    'default_name': rec.name,
                    'default_location_reject_id': location_reject_id.id,
                    'default_production_plan_id': self.production_plan_id.id,
                    'default_operation_id': rec.operation_id.id,
                    'default_product_id': rec.product_id.id,
                    'default_product_uom_id': rec.product_uom_id.id,
                    'default_location_src_id': rec.location_dest_id.id,
                    'default_manufacturing_process_id': rec.id,
                },
            }


    def action_update_lot_product(self):
        for rec in self:
            return {
                'name': _('Update Lot'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'tray.product.lot',
                'target': 'new',
                'context': {
                    'default_manufacturing_process_id': rec.id,
                    'default_dest_location_id': rec.location_dest_id.id,
                    'default_location_src_id':rec.location_src_id.id
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
                    'default_manufacturing_process_id': rec.id,
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
                    'default_manufacturing_process_id': rec.id,
                    'default_type': 'RESTART',
                },
            }


class ProductionBreakdown(models.Model):
    _inherit = 'production.breakdown'

    manufacturing_process_id = fields.Many2one('manufacturing.process')
    end_time = fields.Datetime(string = 'End Time')

    def action_done_breakdown(self):
        for rec in self:
            if rec.manufacturing_process_id:
                if rec.type == 'HOLD':
                    rec.manufacturing_process_id.state = 'hold'
                else:
                    rec.manufacturing_process_id.state = 'progress'

        return super(ProductionBreakdown, self).action_done_breakdown()


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    cell_weight = fields.Float(string='Cell Weight (g)', digits=(16, 4))
    manufacturing_process_id = fields.Many2one('manufacturing.process')
    batch_id = fields.Many2one('manufacturing.batch')