# -*- coding: utf-8 -*-
import base64
import io

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import xlsxwriter  # bundled with Odoo


class MaintenanceReportWizard(models.TransientModel):
    _name = 'maintenance.report.wizard'
    _description = 'PM Maintenance Request Report (XLSX)'

    start_date = fields.Date(
        string='Start Date',
        required=True,
        default=lambda self: fields.Date.context_today(self).replace(day=1),
        help='Filters on Actual Work Start Date (actual_start_date).')
    end_date = fields.Date(
        string='End Date',
        required=True,
        default=fields.Date.context_today,
        help='Filters on Actual Work End Date (actual_end_date).')

    file_data = fields.Binary(string='XLSX File', readonly=True)
    file_name = fields.Char(string='File Name', readonly=True)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------
    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for wizard in self:
            if wizard.start_date and wizard.end_date \
                    and wizard.start_date > wizard.end_date:
                raise ValidationError(
                    _('Start Date must be before End Date.'))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_requests(self):
        """Maintenance Requests whose actual work started on/after
        Start Date and actually ended on/before End Date."""
        self.ensure_one()
        domain = [
            ('actual_start_date', '>=', f'{self.start_date} 00:00:00'),
            ('actual_end_date', '<=', f'{self.end_date} 23:59:59'),
        ]
        return self.env['maintenance.request'].search(
            domain, order='actual_start_date')

    def _fmt_dt(self, value):
        """Datetime -> user-timezone string, empty when not set."""
        if not value:
            return ''
        value = fields.Datetime.context_timestamp(self, value)
        return value.strftime('%d/%m/%Y %H:%M')

    def _fmt_duration(self, value):
        """Float hours -> 'HHH:MM' string.

        Examples: 0.0 -> '00:00', 1.25 -> '1:15', 192.0 -> '192:00',
        192.75 -> '192:45'.
        """
        if not value:
            return '00:00'
        total_minutes = round(value * 60)
        hours, minutes = divmod(total_minutes, 60)
        return '%d:%02d' % (hours, minutes)

    def _report_columns(self):
        """Column spec: (Header, width, getter). Everything on the
        request except Created By and Responsible. Columns whose field
        does not exist on this database are skipped automatically."""
        Request = self.env['maintenance.request']

        def has(fname):
            return fname in Request._fields

        columns = [
            ('S.No', 6, None),  # filled with the row number
            ('Request', 40, lambda r: r.name or ''),
            ('Equipment', 30, lambda r: r.equipment_id.display_name or ''),
            ('Category', 18, lambda r: r.category_id.display_name or ''),
            ('Maintenance Type', 16,
             lambda r: dict(Request._fields['maintenance_type'].selection).get(
                 r.maintenance_type, r.maintenance_type or '')),
        ]
        if has('maintenance_kind'):
            columns.append(('Maintenance Kind', 16,
                            lambda r: r.maintenance_kind or ''))
        columns += [
            ('Team', 20, lambda r: r.maintenance_team_id.display_name or ''),
            ('Stage', 16, lambda r: r.stage_id.display_name or ''),
            ('Scheduled Date', 18, lambda r: self._fmt_dt(r.schedule_date)),
            ('Actual Work Start', 18,
             lambda r: self._fmt_dt(r.actual_start_date)),
            ('Actual Work End', 18,
             lambda r: self._fmt_dt(r.actual_end_date)),
            ('Duration (Hours)', 14,
             lambda r: self._fmt_duration(r.duration)),
        ]
        return columns

    # ------------------------------------------------------------------
    # XLSX generation
    # ------------------------------------------------------------------
    def action_generate_report(self):
        self.ensure_one()
        requests = self._get_requests()

        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        sheet = workbook.add_worksheet('PM Completed')

        # ---- Formats: neat blue/green theme matching the dashboard ----
        title_fmt = workbook.add_format({
            'bold': True, 'font_size': 16, 'font_color': '#FFFFFF',
            'bg_color': '#3B7DDD', 'align': 'center', 'valign': 'vcenter',
            'border': 1, 'border_color': '#2A5DA8',
        })
        subtitle_fmt = workbook.add_format({
            'italic': True, 'font_size': 10, 'font_color': '#37474F',
            'bg_color': '#E8F1FC', 'align': 'center', 'valign': 'vcenter',
            'border': 1, 'border_color': '#B9D3F2',
        })
        header_fmt = workbook.add_format({
            'bold': True, 'font_size': 10, 'font_color': '#FFFFFF',
            'bg_color': '#28A745', 'align': 'center', 'valign': 'vcenter',
            'text_wrap': True, 'border': 1, 'border_color': '#1E7E34',
        })
        cell_fmt = workbook.add_format({
            'font_size': 10, 'valign': 'vcenter',
            'border': 1, 'border_color': '#CFD8DC',
        })
        cell_alt_fmt = workbook.add_format({
            'font_size': 10, 'valign': 'vcenter', 'bg_color': '#F1F7EE',
            'border': 1, 'border_color': '#CFD8DC',
        })
        center_fmt = workbook.add_format({
            'font_size': 10, 'align': 'center', 'valign': 'vcenter',
            'border': 1, 'border_color': '#CFD8DC',
        })
        center_alt_fmt = workbook.add_format({
            'font_size': 10, 'align': 'center', 'valign': 'vcenter',
            'bg_color': '#F1F7EE', 'border': 1, 'border_color': '#CFD8DC',
        })
        total_fmt = workbook.add_format({
            'bold': True, 'font_size': 10, 'font_color': '#FFFFFF',
            'bg_color': '#37474F', 'align': 'right', 'valign': 'vcenter',
            'border': 1,
        })

        columns = self._report_columns()
        last_col = len(columns) - 1

        # Column index of Duration, to center it like a number.
        duration_col = next(
            (i for i, c in enumerate(columns)
             if c[0] == 'Duration (Hours)'), -1)

        # ---- Title & subtitle -----------------------------------------
        sheet.set_row(0, 28)
        sheet.merge_range(0, 0, 0, last_col,
                          'PM Completed Report', title_fmt)
        sheet.set_row(1, 18)
        sheet.merge_range(
            1, 0, 1, last_col,
            'Actual Work Start from %s    to    Actual Work End %s' % (
                self.start_date.strftime('%d/%m/%Y'),
                self.end_date.strftime('%d/%m/%Y')),
            subtitle_fmt)

        # ---- Header row -------------------------------------------------
        header_row = 3
        sheet.set_row(header_row, 24)
        for col, (label, width, _getter) in enumerate(columns):
            sheet.set_column(col, col, width)
            sheet.write(header_row, col, label, header_fmt)
        sheet.freeze_panes(header_row + 1, 0)

        # ---- Data rows (alternating band colors) ------------------------
        row = header_row + 1
        for index, request in enumerate(requests, start=1):
            banded = index % 2 == 0
            text_fmt = cell_alt_fmt if banded else cell_fmt
            num_fmt = center_alt_fmt if banded else center_fmt
            sheet.write(row, 0, index, num_fmt)
            for col, (_label, _width, getter) in enumerate(columns):
                if getter is None:
                    continue
                value = getter(request)
                if isinstance(value, (int, float)) or col == duration_col:
                    # numbers and the HH:MM duration are centered
                    sheet.write(row, col, value, num_fmt)
                else:
                    sheet.write(row, col, value, text_fmt)
            row += 1

        # ---- Total row ---------------------------------------------------
        sheet.merge_range(row, 0, row, last_col,
                          'Total Requests: %s' % len(requests), total_fmt)

        workbook.close()
        buffer.seek(0)

        self.write({
            'file_data': base64.b64encode(buffer.read()),
            'file_name': 'PM_Completed_Report_%s_to_%s.xlsx' % (
                self.start_date, self.end_date),
        })
        buffer.close()

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/file_data/%s?download=true' % (
                self._name, self.id, self.file_name),
            'target': 'self',
        }