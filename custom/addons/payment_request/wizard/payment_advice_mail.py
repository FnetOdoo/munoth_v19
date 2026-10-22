from odoo import api, models, fields,_
from odoo.exceptions import ValidationError
import base64


class PaymentAdviceMail(models.Model):
    _name = 'payment.advice.mail'

    email_to = fields.Char()
    email_cc = fields.Char()
    partner_id = fields.Many2one('res.partner')

    def action_mail_send(self):
        record_ids = self.env.context.get('active_ids', [])
        rec = self.env['account.payment'].search([('id', 'in', record_ids)], limit=1)
        report_template_id = self.env.ref('payment_request.action_report_vendor_payment_receipt')._render_qweb_pdf(rec.id)
        data_record = base64.b64encode(report_template_id[0])
        ir_values = {
            'name': "Payment Advice.pdf",
            'type': 'binary',
            'datas': data_record,
            'store_fname': data_record,
            'mimetype': 'application/x-pdf',
        }
        attachment = self.env['ir.attachment'].create(ir_values)
        mail_template = self.env.ref('payment_request.email_account_payment_advice_email_template')
        if not self.email_to:
            raise ValidationError(_('Please enter the "Email To" Address'))
        email = {
            'email_to' : self.email_to or '',
            'email_cc': self.email_cc or '',
            'partner_to': False,
        }
        mail_template.write(email)
        mail_template.write({'attachment_ids': [(6, 0, [attachment.id])]})
        mail_template.send_mail(rec.id, force_send=True)