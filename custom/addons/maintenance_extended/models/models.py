from odoo import models, api, fields, _
from odoo.exceptions import UserError, ValidationError
from dateutil.relativedelta import relativedelta


class Picking(models.Model):
    _inherit = 'stock.picking'
    
    request_id = fields.Many2one('maintenance.material.request', string="Material Request")


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.equipment'

    checklist_ids = fields.Many2many('equipment.checklist', string="Checklist")
    location_id = fields.Many2one('stock.location', string='Destination Location', copy=True)
    instrument_ids = fields.One2many('maintenance.instrument', 'equipment_id', string='Maintenance Instrument')

    def _prepare_requests_from_plan(self, maintenance_plan, next_maintenance_date):
        res = super()._prepare_request_from_plan(maintenance_plan, next_maintenance_date)
        res['checklist_ids'] = maintenance_plan.checklist_ids.ids
        return res

class MaintenanceInstrument(models.Model):
    _name = "maintenance.instrument"

    name = fields.Char('Instrument ID')
    description = fields.Char('Description')
    make_model = fields.Char('Make/Model')
    spec_range = fields.Char('Spec/Range')
    area_location = fields.Char('Area/Location')

    equipment_id = fields.Many2one('maintenance.equipment', string="Equipment")
    instrument_id = fields.Many2one('maintenance.instrument', string="Instrument ID")

    @api.onchange('instrument_id')
    def change_request(self):
        if self.instrument_id:
            self.name = self.instrument_id.name
            self.make_model = self.instrument_id.make_model
            self.description = self.instrument_id.description
            self.spec_range = self.instrument_id.spec_range
            self.area_location = self.instrument_id.area_location




