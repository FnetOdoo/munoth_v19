from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
import base64
from num2words import num2words
from datetime import date
import xlsxwriter
import json


class PaymentRequest(models.Model):
    _name = 'payment.request'
    _description = 'Payment Request'
    _rec_name = 'request_number'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Name')
    request_number = fields.Char(string='PR No.', required=True, copy=False, readonly=True,
                                 default=lambda self: _('New'), store=True, tracking=True)
    state = fields.Selection([
        ('finance_approval', 'Waiting for Finance Approval'),
        ('md_approval', 'Waiting for MD Approval'),
        ('approved', 'Approved'),
        ('paid','Paid'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected')
    ], default='finance_approval', tracking=True)
    line_ids = fields.One2many('payment.request.line', 'payment_request_id', string='Request Lines')
    account_move_ids = fields.Many2many('account.move', string='Bills', compute='_compute_account_move_ids', store=True)
    payment_request_date = fields.Date(string='Date', default=fields.Date.today())
    payment_approved_date = fields.Date('Approved Date')

    @api.constrains('line_ids')
    def _check_paid_bills(self):
        """Prevent adding already-paid bills to a payment request."""
        for rec in self:
            paid_bills = rec.line_ids.filtered(
                lambda line: line.account_move_id.payment_state == 'paid' or line.account_move_id.amount_residual == 0
            ).mapped('account_move_id')
            if paid_bills:
                bill_names = ', '.join(paid_bills.mapped('name'))
                raise ValidationError(
                    _('You cannot add already paid bills to a payment request.\n'
                      'The following bill(s) are already paid: %s') % bill_names
                )

    @api.onchange('line_ids')
    def _onchange_check_paid_bills(self):
        """Warn and auto-remove any paid bills that the user tries to add."""
        if self.line_ids:
            paid_lines = self.line_ids.filtered(
                lambda line: line.account_move_id and (
                    line.account_move_id.payment_state == 'paid' or
                    line.account_move_id.amount_residual == 0
                )
            )
            if paid_lines:
                bill_names = ', '.join(paid_lines.mapped('account_move_id.name'))
                # Remove paid lines
                self.line_ids -= paid_lines
                return {
                    'warning': {
                        'title': _('Paid Bills Removed'),
                        'message': _(
                            'The following bills are already paid and have been removed from the request:\n%s'
                        ) % bill_names,
                    }
                }

    total_due_amount = fields.Float(string='Total Due Amount', compute='_compute_total_due_amount')
    payment_amount = fields.Float(string='Payment Amount', help='Enter the amount to pay. Leave 0 to pay full due amount.')
    email = fields.Char(string='Email', default='lashok@futurenet.in')
    payment_ids = fields.Many2many('account.payment')
    bill_select = fields.Boolean('Select')
    url_link = fields.Char('Url')
    cancel_reason = fields.Text('Reset to Draft Reason', tracking=True)
    reject_reason = fields.Text('Reject Reason', tracking=True)
    currency_id = fields.Many2one('res.currency', string='Currency', required=True,
                                  default=lambda self: self.env.user.company_id.currency_id)
    company_id = fields.Many2one('res.company', string='Company', required=True,
                                 default=lambda self: self.env.user.company_id)
    file_data = fields.Binary('Download File')
    filename = fields.Char()
    get_invoice_report = fields.Binary('Invoice Report', readonly=True)
    invoice_report_name = fields.Char('Filename', size=64, readonly=True)

    # reset to draft
    def action_state_draft(self):

        for rec in self:
            rec.state = 'finance_approval'

    # Finance approve button

    def action_finance_approval(self):
        for rec in self:
            rec.state = 'md_approval'
            rec.action_payment_request_email()
            rec.print_account_details()
            for invoices in rec.account_move_ids:
                invoices.payment_request_number = rec.request_number

    # MD final approval
    def action_md_approved(self):
        for rec in self:
            rec.state = 'approved'
            rec.payment_approved_date = fields.Date.today()
            print(rec.payment_approved_date, 'approved Date')
            report_template_id = self.env['ir.actions.report']._render_qweb_pdf('payment_request.report_partner_bills_details', res_ids=rec.ids)
            data_record = base64.b64encode(report_template_id[0])
            ir_values = {
                'name': "Payment Request" + ' ' + self.request_number,
                'type': 'binary',
                'datas': data_record,
                'store_fname': data_record,
                'mimetype': 'application/x-pdf',
            }
            attachment = self.env['ir.attachment'].create(ir_values)

            mail_template = self.env.ref('payment_request.email_payment_request_md_approved')
            mail_template.write({'attachment_ids': [(6, 0, [attachment.id])]})
            mail_template.send_mail(self.id, force_send=True)

    def action_cancel(self):
        for rec in self:
            if not rec.cancel_reason:
                raise ValidationError(_('Please fill the cancel reason'))
            mail_body = """<table border="0" cellpadding="0" cellspacing="0" width="1000"style="background-color: white; border-collapse: collapse; margin-left: 5px;">
                                <tr>
                                    <td valign="top" style="padding: 0px 10px;">
                                        <div style="font-size: 13px; margin: 0px; padding: 0px;">
                                            Dear {name},
                                            <br/>
                                             I wanted to inform you that the payment request you submitted on {date} for {prf} has been canceled.
                                            <br/><br/>
                                             Thank you for understanding.
                                             <br/><br/>
                                             Best regards,<br/>
                                             {user}
                                        </div>
                                    </td>
                                </tr>
                            </table>""".format(name=rec.user_id.name, date=rec.create_date.date(), prf=rec.request_number, user=self.env.user.name)

            mail_subject = f"Cancellation of Payment Request {rec.request_number}"
            to_email = rec.user_id.login
            md_logins = ', '.join(
                user.login for user in self.env['res.users'].search([])
                if user.has_group('mm_master.group_company_managing_director')
            )

            self.env['mail.mail'].create({
                'subject': mail_subject,
                'email_to': to_email,
                'email_cc': md_logins,
                'body_html': mail_body,
            }).send()
            rec.state = 'cancel'

    def action_rejected(self):
        for rec in self:
            if not rec.reject_reason:
                raise ValidationError(_('Please fill the reject reason'))
            mail_body = """<table border="0" cellpadding="0" cellspacing="0" width="1000"style="background-color: white; border-collapse: collapse; margin-left: 5px;">
                                            <tr>
                                                <td valign="top" style="padding: 0px 10px;">
                                                    <div style="font-size: 13px; margin: 0px; padding: 0px;">
                                                        Dear {name},
                                                        <br/>
                                                         I wanted to inform you that the payment request you submitted on {date} for {prf} has been rejected.
                                                        <br/><br/>
                                                         Thank you for understanding.
                                                         <br/><br/>
                                                         Best regards,<br/>
                                                         {user}
                                                    </div>
                                                </td>
                                            </tr>
                                        </table>""".format(name=rec.user_id.name, date=rec.create_date.date(),
                                                           prf=rec.request_number, user=self.env.user.name)

            mail_subject = f"Rejection of Payment Request {rec.request_number}"
            to_email = rec.user_id.login

            self.env['mail.mail'].create({
                'subject': mail_subject,
                'email_to': to_email,
                'body_html': mail_body,
            }).send()
            rec.state = 'reject'

    def action_draft_payment_request(self):
        action = self.env['ir.actions.act_window']._for_xml_id('payment_request.action_payment_request_cancel_reason')
        action['context'] = {'default_payment_request_id': self.id}
        return action

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('request_number', _('New')) == _('New'):
                vals['request_number'] = self.env['ir.sequence'].next_by_code('payment.request') or _('New')
        res = super(PaymentRequest, self).create(vals_list)
        return res

    @api.depends('line_ids', 'line_ids.account_move_id')
    def _compute_account_move_ids(self):
        for rec in self:
            rec.account_move_ids = rec.line_ids.mapped('account_move_id')

    @api.depends('line_ids', 'line_ids.request_amount')
    def _compute_total_due_amount(self):
        for rec in self:
            rec.total_due_amount = sum(rec.line_ids.mapped('request_amount'))


    def action_payment_request_email(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%s&model=payment.request&view_type=form' % (self.id)
        self.write({'url_link': base_url})

        report_template_id = self.env['ir.actions.report']._render_qweb_pdf('payment_request.report_partner_bills_details', res_ids=self.ids)
        data_record = base64.b64encode(report_template_id[0])
        ir_values = {
            'name': "Payment Request " + self.request_number,
            'type': 'binary',
            'datas': data_record,
            'store_fname': self.request_number + ".pdf",
            'mimetype': 'application/x-pdf',
            'res_model': 'payment.request',
            'res_id': self.id,
        }
        attachment = self.env['ir.attachment'].create(ir_values)

        account_move_attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'account.move'),
            ('res_id', 'in', self.account_move_ids.ids)
        ])

        new_attachments = []
        for record in account_move_attachments:
            copied_data = record.copy_data()[0]
            new_attachment = self.env['ir.attachment'].create(copied_data)
            new_attachments.append(new_attachment.id)

        all_attachments = [attachment.id] + new_attachments


        mail_template = self.env.ref('payment_request.email_payment_request_for_vendor_payment')
        mail_template.attachment_ids = [(6, 0, all_attachments)]
        mail_template.send_mail(self.id, force_send=True)
        self.env['ir.attachment'].browse(new_attachments).unlink()
        return True

    def action_register_payment(self):
        '''Open the standard payment register wizard for the linked bills.'''
        self.ensure_one()

        # Collect the payable move lines from all linked bills
        bills = self.line_ids.mapped('account_move_id')
        if not bills:
            raise ValidationError(_('No bills found on this payment request.'))

        payable_lines = bills.line_ids.filtered(
            lambda l: l.account_type == 'liability_payable' and not l.reconciled
        )
        if not payable_lines:
            raise ValidationError(_('No outstanding payable lines found on the linked bills.'))

        return {
            'name': _('Register Payment'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment.register',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'active_model': 'account.move.line',
                'active_ids': payable_lines.ids,
                'payment_request_id': self.id,
                'payment_request_amount': self.total_due_amount,
            },
        }

    def action_open_payments(self):
        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
            'view_mode': 'list,form',
            'domain': [('id', 'in', self.payment_ids.ids)],
        }
        return action

    def action_open_bills(self):
        action = {
            'name': _('Bills'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'context': {'create': False},
            'view_mode': 'list,form',
            # 'views': [(self.env.ref('account.view_invoice_tree').id, 'list')],
            'domain': [('id', 'in', self.account_move_ids.ids)],
        }
        return action

    def generate_invoice_details_report(self):
        url = '/tmp/'
        workbook = xlsxwriter.Workbook(url + 'Invoice Report.xlsx')
        sheet = workbook.add_worksheet()
        format1 = workbook.add_format({'font_size': 11, 'align': 'vcenter', 'valign': 'center'})
        parent_format = workbook.add_format({'font_size': 13, 'bold': True, 'align': 'center'})
        center_format = workbook.add_format({'font_size': 11, 'align': 'center'})
        left_format = workbook.add_format({'font_size': 11, 'align': 'left'})
        right_format = workbook.add_format({'font_size': 11, 'align': 'right'})
        amount_format = workbook.add_format({'font_size': 11, 'align': 'right', 'num_format': '#,##0.00'})
        margin_format = workbook.add_format({'font_size': 11, 'align': 'right', 'num_format': '0.00'})
        total_format = workbook.add_format(
            {'font_size': 13, 'bold': True, 'align': 'left', 'valign': 'center', 'bg_color': '#FFCCCB'})
        format1.set_text_wrap()
        format2 = workbook.add_format({'font_size': 12, 'align': 'center'})
        format3 = workbook.add_format({'font_size': 12, 'align': 'left', 'num_format': 'dd-mm-yyyy'})

        bold = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'})
        bold_1 = workbook.add_format({'align': 'right', 'valign': 'vcenter'})

        sheet.set_column('A:A', 30)
        sheet.set_column('B:B', 20)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 20)
        sheet.set_column('H:H', 20)
        sheet.set_column('I:I', 20)
        sheet.set_column('J:J', 20)

        sheet.merge_range('B3:E3', 'INVOICE REPORT', bold)
        sheet.write(5, 0, 'Customer Invoice No.', parent_format)
        sheet.write(5, 1, 'Total Amount', parent_format)
        sheet.write(5, 2, 'Payment Status', parent_format)
        sheet.write(5, 3, 'Sale Order No.', parent_format)
        sheet.write(5, 4, 'Total Amount', parent_format)
        sheet.write(5, 5, 'Invoice Status', parent_format)
        sheet.write(5, 6, 'PO No.', parent_format)
        sheet.write(5, 7, 'Vendor Name', parent_format)
        sheet.write(5, 8, 'Total Amount', parent_format)
        sheet.write(5, 9, 'Status', parent_format)

        rows = 6
        for bill in self.account_move_ids.filtered(lambda x: x.cust_invoice_id):
            sale_order = self.env['sale.order'].search([('name', '=', bill.cust_invoice_id.invoice_origin)])
            # tax_totals_json is gone from v16 onward. Everything that was read
            # out of it here was amount_total, which the record carries directly.
            sale_order_total = sale_order.amount_total if sale_order else 0.0
            sheet.write(rows, 0, bill.cust_invoice_id.name if bill.cust_invoice_id else '', center_format)
            if bill and bill.cust_invoice_id.currency_id != self.env.company.currency_id:
                amount_total_company = bill.cust_invoice_id.currency_id._convert(bill.cust_invoice_id.amount_total,
                                                                                 self.env.company.currency_id,
                                                                                 self.env.company,
                                                                                 bill.cust_invoice_id.invoice_date)
                sheet.write(rows, 1, amount_total_company if bill.cust_invoice_id else '', amount_format)
            else:
                sheet.write(rows, 1, bill.cust_invoice_id.amount_total if bill.cust_invoice_id else '', amount_format)
            sheet.write(rows, 2, dict(bill.cust_invoice_id._fields['payment_state'].selection).get(
                bill.cust_invoice_id.payment_state) if bill.cust_invoice_id else '', center_format)
            sheet.write(rows, 3, bill.cust_invoice_id.invoice_origin if bill.cust_invoice_id else '', center_format)
            if sale_order and sale_order.currency_id != self.env.company.currency_id:
                amount_so_total_company = sale_order.currency_id._convert(sale_order_total,
                                                                          self.env.company.currency_id,
                                                                          self.env.company, sale_order.date_order)
                sheet.write(rows, 4, amount_so_total_company if sale_order else '', amount_format)
            else:
                sheet.write(rows, 4, sale_order_total if sale_order else '', amount_format)
            sheet.write(rows, 5, dict(sale_order._fields['invoice_status'].selection).get(
                sale_order.invoice_status) if sale_order else '', center_format)
            purchase_orders = self.env['purchase.order'].search(
                [('sale_id', '!=', False), ('sale_id', '=', sale_order.id)])
            if purchase_orders:
                for po in purchase_orders:
                    po_total = po.amount_total
                    vendor_bill = self.env['account.move'].search([('invoice_origin', '=', po.name)])
                    sheet.write(rows, 6, po.name, center_format)
                    sheet.write(rows, 7, po.partner_id.name, center_format)
                    if po and po.currency_id != self.env.company.currency_id:
                        amount_po_total_company = po.currency_id._convert(po_total,
                                                                          self.env.company.currency_id,
                                                                          self.env.company, po.date_order)
                        sheet.write(rows, 8, amount_po_total_company, amount_format)
                    else:
                        sheet.write(rows, 8, po_total if po else '', amount_format)
                    sheet.write(rows, 9, dict(po._fields['state'].selection).get(po.state), center_format)
                    if vendor_bill:
                        for b in vendor_bill:
                            sheet.write(rows, 10, b.name, center_format)
                            if b and b.currency_id != self.env.company.currency_id:
                                amount_vb_total_company = b.currency_id._convert(b.amount_total,
                                                                                 self.env.company.currency_id,
                                                                                 self.env.company, b.invoice_date)
                                sheet.write(rows, 11, amount_vb_total_company, amount_format)
                            else:
                                sheet.write(rows, 11, b.amount_total if b else '', amount_format)
                            sheet.write(rows, 12, dict(b._fields['state'].selection).get(b.state), center_format)
                            sheet.write(rows, 13, dict(b._fields['payment_state'].selection).get(b.payment_state),
                                        center_format)
                            rows += 1
                    else:
                        rows += 1
            else:
                rows += 1
        workbook.close()
        fo = open(url + 'Invoice Report.xlsx', "rb+")
        data = fo.read()
        out = base64.encodebytes(data)
        self.write({'get_invoice_report': out, 'invoice_report_name': 'Invoice Report.xlsx'})


