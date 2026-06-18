from odoo import models, fields, api, _
from odoo.exceptions import UserError
import xlsxwriter
import base64


class ManufacturingComponents(models.Model):
    _inherit = 'manufacturing.component'

    production_id = fields.Many2one('production.plan')
    anode_operation_id = fields.Many2one('manufacturing.operation')
    cathode_operation_id = fields.Many2one('manufacturing.operation')

    stock_condition = fields.Selection([
        ('ok', 'OK'),
        ('fail', 'Fail')
    ], compute='_compute_stock_condition')

    def _compute_stock_condition(self):
        for rec in self:
            rec.stock_condition = 'fail'
            if rec.production_id:
                if rec.available_qty >= rec.product_qty:
                    rec.stock_condition = 'ok'
                else:
                    rec.stock_condition = 'fail'
            else:
                rec.stock_condition = 'fail'


class ProductionPlan(models.Model):
    _name = 'production.plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Production Plan'
    _order = "id desc"

    name = fields.Char(
        'Reference', copy=False, readonly=True, default=lambda x: _('New'))
    model_number = fields.Char()
    model_id = fields.Many2one('product.model')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirm'),
        ('in_production', 'Production Process'),
        ('close', 'Close'),
        ('cancel', 'Cancel')
    ], default='draft')
    line_number = fields.Char(default='1')
    date = fields.Datetime(default=fields.Datetime.now, readonly=True)
    manufacturing_stages_id       = fields.Many2one('manufacturing.stages')
    anode_slitting = fields.Many2one('anode.slitting')
    cathode_slitting = fields.Many2one('cathode.slitting')
    injection_id = fields.Many2one('cell.injection')
    diaphragm_id = fields.Many2one('diaphragm.drying')
    product_id = fields.Many2one('product.product')
    expected_production_qty = fields.Float()
    anode_slitting_operation_id = fields.Many2one('manufacturing.operation')
    cathode_slitting_operation_id = fields.Many2one('manufacturing.operation')
    injection_operation_id = fields.Many2one('manufacturing.operation')
    operation_ids = fields.One2many(
        'production.operation', 'production_plan_id', 'Operation')
    component_ids = fields.One2many(
        'manufacturing.component', 'production_id', 'Components',
        copy=False)
    mrp_stage_estimation_id = fields.Many2one('mrp.estimation')
    date_start = fields.Date()
    end_date = fields.Date()
    expected_end_date = fields.Date()
    choose_stage = fields.Selection([
        ('stage_0', 'Process Type 0'),
        ('stage_1', 'Process Type 1'),
        ('stage_2', 'Process Type 2'),
        ('stage_3', 'Process Type 3'),
        ('stage_4', 'Process Type 4'),
        ('stage_5', 'Process Type 5'),
        ('stage_6', 'Process Type 6')], help='Choose stage of going to production')
    # diaphragm_required = fields.Boolean()
    update_operation = fields.Boolean()
    qty_produced = fields.Float("Produced Qty", compute='_compute_produced_qty')
    qty_remaining = fields.Float("Remaining Qty to Produce", compute='_compute_produced_qty')

    first_process_type = fields.Char( string="First Process Type",compute='_compute_first_operation', store=True)
    first_operation_id = fields.Many2one( 'manufacturing.operation', string="First Operation", compute='_compute_first_operation',store=True)
    first_process_type_id = fields.Many2one('manufacturing.process.type',  string="First Process Type", compute='_compute_first_operation', store=True)
    first_production_process_count = fields.Integer(compute='_compute_first_production_process_count')
    batch_id = fields.Many2one('manufacturing.batch', string='Batch')

    def _compute_first_production_process_count(self):
        for rec in self:
            rec.first_production_process_count = self.env['manufacturing.process'].search_count([
                ('is_first_process' ,'=',True),
                ('production_plan_id', '=', rec.id)
            ])

    @api.depends('operation_ids.sequence','manufacturing_stages_id','model_id',
                 'operation_ids.operation_id',
                 'operation_ids.manufacturing_process_type_id')
    def _compute_first_operation(self):
        for rec in self:
            first_line = rec.operation_ids.sorted('sequence')[:1]
            if first_line:
                rec.first_process_type = first_line.manufacturing_process_type_id.name
                rec.first_operation_id = first_line.operation_id
                rec.first_process_type_id = first_line.manufacturing_process_type_id
            else:
                rec.first_process_type = ''

    def open_production_process(self):
        return {
            'name': self.first_process_type,
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'manufacturing.process',
            'context': {
                'default_product_id.tracking': 'none',
                'default_is_first_process': True,
            },
            'domain': [('production_plan_id', '=', self.id),('is_first_process', '=', True)]
        }

    @api.onchange('manufacturing_stages_id', 'model_id')
    def _onchange_choose_stage(self):
        if self.manufacturing_stages_id and self.model_id:
            line_defaults = []
            self.operation_ids = False

            for line in self.model_id.operation_ids.filtered(
                    lambda x: x.manufacturing_stages_id == self.manufacturing_stages_id
            ):
                line_defaults.append((0, 0, {
                    'sequence': line.sequence,
                    'manufacturing_process_type_id': line.manufacturing_process_type_id,
                    'operation_id': line.id,
                }))

            self.operation_ids = line_defaults

    def print_excel_report(self):
        url = '/tmp/'
        workbook = xlsxwriter.Workbook(url + 'Production Plan Sheet.xlsx')
        sheet = workbook.add_worksheet()

        border_width = 1

        merge_format1 = workbook.add_format({
            'font_size': 11,
            'align': 'left',
            'font_name': 'Liberation Serif',
            'border': border_width,
        })

        merge_format2 = workbook.add_format({
            'font_size': 11,
            'bold': 1,
            'align': 'center',
            'font_name': 'Liberation Serif',
            'border': border_width
        })

        sheet.set_column('A:A', 5)
        sheet.set_column('B:B', 10)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:D', 25)

        s_no = 0
        row = 0
        col = 0

        sheet.write(row, col, 'S.No', merge_format2)
        sheet.write(row, col + 1, 'Model', merge_format2)
        sheet.write(row, col + 2, 'Product', merge_format2)
        sheet.write(row, col + 3, 'Rework Date', merge_format2)

        baking = self.env['cell.injection'].search([
            ('production_plan_id', '=', self.id)
        ])

        for injection in baking:
            quality = self.env['mrp.quality'].search([
                ('injection_id', '=', injection.id)
            ])

            for rec in quality:
                s_no += 1
                row += 1

                sheet.write(row, col, s_no, merge_format1)
                sheet.write(row, col + 1, injection.product_model_id.name or '', merge_format1)
                sheet.write(row, col + 2, injection.machine_id.type or '', merge_format1)
                sheet.write(
                    row,
                    col + 3,
                    rec.date.strftime('%d/%m/%Y') if rec.date else '',
                    merge_format1
                )

        clamp = self.env['cell.clamp.baking'].search([
            ('production_plan_id', '=', self.id)
        ])

        for clamp_baking in clamp:
            quality1 = self.env['mrp.quality'].search([
                ('clamp_baking_id', '=', clamp_baking.id)
            ], limit=1)

            s_no += 1
            row += 1

            sheet.write(row, col, s_no, merge_format1)
            sheet.write(row, col + 1, clamp_baking.product_model_id.name or '', merge_format1)
            sheet.write(row, col + 2, clamp_baking.machine_id.type or '', merge_format1)
            sheet.write(
                row,
                col + 3,
                quality1.date.strftime('%d/%m/%Y') if quality1.date else '',
                merge_format1
            )

        capacity_test = self.env['capacity.test'].search([
            ('production_plan_id', '=', self.id)
        ])

        for test in capacity_test:
            quality2 = self.env['mrp.quality'].search([
                ('capacity_id', '=', test.id)
            ], limit=1)

            s_no += 1
            row += 1

            sheet.write(row, col, s_no, merge_format1)
            sheet.write(row, col + 1, test.product_model_id.name or '', merge_format1)
            sheet.write(row, col + 2, test.machine_id.type or '', merge_format1)
            sheet.write(
                row,
                col + 3,
                quality2.date.strftime('%d/%m/%Y') if quality2.date else '',
                merge_format1
            )

        workbook.close()

        with open(url + 'Production Plan Sheet.xlsx', 'rb') as fo:
            data = fo.read()

        out = base64.b64encode(data)

        values = {
            'name': 'production_plan_report.xlsx',
            'res_model': 'ir.ui.view',
            'res_id': False,
            'type': 'binary',
            'public': True,
            'datas': out,
        }

        attachment_id = self.env['ir.attachment'].sudo().create(values)

        download_url = '/web/content/%s?download=true' % attachment_id.id

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        return {
            'type': 'ir.actions.act_url',
            'url': str(base_url) + str(download_url),
            'target': 'new',
        }

    def _compute_produced_qty(self):
        for rec in self:
            lot_ids = []
            if rec.choose_stage == 'stage_2':
                drying_ids = self.env['cell.drying'].search([('production_plan_id', '=', rec.id)])
                lot_ids = drying_ids.mapped('finished_move_ids').mapped('lot_id').ids
            rec.qty_produced = len(lot_ids)
            rec.qty_remaining = rec.expected_production_qty - len(lot_ids)
            if rec.choose_stage == 'stage_3':
                drying_ids = self.env['cell.drying'].search([('production_plan_id', '=', rec.id)])
                lot_ids = drying_ids.mapped('finished_move_ids').mapped('lot_id').ids
            rec.qty_produced = len(lot_ids)
            rec.qty_remaining = rec.expected_production_qty - len(lot_ids)

    def action_view_lots(self):
        self.ensure_one()

        lot_ids = self.env['stock.lot'].search([
            ('production_plan_id', '=', self.id)
        ])

        return {
            'name': _('Available Lots'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'stock.quant',
            'domain': [
                ('lot_id', 'in', lot_ids.ids),
                ('quantity', '>', 0)
            ],
            'context': {
                'group_by': 'location_id'
            }
        }


    @api.onchange('model_id')
    def onchange_of_product_model_id(self):
        if self.model_id:
            self.product_id = self.model_id.product_id.id

    def action_confirm(self):
        for rec in self:
            if not rec.expected_production_qty > 0:
                raise UserError('Expected Production Qty cannot be 0')
            if not rec.operation_ids:
                raise UserError(_("There is no operation found for the current production plan. Please configure in product model %s." % (rec.model_id.name)))
            for line in rec.operation_ids:
                if not line.operation_id:
                    raise UserError(_("Please set operation for type %s" % dict(line._fields['operation_type'].selection).get(line.operation_type)))
            rec.state = 'confirm'

    def action_close(self):
        for rec in self:
            first_production_process = self.env['manufacturing.process'].search([
                ('manufacturing_process_id', '=', rec.first_process_type_id.id),
                ('production_plan_id', '=', self.id)
            ])
            if not first_production_process:
                raise UserError("Please Create a First Production Process")
            for get_process in first_production_process:
                if get_process.state != 'close':
                    raise UserError(_(
                        "Please complete the entire process before closing the Production Plan"
                    ))
        # packing = self.env['package.move'].search([('type', '=', 'packing'), ('production_plan_id', '=', self.id), ('state', '=', 'close')])
        lot_ids = self.env['stock.lot'].search([('production_plan_id', '=', self.id)])
        close_locations = self.env['stock.location'].search(['|', ('usage', '!=', 'inventory'), ('stock_location', '!=', False)])
        stock_quants = self.env['stock.quant'].search([('lot_id', 'in', lot_ids.ids), ('quantity', '>', 0)])
        if any(stock_quant.location_id.id not in close_locations.ids for stock_quant in stock_quants):
            raise UserError(_('Please Complete the entire process'))
        # if not packing:
        #     raise UserError(_('Please Complete the entire process'))
        # self.state = 'close'
        self.end_date = fields.Date.today()

    def action_cancel(self):
        self.state = 'cancel'

    def create_material_request(self):
        pass

    def check_material_available(self):
        if not self.component_ids:
            raise UserError(_("Please fill in the materials"))
        for rec in self.component_ids:
            if rec.product_id and rec.product_qty:
                lot_id = self.env['stock.lot'].search([('name', '=', rec.lot_number), ('product_id', '=', rec.product_id.id)])
                stock_quant = self.env['stock.quant'].search([
                    ('product_id', '=', rec.product_id.id),
                    ('location_id', '=', rec.location_src_id.id),
                    ('lot_id', '=', lot_id.id)
                ])
                available_quantity = sum(stock_quant.mapped('quantity'))
                rec.available_qty = available_quantity  # Update the available_qty field

    @api.onchange('anode_slitting_operation_id')
    def _onchange_of_anode_slitting(self):
        if self.anode_slitting_operation_id and self.anode_slitting_operation_id.bom_id:
            child_records = []
            lines = self.env['manufacturing.bom.line'].search([('bom_id', '=', self.anode_slitting_operation_id.bom_id.id)])
            for line in lines:
                child_records.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'location_src_id': self.anode_slitting_operation_id.location_src_id.id,
                    'location_dest_id': self.anode_slitting_operation_id.location_dest_id.id,
                    'product_qty': line.product_qty,
                    'anode_operation_id': self.anode_slitting_operation_id.id,
                }))
            self.component_ids = child_records

    @api.onchange('cathode_slitting_operation_id')
    def _onchange_of_cathode_slitting(self):
        if self.cathode_slitting_operation_id and self.cathode_slitting_operation_id.bom_id:
            child_records = []
            lines = self.env['manufacturing.bom.line'].search(
                [('bom_id', '=', self.cathode_slitting_operation_id.bom_id.id)])
            for line in lines:
                child_records.append((0, 0, {
                    'product_id': line.product_id.id,
                    'name': line.product_id.name,
                    'location_src_id': self.cathode_slitting_operation_id.location_src_id.id,
                    'location_dest_id': self.cathode_slitting_operation_id.location_dest_id.id,
                    'product_qty': line.product_qty,
                    'anode_operation_id': self.cathode_slitting_operation_id.id,
                }))
            self.component_ids = child_records

    def action_production_start(self):
        for rec in self:
            rec.state = 'in_production'
            rec.date_start = fields.Date.today()

    def open_anode_slitting_processing(self):
        return {
            'name': _('Anode Slitting'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'anode.slitting',
            'domain' : [('production_plan_id','=', self.id)]
        }

    def open_diaphragm_drying_processing(self):
        return {
            'name': _('Diaphragm Drying'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'diaphragm.drying',
            'domain' : [('production_plan_id','=', self.id)]
        }

    def open_cathode_slitting_processing(self):
        return {
            'name': _('Cathode Slitting'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'cathode.slitting',
            'domain': [('production_plan_id', '=', self.id)]
        }

    def open_injection_processing(self):
        return {
            'name': _('Cell Drying'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'cell.drying',
            'domain': [('production_plan_id', '=', self.id)]
        }

    def open_qr_code_printing(self):
        return {
            'name': _('QR Code Printing'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'qr.code.printing',
            'context': {
                    'default_product_id.tracking': 'none',
                },
            'domain': [('production_plan_id', '=', self.id)]
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('manufacturing.plan') or _('New')
        return super(ProductionPlan, self).create(vals_list)


    @api.onchange('operation_ids')
    def _onchange_operation_ids_sequence(self):
        if self.operation_ids:
            first_line = self.operation_ids.sorted('sequence')[:1]
            self.first_process_type = first_line.manufacturing_process_type_id


class Operation(models.Model):
    _name = 'production.operation'
    _description = 'Production Plan Operation'

    manufacturing_process_type_id = fields.Many2one('manufacturing.process.type')
    # operation_type = fields.Selection([
    #     ('anode_slitting', 'Anode Slitting '),
    #     ('cathode_slitting', 'Cathode Slitting '),
    #     ('anode_drying', 'Anode Drying'),
    #     ('cathode_drying', 'Cathode Drying'),
    #     ('diaphragm_drying', 'Diaphragm Drying'),
    #     ('anode_electrode_making', 'Anode Electrode Making'),
    #     ('cathode_electrode_making', 'Cathode Electrode Making'),
    #     ('winding', 'Winding'),
    #     ('hot_press_jelly', 'Hot Press Jelly'),
    #     ('assembly', 'Assembly'),
    #     ('qr_code_print', 'QR Code Printing'),
    #     ('cell_drying', 'Cell Drying'),
    #     ('injection', 'Injection'),
    #     ('high_temperature', 'High Temperature'),
    #     ('cell_clamp_baking', 'Cell Clamp Baking'),
    #     ('ht_clamp_baking', 'HT + Cell Clamp Baking'),
    #     ('aged_formation_cell', 'Aged Formation Cell'),
    #     ('degas', 'Degas'),
    #     ('dsf', 'Double side Folding'),
    #     ('pad_printing', 'Pad Printing'),
    #     ('capacity_test', 'Capacity Test'),
    #     ('voltage_test', 'Voltage Test'),
    #     ('aged_formation_cell_2', 'Aged Formation Cell 2'),
    #     ('voltage_test_2', 'Voltage Test 2'),
    #     ('packing', 'Packing')
    # ])
    bom_id = fields.Many2one('manufacturing.bom')
    production_plan_id = fields.Many2one('production.plan')
    model_id = fields.Many2one(related='production_plan_id.model_id')
    operation_id = fields.Many2one('manufacturing.operation')
    sequence = fields.Integer(index=True, default=1)
    is_process_completed = fields.Boolean(default=False)

    @api.onchange('sequence')
    def _onchange_sequence(self):
        if self.production_plan_id:
            self.production_plan_id._onchange_operation_ids_sequence()

class StockProductionLot(models.Model):
    _inherit = 'stock.lot'

    production_plan_id = fields.Many2one('production.plan', string="Production Plan")