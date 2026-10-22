# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, exceptions, models, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from datetime import datetime
import time
from dateutil.relativedelta import relativedelta
from lxml import etree


# from odoo.exceptions import UserError, RedirectWarning, ValidationError, Warning


class Followers(models.Model):
    _inherit = 'mail.followers'

    @api.model
    def create(self, vals):
        if 'res_model' in vals and 'res_id' in vals and 'partner_id' in vals:
            dups = self.env['mail.followers'].search([('res_model', '=', vals.get('res_model')),
                                                      ('res_id', '=', vals.get('res_id')),
                                                      ('partner_id', '=', vals.get('partner_id'))])
            if len(dups):
                for p in dups:
                    p.unlink()
        return super(Followers, self).create(vals)


class AccountVoucher(models.Model):
    _name = "account.voucher"
    _description = "Account Voucher"
    _inherit = ['mail.thread']
    _order = "create_date desc"

    _PAYMENT_MODE = [('cheque', 'Cheque'), ('demand_draft', 'Demand Draft'), ('neft', 'NEFT'), ('rtgs', 'RTGS'),
                     ('imps', 'IMPS'), ('debit_card', 'Debit Card'), ('credit_card', 'Credit Card'), ('cash', 'Cash')]
    _CARD_TYPE = [('visa', 'VISA'), ('master_card', 'MASTER CARD'), ('others', 'OTHERS')]

    def voucher_update(self):
        check_data = self.env['account.voucher'].search([('state','=','draft'),('create_id','=',2)])
        for check in check_data:
            if not check.number or check.number != check.name :
                check.number = check.name

    def voucher_post(self):
        check_data = self.env['account.voucher'].search([('state','=','draft'),('create_id','=',2)],limit=500)
        for check in check_data:
            check.action_move_line_create()


    @api.model
    def _get_journal(self):
        ttype = self._context.get('journal_type')
        if ttype:
            res = self.env['account.journal'].search([('type', '=', ttype)], limit=1)
        return res

    @api.model
    def _get_currency(self):
        if self.journal_id:
            return self.journal_id.currency_id
        return self.company_id.currency_id

    @api.depends('move_ids.account_id', 'move_ids.full_reconcile_id')
    def _check_paid(self):
        self.paid = any(
            [((line.account_id.type, 'in', ('receivable', 'payable')) and line.full_reconcile_id) for line in
             self.move_ids])

    @api.model
    def _get_tax(self):
    #     if not self.journal_id:
    #         ttype = self._context.get('type', 'bank')
    #         if ttype in ('payment', 'receipt'):
    #             ttype = 'bank'
    #         res = self.env['account.journal'].search([('type', '=', ttype)], limit=1)
    #         if not res:
    #             return False
    #         journal_id = res
    #     account_id = journal_id.default_credit_account_id or journal_id.default_debit_account_id
    #     if account_id and account_id.tax_ids:
    #         tax_id = account_id.tax_ids[0].id
    #         return tax_id
        return False

    @api.depends('journal_id', 'company_id')
    def _get_writeoff_amount(self):
        for voucher in self:
            debit = credit = 0.0
            sign = voucher.type == 'payment' and -1 or 1
            for l in voucher.line_dr_ids:
                debit += l.amount
            for l in voucher.line_cr_ids:
                credit += l.amount
            currency = voucher.currency_id or voucher.company_id.currency_id
            self.writeoff_amount = currency.round(voucher.amount - sign * (credit - debit))

    @api.model
    def _get_payment_rate_currency(self):
        if self.journal_id:
            journal = self.journal_id
            if journal.currency_id:
                return journal.currency_id.id
        return self.env.user.company_id.currency_id

    @api.depends('line_ids.amount', 'line_ids.paid_check')
    def compute_amount(self):
        for voucher in self:
            voucher_amount = 0.00
            amount = 0.00
            for line in voucher.line_ids:
                if line.paid_check == False:
                    amount += line.amount
                voucher_amount += line.amount
            voucher.update({'amount': amount, 'voucher_amount': voucher_amount})

    @api.depends('date', 'payment_rate_currency_id', 'currency_id')
    def _paid_amount_in_company_currency(self):
        ctx = self._context.copy()
        self.paid_amount_in_company_currency = 0.00
        for v in self:
            ctx.update({'date': v.date})
            ctx.update({
                'voucher_special_currency': self.payment_rate_currency_id and self.payment_rate_currency_id.id or False,
                'voucher_special_currency_rate': self.currency_id.rate * self.payment_rate, })
            v.paid_amount_in_company_currency = self.currency_id.with_context(ctx).compute(self.amount,
                                                                                           self.company_id.currency_id)

    def name_get(self):
        return [(r['id'], (r['number'] or _('Voucher'))) for r in self.read(['number'], load='_classic_write')]

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        mod_obj = self.env['ir.model.data']
        if self._context is None: self._context = {}
        res = super(AccountVoucher, self).fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar,
                                                          submenu=submenu)
        doc = etree.XML(res['arch'])
        if self._context.get('type', 'sale') in ('purchase', 'payment'):
            nodes = doc.xpath("//field[@name='partner_id']")
            for node in nodes:
                node.set('context', "{'default_customer': 0, 'search_default_supplier': 1, 'default_supplier': 1}")
                if self._context.get('invoice_type', '') in ('in_invoice', 'in_refund'):
                    node.set('string', _("Supplier"))
        res['arch'] = etree.tostring(doc)
        return res

    def _compute_writeoff_amount(self, line_dr_ids, line_cr_ids, amount, type):
        debit = credit = 0.0
        sign = type == 'payment' and -1 or 1
        for l in line_dr_ids:
            if isinstance(l, dict):
                debit += l['amount']
        for l in line_cr_ids:
            if isinstance(l, dict):
                credit += l['amount']
        return amount - sign * (credit - debit)

    # fields
    type = fields.Selection([
        ('receipt', 'Receipt'),
        ('payment', 'Payment')], 'Default Type', copy=True)
    name = fields.Char('Memo', default='', copy=False)
    date = fields.Date('Date', required=True, help="Effective date for Posting Date", copy=False, default=fields.Date.context_today)
    journal_id = fields.Many2one('account.journal', 'Journal', required=True, copy=True)
    account_id = fields.Many2one('account.account', 'Account', required=True,
                                 )
    line_ids = fields.One2many('account.voucher.line', 'voucher_id', 'Voucher Lines')
    line_cr_ids = fields.One2many('account.voucher.line', 'voucher_id', 'Credits', domain=[('type', '=', 'cr')],
                                  context={'default_type': 'cr'})
    line_dr_ids = fields.One2many('account.voucher.line', 'voucher_id', 'Debits', domain=[('type', '=', 'dr')],
                                  context={'default_type': 'dr'})
    narration = fields.Text('Notes', copy=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True, default=lambda self: self.env.user.company_id.currency_id)
    company_id = fields.Many2one('res.company', 'Company', required=True, default=lambda self: self.env.user.company_id)
    state = fields.Selection(
        [('draft', 'Draft'), ('cancel', 'Cancelled'), ('proforma', 'Pro-forma'), ('posted', 'Posted')], 'Status',
        readonly=True, copy=False, default='draft')
    amount = fields.Float(string='Total', store=True, readonly=True, copy=False, compute='compute_amount')
    voucher_amount = fields.Float(string='Voucher Total', readonly=True, copy=False, compute='compute_amount',store=True)
    tax_amount = fields.Float(string='Tax Amount', readonly=True, copy=False)
    reference = fields.Char('Reference', help="Cheque No / DD No / UTR No / Card No / Etc", copy=False)
    number = fields.Char(string='Number', readonly=True, copy=False)
    move_id = fields.Many2one('account.move', 'Journal Entry', copy=False)
    payment_id = fields.Many2one('account.payment', 'Payment', copy=False)
    move_ids = fields.One2many('account.move.line', related='move_id.line_ids', string='Journal Items', readonly=True,
                               copy=False)
    partner_id = fields.Many2one('res.partner', 'Partner', copy=False)
    paid = fields.Boolean(compute='_check_paid', help="The Voucher has been totally paid.")
    pay_now = fields.Selection([('pay_now', 'Pay Directly'), ('pay_later', 'Pay Later')], 'Payment', index=True,
                               default='pay_now', copy=False)
    date_due = fields.Date('Due Date', index=True)
    tax_id = fields.Many2one('account.tax', 'Tax', default=_get_tax)
    payment_option = fields.Selection([('without_writeoff', 'Keep Open'), ('with_writeoff', 'Reconcile Payment Balance')
                                       ], string='Payment Difference', default='without_writeoff', required=True,
                                      help="This field helps you to choose what you want to do with the eventual difference between the paid amount and the sum of allocated amounts. You can either choose to keep open this difference on the partner's account, or reconcile it with the payment(s)",
                                      copy=False)
    writeoff_acc_id = fields.Many2one('account.account', 'Counterpart Account', copy=False)
    comment = fields.Char('Counterpart Comment', required=True, default=_('Write-Off'), copy=False)
    analytic_id = fields.Many2one('account.analytic.account', 'Write-Off Analytic Account')
    writeoff_amount = fields.Float(compute='_get_writeoff_amount', string='Difference Amount', readonly=True,
                                   help="Computed as the difference between the amount stated in the voucher and the sum of allocation on the voucher lines.")
    payment_rate_currency_id = fields.Many2one('res.currency', 'Payment Rate Currency', default=_get_payment_rate_currency)
    payment_rate = fields.Float('Exchange Rate', digits=(12, 6), default=1.0)
    paid_amount_in_company_currency = fields.Float(compute='_paid_amount_in_company_currency',
                                                   string='Paid Amount in Company Currency', readonly=True)
    payment_mode = fields.Selection(_PAYMENT_MODE, 'Payment Mode', default='cheque')
    #    ref_number = fields.Char('Cheque No/DD No/UTR No/Card No',size=64)
    bank_id = fields.Many2one('res.partner.bank', 'Bank Account')
    bank = fields.Char('Bank')
    in_favour_of = fields.Char('In Favour Of', size=64, copy=False)
    imps_ref = fields.Char('Ref.Name', size=64)
    card_name = fields.Char('Name Of Card', size=64)
    card_type = fields.Selection(_CARD_TYPE, 'Card Type', default='visa')
    branch_code = fields.Char('Deposit Branch Code', size=64)
    remarks = fields.Text('Remarks')
    ref_date = fields.Date('Ref Date', help="Effective date for payment Reference", copy=False)
    user_id = fields.Many2one('res.users', 'Created User', default=lambda self: self.env.user)
    account_type = fields.Selection([('gl', 'GL'), ('customer', 'Customer'), ('supplier', 'Supplier')], 'Account Type',
                                    related='line_ids.account_type', store=True, copy=False)
    upload_file = fields.Many2many('ir.attachment', string='Files')

    @api.onchange('journal_id')
    def _onchange_journal_id(self):
        if self.journal_id:
            self.account_id = self.journal_id.default_account_id.id

    @api.onchange('line_ids')
    def onchange_in_favour(self):
        partner_list = []
        if not self.line_ids:
            self.in_favour_of = " "
        if self.line_ids:
            for line in self.line_ids:
                if line.partner_id and line.partner_id not in partner_list:
                    partner_list.append(line.partner_id)
            if len(partner_list) == 1:
                self.in_favour_of = partner_list[0].in_favour_of or partner_list[0].name.upper()
            elif len(partner_list) == 0:
                self.in_favour_of = ""
            else:
                self.in_favour_of = "MULTIPLE PARTIES"

    def action_view_journal(self):
        '''
        This function returns an action that display existing Journal Entry of given Voucher order ids.
        When only one found, show the journal immediately.
        '''
        return {
            'name': _('Journal Items'),
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': 'account.move.line',
            'view_id': False,
            'type': 'ir.actions.act_window',
            'domain': [('move_id', '=', self.move_id.id)],
            'context': {'default_move_id': self.move_id.id},
        }

    def action_view_payment(self):
        '''
        This function returns an action that display existing Journal Entry of given Voucher order ids.
        When only one found, show the journal immediately.
        '''
        return {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': 'account.payment',
            'view_id': False,
            'context': {'default_voucher_id': self.id},
            'domain': [('voucher_id', '=', self.id)]
        }

    # @api.onchange('partner_id', 'journal_id')
    # def onchange_partner_id(self):
    #     if not self.partner_id and not self.journal_id:
    #         return {}
    #     account_id = False
    #     ttype = self._context.get('type', 'bank')
    #     if ttype in ('payment', 'receipt'):
    #         ttype = 'bank'
    #     res = self.env['account.journal'].search([('type', '=', ttype)], limit=1)
    #     if not res:
    #         return False
    #     journal_id = res
    #     # if not self.journal_id.default_credit_account_id or not self.journal_id.default_debit_account_id:
    #     #     raise Warning(
    #     #         _('Please define default credit/debit accounts on the journal "%s".') % (self.journal_id.name))
    #     if journal_id.type in ('sale'):
    #         self.account_id = journal_id.default_account_id.id or False
    #     elif journal_id.type in ('sale'):
    #         self.account_id = journal_id.default_account_id.id or False
    #     elif journal_id.type in ('purchase', 'expense'):
    #         self.account_id = journal_id.default_account_id.id or False
    #     elif journal_id.type in ('purchase', 'expense'):
    #         self.account_id = journal_id.default_account_id.id or False
    #     elif self.journal_id.type in ('bank', 'cash'):
    #         self.account_id = journal_id.default_account_id.id or False
    #         self.bank_id = journal_id.bank_account_id or False
    #     #        elif self.journal_id.type in ('bank', 'cash') :
    #     #            self.account_id = self.journal_id.default_credit_account_id.id or False
    #     else:
    #         pass
    #         # self.account_id = journal_id.default_credit_account_id.id or journal_id.default_account_id.id
    #     self.currency_id = journal_id.currency_id.id or self.company_id.currency_id.id or False
    #     if self.account_id.tax_ids:
    #         self.tax_id = self.account_id.tax_ids[0].id

    #    @api.multi
    #    @api.onchange('type')
    #    def onchange_type(self):
    #        if self.type and self.partner_id :
    #            if self.type == 'sale' and self.partner_id.customer:
    #                self.account_id = self.partner_id.property_account_receivable_id.id or False
    #            if self.type == 'purchase' and self.partner_id.customer:
    #                self.account_id = self.partner_id.property_account_payable_id.id or False
    #            if self.type == 'purchase' and self.partner_id.supplier:
    #                self.account_id = self.partner_id.property_account_payable_id.id or False
    #            if self.type == 'sale' and self.partner_id.supplier:
    #                self.account_id = self.partner_id.property_account_receivable_id.id or False
    #            if self.account_id.tax_ids:
    #                self.tax_id = self.account_id.tax_ids[0].id

    @api.onchange('date', 'currency_id', 'company_id')
    def onchange_date(self):
        ctx = self._context.copy()
        ctx.update({'company_id': self.company_id.id})
        voucher_currency_id = self.currency_id or self.company_id.currency_id
        if self.payment_rate_currency_id:
            ctx.update({'date': self.date})
            payment_rate = 1.0
            if self.payment_rate_currency_id != self.currency_id:
                tmp = self.payment_rate_currency_id.with_context(ctx).rate
                payment_rate = tmp / voucher_currency_id.with_context(ctx).rate
            self.payment_rate = payment_rate

    @api.onchange('company_id')
    def onchange_company(self):
        journal = self.journal_id
        if journal.company_id.id != self.company_id.id:
            self.journal_id = False

    def action_cancel_draft(self):
        self.write({'state': 'draft'})
        return True

    def cancel_voucher(self):
        move_pool = self.env['account.payment'].search([('voucher_id', '=', self.id)]),
        for voucher in move_pool:
            voucher.action_draft()
            # voucher.cancel()
        self.write({'state': 'cancel', 'payment_id': False})
        return True

    def unlink(self):
        for voucher in self:
            if voucher.state not in ('draft', 'cancel'):
                raise Warning(_('Cannot delete voucher(s) which are already opened or paid.'))
        return super(AccountVoucher, self).unlink()

    def _get_company_currency(self):
        return self.journal_id.company_id.currency_id or self.company_id.currency_id

    def _get_current_currency(self):
        return self.currency_id or self._get_company_currency()

    def _sel_context(self):
        company_currency = self._get_company_currency()
        current_currency = self._get_current_currency()
        if current_currency.id != company_currency.id:
            context_multi_currency = self._context.copy()
            context_multi_currency.update({'date': self.date})
            return context_multi_currency
        return self._context

    def account_move_get(self):
        seq_obj = self.env['ir.sequence']
        voucher = self
        if voucher.number:
            name = voucher.number
        elif voucher.journal_id.sequence_id:
            if not voucher.journal_id.sequence_id.active:
                raise Warning(_('Please activate the sequence of selected journal !'))
            c = dict(self._context)
            name = voucher.journal_id.sequence_id.with_context(c).next_by_id()
        else:
            raise Warning(_('Please define a sequence on the journal.'))
        if not voucher.reference:
            ref = name.replace('/', '')
        else:
            ref = voucher.reference
        move = {
            'name': name,
            'journal_id': voucher.journal_id.id,
            'narration': voucher.narration,
            'date': voucher.date,
            'ref': ref,
            'payment_mode': voucher.payment_mode,
            'ref_date': voucher.ref_date,
            'bank': voucher.bank,
            'in_favour_of': voucher.in_favour_of,
            'card_name': voucher.card_name,
            'card_type': voucher.card_type,
            'branch_code': voucher.branch_code,
            'imps_ref': voucher.imps_ref,
        }
        return move

    def first_move_line_get(self, company_currency, current_currency):
        debit = credit = 0.0
        if self.type == 'payment':
            credit = self.paid_amount_in_company_currency
        elif self.type == 'receipt':
            debit = self.paid_amount_in_company_currency
        if debit < 0: credit = -debit; debit = 0.0
        if credit < 0: debit = -credit; credit = 0.0
        sign = debit - credit < 0 and -1 or 1
        move_line = {
            'name': self.name or '/',
            'debit': debit,
            'credit': credit,
            'account_id': self.account_id.id or False,
            'journal_id': self.journal_id.id or False,
            'partner_id': self.partner_id.id or False,
            'currency_id': (company_currency != current_currency and current_currency) or company_currency,
            'amount_currency': (sign * abs(self.amount)  # amount < 0 for refunds
                                if company_currency != current_currency else 0.0),
            'date': self.date or False,
            'date_maturity': self.date_due or False,
        }
        return move_line

    def _convert_amount(self, amount):
        return self.currency_id.with_context(self._context).compute(amount, self.company_id.currency_id)

    def _get_exchange_lines(self, line, amount_residual, company_currency, current_currency):
        if amount_residual > 0:
            account_id = line.voucher_id.company_id.expense_currency_exchange_account_id
            if not account_id:
                model, action_id = self.env['ir.model.data'].get_object_reference('account', 'action_account_form')
                msg = _(
                    "You should configure the 'Loss Exchange Rate Account' to manage automatically the booking of accounting entries related to differences between exchange rates.")
                raise exceptions.RedirectWarning(msg, action_id, _('Go to the configuration panel'))
        else:
            account_id = line.voucher_id.company_id.income_currency_exchange_account_id
            if not account_id:
                model, action_id = self.env['ir.model.data'].get_object_reference('account', 'action_account_form')
                msg = _(
                    "You should configure the 'Gain Exchange Rate Account' to manage automatically the booking of accounting entries related to differences between exchange rates.")
                raise exceptions.RedirectWarning(msg, action_id, _('Go to the configuration panel'))
        if line.account_id.currency_id:
            account_currency_id = line.account_id.currency_id.id
        else:
            # Odoo 19 made account_move_line.currency_id required; False used
            # to be the way of saying "company currency".
            account_currency_id = (company_currency != current_currency and current_currency.id) or company_currency.id
        move_line = {
            'journal_id': line.voucher_id.journal_id.id,
            'name': _('change') + ': ' + (line.voucher_id.narration or '/'),
            'account_id': line.account_id.id,
            'partner_id': line.partner_id.id,
            'currency_id': account_currency_id,
            # amount_currency is deliberately not set: in Odoo 19 it has an
            # inverse that copies it onto balance whenever the line is in
            # company currency, so passing 0.0 here silently zeroed every
            # debit/credit. Odoo derives it from balance on its own.
            'quantity': 1,
            'credit': amount_residual > 0 and amount_residual or 0.0,
            'debit': amount_residual < 0 and -amount_residual or 0.0,
            'date': line.voucher_id.date,
        }
        move_line_counterpart = {
            'journal_id': line.voucher_id.journal_id.id,
            'name': _('change') + ': ' + (line.voucher_id.narration or '/'),
            'account_id': account_id.id,
            # amount_currency is deliberately not set: in Odoo 19 it has an
            # inverse that copies it onto balance whenever the line is in
            # company currency, so passing 0.0 here silently zeroed every
            # debit/credit. Odoo derives it from balance on its own.
            'partner_id': line.partner_id.id,
            'currency_id': account_currency_id,
            'quantity': 1,
            'debit': amount_residual > 0 and amount_residual or 0.0,
            'credit': amount_residual < 0 and -amount_residual or 0.0,
            'date': line.voucher_id.date,
        }
        return (move_line, move_line_counterpart)

    def voucher_move_line_create(self, line_total, company_currency, current_currency):
        tot_line = line_total
        move_lines = []
        date = self.date
        ctx = self._context.copy()
        ctx.update({'date': date})
        voucher_currency = self.journal_id.currency_id or self.company_id.currency_id
        ctx.update({
            'voucher_special_currency_rate': voucher_currency.rate * self.payment_rate,
            'voucher_special_currency': self.payment_rate_currency_id and self.payment_rate_currency_id.id or False, })
        prec = self.env['decimal.precision'].precision_get('Account')
        for line in self.line_ids:
            if line.paid_check == False:
                if not line.amount and not (
                        line.move_line_id and not float_compare(line.move_line_id.debit, line.move_line_id.credit,
                                                                precision_digits=prec) and not float_compare(
                        line.move_line_id.debit, 0.0, precision_digits=prec)):
                    continue
                amount = self.with_context(ctx)._convert_amount(line.untax_amount or line.amount)
                if line.amount == line.amount_unreconciled:
                    if not line.move_line_id:
                        raise Warning(_("The invoice you are willing to pay is not valid anymore."))
                    sign = line.type == 'dr' and -1 or 1
                    currency_rate_difference = sign * (line.move_line_id.amount_residual - amount)
                else:
                    currency_rate_difference = 0.0
                move_line = {
                    'journal_id': self.journal_id.id,
                    'name': line.voucher_id.narration or '/',
                    'account_id': line.account_id.id,
                    'partner_id': line.partner_id.id,
                    'currency_id': (line.move_line_id
                                    and company_currency.id != line.move_line_id.currency_id.id
                                    and line.move_line_id.currency_id.id) or company_currency.id,
                    'analytic_distribution': {str(line.account_analytic_id.id): 100.0} if line.account_analytic_id else False,
                    # 'analytic_tag_ids': removed in Odoo 19
                    'quantity': 1,
                    'credit': 0.0,
                    'debit': 0.0,
                    'date': self.date
                }
                if amount < 0:
                    amount = -amount
                    if line.type == 'dr':
                        line.type = 'cr'
                    else:
                        line.type = 'dr'
                if (line.type == 'dr'):
                    tot_line += amount
                    move_line['debit'] = amount
                else:
                    tot_line -= amount
                    move_line['credit'] = amount
                if self.tax_id and self.type in ('sale', 'purchase'):
                    move_line.update({'tax_ids': [(6, 0, self.tax_id.ids)]})
                foreign_currency_diff = 0.0
                amount_currency = False
                if line.move_line_id:
                    if line.move_line_id.currency_id and line.move_line_id.currency_id.id != company_currency.id:
                        if line.move_line_id.currency_id.id == current_currency.id:
                            sign = (move_line['debit'] - move_line['credit']) < 0 and -1 or 1
                            amount_currency = sign * (line.amount)
                        else:
                            amount_currency = company_currency.with_context(ctx).compute(
                                move_line['debit'] - move_line['credit'], line.move_line_id.currency_id)
                    if line.amount == line.amount_unreconciled:
                        foreign_currency_diff = line.move_line_id.amount_residual_currency - abs(amount_currency)
                move_line['amount_currency'] = amount_currency
                move_lines.append((0, 0, move_line))
                if not self.company_id.currency_id.is_zero(currency_rate_difference):
                    exch_lines = self._get_exchange_lines(line, currency_rate_difference, company_currency,
                                                          current_currency)
                    move_lines.append((0, 0, exch_lines[0]))
                    move_lines.append((0, 0, exch_lines[1]))
                if line.move_line_id and line.move_line_id.currency_id and not line.move_line_id.currency_id.is_zero(
                        foreign_currency_diff):
                    move_line_foreign_currency = {
                        'journal_id': line.voucher_id.journal_id.id,
                        'name': _('change') + ': ' + (line.voucher_id.narration or '/'),
                        'account_id': line.account_id.id,
                        'partner_id': line.voucher_id.partner_id.id,
                        'currency_id': line.move_line_id.currency_id.id or line.voucher_id.company_id.currency_id.id,
                        'amount_currency': (-1 if line.type == 'cr' else 1) * foreign_currency_diff,
                        'quantity': 1,
                        'credit': 0.0,
                        'debit': 0.0,
                        'date': line.voucher_id.date,
                    }
                    move_lines.append((0, 0, move_line_foreign_currency))
        return tot_line, move_lines

    def writeoff_move_line_get(self, line_total, company_currency, current_currency):
        move_line = {}
        current_currency_obj = self.currency_id or self.journal_id.company_id.currency_id
        if not current_currency_obj.is_zero(line_total):
            diff = line_total
            account_id = False
            write_off_name = ''
            if self.payment_option == 'with_writeoff':
                account_id = self.writeoff_acc_id.id
                write_off_name = self.comment
            elif self.partner_id:
                if self.type in ('sale', 'receipt'):
                    account_id = self.partner_id.property_account_receivable_id.id
                else:
                    account_id = self.partner_id.property_account_payable_id.id
            else:
                account_id = self.account_id.id
            sign = self.type == 'payment' and -1 or 1
            move_line = {
                'name': write_off_name or '',
                'account_id': account_id,
                'partner_id': self.partner_id.id,
                'date': self.date,
                'credit': diff > 0 and diff or 0.0,
                'debit': diff < 0 and -diff or 0.0,
                'amount_currency': company_currency != current_currency and (sign * -1 * self.writeoff_amount) or 0.0,
                'currency_id': (company_currency != current_currency and current_currency) or company_currency,
                'analytic_distribution': {str(self.analytic_id.id): 100.0} if self.analytic_id else False,
                #                'analytic_tag_ids':[(6, 0, line.analytic_tag_ids.ids)] or False,
            }
        return move_line

    def action_move_line_create(self):
        move_vals = []
        cus_pay_id = []
        sup_pay_id = []
        pay_method_id = []
        domain = []
        debit_ids = []
        check = 0
        cr_amt = 0
        dr_amt = 0
        if self.journal_id.sequence_id:
            c = dict(self._context)
            next_num = self.journal_id.sequence_id.with_context(c).next_by_id()
            self.write({'number':next_num})
        AccountMove = self.env['account.move'].with_context(default_type='entry')
        if self.type == 'payment' and self.type != 'receipt':
            for line in self.line_ids:
                # if line.account_type == 'customer':
                #     domain = [('payment_type', '=', 'inbound')]
                # if line.account_type == 'supplier':
                domain = [('payment_type', '=', 'outbound')]
                pay_method_id = self.env['account.payment.method'].search(domain, limit=1).id
                if line.account_type == 'customer':
                    cus_pay_id = self.env['account.payment'].create({
                        'payment_type': 'outbound',
                        'partner_type': line.account_type,
                        'partner_id': line.partner_id.id,
                        'state': 'draft',
                        'amount': line.amount,
                        # 'payment_date': self.date,
                        # 'communication': self.reference or "" + ":" + self.narration,
                        'journal_id': self.journal_id.id,
                        'payment_method_id': pay_method_id,
                        'account_analytic_id': line.account_analytic_id.id,
                        # 'analytic_tag_ids': removed in Odoo 19
                        'voucher_id': self.id,
                        # 'move_name':self.number+"/C-PAY",
                    })
                if line.account_type == 'supplier':
                    sup_pay_id = self.env['account.payment'].create({
                        'payment_type': 'outbound',
                        'partner_type': line.account_type,
                        'partner_id': line.partner_id.id,
                        'state': 'draft',
                        'amount': line.amount,
                        # 'payment_date':self.date,
                        # 'communication': self.reference or "" + ":" + self.narration,
                        'journal_id': self.journal_id.id,
                        'payment_method_id': pay_method_id,
                        'account_analytic_id': line.account_analytic_id.id,
                        # 'analytic_tag_ids': removed in Odoo 19
                        'voucher_id': self.id,
                        # 'move_name':self.number+"/V-PAY",
                    })
                if line.account_type == 'gl':
                    check = 1
                    if self.type == 'payment':
                        balance = line.amount
                    else:
                        balance = -line.amount
                    cr_amt = cr_amt + (balance > 0.0 and balance or 0.0 )
                    dr_amt = dr_amt + (balance < 0.0 and -balance or 0.0)
                    debit_ids.append((0, 0, {
                        'name': _('change') + ': ' + (line.voucher_id.narration or '/'),
                        # amount_currency is deliberately not set: in Odoo 19 it has an
                        # inverse that copies it onto balance whenever the line is in
                        # company currency, so passing 0.0 here silently zeroed every
                        # debit/credit. Odoo derives it from balance on its own.
                        'currency_id': line.account_id.currency_id.id or self.company_id.currency_id.id,
                        'debit': balance > 0.0 and balance or 0.0,
                        'credit': balance < 0.0 and -balance or 0.0,
                        'partner_id': line.partner_id.commercial_partner_id.id or False,
                        'account_id': line.account_id.id,
                        'analytic_distribution': {str(line.account_analytic_id.id): 100.0} if line.account_analytic_id else False,
                        # 'analytic_tag_ids': removed in Odoo 19
                    })),
            debit_ids.insert(0,(0, 0, {
                'name': line.voucher_id.narration or '/',
                # amount_currency is deliberately not set: in Odoo 19 it has an
                # inverse that copies it onto balance whenever the line is in
                # company currency, so passing 0.0 here silently zeroed every
                # debit/credit. Odoo derives it from balance on its own.
                'currency_id': line.account_id.currency_id.id or self.company_id.currency_id.id,
                'debit': dr_amt,
                'credit': cr_amt,
                'partner_id': line.partner_id.commercial_partner_id.id or False,
                'analytic_distribution': {str(line.account_analytic_id.id): 100.0} if line.account_analytic_id else False,
                # 'analytic_tag_ids': removed in Odoo 19
                'account_id': self.account_id.id,
            }))
            if check:
                move_vals = {
                    'name':self.number,
                    'date': self.date,
                    'ref': self.reference,
                    'journal_id': self.journal_id.id,
                    'currency_id': self.journal_id.currency_id.id or self.company_id.currency_id.id,
                    'line_ids': debit_ids,
                }
            moves = AccountMove.create(move_vals)
            if moves:
                moves.action_post()
                self.write({'state': 'posted', 'move_id': moves.id})

                # ✅ Attach Uploaded Files to Journal Entry
                for attachment in self.upload_file:
                    attachment.write({
                        'res_model': 'account.move',
                        'res_id': moves.id,
                    })
                moves.message_post(body="Attachments moved from voucher.", attachment_ids=self.upload_file.ids)

            if cus_pay_id:
                # cus_pay_id.post()
                self.write({'state': 'posted' })
            if sup_pay_id:
                # sup_pay_id.post()
                self.write({'state': 'posted'})
        if self.type == 'receipt' and self.type != 'payment':
            for line in self.line_ids:
                # if line.account_type == 'customer':
                #     domain = [('payment_type', '=', 'inbound')]
                # if line.account_type == 'supplier':
                domain = [('payment_type', '=', 'inbound')]
                pay_method_id = self.env['account.payment.method'].search(domain, limit=1).id
                if line.account_type == 'customer':
                    cus_pay_id = self.env['account.payment'].create({
                        'payment_type': 'inbound',
                        'partner_type': line.account_type,
                        'partner_id': line.partner_id.id,
                        'state': 'draft',
                        'amount': line.amount,
                        # 'payment_date': self.date,
                        # 'communication': self.reference or "" + ":" + self.narration,
                        'journal_id': self.journal_id.id,
                        'payment_method_id': pay_method_id,
                        'account_analytic_id': line.account_analytic_id.id,
                        # 'analytic_tag_ids': removed in Odoo 19
                        'voucher_id': self.id,
                        # 'move_name':self.number+"/C-PAY",
                    })
                if line.account_type == 'supplier':
                    sup_pay_id = self.env['account.payment'].create({
                        'payment_type': 'inbound',
                        'partner_type': line.account_type,
                        'partner_id': line.partner_id.id,
                        'state': 'draft',
                        'amount': line.amount,
                        # 'payment_date':self.date,
                        # 'communication': self.reference or "" + ":" + self.narration,
                        'journal_id': self.journal_id.id,
                        'payment_method_id': pay_method_id,
                        'account_analytic_id': line.account_analytic_id.id,
                        # 'analytic_tag_ids': removed in Odoo 19
                        'voucher_id': self.id,
                        # 'move_name':self.number+"/V-PAY",
                    })
                if line.account_type == 'gl':
                    check = 1
                    if self.type == 'payment':
                        balance = line.amount
                    else:
                        balance = -line.amount
                    cr_amt = cr_amt + (balance > 0.0 and balance or 0.0 )
                    dr_amt = dr_amt + (balance < 0.0 and -balance or 0.0)
                    debit_ids.append((0, 0, {
                        'name': _('change') + ': ' + (line.voucher_id.narration or '/'),
                        # amount_currency is deliberately not set: in Odoo 19 it has an
                        # inverse that copies it onto balance whenever the line is in
                        # company currency, so passing 0.0 here silently zeroed every
                        # debit/credit. Odoo derives it from balance on its own.
                        'currency_id': line.account_id.currency_id.id or self.company_id.currency_id.id,
                        'debit': balance > 0.0 and balance or 0.0,
                        'credit': balance < 0.0 and -balance or 0.0,
                        'partner_id': line.partner_id.commercial_partner_id.id or False,
                        'account_id': line.account_id.id,
                        'analytic_distribution': {str(line.account_analytic_id.id): 100.0} if line.account_analytic_id else False,
                        # 'analytic_tag_ids': removed in Odoo 19
                    })),
            debit_ids.insert(0,(0, 0, {
                'name': line.voucher_id.narration or '/',
                # amount_currency is deliberately not set: in Odoo 19 it has an
                # inverse that copies it onto balance whenever the line is in
                # company currency, so passing 0.0 here silently zeroed every
                # debit/credit. Odoo derives it from balance on its own.
                'currency_id': line.account_id.currency_id.id or self.company_id.currency_id.id,
                'debit': dr_amt,
                'credit': cr_amt,
                'partner_id': line.partner_id.commercial_partner_id.id or False,
                'analytic_distribution': {str(line.account_analytic_id.id): 100.0} if line.account_analytic_id else False,
                # 'analytic_tag_ids': removed in Odoo 19
                'account_id': self.account_id.id,
            }))
            if check:
                move_vals = {
                    'name':self.number,
                    'date': self.date,
                    'ref': self.reference,
                    'journal_id': self.journal_id.id,
                    'currency_id': self.journal_id.currency_id.id or self.company_id.currency_id.id,
                    'line_ids': debit_ids,
                }
            moves = AccountMove.create(move_vals)
            if moves:
                moves.action_post()
                self.write({'state': 'posted', 'move_id': moves.id})

                # ✅ Attach Uploaded Files to Journal Entry
                for attachment in self.upload_file:
                    attachment.write({
                        'res_model': 'account.move',
                        'res_id': moves.id,
                    })
                moves.message_post(body="Attachments moved from voucher.", attachment_ids=self.upload_file.ids)

            if cus_pay_id:
                cus_pay_id.action_post()
                self.write({'state': 'posted' })
            if sup_pay_id:
                sup_pay_id.action_post()
                self.write({'state': 'posted'})
        return True



