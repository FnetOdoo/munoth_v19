from odoo import api, models, fields, _
from odoo.exceptions import ValidationError
import base64
from num2words import num2words
from datetime import date
import xlsxwriter
import json


class InvoiceReport(models.TransientModel):
    _name = 'invoice.report.wizard'
    _description = 'Invoice Report'

    date_from = fields.Date(string='Date From')
    date_to = fields.Date(string='Date To')
    get_invoice_report = fields.Binary('Invoice Report', readonly=True)
    invoice_report_name = fields.Char('Filename', size=64, readonly=True)

    def generate_invoice_details_report(self):
        url = '/tmp/'
        workbook = xlsxwriter.Workbook(url + 'Invoice Report.xlsx')
        sheet = workbook.add_worksheet()
        format1 = workbook.add_format({'font_size': 11, 'align': 'vcenter', 'valign': 'center'})
        parent_format = workbook.add_format({'font_size': 13, 'bold': True, 'align': 'center'})
        center_format = workbook.add_format({'font_size': 11, 'align': 'center'})
        left_format = workbook.add_format({'font_size': 11, 'align': 'left'})
        right_format = workbook.add_format({'font_size': 11, 'align': 'right'})
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
        sheet.set_column('K:K', 20)
        sheet.set_column('L:L', 20)
        sheet.set_column('M:M', 20)
        sheet.set_column('N:N', 20)
        sheet.set_column('O:O', 20)
        sheet.set_column('P:P', 20)
        sheet.set_column('Q:Q', 20)
        sheet.set_column('R:R', 20)
        sheet.set_column('S:S', 20)
        sheet.set_column('T:T', 20)
        sheet.set_column('U:U', 20)
        sheet.set_column('V:V', 20)
        sheet.set_column('W:W', 20)
        sheet.set_column('X:X', 20)
        sheet.set_column('Y:Y', 20)
        sheet.set_column('Z:Z', 20)
        sheet.set_column('AA:AA', 20)
        sheet.set_column('AB:AB', 20)
        sheet.set_column('AC:AC', 20)
        sheet.set_column('AD:AD', 20)
        sheet.set_column('AE:AE', 20)
        sheet.set_column('AF:AF', 20)
        sheet.set_column('AG:AG', 20)
        sheet.set_column('AH:AH', 20)
        sheet.set_column('AI:AI', 20)
        sheet.set_column('AJ:AJ', 20)
        sheet.set_column('AK:AK', 20)
        sheet.set_column('AL:AL', 20)
        sheet.set_column('AM:AM', 20)
        sheet.set_column('AN:AN', 20)
        sheet.set_column('AO:AO', 20)
        sheet.set_column('AP:AP', 20)
        sheet.set_column('AQ:AQ', 20)
        sheet.set_column('AR:AR', 20)
        sheet.set_column('AS:AS', 20)
        sheet.set_column('AT:AT', 20)
        sheet.set_column('AU:AU', 20)
        sheet.merge_range('B3:E3', 'INVOICE REPORT', bold)
        sheet.write(5, 0, 'Customer Invoice No.', parent_format)
        sheet.write(5, 1, 'Untaxed Amount', parent_format)
        sheet.write(5, 2, 'Total Amount', parent_format)
        sheet.write(5, 3, 'Payment Status', parent_format)
        sheet.write(5, 4, 'Sale Order No.', parent_format)
        sheet.write(5, 5, 'Untaxed Amount', parent_format)
        sheet.write(5, 6, 'Total Amount', parent_format)
        sheet.write(5, 7, 'Invoice Status', parent_format)
        sheet.write(5, 8, 'PO No.', parent_format)
        sheet.write(5, 9, 'Vendor Name', parent_format)
        sheet.write(5, 10, 'Untaxed Amount', parent_format)
        sheet.write(5, 11, 'Total Amount', parent_format)
        sheet.write(5, 12, 'Status', parent_format)
        sheet.write(5, 13, 'Billing Status', parent_format)
        sheet.write(5, 14, 'Vendor Bill No.', parent_format)
        sheet.write(5, 15, 'Untaxed Amount', parent_format)
        sheet.write(5, 16, 'Total Amount', parent_format)
        sheet.write(5, 17, 'Status', parent_format)
        sheet.write(5, 18, 'Payment Status', parent_format)
        rows = 6
        invoices = self.env['account.move'].search([('move_type', '=', 'out_invoice'), ('invoice_date', '>=', self.date_from),
                                                    ('invoice_date', '<=', self.date_to), ('state', '=', 'posted'), ('invoice_origin', 'ilike', 'SO/')])
        for inv in invoices:
            sale_order = self.env['sale.order'].search([('name', '=', inv.invoice_origin)])
            # tax_totals_json is gone from v16 onward; both figures read out of it
            # here are carried on the order itself.
            so_untaxed = sale_order.amount_untaxed if sale_order else 0.0
            so_total = sale_order.amount_total if sale_order else 0.0
            sheet.write(rows, 0, inv.name, center_format)
            sheet.write(rows, 1, inv.amount_untaxed, right_format)
            sheet.write(rows, 2, inv.amount_total, right_format)
            sheet.write(rows, 3, dict(inv._fields['payment_state'].selection).get(inv.payment_state), center_format)
            sheet.write(rows, 4, inv.invoice_origin, center_format)
            sheet.write(rows, 5, so_untaxed if sale_order else '', right_format)
            sheet.write(rows, 6, so_total if sale_order else '', right_format)
            sheet.write(rows, 7, dict(sale_order._fields['invoice_status'].selection).get(sale_order.invoice_status) if sale_order else '', center_format)
            purchase_orders = self.env['purchase.order'].search([('sale_id', '!=', False), ('sale_id', '=', sale_order.id)])
            if purchase_orders:
                for po in purchase_orders:
                    po_untaxed, po_total = po.amount_untaxed, po.amount_total
                    vendor_bill = self.env['account.move'].search([('partner_id', '=', po.partner_id.id), ('invoice_origin', '=', po.name)])
                    sheet.write(rows, 8, po.name, center_format)
                    sheet.write(rows, 9, po.partner_id.name, center_format)
                    sheet.write(rows, 10, po_untaxed, right_format)
                    sheet.write(rows, 11, po_total, right_format)
                    sheet.write(rows, 12, dict(po._fields['state'].selection).get(po.state), center_format)
                    sheet.write(rows, 13, dict(po._fields['invoice_status'].selection).get(po.invoice_status),center_format)
                    if vendor_bill:
                        for b in vendor_bill:
                            sheet.write(rows, 14, b.name, center_format)
                            sheet.write(rows, 15, b.amount_untaxed, right_format)
                            sheet.write(rows, 16, b.amount_total, right_format)
                            sheet.write(rows, 17, dict(b._fields['state'].selection).get(b.state), center_format)
                            sheet.write(rows, 18, dict(b._fields['payment_state'].selection).get(b.payment_state), center_format)
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
        return {
            'view_mode': 'form',
            'res_model': 'invoice.report.wizard',
            'res_id': self.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }