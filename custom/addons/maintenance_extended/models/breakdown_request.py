from odoo import models, api, fields, _
from odoo.exceptions import ValidationError
from markupsafe import Markup

class BreakdownRequest(models.Model):
    _name = 'breakdown.request'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = 'Breakdown Request'
    _rec_name = 'name'
    _order = 'id desc'
    
    name = fields.Char(string='Ticket No', default=lambda self: _('New'),
                            copy=False, readonly=True)
    is_breakdown_request = fields.Boolean()
    machine_id = fields.Many2one('maintenance.equipment', string='Machine')
    shift_id = fields.Many2one('mrp.shift', string='Shift')
    problem_category = fields.Selection([('breakdown', 'Breakdown')],
                                        string='Problem Category', default='breakdown')
    nature_of_problem = fields.Char()
    priority = fields.Selection([('0', 'Very Low'), ('1', 'Low'),
                                 ('2', 'Normal'), ('3', 'High')], string='Priority')
    requested_user_id = fields.Many2one('res.users', string='Requested By')
    requested_time = fields.Datetime(string='Requested Time',default=fields.Datetime.now)
    state = fields.Selection([('draft', 'Draft'), ('request', 'Requested'),('done', 'Closed')],default='draft', string='Status', tracking=True)

    # Filled by the maintenance user
    attended_by = fields.Many2one('res.users', string='Attended By')
    root_cause = fields.Text()
    corrective = fields.Char('Corrective action')
    start_date = fields.Datetime()
    end_date = fields.Datetime()
    duration = fields.Float(string='Down Time',compute='_compute_duration', store=True)
    solution_permanent = fields.Selection([('yes', 'Yes'), ('no', 'No')],
                                          default='yes', string='Permanent Solution',
                                          tracking=True)
    remarks = fields.Text()
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company, required=True)
    problem_description = fields.Text()

    @api.depends('start_date', 'end_date')
    def _compute_duration(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date >= rec.start_date:
                rec.duration = (rec.end_date - rec.start_date).total_seconds() / 60.0
            else:
                rec.duration = 0.0

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for rec in self:
            if rec.start_date and rec.end_date and rec.end_date < rec.start_date:
                raise ValidationError(_("End Date cannot be earlier than Start Date."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'breakdown.request') or _('New')
        return super().create(vals_list)

    def action_request(self):
        for record in self:
            if record.state != 'draft':
                continue
            record.state = 'request'
            record._notify_equipment_managers()

    def _notify_equipment_managers(self):
        self.ensure_one()

        # Recipients: all users in the Equipment Manager group
        group = self.env.ref('maintenance.group_equipment_manager',
                             raise_if_not_found=False)
        if not group:
            raise ValidationError(_("Equipment Manager group is not configured."))

        recipient_emails = group.user_ids.filtered(
            lambda u: u.email).mapped('email')
        if not recipient_emails:
            raise ValidationError(_("No Equipment Manager has an email address configured."))

        requester = self.requested_user_id
        machine = self.machine_id.display_name or 'N/A'
        shift = self.shift_id.display_name or 'N/A'
        req_time = self.requested_time and fields.Datetime.to_string(self.requested_time) or 'N/A'
        raw_desc = self.problem_description or 'N/A'
        problem_desc = Markup('<br/>').join(raw_desc.split('\n'))
        priority_label = dict(self._fields['priority'].selection).get(self.priority) or 'N/A'

        mail_body = f"""
            <table border="0" cellpadding="0" cellspacing="0" width="100%"
                   style="background-color:#ffffff; font-family: Helvetica, Arial, sans-serif; font-size:14px; color:#2d2d2d;">

                <!-- Header Banner -->
                <tr>
                    <td style="background-color:#8B0000; padding:24px 32px;">
                        <h1 style="margin:0; color:#ffffff; font-size:20px; font-weight:600; letter-spacing:0.5px;">
                            Breakdown Request
                        </h1>
                    </td>
                </tr>

                <!-- Body -->
                <tr>
                    <td style="padding:32px;">

                        <p style="margin:0 0 16px 0;">Dear Team,</p>

                        <p style="margin:0 0 16px 0; line-height:1.6;">
                            A breakdown request has been raised and requires attention.
                            Please find the details below.
                        </p>

                        <!-- Info Box -->
                        <table border="0" cellpadding="0" cellspacing="0" width="100%"
                               style="background-color:#fdf3f3; border-left:4px solid #8B0000;
                                      border-radius:4px; margin:24px 0;">
                            <tr>
                                <td style="padding:16px 20px;">
                                   <table border="0" cellpadding="6" cellspacing="0" width="100%">
                                        <tr>
                                            <td style="color:#666666; font-size:13px; width:160px;">Machine</td>
                                            <td style="color:#2d2d2d; font-weight:600;">{machine}</td>
                                        </tr>
                                        <tr>
                                            <td style="color:#666666; font-size:13px; vertical-align:top;">Problem Description</td>
                                            <td style="color:#2d2d2d; font-weight:600;">{problem_desc}</td>
                                        </tr>
                                        <tr>
                                            <td style="color:#666666; font-size:13px;">Priority</td>
                                            <td style="color:#2d2d2d; font-weight:600;">{priority_label}</td>
                                        </tr>
                                        <tr>
                                            <td style="color:#666666; font-size:13px;">Requested By</td>
                                            <td style="color:#2d2d2d; font-weight:600;">{requester.name or ''}</td>
                                        </tr>
                                        <tr>
                                            <td style="color:#666666; font-size:13px;">Requested Time</td>
                                            <td style="color:#2d2d2d; font-weight:600;">{req_time}</td>
                                        </tr>
                                        <tr>
                                            <td style="color:#666666; font-size:13px;">Shift</td>
                                            <td style="color:#2d2d2d; font-weight:600;">{shift}</td>
                                        </tr>
                                    </table>
                                </td>
                            </tr>
                        </table>

                        <!-- View Button -->
                        <p style="margin:24px 0;">
                            <a href="{self.get_base_url()}/web#id={self.id}&model=breakdown.request&view_type=form"
                               style="display: inline-block; background-color: #8B0000; color: #ffffff;
                                      text-decoration: none; font-size: 13px; font-weight: 600;
                                      padding: 10px 24px; border-radius: 6px;">
                                View Breakdown Request →
                            </a>
                        </p>

                        <p style="margin:24px 0 4px 0; line-height:1.6;">Thanks &amp; regards,</p>
                        <p style="margin:0; font-weight:600;">{requester.name or ''}</p>
                    </td>
                </tr>

                <!-- Footer -->
                <tr>
                    <td style="background-color:#f0f0f0; padding:16px 32px; border-top:1px solid #dddddd;">
                        <p style="margin:0; font-size:12px; color:#999999; text-align:center;">
                            This is an automated notification.
                        </p>
                    </td>
                </tr>

            </table>
            """

        mail_values = {
            'subject': f'Breakdown Request - {self.name or ""}',
            'email_to': ','.join(recipient_emails),
            'email_from': (requester.email or self.env.company.email or ''),
            'body_html': mail_body,
        }

        mail = self.env['mail.mail'].sudo().create(mail_values)
        mail.sudo().send()


    def action_done(self):
        self.write({'state': 'done'})

