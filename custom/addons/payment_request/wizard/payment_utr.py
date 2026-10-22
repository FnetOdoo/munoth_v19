from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
from odoo.exceptions import UserError, AccessError
import base64


class AccountPaymentUtrWizard(models.TransientModel):
    _name = 'account.payment.utr.wizard'
    _description = 'Payment UTR Number Generations'

    utr_number = fields.Char(string='UTR No.')
    payment_line_ids = fields.Many2many('account.payment')

    def action_action_update_utr(self):
        for record in self:
            for payment in record.payment_line_ids:
                # v15 had account.payment.state = 'posted'. v19 has no such state:
                # a payment reads draft, in_process, paid, canceled or rejected, and
                # the old test was written as `state not in "posted"`, a substring
                # check, so every one of those raises and the button never works.
                # What the message means is that the payment's journal entry must be
                # posted, so that is what is asked.
                if payment.move_id.state != 'posted':
                    raise UserError(_('Please select the Posted payment journals'))
            record.payment_line_ids.write({'bank_reference': record.utr_number})
