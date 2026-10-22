from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
import base64
from num2words import num2words
from odoo.exceptions import UserError, AccessError


class AccountPaymentChequeWizard(models.TransientModel):
    _name = 'account.payment.cheque.wizard'
    _description = 'Payment Cheque Number Generations'

    cheque_number = fields.Char(string='Cheque Number', required=True)
    cheque_date = fields.Date(string='Cheque date', required=True)
    payment_line_ids = fields.Many2many('account.payment')
    cheque_name = fields.Char("Name of the Cheque", required=True)
    total_amount = fields.Float('Total Amount')
    amount_text = fields.Text('Amount Text')


    def action_action_update_cheque(self):
        for rec in self:
            for payment in rec.payment_line_ids:
                # Same as payment_utr: 'posted' is not one of v19's payment states,
                # and the test was a substring check, so it refused everything.
                if payment.move_id.state != 'posted':
                    raise UserError(_('Please select the Posted payment journals'))
            rec.payment_line_ids.write({'cheque_reference': rec.cheque_number, 'cheque_date': rec.cheque_date, 'payment_type':'outbound'})

            rec.total_amount = abs(sum(rec.payment_line_ids.mapped('amount_company_currency_signed')))
            cheque_reference = rec.payment_line_ids.mapped('name')

            rec.amount_text = num2words(rec.total_amount, lang='en_IN').title()
            report_template_id = self.env.ref('payment_request.bank_check_move')._render_qweb_pdf(self.id)
            data_record = base64.b64encode(report_template_id[0])
            att = self.env['ir.attachment'].create({
                'name': "Cheque",
                'type': 'binary',
                'datas': data_record,
                'store_fname': data_record,
                'mimetype': 'application/x-pdf',
            })
            for payment in rec.payment_line_ids:
                payment.message_post(body=cheque_reference, attachment_ids=[att.id])
            return self.env.ref('payment_request.bank_check_move').report_action(self)




class ChequeNumberPayment(models.Model):
    _name = "payment.cheque.number"
    name = fields.Char('Cheque Number')
