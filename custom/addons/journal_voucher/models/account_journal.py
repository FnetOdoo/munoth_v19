# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from datetime import datetime
import time
from dateutil.relativedelta import relativedelta
from lxml import etree
from odoo.exceptions import UserError, RedirectWarning, ValidationError


class AccountJournal(models.Model):
    _inherit = "account.journal"
    _description = "Account Journal"

    type = fields.Selection([
            ('sale', 'Sale'),
            ('purchase', 'Purchase'),
            ('cash', 'Cash'),
            ('bank', 'Bank'),
            ('general', 'Miscellaneous'),
            ('contra','Contra')
        ], required=True,
        help="Select 'Sale' for customer invoices journals.\n"\
        "Select 'Purchase' for vendor bills journals.\n"\
        "Select 'Cash' or 'Bank' for journals that are used in customer or vendor payments.\n"\
        "Select 'General' for miscellaneous operations journals.\n"\
        "Select 'Contra' for Contra operations journals.")


class AccountPayment(models.Model):
    _inherit = "account.payment"
    _description = "Account Payment"

    account_analytic_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    # analytic_tag_ids field removed - account.analytic.tag model removed in Odoo 19
    voucher_id = fields.Many2one('account.voucher', string='Voucher')


    def _prepare_payment_moves(self):
        ''' Prepare the creation of journal entries (account.move) by creating a list of python dictionary to be passed
        to the 'create' method.

        Example 1: outbound with write-off:

        Account             | Debit     | Credit
        ---------------------------------------------------------
        BANK                |   900.0   |
        RECEIVABLE          |           |   1000.0
        WRITE-OFF ACCOUNT   |   100.0   |

        Example 2: internal transfer from BANK to CASH:

        Account             | Debit     | Credit
        ---------------------------------------------------------
        BANK                |           |   1000.0
        TRANSFER            |   1000.0  |
        CASH                |   1000.0  |
        TRANSFER            |           |   1000.0

        :return: A list of Python dictionary to be passed to env['account.move'].create.
        '''
        all_move_vals = []
        for payment in self:
            company_currency = payment.company_id.currency_id
            move_names = payment.move_name.split(payment._get_move_name_transfer_separator()) if payment.move_name else None

            # Compute amounts.
            write_off_amount = payment.payment_difference_handling == 'reconcile' and -payment.payment_difference or 0.0
            if payment.payment_type in ('outbound', 'transfer'):
                counterpart_amount = payment.amount
                liquidity_line_account = payment.journal_id.default_debit_account_id
            else:
                counterpart_amount = -payment.amount
                liquidity_line_account = payment.journal_id.default_credit_account_id

            # Manage currency.
            if payment.currency_id == company_currency:
                # Single-currency.
                balance = counterpart_amount
                write_off_balance = write_off_amount
                counterpart_amount = write_off_amount = 0.0
                currency_id = False
            else:
                # Multi-currencies.
                balance = payment.currency_id._convert(counterpart_amount, company_currency, payment.company_id, payment.payment_date)
                write_off_balance = payment.currency_id._convert(write_off_amount, company_currency, payment.company_id, payment.payment_date)
                currency_id = payment.currency_id.id

            # Manage custom currency on journal for liquidity line.
            if payment.journal_id.currency_id and payment.currency_id != payment.journal_id.currency_id:
                # Custom currency on journal.
                if payment.journal_id.currency_id == company_currency:
                    # Single-currency
                    liquidity_line_currency_id = False
                else:
                    liquidity_line_currency_id = payment.journal_id.currency_id.id
                liquidity_amount = company_currency._convert(
                    balance, payment.journal_id.currency_id, payment.company_id, payment.payment_date)
            else:
                # Use the payment currency.
                liquidity_line_currency_id = currency_id
                liquidity_amount = counterpart_amount

            # Compute 'name' to be used in receivable/payable line.
            rec_pay_line_name = ''
            if payment.payment_type == 'transfer':
                rec_pay_line_name = payment.name
            else:
                if payment.partner_type == 'customer':
                    if payment.payment_type == 'inbound':
                        rec_pay_line_name += _("Customer Payment")
                    elif payment.payment_type == 'outbound':
                        rec_pay_line_name += _("Customer Credit Note")
                elif payment.partner_type == 'supplier':
                    if payment.payment_type == 'inbound':
                        rec_pay_line_name += _("Vendor Credit Note")
                    elif payment.payment_type == 'outbound':
                        rec_pay_line_name += _("Vendor Payment")
                if payment.invoice_ids:
                    rec_pay_line_name += ': %s' % ', '.join(payment.invoice_ids.mapped('name'))

            # Compute 'name' to be used in liquidity line.
            if payment.payment_type == 'transfer':
                liquidity_line_name = _('Transfer to %s') % payment.destination_journal_id.name
            else:
                liquidity_line_name = payment.name

            # ==== 'inbound' / 'outbound' ====

            move_vals = {
                'date': payment.payment_date,
                'ref': payment.communication,
                'journal_id': payment.journal_id.id,
                'currency_id': payment.journal_id.currency_id.id or payment.company_id.currency_id.id,
                'partner_id': payment.partner_id.id,
                'line_ids': [
                    # Receivable / Payable / Transfer line.
                    (0, 0, {
                        'name': rec_pay_line_name,
                        'amount_currency': counterpart_amount + write_off_amount if currency_id else 0.0,
                        'currency_id': currency_id,
                        'debit': balance + write_off_balance > 0.0 and balance + write_off_balance or 0.0,
                        'credit': balance + write_off_balance < 0.0 and -balance - write_off_balance or 0.0,
                        'date_maturity': payment.payment_date,
                        'partner_id': payment.partner_id.commercial_partner_id.id,
                        'account_id': payment.destination_account_id.id,
                        'payment_id': payment.id,
                        'analytic_distribution': {str(payment.account_analytic_id.id): 100.0} if payment.account_analytic_id else False,
                        # 'analytic_tag_ids': removed in Odoo 19
                    }),
                    # Liquidity line.
                    (0, 0, {
                        'name': liquidity_line_name,
                        'amount_currency': -liquidity_amount if liquidity_line_currency_id else 0.0,
                        'currency_id': liquidity_line_currency_id,
                        'debit': balance < 0.0 and -balance or 0.0,
                        'credit': balance > 0.0 and balance or 0.0,
                        'date_maturity': payment.payment_date,
                        'partner_id': payment.partner_id.commercial_partner_id.id,
                        'account_id': liquidity_line_account.id,
                        'payment_id': payment.id,
                        'analytic_distribution': {str(payment.account_analytic_id.id): 100.0} if payment.account_analytic_id else False,
                        # 'analytic_tag_ids': removed in Odoo 19
                    }),
                ],
            }
            if write_off_balance:
                # Write-off line.
                move_vals['line_ids'].append((0, 0, {
                    'name': payment.writeoff_label,
                    'amount_currency': -write_off_amount,
                    'currency_id': currency_id,
                    'debit': write_off_balance < 0.0 and -write_off_balance or 0.0,
                    'credit': write_off_balance > 0.0 and write_off_balance or 0.0,
                    'date_maturity': payment.payment_date,
                    'partner_id': payment.partner_id.commercial_partner_id.id,
                    'account_id': payment.writeoff_account_id.id,
                    'payment_id': payment.id,
                    'analytic_distribution': {str(payment.account_analytic_id.id): 100.0} if payment.account_analytic_id else False,
                    # 'analytic_tag_ids': removed in Odoo 19
                }))

            if move_names:
                move_vals['name'] = move_names[0]

            all_move_vals.append(move_vals)

            # ==== 'transfer' ====
            if payment.payment_type == 'transfer':
                journal = payment.destination_journal_id

                # Manage custom currency on journal for liquidity line.
                if journal.currency_id and payment.currency_id != journal.currency_id:
                    # Custom currency on journal.
                    liquidity_line_currency_id = journal.currency_id.id
                    transfer_amount = company_currency._convert(balance, journal.currency_id, payment.company_id, payment.payment_date)
                else:
                    # Use the payment currency.
                    liquidity_line_currency_id = currency_id
                    transfer_amount = counterpart_amount

                transfer_move_vals = {
                    'date': payment.payment_date,
                    'ref': payment.communication,
                    'partner_id': payment.partner_id.id,
                    'journal_id': payment.destination_journal_id.id,
                    'line_ids': [
                        # Transfer debit line.
                        (0, 0, {
                            'name': payment.name,
                            'amount_currency': -counterpart_amount if currency_id else 0.0,
                            'currency_id': currency_id,
                            'debit': balance < 0.0 and -balance or 0.0,
                            'credit': balance > 0.0 and balance or 0.0,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.commercial_partner_id.id,
                            'account_id': payment.company_id.transfer_account_id.id,
                            'payment_id': payment.id,
                            'analytic_distribution': {str(payment.account_analytic_id.id): 100.0} if payment.account_analytic_id else False,
                            # 'analytic_tag_ids': removed in Odoo 19
                        }),
                        # Liquidity credit line.
                        (0, 0, {
                            'name': _('Transfer from %s') % payment.journal_id.name,
                            'amount_currency': transfer_amount if liquidity_line_currency_id else 0.0,
                            'currency_id': liquidity_line_currency_id,
                            'debit': balance > 0.0 and balance or 0.0,
                            'credit': balance < 0.0 and -balance or 0.0,
                            'date_maturity': payment.payment_date,
                            'partner_id': payment.partner_id.commercial_partner_id.id,
                            'account_id': payment.destination_journal_id.default_credit_account_id.id,
                            'payment_id': payment.id,
                            'analytic_distribution': {str(payment.account_analytic_id.id): 100.0} if payment.account_analytic_id else False,
                            # 'analytic_tag_ids': removed in Odoo 19
                        }),
                    ],
                }

                if move_names and len(move_names) == 2:
                    transfer_move_vals['name'] = move_names[1]

                all_move_vals.append(transfer_move_vals)
        return all_move_vals


