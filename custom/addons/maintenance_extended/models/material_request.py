from odoo import models, api, fields, _
from odoo.exceptions import UserError,ValidationError


class MaintenanceMaterialRequest(models.Model):
    _name = "maintenance.material.request"
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']

    def _get_picking_count(self):
        for rec in self:
            rec.picking_count = self.env['stock.picking'].search_count([('request_id', '=', rec.id)])

    name = fields.Char('Reference', copy=False, readonly=True, default=lambda x: _('New'))
    state = fields.Selection([
        ('draft', 'New'),
        ('request', 'Requested'),
        ('approve', 'Approved'),
        ('receive', 'Received'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected'),
        ('close', 'Close')], string="Status", default='draft', tracking=True)
    request_date = fields.Date(string='Request Date', default=fields.Date.context_today, required=True)
    department_id = fields.Many2one('hr.department', string='Department', copy=True)
    employee_id = fields.Many2one('hr.employee', string='Employee', default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1), copy=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.user.company_id, required=True, copy=True)
    date_end = fields.Date(string='Deadline', help='Last date for the product to be needed', copy=True, tracking=True)
    date_done = fields.Date(string='Received Date', readonly=True, help='Date of Completion of Purchase Requisition')
    reason = fields.Text(string='Reason for Request', required=False, copy=True)
    responsible_id = fields.Many2one('hr.employee', string='Requisition Responsible', copy=True)
    picking_type_id = fields.Many2one('stock.picking.type', 'Operation Type', check_company=True, copy=False,
        default=lambda self: self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1).id)
    location_id = fields.Many2one('stock.location', string='Source Location', copy=True)
    dest_location_id = fields.Many2one('stock.location', string='Destination Location', required=False, copy=True)
    order_id = fields.Many2one('work.order', string="Work Order")
    equipment_id = fields.Many2one('maintenance.equipment', string="Equipment" )
    line_ids = fields.One2many('material.request.line', 'request_id', string="Materials")
    picking_count = fields.Integer("Picking Count", compute='_get_picking_count')
    is_consumed = fields.Boolean()
    temporary_location = fields.Many2one(
        'stock.location', 'Temporary Location',
        domain="[('temporary_location','=',True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        default=lambda self: self.env['stock.location'].search([('temporary_location', '=', True)], limit=1),
        check_company=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('work.order')
        return super().create(vals_list)

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            self.department_id = self.employee_id.department_id.id

    @api.onchange('order_id')
    def onchange_order_id(self):
        if self.order_id:
            self.equipment_id = self.order_id.equipment_id.id

    @api.onchange('equipment_id')
    def onchange_equipment(self):
        if self.equipment_id:
            self.dest_location_id = self.equipment_id.location_id.id or self.picking_type_id.default_location_dest_id.id

    @api.onchange('picking_type_id')
    def onchange_picking_type_id(self):
        self.location_id = self.picking_type_id.default_location_src_id.id
        self.dest_location_id = self.equipment_id.location_id.id or self.picking_type_id.default_location_dest_id.id

    def action_request(self):
        self.write({'state': 'request'})

    def action_approve(self):
        if not self.location_id or not self.dest_location_id or not self.picking_type_id:
            raise UserError(_("Please update the picking details in others tab."))
        picking_id = self.env['stock.picking'].sudo().create({
            'partner_id': self.employee_id.sudo().address_id.id,
            'location_id': self.location_id.id,
            'location_dest_id': self.temporary_location.id,
            'picking_type_id': self.picking_type_id.id,
            'note': self.reason,
            'origin': self.name,
            'request_id': self.id,
            'company_id': self.company_id.id,
        })
        for line in self.line_ids:
            self.env['stock.move'].create({
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.product_qty,
                        'product_uom': line.product_uom_id.id,
                        'location_id': self.location_id.id,
                        'location_dest_id':self.temporary_location.id,
                        'inventory_name': line.name,
                        'picking_type_id': self.picking_type_id.id,
                        'picking_id': picking_id.id,
                        'company_id': line.request_id.company_id.id,
                    })

        self.write({'state': 'approve'})

    def action_close(self):
        for rec in self:
            stock = self.env['stock.picking'].search([('request_id', '=', rec.id)])
            if any(record.picking_type_id.sequence_code == 'INT' and record.state != 'done' for record in stock):
                raise ValidationError("The Material is not received from store. so kindly validate the delivery")
            rec.write({
                'state':'close'
            })




    def action_validate(self):
        stock = self.env['stock.picking'].search([('request_id','=',self.id)])
        if any(record.picking_type_id.sequence_code == 'INT' and record.state != 'done' for record in stock):
            raise ValidationError("The Material is not received from store. so kindly validate the delivery")
        if not self.location_id or not self.dest_location_id or not self.picking_type_id:
            raise UserError(_("Please update the picking details in others tab."))
        stock = self.env['stock.location'].search([('consumed_location', '=', True)], limit=1)
        picking_id = self.env['stock.picking'].sudo().create({
            'partner_id': self.employee_id.sudo().address_id.id,
            'location_id': self.temporary_location.id,
            'location_dest_id': stock.id if self.is_consumed else self.dest_location_id.id,
            # 'location_dest_id': self.dest_location_id.id,
            'picking_type_id': self.picking_type_id.id,
            'note': self.reason,
            'origin': self.name,
            'request_id': self.id,
            'company_id': self.company_id.id,
        })
        for line in self.line_ids:
            self.env['stock.move'].create({
                        'product_id': line.product_id.id,
                        'product_uom_qty': line.product_qty,
                        'product_uom': line.product_uom_id.id,
                        'location_id': self.temporary_location.id,
                        'location_dest_id': stock.id if self.is_consumed else self.dest_location_id.id,
                        'inventory_name': line.name,
                        'picking_type_id': self.picking_type_id.id,
                        'picking_id': picking_id.id,
                        'company_id': line.request_id.company_id.id,
                    })
        self.write({'state': 'receive'})

    def action_refuse(self):
        self.write({'state': 'reject'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_open_pickings(self):
        return {
            'name': _('Transfers'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'stock.picking',
            'context': {'create': False},
            'domain': [('request_id', '=', self.id)]
        }


class MaterialRequestLine(models.Model):
    _name = "material.request.line"
    _description = "Material Line"

    name = fields.Char("Description", required=True)
    request_id = fields.Many2one('maintenance.material.request', string="Request")
    product_id = fields.Many2one('product.product', 'Product',
                                 domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                 required=True, check_company=True)
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True,
                                     domain="[('relative_uom_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.relative_uom_id')
    product_qty = fields.Float("Quantity", default=1.0)
    company_id = fields.Many2one(related='request_id.company_id')
    
    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id
            self.name = self.product_id.name

