from odoo import models, api, fields, _
from odoo.exceptions import UserError


class WorkOrder(models.Model):
    _name = "work.order"
    _description = "Work Order"
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']

    def _get_material_request_count(self):
        for rec in self:
            rec.material_request_count = self.env['mrp.material.request'].search_count([('order_id', '=', rec.id)])
    
    number = fields.Char('Reference', copy=False, readonly=True, default=lambda x: _('New'))
    name = fields.Char('Activity', required=1)
    maintenance_id = fields.Many2one('maintenance.request', string="Maintenance")
    state = fields.Selection([('draft', 'Draft'), ('progress', 'InProgress'), ('done', 'Done'), ('cancel', 'Cancelled')], default='draft', string="Status", tracking=True)
    user_id = fields.Many2one(
        'res.users',
        string="Responsible",
        domain=lambda self: [
            ('group_ids', 'in', self.env.ref('maintenance.group_equipment_manager').id)
        ],
    )
    date_start = fields.Datetime("Work Start Date")
    date_end = fields.Datetime("Work End Date")
    checklist_id = fields.Many2one('equipment.checklist', string="Checklist")
    material_ids = fields.Many2many('checklist.material', string="Materials")
    equipment_id = fields.Many2one('maintenance.equipment', string="Equipment", related='maintenance_id.equipment_id')
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)
    material_request_count = fields.Integer("Material Request Count", compute='_get_material_request_count')
    is_material_request_created = fields.Boolean(copy=False, default=False)
    duration = fields.Float(string='Duration (Hours)', compute='_compute_duration', store=True, )

    @api.depends('date_start', 'date_end')
    def _compute_duration(self):
        for rec in self:
            if rec.date_start and rec.date_end:
                delta = rec.date_end - rec.date_start
                rec.duration = delta.total_seconds() / 3600.0
            else:
                rec.duration = 0.0

    def action_start(self):
        if self.material_ids:
            request_ids = self.env['mrp.material.request'].search([('order_id', '=', self.id)])
            if not request_ids:
                raise UserError(_("Please create material request to start the work order."))
            if any(rec.state not in ['material_accept', 'cancel', 'reject','close'] for rec in request_ids):
                raise UserError(_("Please complete all the material request to start the work order."))
        self.write({
            'state': 'progress',
            'date_start': fields.Datetime.now(),
        })

    def action_finish(self):
        if self.material_ids:
            request_ids = self.env['mrp.material.request'].search([('order_id', '=', self.id)])
            if not request_ids:
                raise UserError(_("Please create material request to start the work order."))
            if any(rec.state not in ['material_accept', 'cancel', 'reject', 'close'] for rec in request_ids):
                raise UserError(_("Please complete all the material request to start the work order."))
        if not self.date_start:
            raise UserError(_("Please Select the Start Date"))
        if not self.date_end:
            raise UserError(_("Please Select the End Date"))
        self.write({'state': 'done'})
        self._capture_maintenance_start()
        self._check_and_mark_maintenance_done()

    def action_cancel(self):
        self.write({'state': 'cancel'})
        self._check_and_mark_maintenance_done()

    def _capture_maintenance_start(self):
        """Capture actual_start_date on the maintenance request only once —
        the first time any work order under it gets a start date."""
        if self.maintenance_id and not self.maintenance_id.actual_start_date and self.date_start:
            self.maintenance_id.write({
                'actual_start_date': self.date_start,
            })

    def _check_and_mark_maintenance_done(self):
        """Check if all non-cancelled work orders under this maintenance request are done,
        and if so, move the maintenance request to its 'done' stage and capture the end date."""
        all_work_orders = self.search([('maintenance_id', '=', self.maintenance_id.id)])
        active_work_orders = all_work_orders.filtered(lambda wo: wo.state != 'cancel')
        if active_work_orders and all(wo.state == 'done' for wo in active_work_orders):
            done_stage = self.env['maintenance.stage'].search([('is_done_state', '=', True)], limit=1)
            if done_stage:
                end_dates = active_work_orders.filtered(lambda wo: wo.date_end).mapped('date_end')
                last_end_date = max(end_dates) if end_dates else fields.Datetime.now()
                self.maintenance_id.write({
                    'stage_id': done_stage.id,
                    'actual_end_date': last_end_date,
                })

    def action_material_request(self):
        if not self.material_ids:
            raise UserError(_("No materials available."))
        picking_type = self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1)
        request_id = self.env['mrp.material.request'].create({
            'department_id': self.equipment_id.department_id.id,
            # 'user_id': self.equipment_id.employee_id.id,
            # 'reason': self.checklist_id.name,
            'is_maintenance_material_request': True,
            'work_order_id': self.id,
            'order_id': self.id,
            'equipment_id': self.equipment_id.id,
            'location_dest_id': self.equipment_id.location_id.id or picking_type.default_location_src_id.id,
            'location_id': picking_type.default_location_dest_id.id,
        })
        for line in self.material_ids:
            self.env['mrp.material.request.line'].create({
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'product_uom': line.product_uom_id.id,
                'quantity': line.product_qty,
                'request_id': request_id.id,
            })
        self.is_material_request_created = True
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
            'res_model': 'mrp.material.request',
            'context': {'create': False},
            'domain': [('work_order_id', '=', self.id)]
        }