class AccountMove(models.Model):
    _inherit = "account.move"
    _description = "Account Move"

    _PAYMENT_MODE = [('cheque' , 'Cheque'), ('demand_draft' , 'Demand Draft'), ('neft' , 'NEFT'), ('rtgs' , 'RTGS'), ('imps' , 'IMPS'),('debit_card' , 'Debit Card'), ('credit_card' , 'Credit Card'), ('cash' , 'Cash'),
                     ('check_return','Cheque Return'),('inter_party_adj','Inter-Party Adjustments')]
    _CARD_TYPE = [('visa' , 'VISA'), ('master_card', 'MASTER CARD'), ('others', 'OTHERS')]

    @api.model
    def _get_journal(self):
        res = []
        ttype = self._context.get('journal_type')
        if ttype:
            res = self.env['account.journal'].search([('name', '=', ttype)], limit=1)
        else:
            # In Odoo 19, _get_default_journal doesn't exist in base account.move
            move_type = self._context.get('default_move_type', 'entry')
            journal_type = 'general'
            if move_type in ('out_invoice', 'out_refund', 'out_receipt'):
                journal_type = 'sale'
            elif move_type in ('in_invoice', 'in_refund', 'in_receipt'):
                journal_type = 'purchase'
            res = self.env['account.journal'].search([('type', '=', journal_type), ('company_id', '=', self.env.company.id)], limit=1)
        return res

    user_id = fields.Many2one('res.users','Created User',default=lambda self: self.env.user)
    payment_mode = fields.Selection(_PAYMENT_MODE,'Payment Mode',default='cheque')
    reference = fields.Char('Reference', help="Cheque No/DD No/UTR No/Card No", copy=False)
    ref_date = fields.Date('Ref Date', help="Effective date for payment Reference", copy=False)
    bank_id = fields.Many2one('res.partner.bank','Bank Account')
    bank = fields.Char('Bank')
    in_favour_of = fields.Char('In Favour Of',size=64,store=True)
    imps_ref = fields.Char('Ref.Name',size=64)
    card_name = fields.Char('Name Of Card',size=64)
    card_type = fields.Selection(_CARD_TYPE,'Card Type',default='visa')
    branch_code = fields.Char('Branch Code',size=64)
    remarks = fields.Text('Remarks')
    parent_id = fields.Many2one('account.move', string='Parent')
    reverse_entry = fields.Boolean(string='Reverse Entry')
    journal_id = fields.Many2one('account.journal', string='Journal', required=True, domain="[('company_id', '=', company_id)]",
                                 default=_get_journal,)

    def _reverse_moves(self, default_values_list=None, cancel=False):
        """Point each reverse at the entry it reverses.

        This read self.id on a recordset, so reversing more than one entry at a time
        stopped with

            ValueError: Expected singleton: account.move(5578, 5579, 5575, ...)

        and it wrote the same parent onto every reverse, which is wrong even when there
        is only one. Odoo reverses several entries in one call whenever a reconciliation
        that produced exchange differences is undone:

            addons/account/models/account_partial_reconcile.py
            moves_to_reverse += self.exchange_move_id
            ...
            not_draft_moves._reverse_moves(default_values_list, cancel=True)

        so undoing a reconciliation with several exchange entries behind it could not be
        done at all -- which is what an accountant hit trying to unpick the payments on
        MAR/2026-27/0657 on the 19th and 21st of August.

        Each reverse is paired with its original through reversed_entry_id, which Odoo
        sets itself, rather than by position.
        """
        reverses = super(AccountMove, self)._reverse_moves(
            default_values_list=default_values_list, cancel=cancel)
        for reverse in reverses:
            if reverse.reversed_entry_id:
                reverse.parent_id = reverse.reversed_entry_id
            reverse.reverse_entry = True
        return reverses


    @api.onchange('line_ids')
    def onchange_in_favour(self):
        partner_list = []
        if not self.line_ids:
            self.in_favour_of = " "
        if self.line_ids:
            for line in self.line_ids:
                if line.partner_id and line.partner_id not in partner_list:
                    partner_list.append(line.partner_id)
            if len(partner_list) == 1 :
                self.in_favour_of= partner_list[0].in_favour_of or partner_list[0].name.upper()
            elif len(partner_list) == 0 :
                self.in_favour_of = ""
            else:
                self.in_favour_of = "MULTIPLE PARTIES"


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"
    _description = "Account Move Line"

    voucher_account_type = fields.Selection([('gl','GL'),('customer','Customer'),('supplier','Supplier')], 'Account Type',default='gl', copy=True)

    @api.onchange('voucher_account_type')
    def onchange_voucher_account_type(self):
        self.partner_id = False
        self.account_id = False
        # self.analytic_tag_ids = False  # removed in Odoo 19
        # Odoo 19: account.account dropped user_type_id/deprecated in favor of
        # account_type/active, and res.partner dropped the customer/supplier
        # booleans in favor of customer_rank/supplier_rank.
        if self.voucher_account_type=='gl':
            return {'domain':{'account_id':[('account_type','not in',('asset_receivable','liability_payable')),('active', '=', True)]}}
        if self.voucher_account_type=='customer':
            return {'domain':{'partner_id':[('customer_rank','>',0)],'account_id':[('account_type','=','asset_receivable'),('active', '=', True)]}}
        if self.voucher_account_type=='supplier':
            return {'domain':{'partner_id':[('supplier_rank','>',0)],'account_id':[('account_type','=','liability_payable'),('active', '=', True)]}}


    @api.onchange('partner_id')
    def onchange_partner(self):
        if self.voucher_account_type=='customer' and self.partner_id:
            self.account_id = self.partner_id.property_account_receivable_id.id or False
        if self.voucher_account_type=='supplier' and self.partner_id:
            self.account_id = self.partner_id.property_account_payable_id.id or False


class Partners(models.Model):
    _inherit = 'res.partner'

    in_favour_of = fields.Char('In Favour Of', size=64, store=True)






