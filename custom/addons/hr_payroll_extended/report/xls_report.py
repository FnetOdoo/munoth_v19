# -*- coding: utf-8 -*-
"""
Migration Notes (v15 → v19) — xls_report.py
=============================================

1.  base64.encodestring() was removed in Python 3.9 (deprecated since 3.1).
    Replaced with base64.encodebytes() throughout.

2.  Employee-specific fields (esi_no, pf_no, pf_uan_no, joining_date,
    employee_id/code) now live on hr.employee directly (or the module
    adds them there).  Access pattern unchanged: payslip.employee_id.<field>.

3.  payslip.employee_id.employee_id  →  payslip.employee_id.emp_code
    (the old field was named employee_id on the employee — ambiguous; renamed
    to emp_code in models.py to avoid ORM confusion).

4.  company_id  →  In v17+ use  self.env.company  instead of
    self.env.user.company_id  (still works but deprecated path).

5.  No other structural changes needed — xlsxwriter API is unchanged.
"""

from odoo import models, api, fields, _
from datetime import datetime
import xlsxwriter
import tempfile
import base64
import logging

_logger = logging.getLogger(__name__)


class HrPayslipRun(models.Model):
    _inherit = "hr.payslip.run"

    filedata = fields.Binary('Excel Report', readonly=True)
    filename = fields.Char('Filename', size=64, readonly=True)

    bank_details = fields.Binary('NEFT Statement', readonly=True)
    bank_details_name = fields.Char('Filename', size=64, readonly=True)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _get_line_total(self, payslip, code):
        """Return the total for a payslip line by code, or 0.0 if absent."""
        line = payslip.line_ids.filtered(lambda x: x.code == code)
        return line.total if line else 0.0

    def _company_address(self, company):
        parts = [
            company.street or '',
            company.street2 or '',
            company.city or '',
            company.state_id.name if company.state_id else '',
            company.country_id.name if company.country_id else '',
            company.zip or '',
        ]
        return ' '.join(p for p in parts if p)

    # ------------------------------------------------------------------
    # Payslip batch Excel report
    # ------------------------------------------------------------------

    def action_xls_report_generate(self):
        url = '/tmp/'
        workbook = xlsxwriter.Workbook(url + 'Payslip Batches Report.xlsx')
        sheet = workbook.add_worksheet()

        payslips = self.env['hr.payslip'].search([('id', 'in', self.slip_ids.ids)])

        fmt_header = workbook.add_format({
            'font_size': 10, 'align': 'vcenter', 'valign': 'center', 'bold': True,
        })
        fmt_header.set_text_wrap()
        fmt_center = workbook.add_format({'font_size': 12, 'align': 'center'})
        fmt_date = workbook.add_format({'font_size': 12, 'align': 'left', 'num_format': 'dd-mm-yyyy'})
        fmt_bold_center = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'})

        # Column widths
        sheet.set_row(5, 50)
        sheet.set_column('A:A', 5)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 28)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:F', 15)
        for col_letter in 'GHIJKLMNOPQRSTUVWXY':
            sheet.set_column(f'{col_letter}:{col_letter}', 15)
        for col_pair in ['AA', 'AB', 'AC', 'AD', 'AE', 'AF', 'AG', 'AH',
                         'AI', 'AJ', 'AK', 'AL', 'AM', 'AN', 'AO', 'AP',
                         'AQ', 'AR', 'AS', 'AT', 'AU']:
            sheet.set_column(f'{col_pair}:{col_pair}', 15)

        # v17+ recommended: use self.env.company
        company = self.env.company
        month = datetime.strptime(str(self.date_start), '%Y-%m-%d').strftime("%B")
        current_year = datetime.strptime(str(self.date_start), '%Y-%m-%d').strftime("%Y")

        sheet.merge_range('B1:E1', company.name, fmt_header)
        sheet.merge_range('B2:E2', self._company_address(company), fmt_bold_center)
        sheet.merge_range('B3:E3', f'PAYSLIP BATCHES REPORT - {month} {current_year}', fmt_header)

        # Header row
        headers = [
            'S.No', 'Employee ID', 'Name', 'Date of Joining',
            'Pay Days', 'Number of Days Present',
            'BASIC', 'Bonus', 'HRA', 'Conveyance Allowance',
            'Other Allowance', 'Travel Allowance', 'Medical Allowance',
            'Earnings Allowance', 'Data Card Allowance', 'Overtime Allowance',
            'Arrears', 'Arrear', 'Consolidate Pay', 'Gross',
            'Employee PF', 'Employer PF', 'Employee ESI', 'Employer ESI',
            'Gratuity', 'Mobile Deduction', 'Advance Salary',
            'TDS', 'Other Deduction', 'PT', 'Total Deduction', 'Net',
            'ESI Number', 'PF Number', 'PF/UAN Number',
        ]
        for idx, h in enumerate(headers):
            sheet.write(5, idx, h, fmt_header)

        # Payslip codes matching headers (cols 6 onward)
        codes = [
            'BASIC', 'BONUS', 'HRA', 'CONV', 'OTHER', 'Travel', 'Medical',
            'EA', 'CARD', 'NOT', 'ARR', 'AR', 'CON', 'GROSS',
            'EEPF', 'EPF', 'ESI', 'ESI2', 'GR', 'MD', 'AS',
            'TDS', 'OD', 'PT',
        ]

        totals = {c: 0.0 for c in codes}
        totals['NET'] = 0.0
        totals['DED'] = 0.0
        s_no = 1
        data_row = 6  # 0-indexed row 6 → row 7 in sheet (row 5 = headers at index 5)

        for payslip in payslips:
            emp = payslip.employee_id
            sheet.write(data_row, 0, s_no, fmt_center)
            sheet.write(data_row, 1, emp.emp_code or '', fmt_center)
            sheet.write(data_row, 2, emp.name, fmt_center)
            sheet.write(data_row, 3, emp.joining_date, fmt_date)
            sheet.write(data_row, 4, payslip.tot_month_days, fmt_center)
            sheet.write(data_row, 5, payslip.tot_month_days - payslip.lop_days, fmt_center)

            col = 6
            for code in codes:
                val = self._get_line_total(payslip, code)
                sheet.write(data_row, col, val, fmt_center)
                totals[code] = totals.get(code, 0.0) + val
                col += 1

            # Total deduction (category DED)
            ded = sum(payslip.line_ids.filtered(
                lambda x: x.category_id.code == 'DED').mapped('total'))
            sheet.write(data_row, col, ded, fmt_center)
            totals['DED'] += ded
            col += 1

            net = self._get_line_total(payslip, 'NET')
            sheet.write(data_row, col, net, fmt_center)
            totals['NET'] += net
            col += 1

            sheet.write(data_row, col, emp.esi_no or '', fmt_center)
            sheet.write(data_row, col + 1, emp.pf_no or '', fmt_center)
            sheet.write(data_row, col + 2, emp.pf_uan_no or '', fmt_center)

            s_no += 1
            data_row += 1

        # Totals row
        total_row = data_row
        sheet.write(total_row, 5, "Totals", fmt_bold_center)
        col = 6
        for code in codes:
            sheet.write(total_row, col, totals.get(code, 0.0), fmt_bold_center)
            col += 1
        sheet.write(total_row, col, totals['DED'], fmt_bold_center)
        col += 1
        sheet.write(total_row, col, totals['NET'], fmt_bold_center)

        workbook.close()

        with open(url + 'Payslip Batches Report.xlsx', 'rb') as fo:
            # base64.encodestring removed in Py3.9 → use encodebytes
            out = base64.encodebytes(fo.read())

        self.write({'filedata': out, 'filename': 'Payslip Batches Report.xlsx'})

    # ------------------------------------------------------------------
    # NEFT bank statement
    # ------------------------------------------------------------------

    def bank_acc_details(self):
        url = '/tmp/'
        workbook = xlsxwriter.Workbook(url + 'NEFT Statement.xlsx')
        sheet = workbook.add_worksheet()

        fmt_header = workbook.add_format({
            'font_size': 10, 'align': 'vcenter', 'valign': 'center', 'bold': True,
        })
        fmt_header.set_text_wrap()
        fmt_center = workbook.add_format({'font_size': 12, 'align': 'center'})
        fmt_bold_center = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter'})

        sheet.set_row(5, 50)
        for col_letter, width in [('A', 5), ('B', 20), ('C', 20), ('D', 28),
                                   ('E', 15), ('F', 15), ('G', 58)]:
            sheet.set_column(f'{col_letter}:{col_letter}', width)

        company = self.env.company
        sheet.merge_range('B1:E1', company.name, fmt_header)
        sheet.merge_range('B2:E2', self._company_address(company), fmt_bold_center)
        sheet.merge_range('B3:E3', 'NEFT Statement', fmt_header)

        headers_neft = [
            'S.No', 'Beneficiary Name', 'Beneficiary Account Number',
            'Bank Name', 'IFSC Code', 'Amount', 'Remarks for Beneficiary',
        ]
        for idx, h in enumerate(headers_neft):
            sheet.write(5, idx, h, fmt_header)

        banks = self.env['hr.payslip'].search([('id', 'in', self.slip_ids.ids)])
        s_no = 1
        amount_total = 0.0
        data_row = 6

        for bank in banks:
            emp = bank.employee_id
            bank_acc = emp.bank_account_id

            sheet.write(data_row, 0, s_no, fmt_center)
            sheet.write(data_row, 1, emp.name, fmt_center)
            sheet.write(data_row, 2, bank_acc.acc_number if bank_acc else ' ', fmt_center)
            sheet.write(data_row, 3,
                        bank_acc.bank_id.name if (bank_acc and bank_acc.bank_id) else ' ',
                        fmt_center)
            sheet.write(data_row, 4,
                        bank_acc.ifsc_code if (bank_acc and hasattr(bank_acc, 'ifsc_code')) else ' ',
                        fmt_center)
            net = self._get_line_total(bank, 'NET')
            sheet.write(data_row, 5, net, fmt_center)
            sheet.write(data_row, 6, bank.name, fmt_center)

            amount_total += net
            s_no += 1
            data_row += 1

        sheet.write(data_row, 5, amount_total, fmt_bold_center)
        workbook.close()

        with open(url + 'NEFT Statement.xlsx', 'rb') as fo:
            out = base64.encodebytes(fo.read())

        self.write({'bank_details': out, 'bank_details_name': 'NEFT Statement.xlsx'})
