from odoo import api, models, fields, _
import xlsxwriter
import base64
from datetime import date, datetime, timedelta, time






class ProcessStatusReport(models.TransientModel):
    _name = "process.status.report"
    _description = "Process Status Report"

    product_model_id=fields.Many2one('product.model',string='Model')
    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)

    def generate_report(self):
            url = '/tmp/'
            workbook = xlsxwriter.Workbook(url + 'Complaint Call Register.xlsx')
            sheet = workbook.add_worksheet()
            header = workbook.add_format({'font_size': 9, 'align': 'vcenter', 'valign': 'center', 'bold': True, 'bg_color': '#7ac5cd','text_wrap': True})
            format1 = workbook.add_format({'font_size': 9, 'align': 'vcenter', 'valign': 'center', 'bold': True, 'text_wrap' : True})
            date_format = workbook.add_format({'num_format': 'dd-mm-yyyy','bold': True,'font_size': 9, 'align': 'vcenter', 'valign': 'center','text_wrap': True})

            sheet.set_column('A:A', 5)
            sheet.set_column('B:B', 5)
            sheet.set_column('C:C', 40)
            sheet.set_column('D:D', 40)
            sheet.set_column('E:E', 20)
            sheet.set_column('F:F', 10)
            sheet.set_column('G:G', 15)
            sheet.set_column('H:H', 10)
            sheet.set_column('I:I', 15)
            sheet.set_column('J:J', 25)
            sheet.set_column('K:K', 10)
            sheet.set_column('L:L', 10)
            sheet.set_column('M:M', 20)
            sheet.set_column('N:N', 15)
            sheet.set_column('O:O', 20)
            sheet.set_column('P:P', 20)
            sheet.set_column('Q:Q', 20)
            sheet.set_row(2,30)


            sheet.merge_range('D1:F1','Customer Complaint - Call Register', format1)
            start_date = self.start_date
            end_date = self.end_date
            dates = []
            while start_date <= end_date:
                dates.append(start_date.isoformat())
                start_date += timedelta(days=1)

            complaints = self.env['complaint.register'].sudo().search([('product_model_id', '=', self.product_model_id.id)])
            row = 2
            sheet.write('O1:O1','Doc', format1)
            sheet.write('O2:O2','Rev No', format1)
            sheet.write(row, 1, 'S.No', header)
            sheet.write(row, 2, 'Customer', header)
            sheet.write(row, 3, 'Product', header)
            sheet.write(row, 4, 'Model No', header)
            sheet.write(row, 5, 'Modality', header)
            sheet.write(row, 6, ' Received On ', header)
            sheet.write(row, 7, '  Completed On ', header)
            sheet.write(row, 8, ' Complaint Details ', header)
            sheet.write(row, 9, 'Lot Qty', header)
            sheet.write(row, 10, ' defect Qty', header)
            sheet.write(row, 11, ' Repeated Complaint (Y/N) ', header)
            sheet.write(row, 12, ' Attended by ', header)
            sheet.write(row, 13, 'Call Solved through ', header)
            sheet.write(row, 14, 'Call Closure Status ', header)
            sheet.write(row, 15, 'Remarks ', header)
            row += 1
            s_no = 1
            for complaint in complaints:
                sheet.write('P1:P1', complaint.doc_no, format1)
                sheet.write('P2:P2', complaint.no_revision, date_format)
                sheet.write(row, 1, s_no, format1)
                sheet.write(row, 2, complaint.customer_id.name if complaint.customer_id else '', format1)
                sheet.write(row, 3, complaint.product_id.name if complaint.product_id else '', format1)
                sheet.write(row, 4, complaint.product_model_id.name if complaint.product_model_id else '', format1)
                sheet.write(row, 5,
                            'In Person' if complaint.modality == 'in_person' else 'Communication via Call or Email' if complaint.modality == 'system' else '',
                            format1)
                sheet.write(row, 6, complaint.received_on if complaint.received_on else '', date_format)
                sheet.write(row, 7, complaint.completed_on if complaint.completed_on else '', date_format)
                sheet.write(row, 8, complaint.complaint_details if complaint.complaint_details else '', format1)
                sheet.write(row,9, complaint.lot_qty if complaint.lot_qty else '', format1)
                sheet.write(row, 10, complaint.defect_qty if complaint.defect_qty else '', format1)
                sheet.write(row, 11, complaint.repeated_complain if complaint.repeated_complain else 'Remote' if complaint.repeated_complain == 'remote' else '',format1)
                sheet.write(row, 12, complaint.attended_by.name,format1)
                sheet.write(row, 13, 'In Person' if complaint.call_solved == 'in_person'else '', format1)
                sheet.write(row, 14, complaint.status,format1)
                sheet.write(row, 15, complaint.remark if complaint.remark else '', format1)
                row += 1
                s_no += 1

            workbook.close()
            fo = open(url + 'Complaint Call Register.xlsx', "rb+")
            data = fo.read()
            # Migration v15→v19: base64.encodestring removed in Python 3.9+
            out = base64.encodebytes(data)
            values = {
                'name': 'customer_complain_register.xlsx',
                'res_model': 'ir.ui.view',
                'res_id': False,
                'type': 'binary',
                'public': True,
                'datas': out,
            }
            attachment_id = self.env['ir.attachment'].sudo().create(values)
            download_url = '/web/content/' + str(attachment_id.id) + '?download=True'
            base_url = self.env['ir.config_parameter'].get_param('web.base.url')
            return {
                "type": "ir.actions.act_url",
                "url": str(base_url) + str(download_url),
                "target": "new",
            }



