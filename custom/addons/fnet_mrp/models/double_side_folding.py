from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta, datetime


class StockProductionLOt(models.Model):
    _inherit = 'stock.lot'

    ds_folding_id = fields.Many2one('double.side.folding')


class StockMove(models.Model):
    _inherit = 'stock.move'
    ds_folding_id = fields.Many2one('double.side.folding')


class ProductSerialNumber(models.Model):
    _inherit = 'product.serial.number'
    ds_folding_id = fields.Many2one('double.side.folding')


class StockMoveLIne(models.Model):
    _inherit = 'stock.move.line'
    ds_folding_id = fields.Many2one('double.side.folding')


class ManufacturingComponents(models.Model):
    _inherit = 'manufacturing.component'

    ds_folding_id = fields.Many2one('double.side.folding')

    @api.onchange('product_id')
    def _onchange_dsf_product_id(self):
        if self.ds_folding_id:
            self.location_src_id = self.ds_folding_id.location_src_id.id
            self.location_dest_id = self.ds_folding_id.location_dest_id.id


class DoubleSideFolding(models.Model):
    _name = 'double.side.folding'
    _description = 'Double Side Folding'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "id desc"

    @api.model
    def default_get(self, fields):
        defaults = super(DoubleSideFolding, self).default_get(fields)
        operation = self.env['manufacturing.operation'].search([('type', '=', 'dsf')], limit=1)
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
    lot_ids = fields.One2many('product.serial.number', 'ds_folding_id', string='Serial Number')

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
         check_company=True)

    bom_id = fields.Many2one(
        'manufacturing.bom', 'Bill of Material')
    component_ids = fields.One2many(
        'manufacturing.component', 'ds_folding_id', 'Components',
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
        readonly=True, required=True, tracking=True,)
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
    production_plan_id = fields.Many2one('production.plan')
    breakdown_ids = fields.One2many('production.breakdown', 'ds_folding_id')
    start_time = fields.Datetime()
    end_time = fields.Datetime()
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
        if self._origin:
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

    def action_confirm(self):
        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1)
        for rec in self:
            for lot in self.lot_ids:
                lot_id = self.env['stock.lot'].sudo().search([
                    ('product_id', '=', rec.product_id.id),
                    ('name', '=', lot.name)], limit=1)
                if lot_id:
                    lot.lot_id = lot_id.id
                else:
                    raise UserError(_('%s -this lot number does not exist' % lot.name))
            for component in self.component_ids:
                lot = self.env['stock.lot'].search(
                    [('product_id', '=', rec.product_id.id), ('name', '=', rec.lot_number)])

                picking = self.env['stock.picking'].create({
                    'picking_type_id': picking_type_id.id,
                    'location_id': rec.location_src_id.id,
                    'location_dest_id': rec.operation_id.production_location_id.id,
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
                    'location_dest_id': rec.operation_id.production_location_id.id,
                    'picking_id': picking.id,
                    'company_id': rec.env.company.id,
                    'injection_id': rec.id,
                    # 'production_id': self.id,
                    'state': 'done',  # Set the state to 'waiting' to be done.
                    'origin': self.name,
                })

                stock_move_line = self.env['stock.move.line'].create({
                    'product_id': rec.product_id.id,
                    # 'product_uom_qty': 1.0,
                    'quantity': component.product_qty,
                    'product_uom_id': rec.product_id.uom_id.id,
                    'location_id': rec.location_src_id.id,
                    'location_dest_id': rec.operation_id.production_location_id.id,
                    'company_id': rec.company_id.id,
                    'injection_id': rec.id,
                    'lot_id': lot.id or False,
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
            'domain': [('ds_folding_id', '=', self.id)],
            'view_mode': 'list,form',
        }

    def action_close(self):
        picking_type_id = self.env['stock.picking.type'].search([('code', '=', 'mrp_operation')], limit=1)
        for rec in self:
            produced_qty = 0
            if rec.lot_ids:
                for lot in rec.lot_ids:
                    # if lot.lot_id:
                    #     raise UserError(
                    #         _('Serial number has already been assigned for product "%s"') % rec.product_id.name)

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
                        'product_uom': rec.product_id.uom_id.id,
                        'location_id': rec.location_src_id.id,
                        'location_dest_id': rec.location_dest_id.id,
                        'picking_id': picking.id,
                        'company_id': rec.env.company.id,
                        'ds_folding_id': rec.id,
                        'state': 'done',
                        'origin': self.name,
                    })
                    stock_move_line = self.env['stock.move.line'].create({
                        'product_id': rec.product_id.id,
                        'quantity': 1,
                        'product_uom_id': rec.product_id.uom_id.id,
                        'location_id': rec.location_src_id.id,
                        'location_dest_id': rec.location_dest_id.id,
                        'company_id': rec.company_id.id,
                        'ds_folding_id': rec.id,
                        'lot_id': lot.lot_id.id,
                        'picking_id': picking.id,
                        'move_id': stock_move.id,
                        'state': 'done',
                    })

                    produced_qty += 1

            else:
                raise UserError(_('Please fill the serial/lot number for the "%s"') % rec.product_id.name)

            rec.qty_produced = produced_qty

        self.state = 'done'

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
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'manufacturing.dsf.cell'
                ) or _('New')
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
                    'default_ds_folding_id': rec.id,
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
                    'default_ds_folding_id': rec.id,
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

    ds_folding_id = fields.Many2one('double.side.folding')

    def action_done_breakdown(self):
        for rec in self:
            if rec.ds_folding_id:
                if rec.type == 'HOLD':
                    rec.ds_folding_id.state = 'hold'
                else:
                    rec.ds_folding_id.state = 'progress'

        return super(ProductionBreakdown, self).action_done_breakdown()