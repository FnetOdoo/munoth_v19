# -*- coding: utf-8 -*-
# Part of Kanak Infosystems LLP. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class PurchaseCustomWarning(models.TransientModel):
    _name = 'purchase.custom.warning'
    _description = 'Custom Warning'

    def action_continue(self):
        active_id = self.env.context.get('active_id')
        if self.env.context.get('purchase_order'):
            purchase_order = self.env['purchase.order'].search([('id', '=', active_id)])
            if purchase_order.purchase_order_approval_rule_ids:
                purchase_order.message_subscribe(
                    partner_ids=purchase_order.purchase_order_approval_rule_ids.mapped(
                        'users.partner_id.id'))
                msg = _("RFQ is waiting for approval.")
                purchase_order.message_post(body=msg, subtype_xmlid='mail.mt_comment')
            self.env['purchase.order.approval.history'].create({
                'purchase_order': purchase_order.id,
                'user': self.env.user.id,
                'date': fields.Datetime.now(),
                'state': 'send_for_approval'
            })
            purchase_order.write({'send_for_approval': True, 'is_rejected': False})
        return True
