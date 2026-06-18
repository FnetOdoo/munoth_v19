from odoo import models, fields, api, _
from datetime import timedelta, datetime
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'
    mo_drying = fields.Many2one('anode.drying')


class StockMoveLIne(models.Model):
    _inherit = 'stock.move.line'
    mo_drying = fields.Many2one('anode.drying')


class ManufacturingComponents(models.Model):
    _inherit = 'manufacturing.component'

    mo_drying = fields.Many2one('anode.drying')

    @api.onchange('product_id')
    def _onchange_roll_dry_product_id(self):
        if self.mo_drying:
            self.location_src_id = self.mo_drying.location_src_id.id
            self.location_dest_id = self.mo_drying.location_dest_id.id


class AnodeDrying(models.Model):
    _name = 'anode.drying'
    _description = 'Roll Drying'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.model
    def default_get(self, fields):
        defaults = super(AnodeDrying, self).default_get(fields)
        operation = self.env['manufacturing.operation'].search([('type', '=', 'anode_drying')], limit=1)
        defaults['operation_id'] = operation.id
        defaults['type'] = operation.type
        defaults['location_src_id'] = operation.location_src_id.id
        defaults['location_dest_id'] = operation.location_dest_id.id
        defaults['production_location_id'] = operation.production_location_id.id
        defaults['product_id'] = operation.bom_id.product_tmpl_id.id
        defaults['bom_id'] = operation.bom_id.id
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
    ])
    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        default=lambda self: self.env.company)
    location_src_id = fields.Many2one('stock.location')
    location_dest_id = fields.Many2one('stock.location')
    production_location_id = fields.Many2one('stock.location')

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
        readonly=True, required=True, check_company=True,
      )
    bom_id = fields.Many2one(
        'manufacturing.bom', 'Bill of Material')
    component_ids = fields.One2many(
        'manufacturing.component', 'mo_drying', 'Components',
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
        readonly=True, required=True, tracking=True,
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
    breakdown_ids = fields.One2many('production.breakdown', 'mo_drying')
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

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.bom_id = False
            self.component_ids = False

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
        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1)
        for line in self.component_ids:
            available_quant = self.env['stock.quant'].sudo().search([
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', line.location_src_id.id)
            ], limit=1)

            # if not available_quant or sum(available_quant.mapped('quantity')) < line.product_qty:
            #     raise UserError(f"Insufficient stock for product: {line.product_id.name} "
            #                     f"at location: {line.location_src_id.complete_name}.\n"
            #                     f"Available Quantity: {sum(available_quant.mapped('quantity')) if sum(available_quant.mapped('quantity')) else 0}\n"
            #                     f"Required Quantity: {line.product_qty}")

        for rec in self.component_ids:
            picking = self.env['stock.picking'].create({
                'picking_type_id': picking_type_id.id,
                'location_id': rec.location_src_id.id,
                'location_dest_id': rec.mo_drying.production_location_id.id,
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
                'location_dest_id': rec.mo_drying.production_location_id.id,
                'picking_id': picking.id,
                'company_id': rec.env.company.id,
                'mo_drying': rec.mo_drying.id,
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
                'location_dest_id': rec.mo_drying.production_location_id.id,
                'company_id': rec.company_id.id,
                'mo_drying': rec.mo_drying.id,
                # 'lot_id': rec.serial_number.id,
                'picking_id': picking.id,
                'move_id': stock_move.id,
                # 'production_id': self.id,
                'state': 'done',
            })
        self.state = 'confirmed'

    def action_start(self):
        for rec in self:
            rec.state = 'progress'

    def action_view_product_move(self):
        return {
            'res_model': 'stock.move.line',
            'type': 'ir.actions.act_window',
            'name': _("Stock Move"),
            'domain': [('mo_drying', '=', self.id)],
            'view_mode': 'list,form',
        }

    def action_close(self):
        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1)
        for rec in self:
            # if rec.qty_produced < 1:
            #     raise UserError(_('Please fill the produced qty'))
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
                'location_id': rec.location_src_id.id,
                'location_dest_id': rec.location_dest_id.id,
                'picking_id': picking.id,
                'company_id': rec.env.company.id,
                'mo_drying': rec.id,
                # 'production_id': self.id,
                'state': 'done',  # Set the state to 'waiting' to be done.
                'origin': self.name,
            })

            stock_move_line = self.env['stock.move.line'].create({
                'product_id': rec.product_id.id,
                # 'product_uom_qty': 1.0,
                'quantity': rec.qty_produced,
                'product_uom_id': rec.product_id.uom_id.id,
                'location_id': rec.location_src_id.id,
                'location_dest_id': rec.location_dest_id.id,
                'company_id': rec.company_id.id,
                'mo_drying': rec.id,
                # 'lot_id': rec.serial_number.id,
                'picking_id': picking.id,
                'move_id': stock_move.id,
                # 'production_id': self.id,
                'state': 'done',
            })
            rec.state = 'done'

    @api.onchange('type')
    def _onchange_of_operation_type(self):
        if self.type:
            machine = self.env['manufacturing.machine'].search([('type', '=', self.type)], limit=1)
            if machine:
                self.machine_id = machine.id

    @api.onchange('operation_id')
    def _onchange_of_operation(self):
        if self.operation_id:
            self.location_src_id = self.operation_id.location_src_id.id
            self.location_dest_id = self.operation_id.location_dest_id.id
            self.production_location_id = self.operation_id.production_location_id.id
        if self.component_ids:
            for line in self.component_ids:
                line.location_src_id = self.location_src_id.id
                line.location_dest_id = self.location_dest_id.id

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = seq.next_by_code('manufacturing.roll.drying') or _('New')
        return super().create(vals_list)

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
                    'default_mo_drying': rec.id,
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
                    'default_mo_drying': rec.id,
                    'default_type': 'RESTART',
                },
            }

    # @api.onchange('product_uom_id')
    # def onchange_product_uom_id(self):
    #     res = {}
    #     if not self.product_uom_id or not self.product_tmpl_id:
    #         return
    #     if self.product_uom_id.category_id.id != self.product_tmpl_id.uom_id.category_id.id:
    #         self.product_uom_id = self.product_tmpl_id.uom_id.id
    #         res['warning'] = {'title': _('Warning'), 'message': _(
    #             'The Product Unit of Measure you chose has a different category than in the product form.')}
    #     return res

    # @api.depends('product_uom_id', 'product_qty', 'product_id.uom_id')
    # def _compute_product_uom_qty(self):
    #     for production in self:
    #         if production.product_id.uom_id != production.product_uom_id:
    #             production.product_uom_qty = production.product_uom_id._compute_quantity(production.product_qty,
    #                                                                                      production.product_id.uom_id)
    #         else:
    #             production.product_uom_qty = production.product_qty
class ProductionBreakdown(models.Model):
    _inherit = 'production.breakdown'

    mo_drying = fields.Many2one('anode.drying')

    def action_done_breakdown(self):
        for rec in self:
            if rec.mo_drying:
                if rec.type == 'HOLD':
                    rec.mo_drying.state = 'hold'
                else:
                    rec.mo_drying.state = 'progress'

        return super(ProductionBreakdown, self).action_done_breakdown()