class AccountVoucherLine(models.Model):
    _name = "account.voucher.line"
    _description = "Voucher Lines"

    def _compute_balance(self):
        rs_data = {}
        for line in self:
            ctx = self._context.copy()
            ctx.update({'date': line.voucher_id.date})
            voucher_rate = line.voucher_id.currency_id.rate
            ctx.update({
                'voucher_special_currency': line.voucher_id.payment_rate_currency_id and line.voucher_id.payment_rate_currency_id.id or False,
                'voucher_special_currency_rate': line.voucher_id.payment_rate * voucher_rate})
            res = {}
            company_currency = line.voucher_id.journal_id.company_id.currency_id.id
            voucher_currency = line.voucher_id.currency_id and line.voucher_id.currency_id.id or company_currency
            move_line = line.move_line_id or False

            if not move_line:
                self.amount_original = 0.0
                self.amount_unreconciled = 0.0
            elif move_line.currency_id and voucher_currency == move_line.currency_id.id:
                self.amount_original = abs(move_line.amount_currency)
                self.amount_unreconciled = abs(move_line.amount_residual_currency)
            else:
                self.amount_original = company_currency.with_context(ctx).compute(
                    move_line.credit or move_line.debit or 0.0, voucher_currency)
                self.amount_unreconciled = company_currency.with_context(ctx).compute(abs(move_line.amount_residual),
                                                                                      voucher_currency)

    # def write(self, vals):
    #     res = super(AccountVoucherLine, self).write(vals)
    #     payment_id = self.env['account.payment'].search([('voucher_line_id', '=', self.id)], limit=1)
    #     payment_id.write({"amount":self.amount})
    #     return res

    # fields
    voucher_id = fields.Many2one('account.voucher', 'Voucher', required=1, ondelete='cascade')
    account_type = fields.Selection([('gl', 'GL'), ('customer', 'Customer'), ('supplier', 'Supplier')], 'Account Type',
                                    default='gl', copy=True)
    #    name = fields.Char(string='Description', required=True, default='')
    account_id = fields.Many2one('account.account', string='Account', store=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    untax_amount = fields.Float('Untax Amount')
    amount = fields.Float('Amount', digits=(16, 2))
    reconcile = fields.Boolean('Full Reconcile')
    type = fields.Selection([('dr', 'Debit'), ('cr', 'Credit')], 'Dr/Cr')
    account_analytic_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    # analytic_tag_ids field removed - account.analytic.tag model removed in Odoo 19
    move_line_id = fields.Many2one('account.move.line', 'Journal Item', copy=False)
    date_original = fields.Date(string='Date')
    date_due = fields.Date(string='Due Date')
    currency_id = fields.Many2one('res.currency', related='voucher_id.currency_id', string='Currency', store=True,
                                  readonly=True)
    company_id = fields.Many2one('res.company', related='voucher_id.company_id', string='Company', store=True,
                                 readonly=True)
    amount_unreconciled = fields.Float(compute='_compute_balance', string='Open Balance', store=True,
                                       digits=(16, 2))
    amount_original = fields.Float(compute='_compute_balance', string='Original Amount', store=True,
                                   digits=(16, 2))
    paid_check = fields.Boolean(string="Paid Check", store=True)

    def payment_view(self):
        context = self.env.context  # Get context from Odoo environment
        for record in self:
            payment_type = False
            # if record.partner_id.customer:
            #     payment_type = 'outbound'
            # elif record.partner_id.supplier:
            #     payment_type = 'inbound'

            ctx = dict(context)
            ctx.update({
                # 'default_payment_type': payment_type,
                'default_partner_id': record.partner_id.id or False,
                'default_amount': record.amount,
                'default_voucher_id': record.voucher_id.id,
                'default_journal_id': record.voucher_id.journal_id.id,
                'default_voucher_line_id': record.id,
                'default_payment_date': record.voucher_id.date,
                'default_account_analytic_id': record.account_analytic_id.id,
                # 'default_analytic_tag_ids': removed in Odoo 19
            })

            payment_id = self.env['account.payment'].search([
                ('voucher_id', '=', record.id)
            ], limit=1)

            if payment_id:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.payment',
                    'view_mode': 'form',
                    'res_id': payment_id.id,
                    'context': ctx,
                }
            else:
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'account.payment',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': ctx,
                }


    @api.onchange('account_type')
    def onchange_account_type(self):
        self.partner_id = False
        self.account_id = False
        self.account_analytic_id = False
        # self.analytic_tag_ids = False  # removed in Odoo 19
        # if self.account_type == 'gl':
        #     return {'domain': {'account_id': [('user_type_id', 'not in', ('Bank and Cash', 'Bank', 'Cash')),
        #                                       ('deprecated', '=', False)]}}
        # if self.account_type == 'customer':
        #     return {'domain': {
        #                        'account_id': [('user_type_id', '=', 'Receivable'), ('deprecated', '=', False)]}}
        # if self.account_type == 'supplier':
        #     return {'domain': {
        #                        'account_id': [('user_type_id', '=', 'Payable'), ('deprecated', '=', False)]}}

    @api.onchange('partner_id')
    def onchange_partner(self):
        if self.account_type == 'customer' and self.partner_id:
            self.account_id = self.partner_id.property_account_receivable_id.id or False
        if self.account_type == 'supplier' and self.partner_id:
            self.account_id = self.partner_id.property_account_payable_id.id or False

    #    @api.model
    #    def create(self, vals):
    #        res = super(account_voucher_line, self).create(vals)
    #        res['account_id'] = res.partner_id.property_account_payable_id.id or res['account_id'] or False
    #        return res

    #    @api.multi
    #    def write(self, vals):
    #        print ("\n\n\n",vals)
    #        vals['account_id'] = self.partner_id.property_account_payable_id.id or self.account_id.id or False
    #        res = super(account_voucher_line, self).write(vals)
    #        return res

    @api.onchange('move_line_id')
    def onchange_move_line_id(self):
        self.account_id = False
        self.type = False
        self.currency_id = False
        if self.move_line_id:
            move_line = self.move_line_id
            if move_line.credit:
                ttype = 'dr'
            else:
                ttype = 'cr'
                self.account_id = move_line.account_id.id
                self.type = ttype
                self.currency_id = move_line.currency_id and move_line.currency_id.id or move_line.company_id.currency_id.id

    @api.model
    def default_get(self, fields_list):
        journal_id = self._context.get('journal_id', False)
        partner_id = self._context.get('partner_id', False)
        values = super(AccountVoucherLine, self).default_get(fields_list)
        if (not journal_id) or ('account_id' not in fields_list):
            return values
        journal = self.env['account.journal'].browse(journal_id)
        partner = self.env['res.partner'].browse(partner_id)
        account_id = False
        ttype = 'cr'
        if journal.type in ('sale', 'sale_refund'):
            account_id = journal.default_credit_account_id and journal.default_credit_account_id.id or False
            ttype = 'cr'
        elif journal.type in ('purchase', 'expense', 'purchase_refund'):
            account_id = journal.default_debit_account_id and journal.default_debit_account_id.id or False
            ttype = 'dr'
        elif partner:
            if self._context.get('type') == 'payment' and partner.supplier:
                ttype = 'dr'
                account_id = partner.property_account_payable_id.id
            elif self._context.get('type') == 'receipt' and partner.supplier:
                ttype = 'cr'
                account_id = partner.property_account_receivable_id.id
            elif self._context.get('type') == 'payment' and partner.customer:
                ttype = 'dr'
                account_id = partner.property_account_payable_id.id
            elif self._context.get('type') == 'receipt' and partner.customer:
                ttype = 'cr'
                account_id = partner.property_account_receivable_id.id
        elif not partner and journal.type in ('bank', 'cash'):
            if self._context.get('type') == 'payment':
                ttype = 'dr'
            if self._context.get('type') == 'receipt':
                ttype = 'cr'
        values.update({'account_id': account_id, 'type': ttype})
        return values
