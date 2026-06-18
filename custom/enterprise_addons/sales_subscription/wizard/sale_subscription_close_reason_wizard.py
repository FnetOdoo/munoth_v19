# -*- coding: utf-8 -*-
from odoo import api, fields, models


class SaleSubscriptionCloseReasonWizard(models.TransientModel):
    _name = "sales.subscription.close.reason.wizard"
    _description = 'Subscription Close Reason Wizard'

    close_reason_id = fields.Many2one("sales.subscription.close.reason", string="Close Reason")

    def set_close_cancel(self):
        self.ensure_one()
        subscription = self.env['sales.subscription'].browse(self.env.context.get('active_id'))
        subscription.close_reason_id = self.close_reason_id
        subscription.set_close()