class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    @api.depends('can_edit_wizard', 'source_amount', 'source_amount_currency', 'source_currency_id', 'company_id', 'currency_id', 'payment_date', 'installments_mode')
    def _compute_amount(self):
        """Override to use the payment request amount when triggered from PR."""
        super()._compute_amount()
        for wizard in self:
            pr_amount = wizard.env.context.get('payment_request_amount')
            if pr_amount and pr_amount > 0:
                wizard.amount = pr_amount

    def action_create_payments(self):
        """Override to write payments back to payment.request when triggered from PR."""
        payment_request_id = self.env.context.get('payment_request_id')
        action = super().action_create_payments()

        if payment_request_id:
            pr = self.env['payment.request'].browse(payment_request_id)
            if pr.exists():
                # Extract created payment IDs from the action result
                payment_ids = []
                if isinstance(action, dict):
                    if action.get('res_id'):
                        payment_ids = [action['res_id']]
                    elif action.get('domain'):
                        for domain_item in action['domain']:
                            if isinstance(domain_item, (list, tuple)) and len(domain_item) == 3:
                                if domain_item[0] == 'id' and domain_item[1] == 'in':
                                    payment_ids = domain_item[2]

                if payment_ids:
                    pr.payment_ids = [(4, pid) for pid in payment_ids]
                pr.state = 'paid'

        return action


