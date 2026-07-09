from odoo import models, fields, api, _
import base64
import xlsxwriter
import io
from datetime import timedelta, datetime




class MttrMtbf(models.TransientModel):
    _name = 'mttr.mtbf'
    _description = 'MTTR MTBF Report'

    date_from = fields.Datetime('Date From', required=True)
    date_to = fields.Datetime('Date To', required=True)
    operation = fields.Many2one('manufacturing.operation')
    quality_id = fields.Many2one('mrp.quality')

    plan = fields.Many2one('production.plan')
    manufacturing_process_type_id = fields.Many2one('manufacturing.process.type')

    def action_mttr_mtbf_report(self):
        url = '/tmp/'
        workbook = xlsxwriter.Workbook(url + 'MTTR MTBF Report.xlsx')
        sheet = workbook.add_worksheet()
        format1 = workbook.add_format({'font_size': 8, 'align': 'vcenter', 'valign': 'center', 'italic': True})
        format3 = workbook.add_format(
            {'font_size': 10, 'align': 'vcenter', 'valign': 'center', 'italic': True, 'font_color': '#D0312D'})
        format2 = workbook.add_format(
            {'font_size': 8, 'align': 'vcenter', 'valign': 'center'})
        format1.set_text_wrap()
        month_year_format = workbook.add_format(
            {'bold': True, 'border': 1, 'font_color': 'black', 'bg_color': '#84B701', 'align': 'center',
             'valign': 'vcenter'})
        heading = workbook.add_format(
            {'bold': True, 'border': 1, 'bg_color': '#84b701', 'align': 'center', 'valign': 'vcenter',
             'font_color': 'white'})
        bold = workbook.add_format({'bold': True, 'align': 'center', 'valign': 'vcenter', 'font_size': 10})
        bold_1 = workbook.add_format({'font_size': 10, 'align': 'center', 'valign': 'vcenter', 'italic': True})

        sheet.set_column('A:A', 5)
        sheet.set_column('B:B', 10)
        sheet.set_column('C:C', 15)
        sheet.set_column('D:D', 20)
        sheet.set_column('E:E', 25)
        sheet.set_column('F:F', 30)
        sheet.set_column('G:G', 25)
        sheet.set_column('H:H', 25)
        sheet.set_column('I:I', 25)
        sheet.set_column('J:J', 25)
        image_data = base64.b64decode(self.env.company.logo)
        image_stream = io.BytesIO(image_data)
        sheet.insert_image('A1', '/web/binary/company_logo',
                           {'image_data': image_stream, 'x_scale': 0.2, 'y_scale': 0.2})

        sheet.merge_range('B1:J2', 'MTTR MTBF Report', heading)
        sheet.write('A3', 'S.no', bold)
        sheet.write('B3', 'Date', bold)
        sheet.write('C3', 'Machine', bold)
        sheet.write('D3', 'issues', bold)
        sheet.write('E3', 'Root cause', bold)
        sheet.write('F3', 'Action taken', bold)
        sheet.write('G3', 'Total Operating time(mins)', bold)
        sheet.write('H3', 'BreakDown time(mins)', bold)
        sheet.write('I3', 'no of downtimes', bold)
        sheet.write('J3', 'Uptime/available time', bold)

        row = 3
        row_1 = 0
        col_1 = 0
        row_val = 0
        col_val = 0
        col = 6
        s_no = 1
        mttr_value = 0
        total_minutes = 0
        mttr_value_list = []
        uptime_avaliable = []
        total_cal = 0
        breakdown_list = 0
        break_down = []
        breakdown_val = 0
        mttr_total = 0
        mtrf_total = 0

        if self.manufacturing_process_type_id:
            domain = [('manufacturing_process_type_id', '=', self.manufacturing_process_type_id.id)]
            if self.plan:
                domain.append(('production_plan_id', '=', self.plan.id))

            processes = self.env['manufacturing.process'].search(domain)

            for breakdown in processes:
                start_time = breakdown.start_time
                end_time = breakdown.end_time

                if start_time and end_time:
                    if end_time < start_time:
                        start_time, end_time = end_time, start_time
                    delta = end_time - start_time
                    minute = abs(delta.total_seconds()) / 60
                    total_minutes = round(minute)

                for rec in breakdown.breakdown_ids.filtered(
                        lambda x: x.time and x.end_time and x.time >= self.date_from and x.end_time <= self.date_to
                ):
                    rec_time = rec.time
                    rec_end_time = rec.end_time

                    if rec_end_time < rec_time:
                        rec_time, rec_end_time = rec_end_time, rec_time

                    delta = rec_end_time - rec_time
                    minutes = abs(delta.total_seconds()) / 60
                    rounded_minutes = round(minutes)
                    mttr_value_list.append(rounded_minutes)
                    mttr_value = sum(mttr_value_list)
                    no_of_breakdown = 1
                    break_down.append(no_of_breakdown)
                    breakdown_val = sum(break_down)
                    if total_minutes and rounded_minutes:
                        uptime = total_minutes + rounded_minutes
                        total_cal = round(uptime)
                        uptime_avaliable.append(total_cal)
                    breakdown_list = sum(uptime_avaliable)
                    if mttr_value and breakdown_val:
                        mttr_total = mttr_value / breakdown_val
                        mtrf_total = breakdown_list / breakdown_val

                    sheet.write(row, col - 4, (breakdown.machine_id.name or '').replace('machine', ''), format2)
                    sheet.write(row, col - 6, s_no, format2)
                    sheet.write(row, col - 5, rec_time.strftime('%d/%m/%Y'), format2)
                    sheet.write(row, col - 3, rec.remarks, format2)
                    sheet.write(row, col - 2, rec.root_cause, format2)
                    sheet.write(row, col - 1, rec.action_taken, format2)
                    sheet.write(row, col + 2, no_of_breakdown, format2)
                    sheet.write(row, col + 3, total_cal, format2)
                    sheet.write(row, col + 1, rounded_minutes, format2)
                    sheet.write(row, col, total_minutes, format2)

                    row += 1
                    s_no += 1

            row_1 += row
            sheet.merge_range(
                row_1, col_1, row_1 + 1, col_1 + 8,
                              'PREPARED by:SENTHAMIZHAN' + '    ' + 'VERIFIED by:SENTHAMIZHAN' + '    ' + 'APPROVED by:SENTHAMIZHAN',
                format2
            )
            row_val += row_1 + 1
            sheet.write(row_val + 2, col_val + 5, 'MTTR=Total downtime/no of failures', format2)
            sheet.write(row_val + 2, col_val + 6, mttr_total, format2)
            sheet.write(row_val + 1, col_val + 5, 'MTRF=uptime/available time/no of failures', format2)
            sheet.write(row_val + 1, col_val + 6, mtrf_total, format2)

        workbook.close()
        with open(url + 'MTTR MTBF Report.xlsx', 'rb') as fo:
            data = fo.read()
        out = base64.encodebytes(data)
        values = {
            'name': 'mttr_mtbf_report.xlsx',
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
