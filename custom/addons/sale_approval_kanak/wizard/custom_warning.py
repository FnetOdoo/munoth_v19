# -*- coding: utf-8 -*-
# Part of Kanak Infosystems LLP. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class CustomWarning(models.TransientModel):
    _name = 'custom.warning'
    _description = 'Custom Warning'

    def action_continue(self):
        active_id = self.env.context.get('order_id')
        if active_id:
            if self.env.context.get('sale_order'):
                sale_order = self.env['sale.order'].browse(active_id)
                if sale_order.sale_order_approval_rule_ids:
                    sale_order.message_subscribe(
                        partner_ids=sale_order.sale_order_approval_rule_ids.mapped(
                            'users.partner_id.id'))
                    msg = _("Quotation is waiting for approval.")
                    sale_order.message_post(body=msg, subtype_xmlid='mail.mt_comment')

                self.env['sale.order.approval.history'].create({
                    'sale_order': sale_order.id,
                    'user': self.env.user.id,
                    'date': fields.Datetime.now(),
                    'state': 'send_for_approval'
                })
                sale_order.write({'send_for_approval': True, 'is_rejected': False})

        return True