class Payments(models.Model):
    _inherit = 'account.payment'

    utr_number = fields.Char('UTR No.')
    cheque_number = fields.Char(string='Cheque Number')
    cheque_date = fields.Date(string='Cheque date')

    def action_utr_number_update(self):
        # _for_xml_id rather than env.ref(...).read()[0]. In Odoo 19 only the
        # administrator may read ir.actions.act_window, so reading the action as the
        # current user raised "You are not allowed to access 'Action Window'" for
        # every accountant pressing this button. It worked in v15 because a custom
        # access rule there granted read on that model to the Billing group, and that
        # rule was not carried over.
        #
        # _for_xml_id is what core uses for exactly this: it reads the action with
        # sudo and returns only the fields that are safe to hand to the web client.
        action = self.env['ir.actions.act_window']._for_xml_id('payment_request.action_payment_update_utr_number')
        action['context'] = {'default_payment_line_ids': self.ids}
        return action

    def action_cheque_number_update(self):
        action = self.env['ir.actions.act_window']._for_xml_id('payment_request.action_payment_update_cheque_number')
        partner_name = self.mapped('partner_id.name')[0]
        count_of_invoice = len(self.ids)
        print(count_of_invoice)
        if count_of_invoice == 1:
            action['context'] = {'default_payment_line_ids': self.ids, 'default_cheque_name': partner_name}
        else:
            action['context'] = {'default_payment_line_ids': self.ids}

        return action

    def payment_advice_mail(self):
        for rec in self:
            if not rec.partner_id.bank_ids:
                raise ValidationError(_('Please fill the "%s" account details in customer master'% rec.partner_id.name))
            if not rec.bank_reference:
                raise ValidationError(_('Please fill the UTR Bank Reference Number'))
            if not rec.partner_id.payment_receipt_email_to:
                raise ValidationError(_('Please fill the "%s" payment receipt email_to address in customer master'% rec.partner_id.name))
        for rec in self:
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
            if not rec.partner_id.payment_receipt_email_to:
                raise ValidationError(_('Please enter the "Email To" Address'))
            email = {
                'email_to': rec.partner_id.payment_receipt_email_to or '',
                'email_cc': rec.partner_id.payment_receipt_email_cc or '',
                'partner_to': False,
            }
            mail_template.write(email)
            mail_template.write({'attachment_ids': [(6, 0, [attachment.id])]})
            mail_template.send_mail(rec.id, force_send=True)

    def amount_in_text(self):
        for rec in self:
            amount_text = 'Zero'
            if rec.amount:
                amount_text = num2words(rec.amount, lang='en_IN').title()
            return amount_text

    def payment_advice_date(self):
        today = date.today()
        today_date = today.strftime("%d/%m/%Y")
        return today_date



