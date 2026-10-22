# -*- coding: utf-8 -*-
from odoo import api, fields, models, tools, _
from datetime import datetime, date, timedelta
import datetime
import xlsxwriter
import base64
from odoo.http import request

class PaymentRequest(models.Model):
    
    _inherit = 'payment.request'
    
    def print_account_details(self):
        
        url = "/tmp/"
        workbook = xlsxwriter.Workbook(url + 'Payment_request.xlsx')
        worksheet = workbook.add_worksheet()
        bold = workbook.add_format(
            {'bold': True, 'align': 'center', 'border': 1})
        norm = workbook.add_format(
            {'bold': False, 'align': 'center', 'border': 1})
        format_1 = workbook.add_format(
            {'bold': True, 'align': 'center', 'bg_color': '#FFFF00', 'font_size': '18px'})
        background1 = workbook.add_format(
            {'bg_color': '#F5CBA7', 'align': 'center', 'bold': True, 'border': 1})
        background2 = workbook.add_format(
            {'bg_color': '#FADBD8', 'align': 'center', 'bold': True, 'border': 1})

        for obj in self:
            row = 0
            col = 0
            row += 3
            worksheet.set_column('A:A', 23)
            worksheet.set_column('B:B', 17)
            worksheet.set_column('C:C', 17)
            worksheet.set_column('D:D', 30)
            worksheet.set_column('E:E', 25)
            worksheet.set_column('F:F', 20)
            worksheet.set_column('G:G', 20)
            worksheet.set_column('H:H', 20)
            worksheet.set_column('I:I', 17)
            worksheet.merge_range(0, 0, 2, 5, 'Creditor Bank Account Details', format_1)
            # row += 1
            worksheet.write(row, col, 'Payment Request ', background2)
            worksheet.write(row, col + 1, (obj.payment_request_date).strftime('%d-%m-%Y'), background2)
            worksheet.write(row, col + 4, 'Payment Request Number', background2)
            worksheet.write(row, col + 5, obj.request_number, background2)
            row += 1
            worksheet.write(row, col, 'Payment Approved ', background2)
            worksheet.write(row, col + 1,
                        (obj.payment_approved_date).strftime('%d-%m-%Y') if obj.payment_approved_date else '',
                        background2)
            worksheet.write(row, col + 4, 'Status', background2)
            worksheet.write(row, col + 5, obj.state, background2)
            row += 1
            worksheet.write(row, col, 'Bank Account Number', bold)
            worksheet.write(row, col + 1, 'Bank IFSC code', bold)
            worksheet.write(row, col + 2, 'Name of the Bank', bold)
            worksheet.write(row, col + 3, 'Name of the Branch', bold)
            worksheet.write(row, col + 4, 'Name of the Beneficiary', bold)
            worksheet.write(row, col + 5, 'Amount', bold)
            row += 1
            for a in obj.account_move_ids:
                worksheet.write(row, col, a.partner_id.bank_ids[0].acc_number if a.partner_id.bank_ids else '', norm)
                worksheet.write(row, col + 1, a.partner_id.bank_ids[0].bank_id.bic if a.partner_id.bank_ids else '', norm)
                worksheet.write(row, col + 2, a.partner_id.bank_ids[0].bank_id.name if a.partner_id.bank_ids else '', norm)
                worksheet.write(row, col + 3, a.partner_id.bank_ids[0].bank_id.street if a.partner_id.bank_ids else '',
                            norm)
                worksheet.write(row, col + 4, a.partner_id.name, norm)
                worksheet.write(row, col + 5, abs(a.amount_residual_signed), norm)
                row += 1
            row += 2
            worksheet.write(row, col + 4, 'Total Due Amount', background1)
            print(obj.total_due_amount)
            worksheet.write(row, col + 5, abs(obj.total_due_amount), background1)
            row += 1

        workbook.close()
        fo = open(url + 'Payment_request.xlsx', "rb+")
        data = fo.read()
        out = base64.encodebytes(data)
        self.write({'file_data': out, 'filename': 'Payment_request.xlsx'})
