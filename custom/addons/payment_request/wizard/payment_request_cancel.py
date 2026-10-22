from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
import base64


class AccountPaymentChequeWizard(models.TransientModel):
    _name = 'payment.request.cancel.reason'
    _description = 'Payment Request Cancel Reason'

    name = fields.Text('Cancel Reason', required=True)
    payment_request_id = fields.Many2one('payment.request')

    def action_update_cancel_reason(self):
        print(self.id)
        payment_request_obj = self.env['payment.request'].search([('id', '=', self.payment_request_id.id)])
        print(payment_request_obj)
        if payment_request_obj:
            payment_request_obj.write({'cancel_reason': self.name, 'state': 'finance_approval'})

            payment_request_obj.message_post(body=self.name)

            mail_template = self.env.ref('payment_request.email_payment_request_state_changed_to_draft')
            mail_template.send_mail(self.id, force_send=True)




