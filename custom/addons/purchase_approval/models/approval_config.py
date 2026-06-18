# -*- coding: utf-8 -*-
# Part of Kanak Infosystems LLP. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ApprovalRole(models.Model):
    _name = 'purchase.approval.role'
    _description = 'Approval Role'

    name = fields.Char(required=True)


class ApprovalCategory(models.Model):
    _name = 'purchase.approval.category'
    _description = 'Approval Category'

    name = fields.Char(required=True)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'
    _description = 'HR Employee'

    purchase_approval_role = fields.Many2many('purchase.approval.role', 'purchase_approval_role_hr_employee_rel', 'purchase_approval_role_id', 'hr_employee_id', string='Purchase Approval Role')
    purchase_order_approval_rule_id = fields.Many2one('purchase.order.approval.rule', related='company_id.purchase_order_approval_rule_id', string='Purchase Order Approval Rules')
    purchase_order_approval = fields.Boolean(related='company_id.purchase_order_approval', string='Purchase Order Approval By Rule')


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    purchase_approval_category = fields.Many2one('purchase.approval.category', string='Purchase Approval Category')
    purchase_order_approval_rule_id = fields.Many2one('purchase.order.approval.rule', related='company_id.purchase_order_approval_rule_id', string='Purchase Order Approval Rules')
    purchase_order_approval = fields.Boolean(related='company_id.purchase_order_approval', string='Purchase Order Approval By Rule')


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'
    _description = 'HR Employee Public'

    purchase_approval_role = fields.Many2many('purchase.approval.role', 'purchase_approval_role_hr_employee_rel', 'purchase_approval_role_id', 'hr_employee_id', string='Purchase Approval Role')
    purchase_order_approval_rule_id = fields.Many2one('purchase.order.approval.rule', related='company_id.purchase_order_approval_rule_id', string='Purchase Order Approval Rules')
    purchase_order_approval = fields.Boolean(related='company_id.purchase_order_approval', string='Purchase Order Approval By Rule')
