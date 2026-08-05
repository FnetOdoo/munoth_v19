# -*- coding: utf-8 -*-
import base64
import io

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

import xlsxwriter  # bundled with Odoo

try:
    from PIL import Image, ImageDraw, ImageFont
    _HAS_PIL = True
except Exception:                       # pragma: no cover
    _HAS_PIL = False

_FONT_CANDIDATES = [
    '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf',
    '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf',
    '/usr/share/fonts/liberation/LiberationSans-Bold.ttf',
]
_PILL_SCALE = 3


def _hex_rgb(value):
    value = value.lstrip('#')
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _make_status_pill(text, fill, font_size):
    """(BytesIO png, w_px, h_px) rounded pill with white text, or None."""
    if not _HAS_PIL:
        return None
    font = None
    for path in _FONT_CANDIDATES:
        try:
            font = ImageFont.truetype(path, font_size * _PILL_SCALE)
            break
        except Exception:
            continue
    if font is None:
        return None
    try:
        b = ImageDraw.Draw(Image.new('RGBA', (4, 4))).textbbox(
            (0, 0), text, font=font)
        tw, th = b[2] - b[0], b[3] - b[1]
        padx, pady = 11 * _PILL_SCALE, 4 * _PILL_SCALE
        w, h = tw + 2 * padx, th + 2 * pady
        img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=h // 2,
                            fill=_hex_rgb(fill), outline=_hex_rgb(fill))
        d.text(((w - tw) / 2 - b[0], (h - th) / 2 - b[1]), text,
               font=font, fill=(255, 255, 255))
        bio = io.BytesIO()
        img.save(bio, 'PNG')
        bio.seek(0)
        return bio, w, h
    except Exception:
        return None


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

    @api.constrains('start_date', 'end_date')
    def _check_dates(self):
        for wizard in self:
            if wizard.start_date and wizard.end_date \
                    and wizard.start_date > wizard.end_date:
                raise ValidationError(_('Start Date must be before End Date.'))

    # ------------------------------------------------------------------
    # Data helpers
    # ------------------------------------------------------------------
    def _get_requests(self):
        self.ensure_one()
        domain = [
            ('request_date', '>=', f'{self.start_date} 00:00:00'),
            ('request_date', '<=', f'{self.end_date} 23:59:59'),
            ('is_calibration', '=', False),
        ]
        return self.env['maintenance.request'].search(
            domain, order='request_date')

    def _get_work_orders(self, request):
        return self.env['work.order'].search(
            [('maintenance_id', '=', request.id)], order='id')

    def _fmt_dt(self, value):
        if not value:
            return ''
        value = fields.Datetime.context_timestamp(self, value)
        return value.strftime('%d/%m/%Y %H:%M')

    def _fmt_duration(self, value):
        if not value:
            return '00:00'
        total_minutes = round(value * 60)
        hours, minutes = divmod(total_minutes, 60)
        return '%d:%02d' % (hours, minutes)

    def _request_type_label(self, request):
        Request = self.env['maintenance.request']
        return dict(Request._fields['maintenance_type'].selection).get(
            request.maintenance_type, request.maintenance_type or '')

    def _request_kind(self, request):
        if 'maintenance_kind_id' in request._fields and request.maintenance_kind_id:
            return str(request.maintenance_kind_id)
        return ''

    def _request_done_by(self, request):
        if 'user_ids' in request._fields:
            return ', '.join(request.user_ids.mapped('name'))
        return ''

    def _request_state_key(self, request):
        if getattr(request, 'is_cancel_state', False):
            return 'cancel'
        if getattr(request, 'done', False):
            return 'done'
        if getattr(request, 'is_progress_state', False):
            return 'progress'
        if getattr(request, 'is_draft_state', False):
            return 'draft'
        return 'other'

    # ------------------------------------------------------------------
    # XLSX generation
    # ------------------------------------------------------------------
    def action_generate_report(self):
        self.ensure_one()
        requests = self._get_requests()

        # Document number configured in Settings (Manufacturing > Maintenance),
        # stored on the company as pm_document_no.
        doc_no = self.env.company.pm_document_no or ''

        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})

        def F(spec):
            spec = dict(spec)
            spec.setdefault('font_name', 'Arial')
            return workbook.add_format(spec)

        # ---- Shared palette & formats --------------------------------
        C_TITLE = '#4472B4'
        C_HEAD = '#5AA478'      # requests header (green)
        C_WO = '#57A6B0'        # work-orders header (teal)
        BORDER = '#D5DCE4'

        BADGE = {'draft': '#3F86D0', 'progress': '#EE9A1E', 'done': '#43A047',
                 'cancel': '#E06A4E', 'other': '#7B8AA0'}
        _badge_cache = {}

        def badge(key, font_size):
            k = (key, font_size)
            if k not in _badge_cache:
                color = BADGE.get(key, BADGE['other'])
                _badge_cache[k] = F({
                    'bold': True, 'font_size': font_size,
                    'font_color': '#FFFFFF', 'bg_color': color,
                    'align': 'center', 'valign': 'vcenter',
                    'border': 1, 'border_color': color})
            return _badge_cache[k]

        title_fmt = F({'bold': True, 'font_size': 15, 'font_color': '#FFFFFF',
                       'bg_color': C_TITLE, 'align': 'center',
                       'valign': 'vcenter'})
        subtitle_fmt = F({'italic': True, 'font_size': 10,
                          'font_color': '#3B4A5E', 'bg_color': '#EAF1FB',
                          'align': 'center', 'valign': 'vcenter'})

        def header_fmt(bg, edge):
            return F({'bold': True, 'font_size': 10, 'font_color': '#FFFFFF',
                      'bg_color': bg, 'align': 'center', 'valign': 'vcenter',
                      'text_wrap': True, 'border': 1, 'border_color': edge})

        req_head_fmt = header_fmt(C_HEAD, '#4C9069')
        wo_head_fmt = header_fmt(C_WO, '#4A9099')
        total_fmt = F({'bold': True, 'font_size': 11, 'font_color': '#FFFFFF',
                       'bg_color': '#4472B4', 'align': 'right',
                       'valign': 'vcenter', 'border': 1,
                       'border_color': '#365F9E'})
        total_alt_fmt = F({'bold': True, 'font_size': 11,
                           'font_color': '#22303F', 'bg_color': '#E9EFF8',
                           'align': 'right', 'valign': 'vcenter',
                           'border': 1, 'border_color': '#C7D6EC'})
        doc_fmt = F({'bold': True, 'font_size': 10, 'font_color': '#FFFFFF',
                     'bg_color': C_TITLE, 'align': 'right',
                     'valign': 'vcenter', 'indent': 1})
        total_val_fmt = F({'bold': True, 'font_size': 11,
                           'font_color': '#FFFFFF', 'bg_color': '#4472B4',
                           'align': 'center', 'valign': 'vcenter',
                           'border': 1, 'border_color': '#365F9E'})

        def total_line(ws, last, val_col, label_text, value_text, r):
            """One total row: label on the left, the duration value placed
            in its own column (val_col)."""
            ws.set_row(r, 20)
            if val_col > 0:
                ws.merge_range(r, 0, r, val_col - 1, label_text, total_fmt)
            else:
                ws.write(r, 0, label_text, total_fmt)
            ws.write(r, val_col, value_text, total_val_fmt)
            if last == val_col + 1:
                ws.write_blank(r, last, None, total_fmt)
            elif last > val_col:
                ws.merge_range(r, val_col + 1, r, last, '', total_fmt)
            return r + 1

        def data_cell(alt):
            return F({'font_size': 10, 'valign': 'vcenter', 'align': 'center',
                      'text_wrap': True,
                      'bg_color': '#F4F8F5' if alt else '#FFFFFF',
                      'border': 1, 'border_color': BORDER})

        cell = {a: data_cell(a) for a in (False, True)}

        # Generic status pill drawer (works on any sheet).
        def put_status(ws, scol, spx, r_, cell_fmt, text, key, fs, row_h):
            fill = BADGE.get(key, BADGE['other'])
            pill = _make_status_pill(text, fill, fs)
            if pill:
                ws.write_blank(r_, scol, None, cell_fmt)
                bio, pw, ph = pill
                dw, dh = pw / _PILL_SCALE, ph / _PILL_SCALE
                rpx = int(row_h * 4 / 3)
                ws.insert_image(r_, scol, 'pill.png', {
                    'image_data': bio,
                    'x_scale': 1.0 / _PILL_SCALE, 'y_scale': 1.0 / _PILL_SCALE,
                    'x_offset': int(max(1, (spx - dw) / 2)),
                    'y_offset': int(max(1, (rpx - dh) / 2)),
                    'object_position': 2})
            else:
                ws.write(r_, scol, text, badge(key, fs))

        period = 'Actual Work Start from %s    to    Actual Work End %s' % (
            self.start_date.strftime('%d/%m/%Y'),
            self.end_date.strftime('%d/%m/%Y'))

        def setup_sheet(ws, columns, head_fmt_):
            ws.set_landscape()
            ws.set_paper(9)
            ws.fit_to_pages(1, 0)
            ws.set_margins(0.3, 0.3, 0.3, 0.3)
            ws.hide_gridlines(2)
            for i, (_label, w) in enumerate(columns):
                ws.set_column(i, i, w)
            last = len(columns) - 1
            side = 3 if last >= 7 else 2      # columns reserved each side
            ws.set_row(0, 26)
            # left spacer keeps the title centred
            ws.merge_range(0, 0, 0, side - 1, '', title_fmt)
            # centred report title
            ws.merge_range(0, side, 0, last - side,
                           'Preventive Maintenance Report', title_fmt)
            # document number at the right corner
            ws.merge_range(0, last - side + 1, 0, last,
                           'Document No : %s' % (doc_no or '-'), doc_fmt)
            ws.set_row(1, 18)
            ws.merge_range(1, 0, 1, last, period, subtitle_fmt)
            ws.set_row(3, 26)
            for c, (label, _w) in enumerate(columns):
                ws.write(3, c, label, head_fmt_)
            ws.freeze_panes(4, 0)
            return last

        # ==============================================================
        # SHEET 1 - Maintenance Requests
        # ==============================================================
        s1 = workbook.add_worksheet('Maintenance Requests')
        cols1 = [
            ('S.No', 6), ('Equipment', 35), ('Category', 16),
            ('Maintenance Type', 15), ('Maintenance Kind', 15), ('Team', 18),
            ('Status', 17), ('Done By', 18), ('Scheduled Date', 17),
            ('Actual Work Start', 17), ('Actual Work End', 17),
            ('Duration (Hours)', 13),
        ]
        i1 = {label: i for i, (label, _w) in enumerate(cols1)}
        last1 = setup_sheet(s1, cols1, req_head_fmt)
        s1_status_px = cols1[i1['Status']][1] * 7 + 5

        row = 4
        for index, request in enumerate(requests, start=1):
            alt = index % 2 == 0
            values = {
                'S.No': index,
                'Equipment': request.equipment_id.display_name or '',
                'Category': request.category_id.display_name or '',
                'Maintenance Type': self._request_type_label(request),
                'Maintenance Kind': self._request_kind(request),
                'Team': request.maintenance_team_id.display_name or '',
                'Status': request.stage_id.display_name or '',
                'Done By': self._request_done_by(request),
                'Scheduled Date': self._fmt_dt(request.schedule_date),
                'Actual Work Start': self._fmt_dt(request.actual_start_date),
                'Actual Work End': self._fmt_dt(request.actual_end_date),
                'Duration (Hours)': self._fmt_duration(request.duration),
            }
            s1.set_row(row, 20)
            for label, _w in cols1:
                if label == 'Status':
                    put_status(s1, i1['Status'], s1_status_px, row, cell[alt],
                               values[label],
                               self._request_state_key(request), 10, 20)
                else:
                    s1.write(row, i1[label], values[label], cell[alt])
            row += 1
        total_req_dur = sum(r.duration or 0.0 for r in requests)
        row = total_line(
            s1, last1, i1['Duration (Hours)'],
            'Total Requests : %s    Total Duration' % len(requests),
            self._fmt_duration(total_req_dur), row)
        # ==============================================================
        # SHEET 2 - Work Orders (all form-view fields except Materials)
        # ==============================================================
        s2 = workbook.add_worksheet('Work Orders')
        cols2 = [
            ('S.No', 6), ('Reference', 16), ('Maintenance', 18),
            ('Equipment', 32), ('Activity', 30), ('Done By', 18),
            ('Status', 17), ('Work Start', 17), ('Work End', 17),
            ('Duration (Hours)', 13), ('Remarks', 28),
        ]
        i2 = {label: i for i, (label, _w) in enumerate(cols2)}
        last2 = setup_sheet(s2, cols2, wo_head_fmt)
        s2_status_px = cols2[i2['Status']][1] * 7 + 5

        wo_state_sel = dict(
            self.env['work.order']._fields['state'].selection)

        # Collect every work order of the in-range requests.
        wo_pairs = []
        for request in requests:
            for wo in self._get_work_orders(request):
                wo_pairs.append((request, wo))

        row = 4
        for n, (request, wo) in enumerate(wo_pairs, start=1):
            alt = n % 2 == 0
            values = {
                'S.No': n,
                'Reference': wo.number or '',
                'Maintenance': request.sequence or request.display_name or '',
                'Equipment': (wo.equipment_id.display_name
                              or request.equipment_id.display_name or ''),
                'Activity': wo.name or '',
                'Done By': wo.user_id.name or '',
                'Status': wo_state_sel.get(wo.state, wo.state or ''),
                'Work Start': self._fmt_dt(wo.date_start),
                'Work End': self._fmt_dt(wo.date_end),
                'Duration (Hours)': self._fmt_duration(wo.duration),
                'Remarks': wo.remarks or '',
            }
            s2.set_row(row, 20)
            for label, _w in cols2:
                if label == 'Status':
                    put_status(s2, i2['Status'], s2_status_px, row, cell[alt],
                               values[label], wo.state or 'other', 10, 20)
                else:
                    s2.write(row, i2[label], values[label], cell[alt])
            row += 1

        if not wo_pairs:
            s2.set_row(row, 20)
            s2.merge_range(row, 0, row, last2, 'No work orders in this period',
                           F({'italic': True, 'font_size': 10,
                              'font_color': '#8A94A2', 'align': 'center',
                              'valign': 'vcenter', 'border': 1,
                              'border_color': BORDER}))
            row += 1
        total_wo_dur = sum((wo.duration or 0.0) for _req, wo in wo_pairs)
        row = total_line(
            s1, last1, i1['Duration (Hours)'],
            'Total Requests : %s' % len(requests),
            'Total Duration : %s' % self._fmt_duration(total_req_dur), row)

        workbook.close()
        buffer.seek(0)

        self.write({
            'file_data': base64.b64encode(buffer.read()),
            'file_name': 'Preventive Maintenance Report %s to %s.xlsx' % (
                self.start_date, self.end_date),
        })
        buffer.close()

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/file_data/%s?download=true' % (
                self._name, self.id, self.file_name),
            'target': 'self',
        }

    # ==================================================================
    # BREAKDOWN REPORT
    # ==================================================================
    def _get_breakdown_requests(self):
        """All breakdown requests created within the selected date range,
        in every state (no state filter)."""
        self.ensure_one()
        domain = [
            ('create_date', '>=', f'{self.start_date} 00:00:00'),
            ('create_date', '<=', f'{self.end_date} 23:59:59'),
        ]
        return self.env['breakdown.request'].search(
            domain, order='create_date')

    def _breakdown_sel_label(self, record, fname):
        """Human label of a selection field value on breakdown.request."""
        Request = self.env['breakdown.request']
        value = record[fname]
        if not value:
            return ''
        return dict(Request._fields[fname].selection).get(value, value)

    def _breakdown_downtime_hours(self, request):
        """Down time of a breakdown request in float hours (for totals).
        Prefers a numeric field; falls back to parsing 'H:MM' display."""
        for fname in ('duration', 'down_time', 'downtime',
                      'duration_hours', 'total_downtime'):
            if fname in request._fields:
                value = request[fname]
                if isinstance(value, (int, float)):
                    return float(value)
        disp = ''
        if 'duration_display' in request._fields:
            disp = (request.duration_display or '').strip()
        if ':' in disp:
            try:
                h, m = disp.split(':')[:2]
                return int(h) + int(m) / 60.0
            except Exception:
                return 0.0
        return 0.0

    def _breakdown_columns(self):
        """Column spec: (Header, width, getter). Missing fields skipped."""
        Request = self.env['breakdown.request']

        def has(fname):
            return fname in Request._fields

        columns = [
            ('S.No', 6, None),  # filled with the row number
            ('Ticket No', 16, lambda r: r.name or ''),
            ('Machine', 30, lambda r: r.machine_id.display_name or ''),
            ('Shift', 16, lambda r: r.shift_id.display_name or ''),
            ('Problem Category', 16,
             lambda r: self._breakdown_sel_label(r, 'problem_category')),
            ('Priority', 12,
             lambda r: self._breakdown_sel_label(r, 'priority')),
            ('Problem Description', 40,
             lambda r: r.problem_description or ''),
            ('Requested By', 20,
             lambda r: r.requested_user_id.display_name or ''),
            ('Requested Time', 18, lambda r: self._fmt_dt(r.requested_time)),
            ('Engineer Name', 20, lambda r: r.engineer_name or ''),
            ('Operated By', 20, lambda r: r.operated_by or ''),
            ('Attended By', 20, lambda r: r.attended_by.display_name or ''),
            ('Root Cause', 30, lambda r: r.root_cause or ''),
            ('Corrective Action', 30, lambda r: r.corrective or ''),
            ('Permanent Solution', 14,
             lambda r: self._breakdown_sel_label(r, 'solution_permanent')),
            ('Start Date', 18, lambda r: self._fmt_dt(r.start_date)),
            ('End Date', 18, lambda r: self._fmt_dt(r.end_date)),
            ('Down Time', 14, lambda r: r.duration_display or ''),
        ]
        if has('user_ids'):
            columns.append(
                ('Done By', 24,
                 lambda r: ', '.join(r.user_ids.mapped('name'))))
        columns += [
            ('Remarks', 30, lambda r: r.remarks or ''),
            ('Status', 14,
             lambda r: self._breakdown_sel_label(r, 'state')),
        ]
        return columns

    def action_generate_breakdown_report(self):
        self.ensure_one()
        requests = self._get_breakdown_requests()

        # Breakdown document number configured in Settings.
        br_doc_no = self.env.company.br_document_no or ''

        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        sheet = workbook.add_worksheet('Breakdown')

        # ---- Formats --------------------------------------------------
        title_fmt = workbook.add_format({
            'bold': True, 'font_size': 16, 'font_color': '#FFFFFF',
            'bg_color': '#3B7DDD', 'align': 'center', 'valign': 'vcenter',
            'border': 1, 'border_color': '#2A5DA8',
        })
        doc_fmt = workbook.add_format({
            'bold': True, 'font_size': 11, 'font_color': '#FFFFFF',
            'bg_color': '#3B7DDD', 'align': 'right', 'valign': 'vcenter',
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
            'bg_color': '#4472B4', 'align': 'right', 'valign': 'vcenter',
            'border': 1, 'border_color': '#365F9E',
        })
        total_alt_fmt = workbook.add_format({
            'bold': True, 'font_size': 10, 'font_color': '#37474F',
            'bg_color': '#E8F1FC', 'align': 'right', 'valign': 'vcenter',
            'border': 1, 'border_color': '#B9D3F2',
        })
        total_val_fmt = workbook.add_format({
            'bold': True, 'font_size': 10, 'font_color': '#FFFFFF',
            'bg_color': '#4472B4', 'align': 'center', 'valign': 'vcenter',
            'border': 1, 'border_color': '#365F9E',
        })

        def total_line(ws, last, val_col, label_text, value_text, r):
            ws.set_row(r, 20)
            if val_col > 0:
                ws.merge_range(r, 0, r, val_col - 1, label_text, total_fmt)
            else:
                ws.write(r, 0, label_text, total_fmt)
            ws.write(r, val_col, value_text, total_val_fmt)
            if last == val_col + 1:
                ws.write_blank(r, last, None, total_fmt)
            elif last > val_col:
                ws.merge_range(r, val_col + 1, r, last, '', total_fmt)
            return r + 1

        columns = self._breakdown_columns()
        last_col = len(columns) - 1

        center_headers = {
            'S.No', 'Priority', 'Problem Category', 'Permanent Solution',
            'Down Time', 'Status',
        }
        center_cols = {
            i for i, c in enumerate(columns) if c[0] in center_headers
        }

        # ---- Title (centred) + Document No at right corner ------------
        sheet.set_row(0, 28)
        side = 3 if last_col >= 7 else 2
        sheet.merge_range(0, 0, 0, side - 1, '', title_fmt)
        sheet.merge_range(0, side, 0, last_col - side,
                          'Breakdown Request Report', title_fmt)
        sheet.merge_range(0, last_col - side + 1, 0, last_col,
                          'Document No : %s' % (br_doc_no or '-'), doc_fmt)
        sheet.set_row(1, 18)
        sheet.merge_range(
            1, 0, 1, last_col,
            'Created from %s    to    %s' % (
                self.start_date.strftime('%d/%m/%Y'),
                self.end_date.strftime('%d/%m/%Y')),
            subtitle_fmt)

        # ---- Header row -----------------------------------------------
        header_row = 3
        sheet.set_row(header_row, 24)
        for col, (label, width, _getter) in enumerate(columns):
            sheet.set_column(col, col, width)
            sheet.write(header_row, col, label, header_fmt)
        sheet.freeze_panes(header_row + 1, 0)

        # ---- Data rows ------------------------------------------------
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
                if col in center_cols:
                    sheet.write(row, col, value, num_fmt)
                else:
                    sheet.write(row, col, value, text_fmt)
            row += 1

        # ---- Total: BR count + down time under the Down Time column ----
        dt_col = next((i for i, c in enumerate(columns)
                       if c[0] == 'Down Time'), last_col)
        total_dt = sum(self._breakdown_downtime_hours(r) for r in requests)
        row = total_line(
            sheet, last_col, dt_col,
            'Total Breakdown Requests : %s' % len(requests),
            'Total Down time : %s' % self._fmt_duration(total_dt), row)

        workbook.close()
        buffer.seek(0)

        self.write({
            'file_data': base64.b64encode(buffer.read()),
            'file_name': 'Breakdown Request Report %s to %s.xlsx' % (
                self.start_date, self.end_date),
        })
        buffer.close()

        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%s/%s/file_data/%s?download=true' % (
                self._name, self.id, self.file_name),
            'target': 'self',
        }