class MaintenanceEquipment(models.Model):
    _inherit = 'maintenance.request'

    def _get_work_order(self):
        for rec in self:
            rec.work_order_count = self.env['work.order'].search_count([('maintenance_id', '=', rec.id)])

    checklist_ids = fields.Many2many('equipment.checklist', string="Checklist")
    work_order_count = fields.Integer("Work Orders", compute='_get_work_order')
    order_ids = fields.One2many('work.order', 'maintenance_id', string="Work Orders")
    is_changed = fields.Boolean(name="This field indicates, if the record has been changed in the time-based process")
    is_request_sent = fields.Boolean(name="Is Approval Request Sent?")
    enable_approval = fields.Boolean(name="Is Approval required?", compute='_get_approval_rule')
    can_approve = fields.Boolean(name="Can Approve?", compute='check_approve')
    instrument_id = fields.Many2one('maintenance.instrument', string="Instrument ID")
    enable_stage = fields.Boolean()
    maintenance_type = fields.Selection(selection_add=[('breakdown', 'Break Down')])

    def write(self, vals):
        if vals.get('stage_id', False):
            vals['is_request_sent'] = False
        return super(MaintenanceEquipment, self).write(vals)

    def check_approve(self):
        for rec in self:
            rec.can_approve = False
            next_stage_id = self.env['maintenance.stage'].search([('sequence', '>=', rec.stage_id.sequence + 1)],limit=1)
            if next_stage_id and self.env.user.id in next_stage_id.user_ids.ids:
                rec.can_approve = True

    @api.depends('stage_id')
    def _get_approval_rule(self):
        for rec in self:
            next_stage_id = self.env['maintenance.stage'].search([('sequence', '>=', rec.stage_id.sequence + 1)], limit=1)
            enable_approval = False
            if next_stage_id and next_stage_id.enable_approval:
                enable_approval = True
            rec.enable_approval = enable_approval

    @api.onchange('equipment_id')
    def onchange_equipment(self):
        if self.equipment_id:
            self.checklist_ids = self.equipment_id.checklist_ids.ids

    def action_create_work_order(self):
        WorkOrder = self.env['work.order']
        if self.maintenance_type == 'breakdown':
            WorkOrder.create({
                'name': self.name,
                'maintenance_id': self.id
            })
        else:
            if not self.checklist_ids:
                raise UserError(_("Checklist not found."))

            existing_checklist_ids = WorkOrder.search([('maintenance_id', '=', self.id)]).mapped('checklist_id')
            print("--------", existing_checklist_ids,"----existing_checklist_ids---\n")

            for checklist in self.checklist_ids.filtered(lambda x: x.id not in existing_checklist_ids.ids):
                WorkOrder.create({
                    'name': checklist.name,
                    'checklist_id': checklist.id,
                    'material_ids': [(6, 0, checklist.material_ids.ids)],
                    'maintenance_id': self.id
                })

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Work order has been created.'),
                'sticky': False,
                'next': {'type': 'ir.actions.act_window_close'},
            }
        }

    def action_open_work_order(self):
        return {
            'name': _('Work Orders'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'work.order',
            'context': {'create': False},
            'domain': [('maintenance_id', '=', self.id)]
        }

    def _cron_maintenance_alert(self):
        categ_ids = self.env['maintenance.equipment.category'].search([('alert_days', '>', 0)])
        for category in categ_ids:
            alert_day = fields.Datetime.now() + relativedelta(days=category.alert_days)
            from_date = alert_day.replace(hour=0, minute=0)
            to_date = alert_day.replace(hour=23, minute=59)
            request_ids = self.env['maintenance.request'].search([('category_id', '=', category.id), ('schedule_date', '>=', from_date), ('schedule_date', '<=', to_date), ('user_id', '!=', False)])
            for request in request_ids:
                subject = 'Maintenance Alert - %s' % request.name
                body = """
                        <div style="font-family: 'Lucica Grande', Ubuntu, Arial, Verdana, sans-serif; font-size: 12px; color: rgb(34, 34, 34); background-color: #FFF; ">
                            <div style="height:auto; text-align: center; font-size: 30px; color: #29408c;">
                                <strong style="border-bottom: 2px solid #29408c; padding-bottom: 1px; text-transform: uppercase;">
                                    Maintenance Alert
                                </strong>
                            </div>
                            <div style="text-align: left; font-size: 20px; margin-top: 10px; color: #29408c;">
                                <p>Dear %s,</p>
                                <p>Maintenance request has been schedule for %s on %s.</p>
                                <p>
                                    Thanks & Regards,<br/>
                                    Odoo Bot.
                                </p>
                            </div>
                        </div>
                              """ % (
                request.user_id.name, request.name, request.schedule_date)
                message_body = body
                template_data = {
                    'subject': subject,
                    'body_html': message_body,
                    'email_from': self.env.user.email,
                    'email_to': request.user_id.login,
                }
                template_id = self.env['mail.mail'].sudo().create(template_data)
                template_id.sudo().send()

    @api.onchange('stage_id')
    def onchange_state(self):
        if self.order_ids:
            is_completed = self.order_ids.filtered(lambda x: x.state not in ['done', 'cancel'])
            if is_completed and self.stage_id.done:
                raise UserError(_("Please complete all the work orders to close the request."))
        if self.stage_id.enable_approval:
            raise UserError(_("Raise approval request to move to next stage."
                              "\nYou cannot drag the record to next stage, please use form buttons."))

    def action_close_approve(self):
        next_stage_id = self.env['maintenance.stage'].search([('sequence', '>=', self.stage_id.sequence + 1)], limit=1)
        for user in next_stage_id.user_ids:
            mail_values = {
                'auto_delete': False,
                'author_id': self.env.user.partner_id.id,
                'email_from': (self.env.user.email_formatted or self.env.ref('base.user_root').email_formatted),
                'email_to': user.login,
                'body_html': """Dear Sir/Madam,<br/> 
                                You have been requested to approve the maintenance request: %s.<br/>
                                Thanks & Regards.""" % self.name,
                'subject': 'Approval request for Maintenance: %s' % self.name,
            }
        self.env['mail.mail'].sudo().create(mail_values).send()
        self.is_request_sent = True

    def action_close_request(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for record in self:
            # Build form view URL of the current record
            form_url = f"{base_url}/web#id={record.id}&model=maintenance.request&view_type=form"

            next_stage_id = self.env['maintenance.stage'].search(
                [('sequence', '>=', record.stage_id.sequence + 1)], limit=1
            )

            for user in next_stage_id.user_ids:
                mail_values = {
                    'auto_delete': False,
                    'author_id': self.env.user.partner_id.id,
                    'email_from': (self.env.user.email_formatted or self.env.ref('base.user_root').email_formatted),
                    'email_to': user.login,
                    'body_html': f"""
                        Dear Sir/Madam,<br/><br/> 
                        You have been requested to approve the maintenance request: 
                        <b>{record.name}</b>.<br/><br/>
                        <a href={form_url}" style="background-color: #1abc9c; padding: 7px; text-decoration: none; color: #fff; border-radius: 5px; font-size: 14px;" class="o_default_snippet_text">View Form</a>
                        <br/> <br/>
                        Thanks & Regards.
                    """,
                    'subject': f'Approval request for Maintenance: {record.name}',
                }
                self.env['mail.mail'].sudo().create(mail_values).send()

            record.is_request_sent = True

    def action_verified(self):
        officer_users = ''
        users = self.env['res.users'].search([])
        for user in users:
            if user.has_group('fnet_mrp.group_manufacturing_manager'):
                officer_users += user.login
                officer_users += ', '
        mail_values = {
            'auto_delete': False,
            'email_from': self.user_id.login,
            'email_to':officer_users,
            'body_html': """Dear Sir<br/> 
                          The maintenance for the equipment has been completed successfully.<br/>
                           Thanks & Regards.""",
            'subject': 'Maintenance Completed: Production Can Start %s' % self.name,
        }
        self.env['mail.mail'].sudo().create(mail_values).send()



    def action_close_reject(self):
        mail_values = {
            'auto_delete': False,
            'author_id': self.env.user.partner_id.id,
            'email_from': (self.env.user.email_formatted or self.env.ref('base.user_root').email_formatted),
            'email_to': self.user_id.login,
            'body_html': """Dear Sir/Madam,<br/> 
                               Your maintenance closing request: %s have been rejected.<br/>
                               Thanks & Regards.""" % self.name,
            'subject': 'Maintenance closing request rejected: %s' % self.name,
        }
        self.env['mail.mail'].sudo().create(mail_values).send()
        self.is_request_sent = False





class MaintenanceStage(models.Model):
    _inherit = 'maintenance.stage'

    enable_approval = fields.Boolean("Enable Approval")
    user_ids = fields.Many2many('res.users', string="Responsible")


class MaintenancePlan(models.Model):
    _inherit = "maintenance.plan"

    checklist_ids = fields.Many2many('equipment.checklist', string="Checklist")
    instrument_id = fields.Many2one('maintenance.instrument', string="Instrument ID")

    def change_start_date(self):
        records = self.search([])
        for record in records:
            next_maintenance_date = record.next_maintenance_date
            start_maintenance = next_maintenance_date - relativedelta(years=1)
            start_maintenance_date = start_maintenance + relativedelta(days=1)
            record.write({
                'start_maintenance_date': start_maintenance_date
            })


class EquipmentCategory(models.Model):
    _inherit = "maintenance.equipment.category"

    alert_days = fields.Integer("Number of days", default=1, help="No of days before the alert needs to sent. Set 0 to disable.")


class SaleSubscription(models.Model):
    _inherit = 'sales.subscription'

    is_maintenance = fields.Boolean("Is Maintenance?")




