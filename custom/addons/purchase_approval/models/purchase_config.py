# -*- coding: utf-8 -*-
# Part of Kanak Infosystems LLP. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    purchase_order_approval_rule_id = fields.Many2one('purchase.order.approval.rule', related='company_id.purchase_order_approval_rule_id', string='Purchase Order Approval Rules', readonly=False)
    purchase_order_approval = fields.Boolean(related='company_id.purchase_order_approval', string='Purchase Order Approval By Rule', readonly=False)


class PurchaseOrderApprovalRule(models.Model):
    _name = 'purchase.order.approval.rule'
    _description = 'Purchase Order Approval Rule'

    name = fields.Char(required=True)
    approval_rule_ids = fields.One2many('purchase.order.approval.rule.lines', 'approval_rule_id', string='Approval Rule Lines')



class PurchaseConfigApprovalRules(models.Model):
    _name = 'purchase.order.approval.rule.lines'
    _description = 'Purchase Config Approval Rules'

    approval_rule_id = fields.Many2one('purchase.order.approval.rule')
    sequence = fields.Integer(string='Sequence', required=True)
    approval_role = fields.Many2one('purchase.approval.role', string='Approval Role', required=True)
    approval_category = fields.Many2one('purchase.approval.category', string='Approval Category')
    email_template = fields.Many2one('mail.template', string='Mail Template')
    team_id = fields.Many2one('crm.team', 'Team')
    quotation_lower_limit = fields.Float(string="Lower Limit", required=True)
    quotation_upper_limit = fields.Float(string="Upper Limit", required=True)

    @api.constrains('quotation_upper_limit')
    def _constrains_reconcile(self):
        for record in self:
            if record.quotation_upper_limit <= record.quotation_lower_limit and record.quotation_upper_limit != -1:
                raise UserError(_('An Upper limit must be grater then lower limit'))
