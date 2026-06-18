# -*- coding: utf-8 -*-
# Part of Kanak Infosystems LLP. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from lxml import etree


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    sale_order_approval_rule_ids = fields.One2many('sale.order.approval.rules', 'sale_order', string='Sale Order Approval Lines', readonly=True, copy=False)
    sale_order_approval_history = fields.One2many('sale.order.approval.history', 'sale_order', string='Sale Order Approval History', readonly=True, copy=False)
    approve_button = fields.Boolean(compute='_compute_approve_button', string='Approve Button ?', search='_search_to_approve_orders', copy=False)
    ready_for_so = fields.Boolean(compute='_compute_ready_for_so', string='Ready For SO ?', copy=False)
    send_for_approval = fields.Boolean(string="Send For Approval", copy=False)
    is_rejected = fields.Boolean(string='Rejected ?', copy=False)
    user_ids = fields.Many2many('res.users', 'sale_user_rel', 'sale_id', 'uid', 'Request Users', compute='_compute_user')

    sale_order_approval_rule_id = fields.Many2one('sale.order.approval.rule', related='company_id.sale_order_approval_rule_id', string='Sale Order Approval Rules')
    sale_order_approval = fields.Boolean(related='company_id.sale_order_approval', string='Sale Order Approval By Rule')
    send_approve_process = fields.Boolean()
    dummy_compute = fields.Float("Dummy compute", compute='compute_rules_for_amount')
    amount_in_company_currency = fields.Float("Amount in Company Currency", compute="_currency_conversion")
    company_currency = fields.Many2one('res.currency', 'Company Currency', related="company_id.currency_id")

    @api.depends('amount_total', 'currency_id', 'company_id', 'date_order')
    def _currency_conversion(self):
        for rec in self:
            if rec.currency_id and rec.company_id.currency_id:
                rec.amount_in_company_currency = rec.currency_id._convert(
                    rec.amount_total,
                    rec.company_id.currency_id,
                    rec.company_id,
                    rec.date_order or fields.Date.today(),
                )
            else:
                rec.amount_in_company_currency = rec.amount_total

    def get_user_emails(self):
        emails = self.user_ids.mapped('login')
        return emails

    @api.depends('amount_total')
    def compute_rules_for_amount(self):
        for rec in self:
            # ONLY set the dummy float — never write/create inside a compute
            rec.dummy_compute = 0.0

    @api.onchange('amount_total', 'order_line')
    def _onchange_create_approval_rules(self):
        for rec in self:
            if not rec.sale_order_approval_rule_ids:
                values = rec._get_data_sale_order_approval_rule_ids()
                if values:
                    rec.send_approve_process = True
                    rule_commands = []
                    for v in values:
                        v.update({'state': 'draft'})
                        rule_commands.append((0, 0, v))
                    rec.sale_order_approval_rule_ids = rule_commands
    @api.depends('sale_order_approval_rule_ids', 'sale_order_approval_rule_ids.approval_role')
    def _compute_user(self):
        for order in self:
            all_users = self.env['res.users']
            for approve_rule in order.sale_order_approval_rule_ids:
                all_users |= approve_rule.users
            order.user_ids = all_users

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(SaleOrder, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = elist.XML(res['arch'])
        if view_type in ['list', 'form'] and (self.user_has_groups('sales_team.group_sale_salesman') and not self.user_has_groups('sales_team.group_sale_manager')):
            if self._context.get('sale_approve'):
                for node in doc.xpath("//list"):
                    node.set('create', 'false')
                    node.set('edit', 'false')
                for node_form in doc.xpath("//form"):
                    node_form.set('create', 'false')
                    node_form.set('edit', 'false')
        res['arch'] = elist.tostring(doc)
        return res

    def _search_to_approve_orders(self, operator, value):
        res = []
        for i in self.search([('sale_order_approval_rule_ids', '!=', False)]):
            approval_lines = i.sale_order_approval_rule_ids.filtered(lambda b: not b.is_approved).sorted(key=lambda r: r.sequence)
            if approval_lines:
                same_seq_lines = approval_lines.filtered(lambda b: b.sequence == approval_lines[0].sequence)
                if self.env.user in same_seq_lines.mapped('users') and i.send_for_approval:
                    res.append(i.id)
        return [('id', 'in', res)]

    @api.depends('sale_order_approval_rule_ids.is_approved')
    def _compute_approve_button(self):
        for rec in self:
            if rec.company_id.sale_order_approval and rec.company_id.sale_order_approval_rule_id:
                approval_lines = rec.sale_order_approval_rule_ids.filtered(lambda b: not b.is_approved).sorted(key=lambda r: r.sequence)
                if approval_lines:
                    same_seq_lines = approval_lines.filtered(lambda b: b.sequence == approval_lines[0].sequence)
                    if same_seq_lines:
                        if self.env.user in same_seq_lines.mapped('users') and rec.send_for_approval:
                            rec.approve_button = True
                        else:
                            rec.approve_button = False
                    else:
                        rec.approve_button = False
                else:
                    rec.approve_button = False
            else:
                rec.approve_button = False

    def _compute_ready_for_so(self):
        for rec in self:
            if rec.company_id.sale_order_approval and rec.company_id.sale_order_approval_rule_id:
                values = rec._get_data_sale_order_approval_rule_ids()
                if values:
                    if rec.sale_order_approval_rule_ids and all([i.is_approved for i in rec.sale_order_approval_rule_ids]):
                        rec.ready_for_so = True
                    else:
                        rec.ready_for_so = False
                else:
                    rec.ready_for_so = True
            else:
                rec.ready_for_so = True

    def action_button_approve(self):
        for rec in self:
            if rec.sale_order_approval_rule_ids:
                rules = rec.sale_order_approval_rule_ids.filtered(
                    lambda b: self.env.user in b.users
                )
                rules.write({
                    'is_approved': True,
                    'date': fields.Datetime.now(),
                    'state': 'approve',
                    'user_id': self.env.user.id,
                })

                msg = _("Quotation has been approved by %s.") % self.env.user.name
                self.message_post(body=msg, subtype_xmlid='mail.mt_comment')

                self.env['sale.order.approval.history'].create({
                    'sale_order': rec.id,
                    'user': self.env.user.id,
                    'date': fields.Datetime.now(),
                    'state': 'approved',
                })

                company = rec.company_id or self.env.company
                body_html = """
                <table border="0" cellpadding="0" cellspacing="0" width="100%"
                       style="font-family: Arial, Helvetica, sans-serif; background-color: #f4f6fa; padding: 24px;">
                    <tr>
                        <td align="center">
                            <table border="0" cellpadding="0" cellspacing="0" width="100%"
                                   style="background: #ffffff; border-radius: 8px; overflow: hidden; border: 1px solid #dde2ed;">

                                <!-- Header -->
                                <tr>
                                    <td style="background: #1a4d2e; padding: 32px 40px; text-align: center;">
                                        <h1 style="color: #ffffff; font-size: 22px; font-weight: 700;
                                                   letter-spacing: 0.5px; margin: 0;">
                                            Quotation Approved
                                        </h1>
                                    </td>
                                </tr>

                                <!-- Body -->
                                <tr>
                                    <td style="padding: 32px 40px;">

                                        <!-- General Message -->
                                        <p style="font-size: 16px; color: #1a3a22; font-weight: 600; margin: 0 0 12px 0;">
                                            Hello {approver_name},
                                        </p>
                                        <p style="font-size: 14px; color: #4a5568; line-height: 1.7; margin: 0 0 24px 0;">
                                            We are pleased to inform you that the quotation has been
                                            <strong style="color: #1a4d2e;">successfully approved</strong>.
                                            Please review the details below and proceed accordingly.
                                        </p>

                                        <!-- Info Card -->
                                        <table border="0" cellpadding="0" cellspacing="0" width="100%"
                                               style="background: #f0faf4; border: 1px solid #b6dfc5;
                                                      border-radius: 6px; margin-bottom: 24px;">
                                            <tr>
                                                <td style="padding: 20px 24px;">
                                                    <table border="0" cellpadding="8" cellspacing="0" width="100%">

                                                        <tr>
                                                            <td style="font-size: 11px; font-weight: 700; letter-spacing: 1px;
                                                                       color: #5a8a6a; text-transform: uppercase; width: 140px;">
                                                                Quotation No.
                                                            </td>
                                                            <td style="font-size: 14px; color: #1a4d2e; font-weight: 600;">
                                                                {order_name}
                                                            </td>
                                                        </tr>

                                                        <tr>
                                                            <td style="font-size: 11px; font-weight: 700; letter-spacing: 1px;
                                                                       color: #5a8a6a; text-transform: uppercase;">
                                                                Customer
                                                            </td>
                                                            <td style="font-size: 14px; color: #1a4d2e; font-weight: 600;">
                                                                {customer_name}
                                                            </td>
                                                        </tr>

                                                        <tr>
                                                            <td style="font-size: 11px; font-weight: 700; letter-spacing: 1px;
                                                                       color: #5a8a6a; text-transform: uppercase;">
                                                                Approved By
                                                            </td>
                                                            <td style="font-size: 14px; color: #1a4d2e; font-weight: 600;">
                                                                {approved_by}
                                                            </td>
                                                        </tr>

                                                        <tr>
                                                            <td style="font-size: 11px; font-weight: 700; letter-spacing: 1px;
                                                                       color: #5a8a6a; text-transform: uppercase;">
                                                                Date
                                                            </td>
                                                            <td style="font-size: 14px; color: #1a4d2e; font-weight: 600;">
                                                                {order_date}
                                                            </td>
                                                        </tr>

                                                        <tr>
                                                            <td style="font-size: 11px; font-weight: 700; letter-spacing: 1px;
                                                                       color: #5a8a6a; text-transform: uppercase;">
                                                                Status
                                                            </td>
                                                            <td>
                                                                <span style="display: inline-block; background: #eaf3de;
                                                                             color: #27500a; border: 1px solid #97c459;
                                                                             border-radius: 4px; font-size: 11px;
                                                                             font-weight: 700; padding: 3px 10px;
                                                                             letter-spacing: 0.5px; text-transform: uppercase;">
                                                                    Approved
                                                                </span>
                                                            </td>
                                                        </tr>

                                                    </table>
                                                </td>
                                            </tr>
                                        </table>

                                        <!-- View Button -->
                                        <p style="margin: 24px 0;">
                                            <a href="{base_url}/web#id={order_id}&model=sale.order&view_type=form"
                                               style="display: inline-block; background-color: #16a34a; color: #ffffff;
                                                      text-decoration: none; font-size: 13px; font-weight: 600;
                                                      padding: 10px 24px; border-radius: 6px; letter-spacing: 0.02em;">
                                                View Quotation &#8594;
                                            </a>
                                        </p>

                                        <!-- Thanks & Regards -->
                                        <p style="margin: 24px 0 4px 0; font-size: 14px; color: #4a5568;">
                                            Thanks &amp; regards,
                                        </p>
                                        <p style="margin: 0; font-size: 14px; font-weight: 600; color: #1a3a22;">
                                            {sender_name}
                                        </p>

                                        <hr style="border: none; border-top: 1px solid #d4eadb; margin: 24px 0;" />
                                    </td>
                                </tr>

                                <!-- Footer -->
                                <tr>
                                    <td style="background: #f2faf5; border-top: 1px solid #c8e6d0;
                                                padding: 18px 40px; text-align: center;">
                                        <p style="font-size: 11px; color: #5a8a6a; line-height: 1.7; margin: 0;">
                                            You are receiving this because you are part of this quotation approval workflow.<br/>
                                            &copy; {company_name}
                                        </p>
                                    </td>
                                </tr>

                            </table>
                        </td>
                    </tr>
                </table>
                """.format(
                    company_name=company.name or '',
                    order_name=rec.name or '',
                    approved_by=self.env.user.name or '',
                    approver_name=rec.sale_order_approval_history[-1].user.name or '',
                    customer_name=rec.partner_id.name or '',
                    order_date=str(rec.date_order)[:10] if rec.date_order else '',
                    base_url=rec.get_base_url(),
                    order_id=rec.id,
                    sender_name=self.env.user.name or '',
                )
                mail_values = {
                    'subject': 'Quotation Approved - %s' % rec.name,
                    'email_from': self.env.user.email or '',
                    'email_to': rec.sale_order_approval_history[-1].user.email or '',
                    'body_html': body_html,
                    'auto_delete': True,
                }
                self.env['mail.mail'].create(mail_values).send()

    def _get_data_sale_order_approval_rule_ids(self):
        values = []
        approval_rule = self.company_id.sale_order_approval_rule_id
        if self.company_id.sale_order_approval and approval_rule.approval_rule_ids:
            if approval_rule.approval_rule_ids:
                for rule in approval_rule.approval_rule_ids.sorted(key=lambda r: r.sequence):
                    if not rule.approval_category:
                        if not(rule.quotation_lower_limit == -1 or rule.quotation_upper_limit == -1) and self.amount_in_company_currency:
                            if rule.quotation_lower_limit <= self.amount_in_company_currency and self.amount_in_company_currency <= rule.quotation_upper_limit:
                                values.append({
                                    'sequence': rule.sequence,
                                    'approval_role': rule.approval_role.id,
                                    'email_template': rule.email_template.id,
                                    'sale_order': self.id,
                                })
                        else:
                            if rule.quotation_upper_limit == -1 and self.amount_in_company_currency >= rule.quotation_lower_limit and self.amount_in_company_currency:
                                values.append({
                                    'sequence': rule.sequence,
                                    'approval_role': rule.approval_role.id,
                                    'email_template': rule.email_template.id,
                                    'sale_order': self.id,
                                })
                            if rule.quotation_lower_limit == -1 and self.amount_in_company_currency <= rule.quotation_upper_limit and self.amount_in_company_currency:
                                values.append({
                                    'sequence': rule.sequence,
                                    'approval_role': rule.approval_role.id,
                                    'email_template': rule.email_template.id,
                                    'sale_order': self.id,
                                })
                    if rule.approval_category:
                        rule_approval_category_order_lines = self.order_line.filtered(lambda b: b.product_id.approval_category == rule.approval_category)
                        if rule_approval_category_order_lines:
                            subtotal = sum(rule_approval_category_order_lines.mapped('price_subtotal'))
                            if not(rule.quotation_lower_limit == -1 or rule.quotation_upper_limit == -1):
                                if rule.quotation_lower_limit <= subtotal and subtotal <= rule.quotation_upper_limit:
                                    values.append({
                                        'sequence': rule.sequence,
                                        'approval_role': rule.approval_role.id,
                                        'email_template': rule.email_template.id,
                                        'sale_order': self.id,
                                    })
                            else:
                                if rule.quotation_upper_limit == -1 and subtotal >= rule.quotation_lower_limit:
                                    values.append({
                                        'sequence': rule.sequence,
                                        'approval_role': rule.approval_role.id,
                                        'email_template': rule.email_template.id,
                                        'sale_order': self.id,
                                    })
                                if rule.quotation_lower_limit == -1 and subtotal <= rule.quotation_upper_limit:
                                    values.append({
                                        'sequence': rule.sequence,
                                        'approval_role': rule.approval_role.id,
                                        'email_template': rule.email_template.id,
                                        'sale_order': self.id,
                                    })
        return values

    @api.model
    def create(self, vals_list):
        records = super(SaleOrder, self).create(vals_list)
        for rec, vals in zip(records, vals_list):
            if not vals.get('sale_order_approval_rule_ids'):
                values = rec._get_data_sale_order_approval_rule_ids()
                if values:
                    rec.write({'send_approve_process': True})
                    for v in values:
                        v.update({'state': 'draft'})
                        self.env['sale.order.approval.rules'].create(v)

        return records
    def write(self, vals):
        res = super(SaleOrder, self).write(vals)
        if vals.get('order_line'):
            values = self._get_data_sale_order_approval_rule_ids()
            approval_roles = self.sale_order_approval_rule_ids.mapped('approval_role')
            for v in values:
                if not v.get('approval_role') in approval_roles.ids:
                    v.update({'state': 'draft'})
                    self.env['sale.order.approval.rules'].create(v)
            for a in self.sale_order_approval_rule_ids:
                if a.approval_role.id not in map(lambda x: x['approval_role'], values):
                    a.unlink()
        return res

    def reject_quotation(self):
        return {
            'name': _('Rejection Reason'),
            'view_mode': 'form',
            'res_model': 'quotation.rejection.reason',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def action_send_for_approval(self):
        for record in self:
            for line in record.order_line:
                if line.price_subtotal <= 0.0:
                    context = dict(self._context or {})
                    context['sale_order'] = True
                    context['order_id'] = self.id
                    return {
                        'name': _('Warning !'),
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'custom.warning',
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': context
                    }

            if record.sale_order_approval_rule_ids:
                record.message_subscribe(
                    partner_ids=record.sale_order_approval_rule_ids.mapped('users.partner_id.id'))
                msg = _("Quotation is waiting for approval.")
                record.message_post(body=msg, subtype_xmlid='mail.mt_comment')

            self.env['sale.order.approval.history'].create({
                'sale_order': record.id,
                'user': self.env.user.id,
                'date': fields.Datetime.now(),
                'state': 'send_for_approval'
            })

            self._send_approval_request_email(record)
            record.write({'send_for_approval': True, 'is_rejected': False})

    def _send_approval_request_email(self, record):
        recipient_emails = record.get_user_emails()
        if not recipient_emails:
            return

        company = self.env.company
        user = self.env.user
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
        body_html = """
        <table border="0" cellpadding="0" cellspacing="0" width="100%"
               style="font-family: Arial, Helvetica, sans-serif; background-color: #f4f6fa; padding: 24px;">
            <tr>
                <td align="center">
                    <table border="0" cellpadding="0" cellspacing="0" width="100%"
                           style="background: #ffffff;
                                  border-radius: 8px; overflow: hidden; border: 1px solid #dde2ed;">

                        <!-- Header -->
                        <tr>
                            <td style="background: #1a3a6b; padding: 32px 40px; text-align: center;">
                                <h1 style="color: #ffffff; font-size: 22px; font-weight: 700;
                                           letter-spacing: 0.5px; margin: 0;">
                                    Quotation Approval Request
                                </h1>
                            </td>
                        </tr>

                        <!-- Body -->
                        <tr>
                            <td style="padding: 32px 40px;">

                                <p style="font-size: 16px; color: #1a2a4a; font-weight: 600; margin: 0 0 20px 0;">
                                    Hello Approvers,
                                </p>
                                <p style="font-size: 14px; color: #4a5568; line-height: 1.7; margin: 0 0 24px 0;">
                                    A new quotation has been submitted and requires your review.
                                    Please examine the details below and take the appropriate
                                    action at your earliest convenience.
                                </p>

                                <!-- Info Card -->
                                <table border="0" cellpadding="0" cellspacing="0" width="100%"
                                       style="background: #f0f5ff; border: 1px solid #c7d9f5;
                                              border-radius: 6px; margin-bottom: 24px;">
                                    <tr>
                                        <td style="padding: 20px 24px;">
                                            <table border="0" cellpadding="8" cellspacing="0" width="100%">

                                                <tr>
                                                    <td style="font-size: 11px; font-weight: 700; letter-spacing: 1px;
                                                               color: #7a90bb; text-transform: uppercase; width: 140px;">
                                                        Quotation No.
                                                    </td>
                                                    <td style="font-size: 14px; color: #1a3a6b; font-weight: 600;">
                                                        {order_name}
                                                    </td>
                                                </tr>

                                                <tr>
                                                    <td style="font-size: 11px; font-weight: 700; letter-spacing: 1px;
                                                               color: #7a90bb; text-transform: uppercase;">
                                                        Requested By
                                                    </td>
                                                    <td style="font-size: 14px; color: #1a3a6b; font-weight: 600;">
                                                        {user_name}
                                                    </td>
                                                </tr>

                                                <tr>
                                                    <td style="font-size: 11px; font-weight: 700; letter-spacing: 1px;
                                                               color: #7a90bb; text-transform: uppercase;">
                                                        Customer
                                                    </td>
                                                    <td style="font-size: 14px; color: #1a3a6b; font-weight: 600;">
                                                        {customer_name}
                                                    </td>
                                                </tr>

                                                <tr>
                                                    <td style="font-size: 11px; font-weight: 700; letter-spacing: 1px;
                                                               color: #7a90bb; text-transform: uppercase;">
                                                        Date
                                                    </td>
                                                    <td style="font-size: 14px; color: #1a3a6b; font-weight: 600;">
                                                        {order_date}
                                                    </td>
                                                </tr>

                                                <tr>
                                                    <td style="font-size: 11px; font-weight: 700; letter-spacing: 1px;
                                                               color: #7a90bb; text-transform: uppercase;">
                                                        Status
                                                    </td>
                                                    <td>
                                                        <span style="display: inline-block; background: #fff3cd;
                                                                     color: #856404; border: 1px solid #ffc107;
                                                                     border-radius: 4px; font-size: 11px;
                                                                     font-weight: 700; padding: 3px 10px;
                                                                     letter-spacing: 0.5px; text-transform: uppercase;">
                                                            Pending Approval
                                                        </span>
                                                    </td>
                                                </tr>

                                            </table>
                                        </td>
                                    </tr>
                                </table>

                                <!-- View Button -->
                                <p style="margin: 24px 0;">
                                    <a href="{base_url}/web#id={order_id}&model=sale.order&view_type=form"
                                       style="display: inline-block; background-color: #1a3a6b; color: #ffffff;
                                              text-decoration: none; font-size: 13px; font-weight: 600;
                                              padding: 10px 24px; border-radius: 6px; letter-spacing: 0.02em;">
                                        View Quotation &#8594;
                                    </a>
                                </p>

                                <!-- Thanks & Regards -->
                                <p style="margin: 24px 0 4px 0; font-size: 14px; color: #4a5568;">
                                    Thanks &amp; regards,
                                </p>
                                <p style="margin: 0; font-size: 14px; font-weight: 600; color: #1a2a4a;">
                                    {sender_name}
                                </p>

                                <hr style="border: none; border-top: 1px solid #e8edf5; margin: 24px 0;" />
                            </td>
                        </tr>

                        <!-- Footer -->
                        <tr>
                            <td style="background: #f7f9fd; border-top: 1px solid #e0e7f2;
                                        padding: 18px 40px; text-align: center;">
                                <p style="font-size: 11px; color: #9aa5bc; line-height: 1.7; margin: 0;">
                                    You are receiving this because you are an assigned approver
                                    for this quotation.<br/>
                                    &copy; {company_name}
                                </p>
                            </td>
                        </tr>

                    </table>
                </td>
            </tr>
        </table>
        """.format(
            company_name=company.name or '',
            order_name=record.name or '',
            user_name=user.name or '',
            customer_name=record.partner_id.name or '',
            order_date=str(record.date_order)[:10] if record.date_order else '',
            base_url=record.get_base_url(),
            order_id=record.id,
            sender_name=user.name or '',
        )

        mail_values = {
            'subject': f'Quotation Approval Request - {self.name}',
            'email_from': user.email or company.email or '',
            'email_to': recipient_emails,
            'body_html': body_html,
            'auto_delete': True,
        }

        mail = self.env['mail.mail'].create(mail_values)
        mail.send()


class SaleOrderApprovalRules(models.Model):
    _name = 'sale.order.approval.rules'
    _description = 'Sale Order Approval Rules'
    _order = 'sequence'

    sale_order = fields.Many2one('sale.order', string='Sale Order', ondelete='cascade')
    sequence = fields.Integer(required=True)
    approval_role = fields.Many2one('approval.role', string='Approval Role', required=True)
    users = fields.Many2many('res.users', compute='_compute_users')
    user_id = fields.Many2one('res.users', string='User')
    email_template = fields.Many2one('mail.template', string='Mail Template')
    date = fields.Datetime()
    is_approved = fields.Boolean(string='Approved ?')
    state = fields.Selection([
            ('approve', 'Approved'),
            ('reject', 'Reject'),
            ('draft', 'Draft')
        ], string='Status', index=True, readonly=True, default='draft')

    @api.depends('approval_role')
    def _compute_users(self):
        for rec in self:
            rec.users = [(6, 0, [])]
            if rec.approval_role:
                employees = self.env['hr.employee'].search([('approval_role', '=', rec.approval_role.id)])
                users = self.env['res.users'].search([('employee_ids', 'in', employees.ids)])
                rec.users = [(6, 0, users.ids)]


class QuotationRejectionReason(models.TransientModel):
    _name = 'quotation.rejection.reason'
    _description = 'Quotation Rejection Reason'
    _rec_name = 'reason'

    reason = fields.Text(required=True)

    def _send_rejection_email(self, order, user, reason):
        company = self.env.company

        body_html = """
            <div style="font-family: Arial, Helvetica, sans-serif; background-color: #f4f6fa; padding: 24px;">
                <div style="max-width: 620px; margin: 0 auto; background: #ffffff;
                            border-radius: 8px; overflow: hidden; border: 1px solid #dde2ed;">

                    <!-- Header -->
                    <div style="background: #6b1a1a; padding: 32px 40px 24px; text-align: center;">
                        <div style="font-size: 11px; letter-spacing: 2px; color: #d68a8a;
                                    text-transform: uppercase; margin-bottom: 8px;">
                            {company_name}
                        </div>
                        <h1 style="color: #ffffff; font-size: 22px; font-weight: 700;
                                   letter-spacing: 0.5px; margin: 0;">
                            Quotation Rejected
                        </h1>
                        <div style="width: 48px; height: 3px; background: #d94a4a;
                                    margin: 12px auto 0; border-radius: 2px;"></div>
                    </div>

                    <!-- Body -->
                    <div style="padding: 32px 40px;">
                        <div style="font-size: 16px; color: #1a2a4a;
                                    font-weight: 600; margin-bottom: 20px;">
                            Hello {requester_name},
                        </div>
                        <div style="font-size: 14px; color: #4a5568;
                                    line-height: 1.7; margin-bottom: 24px;">
                            Your quotation has been <strong style="color: #a32d2d;">rejected</strong>
                            by <strong>{approver_name}</strong>. Please review the details below,
                            discuss with the approver, make the necessary changes, and
                            re-submit for approval.
                        </div>

                        <!-- Info Card -->
                        <div style="background: #fff0f0; border: 1px solid #f5c5c5;
                                    border-radius: 6px; padding: 20px 24px; margin-bottom: 24px;">

                            <div style="display: flex; align-items: center;
                                        gap: 10px; margin-bottom: 12px;">
                                <span style="font-size: 11px; font-weight: 700; letter-spacing: 1px;
                                             color: #bb7a7a; text-transform: uppercase; min-width: 120px;">
                                    Quotation No.
                                </span>
                                <span style="font-size: 14px; color: #6b1a1a; font-weight: 600;">
                                    {order_name}
                                </span>
                            </div>

                            <div style="display: flex; align-items: center;
                                        gap: 10px; margin-bottom: 12px;">
                                <span style="font-size: 11px; font-weight: 700; letter-spacing: 1px;
                                             color: #bb7a7a; text-transform: uppercase; min-width: 120px;">
                                    Customer
                                </span>
                                <span style="font-size: 14px; color: #6b1a1a; font-weight: 600;">
                                    {customer_name}
                                </span>
                            </div>

                            <div style="display: flex; align-items: center;
                                        gap: 10px; margin-bottom: 12px;">
                                <span style="font-size: 11px; font-weight: 700; letter-spacing: 1px;
                                             color: #bb7a7a; text-transform: uppercase; min-width: 120px;">
                                    Rejected By
                                </span>
                                <span style="font-size: 14px; color: #6b1a1a; font-weight: 600;">
                                    {approver_name}
                                </span>
                            </div>

                            <div style="display: flex; align-items: center;
                                        gap: 10px; margin-bottom: 12px;">
                                <span style="font-size: 11px; font-weight: 700; letter-spacing: 1px;
                                             color: #bb7a7a; text-transform: uppercase; min-width: 120px;">
                                    Date
                                </span>
                                <span style="font-size: 14px; color: #6b1a1a; font-weight: 600;">
                                    {order_date}
                                </span>
                            </div>

                            <div style="display: flex; align-items: flex-start; gap: 10px; margin-bottom: 12px;">
                                <span style="font-size: 11px; font-weight: 700; letter-spacing: 1px;
                                             color: #bb7a7a; text-transform: uppercase; min-width: 120px; padding-top: 2px;">
                                    Reason
                                </span>
                                <span style="font-size: 14px; color: #6b1a1a; font-weight: 600; line-height: 1.5;">
                                    {reason}
                                </span>
                            </div>

                            <div style="display: flex; align-items: center; gap: 10px;">
                                <span style="font-size: 11px; font-weight: 700; letter-spacing: 1px;
                                             color: #bb7a7a; text-transform: uppercase; min-width: 120px;">
                                    Status
                                </span>
                                <span style="display: inline-block; background: #fde8e8; color: #a32d2d;
                                             border: 1px solid #e24b4a; border-radius: 4px; font-size: 11px;
                                             font-weight: 700; padding: 3px 10px; letter-spacing: 0.5px;
                                             text-transform: uppercase;">
                                    Rejected
                                </span>
                            </div>
                        </div>

                        <!-- Divider -->
                        <hr style="border: none; border-top: 1px solid #e8edf5; margin: 24px 0;" />

                        <!-- Notes -->
                        <div style="font-size: 12px; color: #8a95a8;
                                    text-align: center; line-height: 1.6; margin-bottom: 4px;">
                            Please contact <strong>{approver_name}</strong> directly to discuss the rejection.
                        </div>
                        <div style="font-size: 12px; color: #8a95a8;
                                    text-align: center; line-height: 1.6;">
                            This is an automated notification — do not reply to this email.
                        </div>
                    </div>

                    <!-- Footer -->
                    <div style="background: #f7f9fd; border-top: 1px solid #e0e7f2;
                                padding: 18px 40px; text-align: center;">
                        <p style="font-size: 11px; color: #9aa5bc; line-height: 1.7; margin: 0;">
                            You are receiving this because you submitted this quotation for approval.<br/>
                            &copy; {company_name}
                        </p>
                    </div>

                </div>
            </div>
        """.format(
            company_name=company.name or '',
            order_name=order.name or '',
            requester_name=order.sale_order_approval_history[-1].user.name or '',
            approver_name=self.env.user.name or '',
            customer_name=order.partner_id.name or '',
            order_date=str(order.date_order)[:10] if order.date_order else '',
            reason=reason or 'No reason provided.',
        )

        mail_values = {
            'subject': f'Quotation {order.name} has been Rejected',
            'email_from': self.env.user.email or '',
            'email_to': order.sale_order_approval_history[-1].user.email or '',
            'body_html': body_html,
            'auto_delete': True,
        }
        mail = self.env['mail.mail'].create(mail_values)
        mail.send()

    def button_reject(self):
        if self.env.context.get('active_id'):
            order = self.env['sale.order'].browse(self.env.context['active_id'])
            if order.sale_order_approval_rule_ids:
                rules = order.sale_order_approval_rule_ids.filtered(
                    lambda b: self.env.user in b.users
                )
                rules.write({
                    'is_approved': False,
                    'date': fields.Datetime.now(),
                    'state': 'reject',
                    'user_id': self.env.user.id,
                })

                msg = _("Quotation has been rejected by %s.") % self.env.user.name
                order.message_post(body=msg, subtype='mail.mt_comment')

                # Send styled rejection email (no XML template needed)
                self._send_rejection_email(order, self.env.user, self.reason)

                order.write({'is_rejected': True, 'send_for_approval': False})

                self.env['sale.order.approval.history'].create({
                    'sale_order': order.id,
                    'user': self.env.user.id,
                    'date': fields.Datetime.now(),
                    'state': 'reject',
                    'rejection_reason': self.reason,
                })

class ResUsers(models.Model):
    _inherit = 'res.users'

    sale_id = fields.Many2one('sale.order', string="sale")
