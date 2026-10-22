from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta
import json


class AccountPayment(models.Model):
    # These fields came from base_accounting_kit on fnet, which munoth does not have.
    _inherit = 'account.payment'

    bank_reference = fields.Char(string="Bank Reference", copy=False)
    cheque_reference = fields.Char(string="Cheque Reference", copy=False)
    effective_date = fields.Date('Effective Date', help='Effective date of PDC', copy=False)


class AccountMove(models.Model):
    _inherit = 'account.move'

    cust_invoice_id = fields.Many2one('account.move', 'Customer Invoice')
    cust_invoice_partner_id = fields.Many2one('res.partner', string="Invoice Customer",related='cust_invoice_id.partner_id', store=True)
    cust_invoice_name = fields.Char(related='cust_invoice_id.name', store=True)
    cust_invoice_amount_residual = fields.Monetary(related='cust_invoice_id.amount_residual', string="Invoice Amount Due", store=True)
    bill_select = fields.Boolean('Select')
    payment_request_number = fields.Char()
    reference_1 = fields.Char("Reference")

    def payment_request(self):
        if any(bill.move_type != 'in_invoice' for bill in self):
            raise UserError(_('Please select the vendor bill only'))

        if any(bill.state != 'posted' for bill in self):
            raise UserError(_('Please choose the posted bills'))

        if any(bill.payment_state in ('paid', 'in_payment') for bill in self):
            raise UserError(_('Please choose the unpaid bills'))

        # Check if any selected bill has zero residual amount
        zero_balance_bills = self.filtered(lambda bill: bill.amount_residual == 0)
        if zero_balance_bills:
            bill_names = ', '.join(zero_balance_bills.mapped('name'))
            raise UserError(
                _('The following bills have zero balance and cannot be added to a payment request:\n%s') % bill_names
            )

        matched_bills = []
        for bill in self:
            payment_request = self.env['payment.request'].search(
                [('line_ids.account_move_id', '=', bill.id),
                 ('state', 'in', ['finance_approval', 'md_approval'])])
            if payment_request:
                matched_bills.append(bill.name)
        if matched_bills:
            raise UserError(
                _('Payment request is ALREADY created for following bills. Please check.\n%s') % (matched_bills))

        # 10-day cooldown: prevent re-creating payment requests for the same bill
        # within 10 days of the previous request date
        today = fields.Date.today()
        cooldown_bills = []
        for bill in self:
            latest_request = self.env['payment.request'].search(
                [('line_ids.account_move_id', '=', bill.id),
                 ('state', 'not in', ['cancel', 'reject'])],
                order='payment_request_date desc, id desc',
                limit=1)
            if latest_request:
                request_date = latest_request.payment_request_date
                if request_date and (today - request_date).days < 10:
                    next_allowed_date = request_date + timedelta(days=10)
                    cooldown_bills.append(
                        '%s (last request: %s, next allowed: %s)' % (
                            bill.name,
                            request_date.strftime('%d-%m-%Y'),
                            next_allowed_date.strftime('%d-%m-%Y'),
                        )
                    )
        if cooldown_bills:
            raise UserError(
                _('A new payment request can only be created after 10 days from the previous request date.\n\n%s')
                % ('\n'.join(cooldown_bills)))

        line_vals = []
        for bill in self:
            line_vals.append((0, 0, {
                'account_move_id': bill.id,
                'request_amount': abs(bill.amount_residual_signed),
            }))
        self.env['payment.request'].create({'line_ids': line_vals})
        return True

    def _tax_group_amounts(self):
        """{tax group name: tax amount} for this document, in its own currency.

        v15 kept this in tax_totals_json, a JSON string shaped

            {'amount_untaxed': .., 'groups_by_subtotal':
                {'Untaxed Amount': [{'tax_group_name': .., 'tax_group_amount': ..}]}}

        The field is gone from v16 onward. v19 has tax_totals, already a dict, and
        shaped differently:

            {'base_amount_currency': .., 'subtotals':
                [{'tax_groups': [{'group_name': .., 'tax_amount_currency': ..}]}]}

        Read through get() throughout so a further change of shape leaves the
        report with a zero rather than a traceback in front of a vendor.
        """
        self.ensure_one()
        amounts = {}
        for subtotal in (self.tax_totals or {}).get('subtotals') or []:
            for group in subtotal.get('tax_groups') or []:
                name = group.get('group_name') or ''
                amount = group.get('tax_amount_currency')
                if amount is None:
                    amount = group.get('tax_amount') or 0.0
                amounts[name] = amounts.get(name, 0.0) + amount
        return amounts

    def un_tax_amount(self):
        groups = self._tax_group_amounts()
        cgst_amount = groups.get('CGST', 0.00)
        sgst_amount = groups.get('SGST', 0.00)
        igst_amount = groups.get('IGST', 0.00)
        taxes_amount = groups.get('Taxes', 0.00)
        debit_total = 0.00

        un_tax_amount = self.amount_untaxed
        if groups:
            total_amount = un_tax_amount + cgst_amount + sgst_amount + igst_amount
            tax_reduced = taxes_amount
            amount_paid = total_amount + taxes_amount + self.amount_tds
        else:
            total_amount = un_tax_amount
            amount_paid = un_tax_amount + self.amount_tds
            tax_reduced = self.amount_tds
        # v15 called this one2many reversal_move_id; v19 names it reversal_move_ids.
        if self.reversal_move_ids:
            debit_total = sum(self.reversal_move_ids
                              .filtered(lambda x: x.payment_state == 'paid')
                              .mapped('amount_total_signed'))
        vals = {
            'total_amount': total_amount or 0.00,
            'tax_reduced': abs(tax_reduced) or 0.00,
            'amount_paid': amount_paid or 0.00,
            'debit_amount': debit_total or 0.00,
        }
        return vals


