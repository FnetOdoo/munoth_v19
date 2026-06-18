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
    ],required=True)
    plan = fields.Many2one('production.plan')


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
        # sheet.add_image(image_data, 'A1')
        sheet.insert_image('A1', '/web/binary/company_logo',
                           {'image_data': image_stream,'x_scale': 0.2, 'y_scale': 0.2})

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


        start_date = self.date_from
        end_date = self.date_to
        dates = []
        while start_date <= end_date:
            dates.append(start_date.isoformat())
            start_date += timedelta(days=1)
        domain = []
        if self.date_from and self.date_to:
            domain.append(('time', '>=', self.date_from))
            domain.append(('end_time', '<=', self.date_to))
        row = 3
        row_1 =0
        col_1 =0
        row_val =0
        col_val =0
        col = 6
        s_no = 1
        cell_drying = self.env['cell.drying'].search([])
        mttr_value = 0
        total_minutes = 0
        mttr_value_list = []
        uptime_avaliable=[]
        total_cal =0
        breakdown_list = 0
        break_down=[]
        breakdown_val = 0
        mttr_total = 0
        mtrf_total = 0

        if self.type == 'cell_drying':
            for breakdown in cell_drying:
                if breakdown.start_time and breakdown.end_time:
                    if breakdown.end_time < breakdown.start_time:
                        breakdown.time, breakdown.end_time = breakdown.end_time, breakdown.start_time
                    delta = breakdown.end_time - breakdown.start_time
                    minute = abs(delta.total_seconds()) / 60
                    total_minutes =round(minute)
                for rec in breakdown.breakdown_ids.filtered(lambda x: x.time and x.end_time and x.time >= self.date_from and x.end_time <= self.date_to):
                    if rec.time and rec.end_time:
                        if rec.end_time < rec.time:
                            rec.time, rec.end_time = rec.end_time, rec.time
                        delta = rec.end_time - rec.time
                        minutes = abs(delta.total_seconds()) / 60
                        rounded_minutes = round(minutes)
                        mttr_value_list.append(rounded_minutes)
                        mttr_value =sum(mttr_value_list)
                        no_of_breakdown =1
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

                        sheet.write(row, col - 4, breakdown.machine_id.name.replace('machine', ''), format2)
                        sheet.write(row, col - 6, s_no, format2)
                        sheet.write(row, col - 5, rec.time.strftime('%d/%m/%Y'), format2)
                        sheet.write(row, col - 3, rec.remarks, format2)
                        sheet.write(row, col - 2, rec.root_cause, format2)
                        sheet.write(row, col - 1, rec.action_taken, format2)
                        sheet.write(row, col + 2, no_of_breakdown, format2)
                        sheet.write(row, col + 3, total_cal, format2)
                        sheet.write(row, col+ 1, rounded_minutes, format2)
                        sheet.write(row, col, total_minutes, format2)
                    row+=1
                    s_no+=1
            row_1 += row
            sheet.merge_range(row_1, col_1,row_1+1, col_1+8,'PREPARED by:SENTHAMIZHAN' +'    '+'VERIFIED by:SENTHAMIZHAN' +'    '+ 'APPROVED by:SENTHAMIZHAN', format2)
            row_val += row_1+1
            sheet.write(row_val+2,col_val+5,'MTTR=Total downtime/no of failures', format2)
            sheet.write(row_val+2,col_val+6,mttr_total, format2)
            sheet.write(row_val+1, col_val + 5, 'MTRF=uptime/available time/no of failures', format2)
            sheet.write(row_val+1, col_val + 6, mtrf_total, format2)

        #injection
        cell_injection = self.env['cell.injection'].search([])
        print("-----------", cell_injection,"-----cell_injection------\n")
        if self.type == 'injection':
            print("-----------", 1111111111111111111111,"-----1111111111111111111111------\n")
            for breakdown in cell_injection:
                if breakdown.start_time and breakdown.end_time:
                    if breakdown.end_time < breakdown.start_time:
                        breakdown.time, breakdown.end_time = breakdown.end_time, breakdown.start_time
                    delta = breakdown.end_time - breakdown.start_time
                    minute = abs(delta.total_seconds()) / 60
                    total_minutes =round(minute)
                for rec in breakdown.breakdown_ids.filtered(lambda x: x.time and x.end_time and x.time >= self.date_from and x.end_time <= self.date_to):
                    if rec.time and rec.end_time:
                        if rec.end_time < rec.time:
                            rec.time, rec.end_time = rec.end_time, rec.time
                        delta = rec.end_time - rec.time
                        minutes = abs(delta.total_seconds()) / 60
                        rounded_minutes = round(minutes)
                        mttr_value_list.append(rounded_minutes)
                        mttr_value =sum(mttr_value_list)
                        no_of_breakdown =1
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

                        sheet.write(row, col - 4, breakdown.machine_id.name.replace('machine', ''), format2)
                        sheet.write(row, col - 6, s_no, format2)
                        sheet.write(row, col - 5, rec.time.strftime('%d/%m/%Y'), format2)
                        sheet.write(row, col - 3, rec.remarks, format2)
                        sheet.write(row, col - 2, rec.root_cause, format2)
                        sheet.write(row, col - 1, rec.action_taken, format2)
                        sheet.write(row, col + 2, no_of_breakdown, format2)
                        sheet.write(row, col + 3, total_cal, format2)
                        sheet.write(row, col+ 1, rounded_minutes, format2)
                        sheet.write(row, col, total_minutes, format2)
                    row+=1
                    s_no+=1
            row_1 += row
            sheet.merge_range(row_1, col_1,row_1+1, col_1+8,'PREPARED by:SENTHAMIZHAN' +'    '+'VERIFIED by:SENTHAMIZHAN' +'    '+ 'APPROVED by:SENTHAMIZHAN', format2)
            row_val += row_1+1
            sheet.write(row_val+2,col_val+5,'MTTR=Total downtime/no of failures', format2)
            sheet.write(row_val+2,col_val+6,mttr_total, format2)
            sheet.write(row_val+1, col_val + 5, 'MTRF=uptime/available time/no of failures', format2)
            sheet.write(row_val+1, col_val + 6, mtrf_total, format2)


        #high tempture cell
        high_temp_cell = self.env['high.temperature.cell'].search([])
        if self.type == 'high_temperature':
            for breakdown in high_temp_cell:
                if breakdown.start_time and breakdown.end_time:
                    if breakdown.end_time < breakdown.start_time:
                        breakdown.time, breakdown.end_time = breakdown.end_time, breakdown.start_time
                    delta = breakdown.end_time - breakdown.start_time
                    minute = abs(delta.total_seconds()) / 60
                    total_minutes =round(minute)
                for rec in breakdown.breakdown_ids.filtered(lambda x: x.time and x.end_time and x.time >= self.date_from and x.end_time <= self.date_to):
                    if rec.time and rec.end_time:
                        if rec.end_time < rec.time:
                            rec.time, rec.end_time = rec.end_time, rec.time
                        delta = rec.end_time - rec.time
                        minutes = abs(delta.total_seconds()) / 60
                        rounded_minutes = round(minutes)
                        mttr_value_list.append(rounded_minutes)
                        mttr_value =sum(mttr_value_list)
                        no_of_breakdown =1
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

                        sheet.write(row, col - 4, breakdown.machine_id.name.replace('machine', ''), format2)
                        sheet.write(row, col - 6, s_no, format2)
                        sheet.write(row, col - 5, rec.time.strftime('%d/%m/%Y'), format2)
                        sheet.write(row, col - 3, rec.remarks, format2)
                        sheet.write(row, col - 2, rec.root_cause, format2)
                        sheet.write(row, col - 1, rec.action_taken, format2)
                        sheet.write(row, col + 2, no_of_breakdown, format2)
                        sheet.write(row, col + 3, total_cal, format2)
                        sheet.write(row, col+ 1, rounded_minutes, format2)
                        sheet.write(row, col, total_minutes, format2)
                    row+=1
                    s_no+=1
            row_1 += row
            sheet.merge_range(row_1, col_1,row_1+1, col_1+8,'PREPARED by:SENTHAMIZHAN' +'    '+'VERIFIED by:SENTHAMIZHAN' +'    '+ 'APPROVED by:SENTHAMIZHAN', format2)
            row_val += row_1+1
            sheet.write(row_val+2,col_val+5,'MTTR=Total downtime/no of failures', format2)
            sheet.write(row_val+2,col_val+6,mttr_total, format2)
            sheet.write(row_val+1, col_val + 5, 'MTRF=uptime/available time/no of failures', format2)
            sheet.write(row_val+1, col_val + 6, mtrf_total, format2)

        cell_clamp_bak = self.env['cell.clamp.baking'].search([])
        if self.type == 'cell_baking_formation':
            for breakdown in cell_clamp_bak:
                if breakdown.start_time and breakdown.end_time:
                    if breakdown.end_time < breakdown.start_time:
                        breakdown.time, breakdown.end_time = breakdown.end_time, breakdown.start_time
                    delta = breakdown.end_time - breakdown.start_time
                    minute = abs(delta.total_seconds()) / 60
                    total_minutes =round(minute)
                for rec in breakdown.breakdown_ids.filtered(lambda x: x.time and x.end_time and x.time >= self.date_from and x.end_time <= self.date_to):
                    if rec.time and rec.end_time:
                        if rec.end_time < rec.time:
                            rec.time, rec.end_time = rec.end_time, rec.time
                        delta = rec.end_time - rec.time
                        minutes = abs(delta.total_seconds()) / 60
                        rounded_minutes = round(minutes)
                        mttr_value_list.append(rounded_minutes)
                        mttr_value =sum(mttr_value_list)
                        no_of_breakdown =1
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

                        sheet.write(row, col - 4, breakdown.machine_id.name.replace('machine', ''), format2)
                        sheet.write(row, col - 6, s_no, format2)
                        sheet.write(row, col - 5, rec.time.strftime('%d/%m/%Y'), format2)
                        sheet.write(row, col - 3, rec.remarks, format2)
                        sheet.write(row, col - 2, rec.root_cause, format2)
                        sheet.write(row, col - 1, rec.action_taken, format2)
                        sheet.write(row, col + 2, no_of_breakdown, format2)
                        sheet.write(row, col + 3, total_cal, format2)
                        sheet.write(row, col+ 1, rounded_minutes, format2)
                        sheet.write(row, col, total_minutes, format2)
                    row+=1
                    s_no+=1
            row_1 += row
            sheet.merge_range(row_1, col_1,row_1+1, col_1+8,'PREPARED by:SENTHAMIZHAN' +'    '+'VERIFIED by:SENTHAMIZHAN' +'    '+ 'APPROVED by:SENTHAMIZHAN', format2)
            row_val += row_1+1
            sheet.write(row_val+2,col_val+5,'MTTR=Total downtime/no of failures', format2)
            sheet.write(row_val+2,col_val+6,mttr_total, format2)
            sheet.write(row_val+1, col_val + 5, 'MTRF=uptime/available time/no of failures', format2)
            sheet.write(row_val+1, col_val + 6, mtrf_total, format2)
        #aged formation cell
        aged_formation_cell = self.env['aged.formation.cell'].search([])
        if self.type == 'aged_formation_cell':
            for breakdown in aged_formation_cell:
                if breakdown.start_time and breakdown.end_time:
                    if breakdown.end_time < breakdown.start_time:
                        breakdown.time, breakdown.end_time = breakdown.end_time, breakdown.start_time
                    delta = breakdown.end_time - breakdown.start_time
                    minute = abs(delta.total_seconds()) / 60
                    total_minutes =round(minute)
                for rec in breakdown.breakdown_ids.filtered(lambda x: x.time and x.end_time and x.time >= self.date_from and x.end_time <= self.date_to):
                    if rec.time and rec.end_time:
                        if rec.end_time < rec.time:
                            rec.time, rec.end_time = rec.end_time, rec.time
                        delta = rec.end_time - rec.time
                        minutes = abs(delta.total_seconds()) / 60
                        rounded_minutes = round(minutes)
                        mttr_value_list.append(rounded_minutes)
                        mttr_value =sum(mttr_value_list)
                        no_of_breakdown =1
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

                        sheet.write(row, col - 4, breakdown.machine_id.name.replace('machine', ''), format2)
                        sheet.write(row, col - 6, s_no, format2)
                        sheet.write(row, col - 5, rec.time.strftime('%d/%m/%Y'), format2)
                        sheet.write(row, col - 3, rec.remarks, format2)
                        sheet.write(row, col - 2, rec.root_cause, format2)
                        sheet.write(row, col - 1, rec.action_taken, format2)
                        sheet.write(row, col + 2, no_of_breakdown, format2)
                        sheet.write(row, col + 3, total_cal, format2)
                        sheet.write(row, col+ 1, rounded_minutes, format2)
                        sheet.write(row, col, total_minutes, format2)
                    row+=1
                    s_no+=1
            row_1 += row
            sheet.merge_range(row_1, col_1,row_1+1, col_1+8,'PREPARED by:SENTHAMIZHAN' +'    '+'VERIFIED by:SENTHAMIZHAN' +'    '+ 'APPROVED by:SENTHAMIZHAN', format2)
            row_val += row_1+1
            sheet.write(row_val+2,col_val+5,'MTTR=Total downtime/no of failures', format2)
            sheet.write(row_val+2,col_val+6,mttr_total, format2)
            sheet.write(row_val+1, col_val + 5, 'MTRF=uptime/available time/no of failures', format2)
            sheet.write(row_val+1, col_val + 6, mtrf_total, format2)

        #degas
        degas = self.env['degas.cell'].search([])
        if self.type == 'degas':
            for breakdown in degas:
                if breakdown.start_time and breakdown.end_time:
                    if breakdown.end_time < breakdown.start_time:
                        breakdown.time, breakdown.end_time = breakdown.end_time, breakdown.start_time
                    delta = breakdown.end_time - breakdown.start_time
                    minute = abs(delta.total_seconds()) / 60
                    total_minutes =round(minute)
                for rec in breakdown.breakdown_ids.filtered(lambda x: x.time and x.end_time and x.time >= self.date_from and x.end_time <= self.date_to):
                    if rec.time and rec.end_time:
                        if rec.end_time < rec.time:
                            rec.time, rec.end_time = rec.end_time, rec.time
                        delta = rec.end_time - rec.time
                        minutes = abs(delta.total_seconds()) / 60
                        rounded_minutes = round(minutes)
                        mttr_value_list.append(rounded_minutes)
                        mttr_value =sum(mttr_value_list)
                        no_of_breakdown =1
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

                        sheet.write(row, col - 4, breakdown.machine_id.name.replace('machine', ''), format2)
                        sheet.write(row, col - 6, s_no, format2)
                        sheet.write(row, col - 5, rec.time.strftime('%d/%m/%Y'), format2)
                        sheet.write(row, col - 3, rec.remarks, format2)
                        sheet.write(row, col - 2, rec.root_cause, format2)
                        sheet.write(row, col - 1, rec.action_taken, format2)
                        sheet.write(row, col + 2, no_of_breakdown, format2)
                        sheet.write(row, col + 3, total_cal, format2)
                        sheet.write(row, col+ 1, rounded_minutes, format2)
                        sheet.write(row, col, total_minutes, format2)
                    row+=1
                    s_no+=1
            row_1 += row
            sheet.merge_range(row_1, col_1,row_1+1, col_1+8,'PREPARED by:SENTHAMIZHAN' +'    '+'VERIFIED by:SENTHAMIZHAN' +'    '+ 'APPROVED by:SENTHAMIZHAN', format2)
            row_val += row_1+1
            sheet.write(row_val+2,col_val+5,'MTTR=Total downtime/no of failures', format2)
            sheet.write(row_val+2,col_val+6,mttr_total, format2)
            sheet.write(row_val+1, col_val + 5, 'MTRF=uptime/available time/no of failures', format2)
            sheet.write(row_val+1, col_val + 6, mtrf_total, format2)

        # capacity_test
        capacity_test = self.env['capacity.test'].search([])
        if self.type == 'capacity_test':
            for breakdown in capacity_test:
                if breakdown.start_time and breakdown.end_time:
                    if breakdown.end_time < breakdown.start_time:
                        breakdown.time, breakdown.end_time = breakdown.end_time, breakdown.start_time
                    delta = breakdown.end_time - breakdown.start_time
                    minute = abs(delta.total_seconds()) / 60
                    total_minutes =round(minute)
                for rec in breakdown.breakdown_ids.filtered(lambda x: x.time and x.end_time and x.time >= self.date_from and x.end_time <= self.date_to):
                    if rec.time and rec.end_time:
                        if rec.end_time < rec.time:
                            rec.time, rec.end_time = rec.end_time, rec.time
                        delta = rec.end_time - rec.time
                        minutes = abs(delta.total_seconds()) / 60
                        rounded_minutes = round(minutes)
                        mttr_value_list.append(rounded_minutes)
                        mttr_value =sum(mttr_value_list)
                        no_of_breakdown =1
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

                        sheet.write(row, col - 4, breakdown.machine_id.name.replace('machine', ''), format2)
                        sheet.write(row, col - 6, s_no, format2)
                        sheet.write(row, col - 5, rec.time.strftime('%d/%m/%Y'), format2)
                        sheet.write(row, col - 3, rec.remarks, format2)
                        sheet.write(row, col - 2, rec.root_cause, format2)
                        sheet.write(row, col - 1, rec.action_taken, format2)
                        sheet.write(row, col + 2, no_of_breakdown, format2)
                        sheet.write(row, col + 3, total_cal, format2)
                        sheet.write(row, col+ 1, rounded_minutes, format2)
                        sheet.write(row, col, total_minutes, format2)
                    row+=1
                    s_no+=1
            row_1 += row
            sheet.merge_range(row_1, col_1,row_1+1, col_1+8,'PREPARED by:SENTHAMIZHAN' +'    '+'VERIFIED by:SENTHAMIZHAN' +'    '+ 'APPROVED by:SENTHAMIZHAN', format2)
            row_val += row_1+1
            sheet.write(row_val+2,col_val+5,'MTTR=Total downtime/no of failures', format2)
            sheet.write(row_val+2,col_val+6,mttr_total, format2)
            sheet.write(row_val+1, col_val + 5, 'MTRF=uptime/available time/no of failures', format2)
            sheet.write(row_val+1, col_val + 6, mtrf_total, format2)

        # pad_printing
        pad_printing = self.env['pad.printing'].search([])
        if self.type == 'pad_printing':
            for breakdown in pad_printing:
                if breakdown.start_time and breakdown.end_time:
                    if breakdown.end_time < breakdown.start_time:
                        breakdown.time, breakdown.end_time = breakdown.end_time, breakdown.start_time
                    delta = breakdown.end_time - breakdown.start_time
                    minute = abs(delta.total_seconds()) / 60
                    total_minutes =round(minute)
                for rec in breakdown.breakdown_ids.filtered(lambda x: x.time and x.end_time and x.time >= self.date_from and x.end_time <= self.date_to):
                    if rec.time and rec.end_time:
                        if rec.end_time < rec.time:
                            rec.time, rec.end_time = rec.end_time, rec.time
                        delta = rec.end_time - rec.time
                        minutes = abs(delta.total_seconds()) / 60
                        rounded_minutes = round(minutes)
                        mttr_value_list.append(rounded_minutes)
                        mttr_value =sum(mttr_value_list)
                        no_of_breakdown =1
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

                        sheet.write(row, col - 4, breakdown.machine_id.name.replace('machine', ''), format2)
                        sheet.write(row, col - 6, s_no, format2)
                        sheet.write(row, col - 5, rec.time.strftime('%d/%m/%Y'), format2)
                        sheet.write(row, col - 3, rec.remarks, format2)
                        sheet.write(row, col - 2, rec.root_cause, format2)
                        sheet.write(row, col - 1, rec.action_taken, format2)
                        sheet.write(row, col + 2, no_of_breakdown, format2)
                        sheet.write(row, col + 3, total_cal, format2)
                        sheet.write(row, col+ 1, rounded_minutes, format2)
                        sheet.write(row, col, total_minutes, format2)
                    row+=1
                    s_no+=1
            row_1 += row
            sheet.merge_range(row_1, col_1,row_1+1, col_1+8,'PREPARED by:SENTHAMIZHAN' +'    '+'VERIFIED by:SENTHAMIZHAN' +'    '+ 'APPROVED by:SENTHAMIZHAN', format2)
            row_val += row_1+1
            sheet.write(row_val+2,col_val+5,'MTTR=Total downtime/no of failures', format2)
            sheet.write(row_val+2,col_val+6,mttr_total, format2)
            sheet.write(row_val+1, col_val + 5, 'MTRF=uptime/available time/no of failures', format2)
            sheet.write(row_val+1, col_val + 6, mtrf_total, format2)

        # voltage
        voltage = self.env['voltage.test'].search([])
        if self.type == 'voltage':
            for breakdown in voltage:
                if breakdown.start_time and breakdown.end_time:
                    if breakdown.end_time < breakdown.start_time:
                        breakdown.time, breakdown.end_time = breakdown.end_time, breakdown.start_time
                    delta = breakdown.end_time - breakdown.start_time
                    minute = abs(delta.total_seconds()) / 60
                    total_minutes =round(minute)
                for rec in breakdown.breakdown_ids.filtered(lambda x: x.time and x.end_time and x.time >= self.date_from and x.end_time <= self.date_to):
                    if rec.time and rec.end_time:
                        if rec.end_time < rec.time:
                            rec.time, rec.end_time = rec.end_time, rec.time
                        delta = rec.end_time - rec.time
                        minutes = abs(delta.total_seconds()) / 60
                        rounded_minutes = round(minutes)
                        mttr_value_list.append(rounded_minutes)
                        mttr_value =sum(mttr_value_list)
                        no_of_breakdown =1
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

                        sheet.write(row, col - 4, breakdown.machine_id.name.replace('machine', ''), format2)
                        sheet.write(row, col - 6, s_no, format2)
                        sheet.write(row, col - 5, rec.time.strftime('%d/%m/%Y'), format2)
                        sheet.write(row, col - 3, rec.remarks, format2)
                        sheet.write(row, col - 2, rec.root_cause, format2)
                        sheet.write(row, col - 1, rec.action_taken, format2)
                        sheet.write(row, col + 2, no_of_breakdown, format2)
                        sheet.write(row, col + 3, total_cal, format2)
                        sheet.write(row, col+ 1, rounded_minutes, format2)
                        sheet.write(row, col, total_minutes, format2)
                    row+=1
                    s_no+=1
            row_1 += row
            sheet.merge_range(row_1, col_1,row_1+1, col_1+8,'PREPARED by:SENTHAMIZHAN' +'    '+'VERIFIED by:SENTHAMIZHAN' +'    '+ 'APPROVED by:SENTHAMIZHAN', format2)
            row_val += row_1+1
            sheet.write(row_val+2,col_val+5,'MTTR=Total downtime/no of failures', format2)
            sheet.write(row_val+2,col_val+6,mttr_total, format2)
            sheet.write(row_val+1, col_val + 5, 'MTRF=uptime/available time/no of failures', format2)
            sheet.write(row_val+1, col_val + 6, mtrf_total, format2)

        # package
        package = self.env['package.move'].search([])
        if self.type == 'package':
            for breakdown in package:
                if breakdown.start_time and breakdown.end_time:
                    if breakdown.end_time < breakdown.start_time:
                        breakdown.time, breakdown.end_time = breakdown.end_time, breakdown.start_time
                    delta = breakdown.end_time - breakdown.start_time
                    minute = abs(delta.total_seconds()) / 60
                    total_minutes =round(minute)
                for rec in breakdown.breakdown_ids.filtered(lambda x: x.time and x.end_time and x.time >= self.date_from and x.end_time <= self.date_to):
                    if rec.time and rec.end_time:
                        if rec.end_time < rec.time:
                            rec.time, rec.end_time = rec.end_time, rec.time
                        delta = rec.end_time - rec.time
                        minutes = abs(delta.total_seconds()) / 60
                        rounded_minutes = round(minutes)
                        mttr_value_list.append(rounded_minutes)
                        mttr_value =sum(mttr_value_list)
                        no_of_breakdown =1
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

                        sheet.write(row, col - 4, breakdown.machine_id.name.replace('machine', ''), format2)
                        sheet.write(row, col - 6, s_no, format2)
                        sheet.write(row, col - 5, rec.time.strftime('%d/%m/%Y'), format2)
                        sheet.write(row, col - 3, rec.remarks, format2)
                        sheet.write(row, col - 2, rec.root_cause, format2)
                        sheet.write(row, col - 1, rec.action_taken, format2)
                        sheet.write(row, col + 2, no_of_breakdown, format2)
                        sheet.write(row, col + 3, total_cal, format2)
                        sheet.write(row, col+ 1, rounded_minutes, format2)
                        sheet.write(row, col, total_minutes, format2)
                    row+=1
                    s_no+=1
            row_1 += row
            sheet.merge_range(row_1, col_1,row_1+1, col_1+8,'PREPARED by:SENTHAMIZHAN' +'    '+'VERIFIED by:SENTHAMIZHAN' +'    '+ 'APPROVED by:SENTHAMIZHAN', format2)
            row_val += row_1+1
            sheet.write(row_val+2,col_val+5,'MTTR=Total downtime/no of failures', format2)
            sheet.write(row_val+2,col_val+6,mttr_total, format2)
            sheet.write(row_val+1, col_val + 5, 'MTRF=uptime/available time/no of failures', format2)
            sheet.write(row_val+1, col_val + 6, mtrf_total, format2)

        workbook.close()
        fo = open(url + 'MTTR MTBF Report.xlsx', "rb+")
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

