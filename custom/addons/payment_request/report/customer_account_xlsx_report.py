from odoo import models


class PartnerXlsx(models.AbstractModel):
    _name = 'report.payment_request.report_customer_acc_details_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, payment):
        print(payment)
        print(data)
        bold = workbook.add_format(
            {'bold': True, 'align': 'center', 'border': 1})
        norm = workbook.add_format(
            {'bold': False, 'align': 'center', 'border': 1})
        format_1 = workbook.add_format(
            {'bold': True, 'align': 'center', 'bg_color': '#FFFF00', 'font_size': '18px'})
        background = workbook.add_format(
            {'bg_color': 'red', 'align': 'center', 'bold': False, 'border': 1})
        background1 = workbook.add_format(
            {'bg_color': '#F5CBA7', 'align': 'center', 'bold': True, 'border': 1})
        background2 = workbook.add_format(
            {'bg_color': '#FADBD8', 'align': 'center', 'bold': True, 'border': 1})
        cell_format = workbook.add_format({'align': 'center', 'font_size': '12px', 'bold': True, 'border': 2})

        for obj in payment:
            sheet = workbook.add_worksheet(obj.request_number)
            row = 0
            col = 0
            row += 3
            sheet.set_column('A:A', 25)
            sheet.set_column('B:B', 20)
            sheet.set_column('C:C', 20)
            sheet.set_column('D:D', 20)
            sheet.set_column('E:E', 25)
            sheet.set_column('F:F', 23)
            sheet.set_column('G:G', 20)
            sheet.set_column('H:H', 20)
            sheet.set_column('I:I', 20)
            sheet.merge_range(0, 0, 2, 5, 'Creditor Bank Account Details', format_1)
            # row += 1
            sheet.write(row, col, 'Payment Request ', background2)
            sheet.write(row, col + 1, (obj.payment_request_date).strftime('%d-%m-%Y'), background2)
            sheet.write(row, col + 4, 'Payment Request Number', background2)
            sheet.write(row, col + 5, obj.request_number, background2)
            row += 1
            sheet.write(row, col, 'Payment Approved ', background2)
            sheet.write(row, col + 1,
                        (obj.payment_approved_date).strftime('%d-%m-%Y') if obj.payment_approved_date else '',
                        background2)
            sheet.write(row, col + 4, 'Status', background2)
            sheet.write(row, col + 5, obj.state, background2)
            row += 1
            sheet.write(row, col, 'Bank Account Number', bold)
            sheet.write(row, col + 1, 'Bank IFSC code', bold)
            sheet.write(row, col + 2, 'Name of the Bank', bold)
            sheet.write(row, col + 3, 'Name of the Branch', bold)
            sheet.write(row, col + 4, 'Name of the Beneficiary', bold)
            sheet.write(row, col + 5, 'Amount', bold)
            row += 1
            for a in obj.account_move_ids:
                sheet.write(row, col, a.partner_id.bank_ids[0].acc_number if a.partner_id.bank_ids else '', norm)
                sheet.write(row, col + 1, a.partner_id.bank_ids[0].bank_id.bic if a.partner_id.bank_ids else '', norm)
                sheet.write(row, col + 2, a.partner_id.bank_ids[0].bank_id.name if a.partner_id.bank_ids else '', norm)
                sheet.write(row, col + 3, a.partner_id.bank_ids[0].bank_id.street if a.partner_id.bank_ids else '',
                            norm)
                sheet.write(row, col + 4, a.partner_id.name, norm)
                sheet.write(row, col + 5, abs(a.amount_residual_signed), norm)
                row += 1
            row += 2
            sheet.write(row, col + 4, 'Total Due Amount', background1)
            print(obj.total_due_amount)
            sheet.write(row, col + 5, abs(obj.total_due_amount), background1)
            row += 1
