from odoo import models, api, fields, _
from odoo.exceptions import UserError


class WorkOrder(models.Model):
    _name = "work.order"
    _description = "Work Order"
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']

    def _get_material_request_count(self):
        for rec in self:
            rec.material_request_count = self.env['maintenance.material.request'].search_count([('order_id', '=', rec.id)])
    
    number = fields.Char('Reference', copy=False, readonly=True, default=lambda x: _('New'))
    name = fields.Char('Name', required=1)
    maintenance_id = fields.Many2one('maintenance.request', string="Maintenance")
    state = fields.Selection([('draft', 'Draft'), ('progress', 'InProgress'), ('done', 'Done'), ('cancel', 'Cancelled')], default='draft', string="Status", tracking=True)
    user_id = fields.Many2one('res.users', string="Responsible")
    date_start = fields.Datetime("Start Date")
    date_end = fields.Datetime("End Date")
    checklist_id = fields.Many2one('equipment.checklist', string="Checklist")
    material_ids = fields.Many2many('checklist.material', string="Materials")
    equipment_id = fields.Many2one('maintenance.equipment', string="Equipment", related='maintenance_id.equipment_id')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)
    material_request_count = fields.Integer("Material Request Count", compute='_get_material_request_count')

    def action_start(self):
        if self.material_ids:
            request_ids = self.env['maintenance.material.request'].search([('order_id', '=', self.id)])
            if not request_ids:
                raise UserError(_("Please create material request to start the work order."))
            if any(rec.state not in ['receive', 'cancel', 'reject'] for rec in request_ids):
                raise UserError(_("Please complete all the material request to start the work order."))
        self.write({
            'state': 'progress',
            'date_start': fields.Datetime.now(),
        })

    def action_finish(self):

        self.write({
            'state': 'done',
            'date_end': fields.Datetime.now(),
        })

    def action_cancel(self):
        self.write({
            'state': 'cancel',
        })

    def action_material_request(self):
        if not self.material_ids:
            raise UserError(_("No materials available."))
        picking_type = self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)
        request_id = self.env['maintenance.material.request'].create({
            'department_id': self.equipment_id.department_id.id,
            'employee_id': self.equipment_id.employee_id.id,
            'reason': self.checklist_id.name,
            'order_id': self.id,
            'equipment_id': self.equipment_id.id,
            'dest_location_id': self.equipment_id.location_id.id or picking_type.default_location_src_id.id,
            'location_id': picking_type.default_location_dest_id.id,
        })
        for line in self.material_ids:
            self.env['material.request.line'].create({
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'product_uom_id': line.product_uom_id.id,
                'product_qty': line.product_qty,
                'request_id': request_id.id,
            })
        return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Material request has been created.'),
                    'sticky': False,
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

    def action_open_material_request(self):
        return {
            'name': _('Material Request'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'maintenance.material.request',
            'context': {'create': False},
            'domain': [('order_id', '=', self.id)]
        }

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('number', _('New')) == _('New'):
                vals['number'] = self.env['ir.sequence'].next_by_code('work.order')
        return super().create(vals_list)

