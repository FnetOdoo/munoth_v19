# -*- coding: utf-8 -*-
# Part of Kanak Infosystems LLP. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ApprovalRole(models.Model):
    _name = 'approval.role'
    _description = 'Approval Role'

    name = fields.Char(required=True)


class ApprovalCategory(models.Model):
    _name = 'approval.category.knk'
    _description = 'Approval Category'

    name = fields.Char(required=True)


class HrEmployeeBase(models.Model):
    _inherit = 'hr.employee'

    approval_role = fields.Many2many('approval.role', 'approval_role_hr_employee_rel', 'approval_role_id', 'hr_employee_id', string='Sale Approval Role', store=True)
    sale_order_approval_rule_id = fields.Many2one('sale.order.approval.rule', related='company_id.sale_order_approval_rule_id', string='Sale Order Approval Rules', store=True)
    sale_order_approval = fields.Boolean(related='company_id.sale_order_approval', string='Sale Order Approval By Rule', store=True)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    approval_category = fields.Many2one('approval.category.knk', string='Approval Category')
    sale_order_approval_rule_id = fields.Many2one('sale.order.approval.rule', related='company_id.sale_order_approval_rule_id', string='Sale Order Approval Rules')
    sale_order_approval = fields.Boolean(related='company_id.sale_order_approval', string='Sale Order Approval By Rule')
