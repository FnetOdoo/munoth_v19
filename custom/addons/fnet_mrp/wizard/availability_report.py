from odoo import models, fields, api, _
import base64
import xlsxwriter
import io
from datetime import timedelta, datetime

class AvailabilityReport(models.TransientModel):
    _name = 'availability.report'
    _description = 'Availability Report'

    date_from = fields.Datetime('Date From', required=True)
    date_to = fields.Datetime('Date To', required=True)
    plan = fields.Many2one('production.plan')
    type = fields.Selection([
        ('anode_slitting', 'Anode Slitting '),
        ('cathode_slitting', 'Cathode Slitting '),
        ('anode_drying', 'Anode Drying'),
        ('cathode_drying', 'Cathode Drying'),
        ('diaphragm_drying', 'Diaphragm Drying'),
        ('anode_electrode_making', 'Anode Electrode Making'),
        ('cathode_electrode_making', 'Cathode Electrode Making'),
        ('winding', 'Winding'),
        ('hot_press_jelly', 'Hot Press Jelly'),
        ('assembly', 'Assembly'),
        ('cell_drying', 'Cell Drying'),
        ('injection', 'Injection'),
        ('high_temperature', 'High Temperature'),
        ('cell_baking_formation', 'Cell Formation'),
        ('aged_formation_cell', 'Aged Formation Cell'),
        ('degas', 'Degas'),
        ('dsf', 'Double side Folding'),
        ('pad_printing', 'Pad Printing'),
        ('capacity_test', 'Capacity Test'),
        ('voltage', 'Voltage Test'),
        ('package', 'Package Test')
    ])
    no_of_machine = fields.Char(required=True)


    def action_availability_report(self):
        url = '/tmp/'
        workbook = xlsxwriter.Workbook(url + 'Availability Report.xlsx')
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
        # sheet.add_image(image_data, 'A1')
        sheet.insert_image('A1', '/web/binary/company_logo',
                           {'image_data': image_stream, 'x_scale': 0.2, 'y_scale': 0.2})

        sheet.merge_range('A1:F2', 'Availability Report', heading)
        sheet.write('A3', 'S.no', bold)
        sheet.write('B3', 'Month', bold)
        sheet.write('C3', 'Days', bold)
        sheet.write('D3', 'no of Machines ', bold)
        sheet.write('E3', 'Over all down Time (Mins)', bold)
        sheet.write('F3', 'Availability', bold)

        start_date = self.date_from
        end_date = self.date_to
        months = {}
        production_plan = self.env['production.plan'].search([],limit=1)
        plan = len(production_plan.operation_ids)
        print("-----------", plan,"-----plan------\n")
        print("-----------", production_plan,"-----production_plan------\n")

        while start_date <= end_date:
            if start_date.month not in months:
                months[start_date.month] = []
            months[start_date.month].append(start_date.day)
            start_date += timedelta(days=1)

        row = 3
        s_no = 1
        for month, days in months.items():
            production = self.env['production.breakdown'].search([
                ('time', '>=', self.date_from),
                ('end_time', '<=', self.date_to),
                ('code', '=', 'hold')
              
            ])
            monthly_totals = {}
            for record in production:
                if record.time and record.end_time:
                    record_month = record.time.month
                    delta = record.end_time - record.time
                    if record_month not in monthly_totals:
                        monthly_totals[record_month] = delta.total_seconds() / 60
                    else:
                        monthly_totals[record_month] += delta.total_seconds() / 60

            total_minutes = monthly_totals.get(month, 0)
            total_minutes_rounded = round(total_minutes, 2)
            total_days = len(days)
            availability = 0
            if total_minutes:
                available_minutes = total_days * 8 * 60 * 14
                availability = (available_minutes - total_minutes_rounded) / available_minutes
            availability_rounded = availability

            if month == self.date_from.month:
                year = self.date_from.year
            elif month == self.date_to.month:
                year = self.date_to.year
            else:
                year = self.date_from.year if month < self.date_from.month else self.date_to.year
            sheet.write(row, 0, s_no, format2)
            sheet.write(row, 1, f"{month}/{year}", format2)
            sheet.write(row, 2, total_days, format2)
            sheet.write(row, 3, self.no_of_machine, format2)
            sheet.write(row, 4, total_minutes_rounded, format2)
            sheet.write(row, 5, availability_rounded, format2)

            row += 1
            s_no += 1

        workbook.close()
        fo = open(url + 'Availability Report.xlsx', "rb+")
        data = fo.read()
        out = base64.encodebytes(data)
        values = {
            'name': 'availability_report.xlsx',
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