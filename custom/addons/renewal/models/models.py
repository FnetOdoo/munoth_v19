# -*- coding: utf-8 -*-
from lxml.html import find_rel_links
from odoo import models, fields, api ,_
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from datetime import timedelta, date, datetime

class Renewal(models.Model):
    _name = 'renewal.renewal'
    _order = "id desc"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'renewal.renewal'

    name = fields.Char()
    vendor_id = fields.Many2one('res.partner','Vendor')
    agency = fields.Char('Agency')
    employee_id = fields.Many2one('hr.employee','Employee')
    company_id = fields.Many2one("res.company", default=lambda self: self.env.user.company_id)
    attachment = fields.Many2many('ir.attachment', string='Attachment', store=True, tracking=True,
                                        help="Attach the Document")
    description = fields.Text()
    file = fields.Char()
    department = fields.Char('Department')
    nature_id = fields.Many2one('nature.config','Nature')
    renewal_id = fields.Many2one('renewal.template','Renewal Template')
    from_date = fields.Date('From Date')
    to_date = fields.Date('To Date')
    check_date = fields.Date(related="to_date")
    amount = fields.Monetary(string="Amount", currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', string="Currency", required=True,
                                  default=lambda self: self.env.company.currency_id)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('approved', 'Approved'),
        ('to_renewal', 'To Renewal'),
        ('expired', 'Expired'),
    ], default='draft', tracking=True)
    renewal = fields.Boolean()
    renewal_history_ids = fields.One2many('renewal.history','main_id')
    show_renewal_button = fields.Boolean(compute='_compute_show_renewal_button')
    show_vendor = fields.Boolean(compute='_compute_show_vendor_button')
    details_of_act = fields.Char('Details of act')
    retention_period = fields.Char('Retention Period')
    form = fields.Char("Form")
    remarks = fields.Char('Remarks')

    @api.depends('state', 'employee_id.parent_id.user_id')
    def _compute_show_renewal_button(self):
        for record in self:
            print(record.employee_id.parent_id.user_id.id,"///",record.env.user.id)
            if record.employee_id.parent_id.user_id.id == record.env.user.id and record.state in 'submit':
                record.show_renewal_button = True
            else:
                record.show_renewal_button = False
    @api.depends('state', 'employee_id.user_id')
    def _compute_show_vendor_button(self):
        for record in self:
            if record.employee_id.user_id.id == record.env.user.id and record.state in 'draft':
                record.show_vendor = True
            else:
                record.show_vendor = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _("New"):
                vals['name'] = self.env['ir.sequence'].next_by_code('renewal.seq') or _("New")
        return super().create(vals_list)

    def action_renewal(self):
        self.renewal_id = False
        self.from_date = False
        self.attachment = False
        self.state = 'draft'
        self.renewal = True

    @api.onchange('employee_id')
    def onchange_employee_id(self):
        if self.employee_id:
            self.department = self.employee_id.department_id.name
        else:
            self.department = ""

    @api.constrains('from_date')
    def constrains_from_date(self):
        if self.from_date and not self.renewal_id:
            raise ValidationError("Please Enter Renewal Template")
        else:
            pass

    @api.onchange('from_date')
    def onchange_no_of_renewal(self):
        if self.renewal_id:
            if self.from_date and self.renewal_id.recurring_rule_type == 'daily':
                delta = relativedelta(days=self.renewal_id.recurring_interval)
                self.to_date = self.from_date + delta - timedelta(days=1)

            elif self.from_date and self.renewal_id.recurring_rule_type == 'weekly':
                delta = relativedelta(weeks=self.renewal_id.recurring_interval)
                self.to_date = self.from_date + delta - timedelta(days=1)

            elif self.from_date and self.renewal_id.recurring_rule_type == 'monthly':
                delta = relativedelta(months=self.renewal_id.recurring_interval)
                self.to_date = self.from_date + delta - timedelta(days=1)

            elif self.from_date and self.renewal_id.recurring_rule_type == 'yearly':
                delta = relativedelta(years=self.renewal_id.recurring_interval)
                self.to_date = self.from_date + delta - timedelta(days=1)
        else:
            print("No renewal_id found or from_date is missing.")
            # else:
            #     self.to_date = False

    def action_submit(self):
        for record in self:
            if not record.renewal_id:
                raise ValidationError("Please select a Renewal Template.")

            if not record.employee_id or not record.employee_id.parent_id:
                raise ValidationError("Employee or their manager is missing.")

            if not record.employee_id.parent_id.work_email:
                raise ValidationError("Manager's email is not defined.")

            if not record.description:
                raise ValidationError("Please enter a description.")

            if not self.from_date:
                raise ValidationError("Please Select a From Date.")

            manager = record.employee_id.parent_id
            employee = record.employee_id
            mail_body = f"""
                 <table border="0" cellpadding="0" cellspacing="0" width="100%"
                        style="background-color:#ffffff; font-family: Helvetica, Arial, sans-serif; font-size:14px; color:#2d2d2d;">

                     <!-- Header Banner -->
                     <tr>
                         <td style="background-color:#003366; padding:24px 32px;">
                             <h1 style="margin:0; color:#ffffff; font-size:20px; font-weight:600; letter-spacing:0.5px;">
                                 Renewal Approval Request
                             </h1>
                         </td>
                     </tr>

                     <!-- Body -->
                     <tr>
                         <td style="padding:32px;">

                             <p style="margin:0 0 16px 0;">Dear <strong>{manager.name}</strong>,</p>

                             <p style="margin:0 0 16px 0; line-height:1.6;">
                                 We would like to bring to your attention that a renewal request has been submitted
                                 and is currently pending your approval. Please find the details below.
                             </p>

                             <!-- Info Box -->
                             <table border="0" cellpadding="0" cellspacing="0" width="100%"
                                    style="background-color:#f4f7fb; border-left:4px solid #003366;
                                           border-radius:4px; margin:24px 0;">
                                 <tr>
                                     <td style="padding:16px 20px;">
                                         <table border="0" cellpadding="6" cellspacing="0" width="100%">
                                             <tr>
                                                 <td style="color:#666666; font-size:13px; width:160px;">Renewal Description</td>
                                                 <td style="color:#2d2d2d; font-weight:600;">{record.description}</td>
                                             </tr>
                                             <tr>
                                                 <td style="color:#666666; font-size:13px;">Requested By</td>
                                                 <td style="color:#2d2d2d; font-weight:600;">{employee.name}</td>
                                             </tr>
                                             <tr>
                                                 <td style="color:#666666; font-size:13px;">Reference</td>
                                                 <td style="color:#2d2d2d; font-weight:600;">{record.name}</td>
                                             </tr>
                                         </table>
                                     </td>
                                 </tr>
                             </table>

                             <!-- View Button -->
                             <p style="margin:24px 0;">
                                 <a href="{record.get_base_url()}/web#id={record.id}&model=renewal.renewal&view_type=form"
                                    style="display: inline-block; background-color: #003366; color: #ffffff;
                                           text-decoration: none; font-size: 13px; font-weight: 600;
                                           padding: 10px 24px; border-radius: 6px;">
                                     View Renewal →
                                 </a>
                             </p>
                             <p style="margin:24px 0 4px 0; line-height:1.6;">Thanks & regards,</p>
                             <p style="margin:0; font-weight:600;">{employee.name}</p>
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
                'subject': f'Renewal Approval Request - {record.name}',
                'email_to': manager.work_email,
                'email_from': employee.work_email,
                'body_html': mail_body,
            }

            mail = self.env['mail.mail'].sudo().create(mail_values)
            mail.sudo().send()
            record.state = 'submit'

    def action_approved(self):
        if self.from_date:
            self.state = 'approved'
            self.renewal_history_ids.create({
                'main_id': self.id,
                'vendor_id': self.vendor_id.id,
                'agency': self.agency,
                'employee_id': self.employee_id.id,
                'renewal_id': self.renewal_id.id,
                'file': self.file,
                'attachment': self.attachment.ids,
                'from_date': self.from_date,
                'amount': self.amount,
                'to_date': self.to_date,
            })
            self._send_approved_email()
        else:
            raise ValidationError("Please Enter From Date")

    def _send_approved_email(self):
        record = self
        employee = record.employee_id

        mail_body = f"""
        <table border="0" cellpadding="0" cellspacing="0" width="100%"
               style="background-color:#ffffff; font-family: Helvetica, Arial, sans-serif; font-size:14px; color:#2d2d2d;">

            <!-- Header Banner -->
            <tr>
                <td style="background-color:#1a6b3a; padding:24px 32px;">
                    <h1 style="margin:0; color:#ffffff; font-size:20px; font-weight:600; letter-spacing:0.5px;">
                        Renewal Approved
                    </h1>
                </td>
            </tr>

            <!-- Body -->
            <tr>
                <td style="padding:32px;">

                    <p style="margin:0 0 16px 0;">Dear <strong>{employee.name}</strong>,</p>

                    <p style="margin:0 0 16px 0; line-height:1.6;">
                        We are pleased to inform you that your renewal request has been
                        <strong style="color:#1a6b3a;">approved</strong>. Please find the details below.
                    </p>

                    <!-- Info Box -->
                    <table border="0" cellpadding="0" cellspacing="0" width="100%"
                           style="background-color:#f4fbf6; border-left:4px solid #1a6b3a;
                                  border-radius:4px; margin:24px 0;">
                        <tr>
                            <td style="padding:16px 20px;">
                                <table border="0" cellpadding="6" cellspacing="0" width="100%">
                                    <tr>
                                        <td style="color:#666666; font-size:13px; width:160px;">Reference</td>
                                        <td style="color:#2d2d2d; font-weight:600;">{record.name}</td>
                                    </tr>
                                    <tr>
                                        <td style="color:#666666; font-size:13px;">Description</td>
                                        <td style="color:#2d2d2d; font-weight:600;">{record.description}</td>
                                    </tr>
                                    <tr>
                                        <td style="color:#666666; font-size:13px;">From Date</td>
                                        <td style="color:#2d2d2d; font-weight:600;">{record.from_date}</td>
                                    </tr>
                                    <tr>
                                        <td style="color:#666666; font-size:13px;">To Date</td>
                                        <td style="color:#2d2d2d; font-weight:600;">{record.to_date}</td>
                                    </tr>
                                    <tr>
                                        <td style="color:#666666; font-size:13px;">Amount</td>
                                        <td style="color:#2d2d2d; font-weight:600;">{record.amount}</td>
                                    </tr>
                                    <tr>
                                        <td style="color:#666666; font-size:13px;">Status</td>
                                        <td style="color:#1a6b3a; font-weight:700;">Approved</td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>

                    <!-- View Button -->
                    <p style="margin:24px 0;">
                        <a href="{record.get_base_url()}/web#id={record.id}&model=renewal.renewal&view_type=form"
                           style="display: inline-block; background-color: #1a6b3a; color: #ffffff;
                                  text-decoration: none; font-size: 13px; font-weight: 600;
                                  padding: 10px 24px; border-radius: 6px;">
                            View Renewal →
                        </a>
                    </p>
                    <p style="margin:24px 0 4px 0;">Thanks & regards,</p>
                    <p style="margin:0; font-weight:600;">{employee.parent_id.name or ''}</p>
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
            'subject': f'Renewal Approved - {record.name}',
            'email_to': employee.work_email,
            'email_from': employee.parent_id.work_email or self.env.user.email,
            'body_html': mail_body,
        }

        self.env['mail.mail'].create(mail_values).send()

    @api.model
    def check_renewal_cron(self):
        records = self.env['renewal.renewal'].search([])
        today = fields.Date.today()

        for rec in records:
            # Ensure rec.to_date is a valid date
            if rec.to_date:
                # 1. Set to 'to_renewal' 30 days before to_date
                if today >= rec.to_date - timedelta(days=30):
                    rec.write({'state': 'to_renewal'})

                # 2. Set to 'expired' if today is past to_date
                if today > rec.to_date:
                    rec.write({'state': 'expired'})

                # 3. Send alert email if auto_close_limit matches
                if rec.renewal_id and rec.renewal_id.auto_close_limit:
                    notify_date = rec.to_date - timedelta(days=rec.renewal_id.auto_close_limit)
                    if notify_date == today:
                        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                        base_url += f"/web#id={rec.id}&view_type=form&model={rec._name}&cids=1"
                        days_left = (rec.to_date - today).days

                        header_color = '#5b6e91'  # Mild Steel Blue
                        status_label = 'Reminder'
                        urgency_msg = 'This is a reminder that your renewal is approaching its expiry date. Please take the necessary action.'

                        mail_body = f"""
                        <table border="0" cellpadding="0" cellspacing="0" width="100%"
                               style="background-color:#ffffff; font-family: Helvetica, Arial, sans-serif; font-size:14px; color:#2d2d2d;">

                            <!-- Header Banner -->
                            <tr>
                                <td style="background-color:{header_color}; padding:24px 32px;">
                                    <h1 style="margin:0; color:#ffffff; font-size:20px; font-weight:600; letter-spacing:0.5px;">
                                        Renewal Expiry Alert
                                    </h1>
                                </td>
                            </tr>

                            <!-- Body -->
                            <tr>
                                <td style="padding:32px;">

                                    <p style="margin:0 0 16px 0;">Dear <strong>{rec.employee_id.name}</strong>,</p>

                                    <p style="margin:0 0 16px 0; line-height:1.6;">
                                        {urgency_msg}
                                    </p>

                                    <!-- Info Box -->
                                    <table border="0" cellpadding="0" cellspacing="0" width="100%"
                                           style="background-color:#fafafa; border-left:4px solid {header_color};
                                                  border-radius:4px; margin:24px 0;">
                                        <tr>
                                            <td style="padding:16px 20px;">
                                                <table border="0" cellpadding="6" cellspacing="0" width="100%">
                                                    <tr>
                                                        <td style="color:#666666; font-size:13px; width:160px;">Reference</td>
                                                        <td style="color:#2d2d2d; font-weight:600;">{rec.name}</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="color:#666666; font-size:13px;">Description</td>
                                                        <td style="color:#2d2d2d; font-weight:600;">{rec.description}</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="color:#666666; font-size:13px;">Expiry Date</td>
                                                        <td style="color:#2d2d2d; font-weight:600;">{rec.to_date}</td>
                                                    </tr>
                                                    <tr>
                                                        <td style="color:#666666; font-size:13px;">Days Remaining</td>
                                                        <td style="color:{header_color}; font-weight:700;">{days_left} days</td>
                                                    </tr>
                                                </table>
                                            </td>
                                        </tr>
                                    </table>

                                    <!-- View Button -->
                                    <p style="margin:24px 0;">
                                        <a href="{base_url}"
                                           style="display: inline-block; background-color:{header_color}; color:#ffffff;
                                                  text-decoration:none; font-size:13px; font-weight:600;
                                                  padding:10px 24px; border-radius:6px;">
                                            View Renewal →
                                        </a>
                                    </p>

                                    <p style="margin:0 0 16px 0; line-height:1.6;">
                                        Please log in to the system and take the necessary action at your earliest convenience.
                                    </p>

                                    <p style="margin:24px 0 4px 0;">Warm regards,</p>
                                    <p style="margin:0; font-weight:600;">Renewal Management System</p>

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
                            'subject': f"Renewal Expire Alert - {rec.name}",
                            'body_html': mail_body,
                            'email_to': rec.employee_id.work_email,
                            'email_from': self.env.user.email,
                        }
                        mail = self.env['mail.mail'].sudo().create(mail_values)
                        mail.sudo().send()

class RenewalDepartmentConfig(models.Model):
    _name = "renewal.department.config"
    _description = "Hr Config"

    name = fields.Char("name")

class NativeConfig(models.Model):
    _name = 'nature.config'
    _order = "id desc"

    name = fields.Char("Name")

class RenewalTemplate(models.Model):
    _name = "renewal.template"
    _description = "Renewal Template"
    _inherit = "mail.thread"
    _order = "id desc"
    _check_company_auto = True

    active = fields.Boolean(default=True)
    name = fields.Char(required=True)
    no_of_renewal = fields.Integer()
    code = fields.Char(help="Code is added automatically in the display name of every subscription.")
    recurring_rule_type = fields.Selection([('daily', 'Days'), ('weekly', 'Weeks'),
                                            ('monthly', 'Months'), ('yearly', 'Years'), ],
                                           string='Recurrence', required=True,
                                           help="Invoice automatically repeat at specified interval",
                                           default='monthly', tracking=True)
    recurring_interval = fields.Integer(string="Invoicing Period", help="Repeat every (Days/Week/Month/Year)", required=True, default=1, tracking=True)
    recurring_rule_count = fields.Integer(string="End After", default=1)
    auto_close_limit = fields.Integer(
        string="Automatic Closing", default=15,
        help="If the chosen payment method has failed to renew the subscription after this time, "
             "the subscription is automatically closed.")
    company_id = fields.Many2one('res.company', index=True)

    @api.constrains('recurring_interval')
    def _check_recurring_interval(self):
        for template in self:
            if template.recurring_interval <= 0:
                raise ValidationError(_("The recurring interval must be positive"))

class RenewalHistory(models.Model):
    _name = "renewal.history"
    _description = "Renewal History"

    main_id = fields.Many2one('renewal.renewal',"Main ID")
    vendor_id = fields.Many2one('res.partner',"Vendor")
    agency = fields.Char('Agency')
    employee_id = fields.Many2one('hr.employee','Employee')
    file = fields.Char()
    attachment = fields.Many2many('ir.attachment', string='Attachment', store=True, tracking=True,
                                  help="Attach the Document")
    renewal_id = fields.Many2one('renewal.template', 'Renewal Template')
    from_date = fields.Date("From Date")
    to_date = fields.Date("To Date")
    currency_id = fields.Many2one('res.currency', string="Currency", required=True,
                                  default=lambda self: self.env.company.currency_id)
    amount = fields.Monetary(string="Amount", currency_field='currency_id')