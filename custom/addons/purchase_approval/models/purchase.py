# -*- coding: utf-8 -*-
# Part of Kanak Infosystems LLP. See LICENSE file for full copyright and licensing details.
from fcntl import FASYNC

from odoo import api, fields, models, _
from lxml import etree
from odoo.tools.misc import clean_context, split_every
import logging
from markupsafe import Markup
_logger = logging.getLogger(__name__)
from datetime import datetime


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    purchase_order_approval_rule_ids = fields.One2many('purchase.order.approval.rules', 'purchase_order', string='Purchase Order Approval Lines', readonly=True, copy=False)
    purchase_order_approval_history = fields.One2many('purchase.order.approval.history', 'purchase_order', string='Purchase Order Approval History', readonly=True, copy=False)
    approve_button = fields.Boolean(compute='_compute_approve_button', string='Approve Button ?', search='_search_to_approve_orders', copy=False)
    ready_for_po = fields.Boolean(compute='_compute_ready_for_po', string='Ready For PO ?', copy=False)
    send_for_approval = fields.Boolean(string="Send For Approval", copy=False)
    is_rejected = fields.Boolean(string='Rejected ?', copy=False)
    user_ids = fields.Many2many('res.users', 'purchase_user_rel', 'purchase_id', 'uid', 'Request Users', compute='_compute_user')

    purchase_order_approval_rule_id = fields.Many2one('purchase.order.approval.rule', related='company_id.purchase_order_approval_rule_id', string='Purchase Order Approval Rules')
    purchase_order_approval = fields.Boolean(related='company_id.purchase_order_approval', string='Purchase Order Approval By Rule')
    send_approve_process = fields.Boolean()
    dummy_compute = fields.Float("Dummy compute", compute='compute_rules_for_amount')
    approval_state = fields.Selection([('no', 'No Approvals'),
                                       ('not_sent', 'Not Sent'),
                                       ('to_approve', 'Waiting for Approval'),
                                       ('approved', 'Quotation Approved'),
                                       ], string="Approval Status", compute='_get_approval_status', copy=False)
    amount_in_company_currency = fields.Float("Amount in Company Currency", compute="_currency_conversion")
    company_currency = fields.Many2one('res.currency', 'Company Currency', related="company_id.currency_id")
    editable_compute = fields.Boolean(string='Editable', compute='_compute_editable')

    @api.depends('state', 'approval_state')
    def _compute_editable(self):
        confirm_user_group = self.env.ref('purchase_approval.group_confirm_order_user')
        approval_user_group = self.env.ref('purchase_approval.group_second_approval_user')

        for order in self:
            current_user = self.env.user

            if order.state == 'draft' or order.state == 'sent':
                order.editable_compute = True
            elif order.state == 'bid received' and order.approval_state == 'not_sent':
                order.editable_compute = True
            elif order.state == 'bid received':
                if current_user in approval_user_group.user_ids:
                    order.editable_compute = True
                else:
                    order.editable_compute = False
            else:
                order.editable_compute = False

            if order.approval_state == 'approved':
                if current_user in approval_user_group.user_ids:
                    order.editable_compute = False
            if order.state == 'bid received':
                if current_user in confirm_user_group.user_ids:
                    order.editable_compute = True
                else:
                    order.editable_compute = False

    @api.model
    def _get_default_team(self):
        return self.env['crm.team']._get_default_team_id()

    team_id = fields.Many2one(
        'crm.team', 'Purchase Team',
        change_default=True, default=_get_default_team, check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    @api.depends('amount_total', 'currency_id', 'company_id', 'date_order')
    def _currency_conversion(self):
        for rec in self:
            rec.amount_in_company_currency = rec.currency_id._convert(
                rec.amount_total,
                rec.company_id.currency_id,
                rec.company_id,
                rec.date_order or fields.Date.today(),
            )

    def _get_users(self):
        upcoming_approvals = self.purchase_order_approval_rule_ids.filtered(lambda x: not x.is_approved).sorted(
            key=lambda x: x.sequence)
        next_approver_mails = ''

        # ✅ FIXED: Guard check moved BEFORE accessing [0] to prevent IndexError
        if upcoming_approvals:
            next_approval = upcoming_approvals[0]  # ✅ now safe — was crashing here before
            can_sent_user_ids = self.env['res.users']
            if len(next_approval.users) == 1 or len(upcoming_approvals) == 1:
                can_sent_user_ids += next_approval.users
            else:
                for user in next_approval.users:
                    if len(upcoming_approvals) > 1:
                        if user.id not in upcoming_approvals[1].users.ids:
                            can_sent_user_ids += user
            if not can_sent_user_ids and len(upcoming_approvals) > 1:
                can_sent_user_ids += upcoming_approvals[1].users
            for user in can_sent_user_ids:
                next_approver_mails += user.login
                next_approver_mails += ', '
        return next_approver_mails


    @api.depends('purchase_order_approval_rule_ids.is_approved')
    def _get_approval_status(self):
        for rec in self:
            if rec.company_id.purchase_order_approval and rec.company_id.purchase_order_approval_rule_id and rec.purchase_order_approval_rule_ids:
                if all([i.is_approved for i in rec.purchase_order_approval_rule_ids]) and rec.purchase_order_approval_rule_ids:
                    rec.approval_state = 'approved'
                else:
                    if rec.send_for_approval:
                        rec.approval_state = 'to_approve'
                    else:
                        rec.approval_state = 'not_sent'
            else:
                rec.approval_state = 'no'

    @api.depends('amount_total')
    def compute_rules_for_amount(self):
        # Compute methods must ONLY assign field values - no write/create calls
        for rec in self:
            rec.dummy_compute = 0

    @api.onchange('amount_total', 'order_line')
    def _onchange_compute_approval_rules(self):
        """Populate approval rules on the form when amount changes (UI only)."""
        for rec in self:
            if not rec.purchase_order_approval_rule_ids:
                values = rec._get_data_purchase_order_approval_rule_ids()
                if values:
                    rec.send_approve_process = True
                    rule_lines = []
                    for v in values:
                        v.update({'state': 'draft'})
                        rule_lines.append((0, 0, v))
                    rec.purchase_order_approval_rule_ids = rule_lines

    @api.depends('purchase_order_approval_rule_ids')
    def _compute_user(self):
        for order in self:
            order.user_ids = []
            for approve_rule in order.purchase_order_approval_rule_ids:
                order.user_ids = [(4, user.id) for user in approve_rule.users]

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(PurchaseOrder, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        doc = elist.XML(res['arch'])
        if view_type in ['list', 'form'] and (self.user_has_groups('purchase.group_purchase_user') and not self.user_has_groups('purchase.group_purchase_manager')):
            if self._context.get('purchase_approve'):
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
        for i in self.search([('purchase_order_approval_rule_ids', '!=', False)]):
            approval_lines = i.purchase_order_approval_rule_ids.filtered(lambda b: not b.is_approved).sorted(key=lambda r: r.sequence)
            if approval_lines:
                same_seq_lines = approval_lines.filtered(lambda b: b.sequence == approval_lines[0].sequence)
                if self.env.user in same_seq_lines.mapped('users') and i.send_for_approval:
                    res.append(i.id)
        return [('id', 'in', res)]

    @api.depends('purchase_order_approval_rule_ids.is_approved')
    def _compute_approve_button(self):
        for rec in self:
            if rec.company_id.purchase_order_approval and rec.company_id.purchase_order_approval_rule_id:
                approval_lines = rec.purchase_order_approval_rule_ids.filtered(lambda b: not b.is_approved).sorted(key=lambda r: r.sequence)
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

    @api.depends('purchase_order_approval_rule_ids.is_approved')
    def _compute_ready_for_po(self):
        for rec in self:
            if rec.company_id.purchase_order_approval and rec.company_id.purchase_order_approval_rule_id and rec.purchase_order_approval_rule_ids:
                if all([i.is_approved for i in rec.purchase_order_approval_rule_ids]) and rec.purchase_order_approval_rule_ids:
                    rec.ready_for_po = True
                else:
                    rec.ready_for_po = False
            else:
                rec.ready_for_po = True

    def action_button_approve(self):
        for rec in self:
            if rec.purchase_order_approval_rule_ids:
                rules = rec.purchase_order_approval_rule_ids.filtered(lambda b: self.env.user in b.users)
                rules.write({'is_approved': True, 'date': fields.Datetime.now(), 'state': 'approve',
                             'user_id': self.env.user.id})
                msg = Markup(_("Quotation has been approved by %s.") % (self.env.user.name))
                self.message_post(body=msg)
                self.env['purchase.order.approval.history'].create({
                    'purchase_order': rec.id,
                    'user': self.env.user.id,
                    'date': fields.Datetime.now(),
                    'state': 'approved'
                })
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)

                if rec.approval_state == 'to_approve':
                    subject = 'RFQ Approved'
                    message_body = """
                    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 14px; color: #222; background-color: #f4f6fa; padding: 32px 0;">
                        <div style="max-width: 560px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; overflow: hidden; border: 1px solid #dde2ef;">

                            <div style="background-color: #1a6b3a; padding: 32px 40px 24px;">
                                <div style="margin-bottom: 16px;">
                                    <span style="font-size: 11px; color: #a0e8c0; letter-spacing: 0.08em; text-transform: uppercase;">Procurement</span>
                                </div>
                                <h1 style="font-size: 22px; font-weight: 600; color: #ffffff; margin: 0 0 4px;">RFQ Approved</h1>
                                <p style="font-size: 13px; color: #7ad4a0; margin: 0;">Action completed — please proceed further</p>
                            </div>

                            <div style="padding: 32px 40px;">
                                <p style="font-size: 15px; color: #111; font-weight: 600; margin: 0 0 12px;">Hello,</p>
                                <p style="font-size: 14px; color: #444; line-height: 1.7; margin: 0 0 24px;">
                                    RFQ <strong style="color: #111;">%s</strong> has been approved by
                                    <strong style="color: #111;">%s</strong>. You may proceed further to approve from your end.
                                    Please ignore if already approved.
                                </p>

                                <div style="background-color: #f7f9fc; border-radius: 8px; padding: 16px 20px; margin-bottom: 28px; border-left: 3px solid #1a6b3a;">
                                    <table style="width: 100%%; border-collapse: collapse;">
                                        <tr>
                                            <td style="padding: 6px 0; width: 50%%;">
                                                <p style="font-size: 11px; color: #888; margin: 0 0 2px; text-transform: uppercase; letter-spacing: 0.06em;">Reference</p>
                                                <p style="font-size: 13px; font-weight: 600; color: #111; margin: 0;">%s</p>
                                            </td>
                                            <td style="padding: 6px 0;">
                                                <p style="font-size: 11px; color: #888; margin: 0 0 2px; text-transform: uppercase; letter-spacing: 0.06em;">Approved By</p>
                                                <p style="font-size: 13px; font-weight: 600; color: #111; margin: 0;">%s</p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 6px 0;">
                                                <p style="font-size: 11px; color: #888; margin: 0 0 2px; text-transform: uppercase; letter-spacing: 0.06em;">Status</p>
                                                <p style="margin: 0;">
                                                    <span style="background-color: #d4edda; color: #155724; padding: 2px 10px; border-radius: 4px; font-size: 12px; font-weight: 500;">Approved</span>
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                </div>
                            </div>

                            <div style="border-top: 1px solid #eaecf0; padding: 16px 40px;">
                                <p style="font-size: 11px; color: #aaa; margin: 0;">This is an automated notification.</p>
                            </div>

                        </div>
                    </div>
                    """ % (self.name, self.env.user.name, self.name, self.env.user.name)

                    template_data = {
                        'subject': subject,
                        'body_html': message_body,
                        'email_from': self.env.user.login,
                        'email_to': self._get_users(),
                    }
                    # ✅ Same body for chatter and email
                    self.message_post(body=Markup(message_body), subject=subject)
                    template_id = self.env['mail.mail'].sudo().create(template_data)
                    template_id.sudo().send()

                elif rec.approval_state == 'approved':
                    subject = 'RFQ Approved'
                    message_body = f"""
                    <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 14px; color: #222; background-color: #f4f6fa; padding: 32px 0;">
                        <div style="max-width: 560px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; overflow: hidden; border: 1px solid #dde2ef;">

                            <div style="background-color: #1a6b3a; padding: 32px 40px 24px;">
                                <div style="margin-bottom: 16px;">
                                    <span style="font-size: 11px; color: #a0e8c0; letter-spacing: 0.08em; text-transform: uppercase;">Procurement</span>
                                </div>
                                <h1 style="font-size: 22px; font-weight: 600; color: #ffffff; margin: 0 0 4px;">RFQ Approved</h1>
                                <p style="font-size: 13px; color: #7ad4a0; margin: 0;">Action completed — please proceed further</p>
                            </div>

                            <div style="padding: 32px 40px;">
                                <p style="font-size: 15px; color: #111; font-weight: 600; margin: 0 0 12px;">Hello {rec.purchase_order_approval_history[-1].user.name},</p>
                                <p style="font-size: 14px; color: #444; line-height: 1.7; margin: 0 0 24px;">
                                    Respective approval has been done for <strong style="color: #111;">{self.name}</strong>. You may proceed further from your end.
                                </p>

                                <div style="background-color: #f7f9fc; border-radius: 8px; padding: 16px 20px; margin-bottom: 28px; border-left: 3px solid #1a6b3a;">
                                    <table style="width: 100%; border-collapse: collapse;">
                                        <tr>
                                            <td style="padding: 6px 0; width: 50%;">
                                                <p style="font-size: 11px; color: #888; margin: 0 0 2px; text-transform: uppercase; letter-spacing: 0.06em;">Reference</p>
                                                <p style="font-size: 13px; font-weight: 600; color: #111; margin: 0;">{self.name}</p>
                                            </td>
                                            <td style="padding: 6px 0;">
                                                <p style="font-size: 11px; color: #888; margin: 0 0 2px; text-transform: uppercase; letter-spacing: 0.06em;">Approved By</p>
                                                <p style="font-size: 13px; font-weight: 600; color: #111; margin: 0;">{self.env.user.name}</p>
                                            </td>
                                        </tr>
                                        <tr>
                                            <td style="padding: 6px 0;">
                                                <p style="font-size: 11px; color: #888; margin: 0 0 2px; text-transform: uppercase; letter-spacing: 0.06em;">Status</p>
                                                <p style="margin: 0;">
                                                    <span style="background-color: #d4edda; color: #155724; padding: 2px 10px; border-radius: 4px; font-size: 12px; font-weight: 500;">Approved</span>
                                                </p>
                                            </td>
                                        </tr>
                                    </table>
                                </div>

                                <a href="{base_url}"
                                   style="display: inline-block; background-color: #1a6b3a; color: #ffffff; text-decoration: none;
                                          font-size: 13px; font-weight: 600; padding: 10px 24px;
                                          border-radius: 6px; letter-spacing: 0.02em;">
                                    View Form &#8594;
                                </a>
                            </div>

                            <div style="border-top: 1px solid #eaecf0; padding: 16px 40px;">
                                <p style="font-size: 11px; color: #aaa; margin: 0;">This is an automated notification.</p>
                            </div>

                        </div>
                    </div>
                    """
                    template_data = {
                        'subject': subject,
                        'body_html': message_body,
                        'email_from': self.env.user.login,
                        'email_to': rec.purchase_order_approval_history[-1].user.login,
                    }
                    # ✅ Same body for chatter and email
                    self.message_post(body=Markup(message_body), subject=subject)
                    template_id = self.env['mail.mail'].sudo().create(template_data)
                    template_id.sudo().send()

                group = self.env.ref('purchase_approval.group_confirm_order_user')
                users_in_group = self.env['res.users'].search(
                    [('name', '!=', "Administrator"), ('group_ids', 'in', group.id)], limit=1)

                subject = 'RFQ Approved'
                final_body = f"""
                <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 14px; color: #222; background-color: #f4f6fa; padding: 32px 0;">
                    <div style="max-width: 560px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; overflow: hidden; border: 1px solid #dde2ef;">

                        <div style="background-color: #1a6b3a; padding: 32px 40px 24px;">
                            <div style="margin-bottom: 16px;">
                                <span style="font-size: 11px; color: #a0e8c0; letter-spacing: 0.08em; text-transform: uppercase;">Procurement</span>
                            </div>
                            <h1 style="font-size: 22px; font-weight: 600; color: #ffffff; margin: 0 0 4px;">RFQ Approved</h1>
                            <p style="font-size: 13px; color: #7ad4a0; margin: 0;">Action completed — please proceed further</p>
                        </div>

                        <div style="padding: 32px 40px;">
                            <p style="font-size: 15px; color: #111; font-weight: 600; margin: 0 0 12px;">Hello {users_in_group.name} Sir!</p>
                            <p style="font-size: 14px; color: #444; line-height: 1.7; margin: 0 0 24px;">
                                The necessary approval has been completed. You are kindly requested to proceed further and confirm the Purchase Order <strong style="color: #111;">{self.name}</strong>.
                            </p>

                            <div style="background-color: #f7f9fc; border-radius: 8px; padding: 16px 20px; margin-bottom: 28px; border-left: 3px solid #1a6b3a;">
                                <table style="width: 100%; border-collapse: collapse;">
                                    <tr>
                                        <td style="padding: 6px 0; width: 50%;">
                                            <p style="font-size: 11px; color: #888; margin: 0 0 2px; text-transform: uppercase; letter-spacing: 0.06em;">Reference</p>
                                            <p style="font-size: 13px; font-weight: 600; color: #111; margin: 0;">{self.name}</p>
                                        </td>
                                        <td style="padding: 6px 0;">
                                            <p style="font-size: 11px; color: #888; margin: 0 0 2px; text-transform: uppercase; letter-spacing: 0.06em;">Approved By</p>
                                            <p style="font-size: 13px; font-weight: 600; color: #111; margin: 0;">{self.env.user.name}</p>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0;">
                                            <p style="font-size: 11px; color: #888; margin: 0 0 2px; text-transform: uppercase; letter-spacing: 0.06em;">Status</p>
                                            <p style="margin: 0;">
                                                <span style="background-color: #d4edda; color: #155724; padding: 2px 10px; border-radius: 4px; font-size: 12px; font-weight: 500;">Approved</span>
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                            </div>

                            <a href="{base_url}"
                               style="display: inline-block; background-color: #1a6b3a; color: #ffffff; text-decoration: none;
                                      font-size: 13px; font-weight: 600; padding: 10px 24px;
                                      border-radius: 6px; letter-spacing: 0.02em;">
                                View Form &#8594;
                            </a>
                        </div>

                        <div style="border-top: 1px solid #eaecf0; padding: 16px 40px;">
                            <p style="font-size: 11px; color: #aaa; margin: 0;">This is an automated notification.</p>
                        </div>

                    </div>
                </div>
                """
                template_data = {
                    'subject': subject,
                    'body_html': final_body,
                    'email_from': self.env.user.login,
                    'email_to': users_in_group.login,
                }
                # ✅ Same body for chatter and email
                self.message_post(body=Markup(final_body), subject=subject)
                template_id = self.env['mail.mail'].sudo().create(template_data)
                template_id.sudo().send()

    def _get_data_purchase_order_approval_rule_ids(self):
        values = []
        approval_rule = self.company_id.purchase_order_approval_rule_id
        if self.company_id.purchase_order_approval and approval_rule.approval_rule_ids:
            if approval_rule.approval_rule_ids:
                for rule in approval_rule.approval_rule_ids.sorted(key=lambda r: r.sequence):
                    if not rule.approval_category:
                        if rule.team_id:
                            if self.team_id == rule.team_id:
                                if not(rule.quotation_lower_limit == -1 or rule.quotation_upper_limit == -1) and self.amount_in_company_currency:
                                    if rule.quotation_lower_limit <= self.amount_in_company_currency and self.amount_in_company_currency <= rule.quotation_upper_limit:
                                        values.append({
                                            'sequence': rule.sequence,
                                            'approval_role': rule.approval_role.id,
                                            'email_template': rule.email_template.id,
                                            'purchase_order': self.id,
                                        })
                                else:
                                    if rule.quotation_upper_limit == -1 and self.amount_in_company_currency >= rule.quotation_lower_limit and self.amount_in_company_currency:
                                        values.append({
                                            'sequence': rule.sequence,
                                            'approval_role': rule.approval_role.id,
                                            'email_template': rule.email_template.id,
                                            'purchase_order': self.id,
                                        })
                                    if rule.quotation_lower_limit == -1 and self.amount_in_company_currency <= rule.quotation_upper_limit and self.amount_in_company_currency:
                                        values.append({
                                            'sequence': rule.sequence,
                                            'approval_role': rule.approval_role.id,
                                            'email_template': rule.email_template.id,
                                            'purchase_order': self.id,
                                        })
                        else:
                            if not (
                                    rule.quotation_lower_limit == -1 or rule.quotation_upper_limit == -1) and self.amount_in_company_currency:
                                if rule.quotation_lower_limit <= self.amount_in_company_currency and self.amount_in_company_currency <= rule.quotation_upper_limit:
                                    values.append({
                                        'sequence': rule.sequence,
                                        'approval_role': rule.approval_role.id,
                                        'email_template': rule.email_template.id,
                                        'purchase_order': self.id,
                                    })
                            else:
                                if rule.quotation_upper_limit == -1 and self.amount_in_company_currency >= rule.quotation_lower_limit and self.amount_in_company_currency:
                                    values.append({
                                        'sequence': rule.sequence,
                                        'approval_role': rule.approval_role.id,
                                        'email_template': rule.email_template.id,
                                        'purchase_order': self.id,
                                    })
                                if rule.quotation_lower_limit == -1 and self.amount_in_company_currency <= rule.quotation_upper_limit and self.amount_in_company_currency:
                                    values.append({
                                        'sequence': rule.sequence,
                                        'approval_role': rule.approval_role.id,
                                        'email_template': rule.email_template.id,
                                        'purchase_order': self.id,
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
                                        'purchase_order': self.id,
                                    })
                            else:
                                if rule.quotation_upper_limit == -1 and subtotal >= rule.quotation_lower_limit:
                                    values.append({
                                        'sequence': rule.sequence,
                                        'approval_role': rule.approval_role.id,
                                        'email_template': rule.email_template.id,
                                        'purchase_order': self.id,
                                    })
                                if rule.quotation_lower_limit == -1 and subtotal <= rule.quotation_upper_limit:
                                    values.append({
                                        'sequence': rule.sequence,
                                        'approval_role': rule.approval_role.id,
                                        'email_template': rule.email_template.id,
                                        'purchase_order': self.id,
                                    })
        return values

    @api.model_create_multi
    def create(self, vals_list):
        res = super(PurchaseOrder, self).create(vals_list)
        for record in res:
            # Find the matching vals for this record (check if rules were passed)
            has_rules = any(
                v.get('purchase_order_approval_rule_ids')
                for v in vals_list
                if isinstance(v, dict)
            )
            if not has_rules:
                values = record._get_data_purchase_order_approval_rule_ids()
                if values:
                    record.write({'send_approve_process': True})
                    for v in values:
                        v.update({'state': 'draft'})
                        self.env['purchase.order.approval.rules'].create(v)
        return res

    def write(self, vals):
        res = super(PurchaseOrder, self).write(vals)
        if vals.get('order_line'):
            values = self._get_data_purchase_order_approval_rule_ids()
            approval_roles = self.purchase_order_approval_rule_ids.mapped('approval_role')
            for v in values:
                if not v.get('approval_role') in approval_roles.ids:
                    v.update({'state': 'draft'})
                    self.env['purchase.order.approval.rules'].create(v)
            for a in self.purchase_order_approval_rule_ids:
                if a.approval_role.id not in map(lambda x: x['approval_role'], values):
                    a.unlink()
        return res

    def reject_quotation(self):
        return {
            'name': _('Rejection Reason'),
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'rfq.rejection.reason',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }


    def action_send_for_approval(self):
        for record in self:

            for line in record.order_line:
                if line.product_id and line.price_subtotal <= 0.0:
                    context = dict(self._context or {})
                    context['purchase_order'] = True
                    return {
                        'name': _('Warning !'),
                        'view_type': 'form',
                        'view_mode': 'form',
                        'res_model': 'purchase.custom.warning',
                        'type': 'ir.actions.act_window',
                        'target': 'new',
                        'context': context
                    }

            self.env['purchase.order.approval.history'].create({
                'purchase_order': record.id,
                'user': self.env.user.id,
                'date': fields.Datetime.now(),
                'state': 'send_for_approval'
            })

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (record.id, record._name)

            subject = 'RFQ Approval Request'
            body = """
            <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 14px; color: #222; background-color: #f4f6fa; padding: 32px 0;">
                <div style="max-width: 560px; margin: 0 auto; background: #ffffff; border-radius: 10px; overflow: hidden; border: 1px solid #dde2ef;">

                    <!-- Header -->
                    <div style="background-color: #1a2d6b; padding: 32px 40px 24px;">
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 16px;">
                            <div style="width: 8px; height: 8px; border-radius: 50%; background: #5b8fff;"></div>
                            <span style="font-size: 11px; color: #a0b4e8; letter-spacing: 0.08em; text-transform: uppercase;">Procurement</span>
                        </div>
                        <h1 style="font-size: 22px; font-weight: 600; color: #ffffff; margin: 0 0 4px;">RFQ Approval Request</h1>
                        <p style="font-size: 13px; color: #7a9bd4; margin: 0;">Action required — please review and respond</p>
                    </div>

                    <!-- Body -->
                    <div style="padding: 32px 40px;">
                        <p style="font-size: 15px; color: #111; font-weight: 600; margin: 0 0 12px;">Hello Approvers,</p>
                        <p style="font-size: 14px; color: #444; line-height: 1.7; margin: 0 0 24px;">
                            RFQ approval <strong style="color: #111;">{rfq_name}</strong> has been raised by
                            <strong style="color: #111;">{user_name}</strong>. Please review and approve or reject
                            this request — if rejecting, kindly include a reason.
                        </p>

                        <!-- Info Card -->
                        <div style="background: #f7f9fc; border-radius: 8px; padding: 16px 20px; margin-bottom: 28px; border-left: 3px solid #1a2d6b;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 6px 0; width: 50%;">
                                        <p style="font-size: 11px; color: #888; margin: 0 0 2px; text-transform: uppercase; letter-spacing: 0.06em;">Reference</p>
                                        <p style="font-size: 13px; font-weight: 600; color: #111; margin: 0;">{rfq_name}</p>
                                    </td>
                                    <td style="padding: 6px 0;">
                                        <p style="font-size: 11px; color: #888; margin: 0 0 2px; text-transform: uppercase; letter-spacing: 0.06em;">Raised by</p>
                                        <p style="font-size: 13px; font-weight: 600; color: #111; margin: 0;">{user_name}</p>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 6px 0;">
                                        <p style="font-size: 11px; color: #888; margin: 0 0 2px; text-transform: uppercase; letter-spacing: 0.06em;">Status</p>
                                        <p style="margin: 0;">
                                            <span style="background: #fff3cd; color: #7a5200; padding: 2px 10px; border-radius: 4px; font-size: 12px; font-weight: 500;">Pending Review</span>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </div>

                        <!-- CTA Button -->
                        <a href="{base_url}"
                           style="display: inline-block; background: #1a2d6b; color: #ffffff; text-decoration: none;
                                  font-size: 13px; font-weight: 600; padding: 10px 24px;
                                  border-radius: 6px; letter-spacing: 0.02em;">
                            View Form &#8594;
                        </a>
                    </div>

                    <!-- Footer -->
                    <div style="border-top: 1px solid #eaecf0; padding: 16px 40px; display: flex; justify-content: space-between;">
                        <p style="font-size: 11px; color: #aaa; margin: 0;">This is an automated notification.</p>
                        <p style="font-size: 11px; color: #aaa; margin: 0;">&#169; {current_year} {company_name}</p>
                    </div>

                </div>
            </div>
            """.format(
                rfq_name=record.name,
                user_name=self.env.user.name,
                base_url=base_url,
                company_name=self.env.company.name,
                current_year=datetime.now().year,
            )
            message_body = Markup(body)

            # ✅ Both chatter and email now use identical HTML
            record.message_post(body=message_body, subject=subject)
            template_data = {
                'subject': subject,
                'body_html': body,
                'email_from': self.env.user.login,
                'email_to': self._get_users(),
            }

            template_id = self.env['mail.mail'].sudo().create(template_data)
            template_id.sudo().send()
            record.write({'send_for_approval': True, 'is_rejected': False})

class PurchaseOrderApprovalRules(models.Model):
    _name = 'purchase.order.approval.rules'
    _description = 'Purchase Order Approval Rules'
    _order = 'sequence'

    purchase_order = fields.Many2one('purchase.order', string='Purchase Order', ondelete='cascade')
    sequence = fields.Integer(required=True)
    approval_role = fields.Many2one('purchase.approval.role', string='Approval Role', required=True)
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
                employees = self.env['hr.employee'].search([('purchase_approval_role', '=', rec.approval_role.id), ('user_id.company_ids', 'in', rec.purchase_order.company_id.id)])
                users = self.env['res.users'].search([('employee_ids', 'in', employees.ids)])
                rec.users = [(6, 0, users.ids)]


class QuotationRejectionReason(models.TransientModel):
    _name = 'rfq.rejection.reason'
    _description = 'Quotation Rejection Reason'
    _rec_name = 'reason'

    reason = fields.Text(required=True)

    def button_reject(self):
        if self.env.context.get('active_id'):
            order = self.env['purchase.order'].browse(self.env.context['active_id'])
            if order.purchase_order_approval_rule_ids:
                rules = order.purchase_order_approval_rule_ids.filtered(lambda b: self.env.user in b.users)
                rules.write({'is_approved': False, 'date': fields.Datetime.now(), 'state': 'reject',
                             'user_id': self.env.user.id})

                self.env['purchase.order.approval.history'].create({
                    'purchase_order': order.id,
                    'user': self.env.user.id,
                    'date': fields.Datetime.now(),
                    'state': 'reject',
                    'rejection_reason': self.reason
                })

                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                base_url += '/web#id=%d&view_type=form&model=%s' % (order.id, order._name)

                # ✅ Get the user who submitted the RFQ (send rejection back to them)
                send_to_user = order.user_id or order.create_uid

                subject = 'RFQ Rejected'
                reject_body = f"""
                <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 14px; color: #222; background-color: #f4f6fa; padding: 32px 0;">
                    <div style="max-width: 560px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; overflow: hidden; border: 1px solid #dde2ef;">

                        <!-- Header -->
                        <div style="background-color: #6b1a1a; padding: 32px 40px 24px;">
                            <div style="margin-bottom: 16px;">
                                <span style="font-size: 11px; color: #e8a0a0; letter-spacing: 0.08em; text-transform: uppercase;">Procurement</span>
                            </div>
                            <h1 style="font-size: 22px; font-weight: 600; color: #ffffff; margin: 0 0 4px;">RFQ Rejected</h1>
                            <p style="font-size: 13px; color: #d47a7a; margin: 0;">Action required — please review the rejection reason</p>
                        </div>

                        <!-- Body -->
                        <div style="padding: 32px 40px;">
                            <p style="font-size: 15px; color: #111; font-weight: 600; margin: 0 0 12px;">Hello {send_to_user.name},</p>
                            <p style="font-size: 14px; color: #444; line-height: 1.7; margin: 0 0 24px;">
                                Your RFQ <strong style="color: #111;">{order.name}</strong> has been 
                                <strong style="color: #6b1a1a;">rejected</strong> by 
                                <strong style="color: #111;">{self.env.user.name}</strong>. 
                                Please review the reason below and take the necessary action.
                            </p>

                            <!-- Info Card -->
                            <div style="background-color: #f7f9fc; border-radius: 8px; padding: 16px 20px; margin-bottom: 20px; border-left: 3px solid #6b1a1a;">
                                <table style="width: 100%; border-collapse: collapse;">
                                    <tr>
                                        <td style="padding: 6px 0; width: 50%;">
                                            <p style="font-size: 11px; color: #888; margin: 0 0 2px; text-transform: uppercase; letter-spacing: 0.06em;">Reference</p>
                                            <p style="font-size: 13px; font-weight: 600; color: #111; margin: 0;">{order.name}</p>
                                        </td>
                                        <td style="padding: 6px 0;">
                                            <p style="font-size: 11px; color: #888; margin: 0 0 2px; text-transform: uppercase; letter-spacing: 0.06em;">Rejected By</p>
                                            <p style="font-size: 13px; font-weight: 600; color: #111; margin: 0;">{self.env.user.name}</p>
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding: 6px 0;">
                                            <p style="font-size: 11px; color: #888; margin: 0 0 2px; text-transform: uppercase; letter-spacing: 0.06em;">Status</p>
                                            <p style="margin: 0;">
                                                <span style="background-color: #f8d7da; color: #721c24; padding: 2px 10px; border-radius: 4px; font-size: 12px; font-weight: 500;">Rejected</span>
                                            </p>
                                        </td>
                                    </tr>
                                </table>
                            </div>

                            <!-- Rejection Reason Box -->
                            <div style="background-color: #fff3f3; border-radius: 8px; padding: 16px 20px; margin-bottom: 28px; border-left: 3px solid #e05555;">
                                <p style="font-size: 11px; color: #888; margin: 0 0 6px; text-transform: uppercase; letter-spacing: 0.06em;">Rejection Reason</p>
                                <p style="font-size: 14px; color: #333; margin: 0; line-height: 1.6;">{self.reason or 'No reason provided.'}</p>
                            </div>

                            <!-- CTA Button -->
                            <a href="{base_url}"
                               style="display: inline-block; background-color: #6b1a1a; color: #ffffff; text-decoration: none;
                                      font-size: 13px; font-weight: 600; padding: 10px 24px;
                                      border-radius: 6px; letter-spacing: 0.02em;">
                                View Form &#8594;
                            </a>
                        </div>

                        <!-- Footer -->
                        <div style="border-top: 1px solid #eaecf0; padding: 16px 40px;">
                            <p style="font-size: 11px; color: #aaa; margin: 0;">This is an automated notification.</p>
                        </div>

                    </div>
                </div>
                """

                # ✅ Chatter + Email use the same styled body
                order.message_post(body=Markup(reject_body), subject=subject)

                template_data = {
                    'subject': subject,
                    'body_html': reject_body,
                    'email_from': self.env.user.login,
                    'email_to': send_to_user.login,
                }
                template_id = self.env['mail.mail'].sudo().create(template_data)
                template_id.sudo().send()

                order.write({'is_rejected': True, 'send_for_approval': False})


class ResUsers(models.Model):
    _inherit = 'res.users'

    purchase_id = fields.Many2one('purchase.order', string="Purchase")
