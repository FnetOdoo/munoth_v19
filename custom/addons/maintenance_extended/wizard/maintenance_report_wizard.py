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
        """Datetime -> user-tz string, '' when not set."""
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
        if 'maintenance_kind' in request._fields and request.maintenance_kind:
            return str(request.maintenance_kind)
        return ''

    def _request_done_by(self, request):
        if 'user_ids' in request._fields:
            return ', '.join(request.user_ids.mapped('name'))
        return ''

    def _request_state_key(self, request):
        """Colour key for the request Status pill: done -> green,
        in-progress -> amber, draft/new -> blue, else neutral."""
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

        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        sheet = workbook.add_worksheet('PM Report')
        sheet.set_landscape()
        sheet.set_paper(9)
        sheet.fit_to_pages(1, 0)
        sheet.set_margins(0.3, 0.3, 0.3, 0.3)
        sheet.hide_gridlines(2)

        def F(spec):
            spec = dict(spec)
            spec.setdefault('font_name', 'Arial')
            return workbook.add_format(spec)

        # State badges (fill colour per state, white text). Keys match both
        # the request state helper and work.order.state selection.
        BADGE = {'draft': '#3F86D0', 'progress': '#EE9A1E', 'done': '#43A047',
                 'cancel': '#E06A4E', 'other': '#7B8AA0'}
        _badge_cache = {}

        def badge(key, font_size):
            k = (key, font_size)
            if k not in _badge_cache:
                color = BADGE.get(key, BADGE['other'])
                _badge_cache[k] = F({
                    'bold': True, 'font_size': font_size, 'font_color': '#FFFFFF',
                    'bg_color': color, 'align': 'center', 'valign': 'vcenter',
                    'border': 1, 'border_color': color})
            return _badge_cache[k]

        # ---- Soft professional palette (not dark) --------------------
        C_TITLE = '#4472B4'      # calm blue (title + total)
        C_HEAD = '#5AA478'       # soft green (request header)
        C_WO = '#57A6B0'         # soft teal (WO sub-header)
        BORDER = '#D5DCE4'

        title_fmt = F({
            'bold': True, 'font_size': 15, 'font_color': '#FFFFFF',
            'bg_color': C_TITLE, 'align': 'center', 'valign': 'vcenter'})
        subtitle_fmt = F({
            'italic': True, 'font_size': 10, 'font_color': '#3B4A5E',
            'bg_color': '#EAF1FB', 'align': 'center', 'valign': 'vcenter'})
        head_fmt = F({
            'bold': True, 'font_size': 10, 'font_color': '#FFFFFF',
            'bg_color': C_HEAD, 'align': 'center', 'valign': 'vcenter',
            'text_wrap': True, 'border': 1, 'border_color': '#4C9069'})
        wo_header_fmt = F({
            'bold': True, 'font_size': 9, 'font_color': '#FFFFFF',
            'bg_color': C_WO, 'align': 'center', 'valign': 'vcenter',
            'text_wrap': True, 'border': 1, 'border_color': '#4A9099'})
        total_fmt = F({
            'bold': True, 'font_size': 11, 'font_color': '#FFFFFF',
            'bg_color': C_TITLE, 'align': 'right', 'valign': 'vcenter',
            'border': 1, 'border_color': C_TITLE})
        subno_fmt = F({
            'bold': True, 'font_size': 9, 'font_color': '#2C7A84',
            'align': 'center', 'valign': 'vcenter', 'bg_color': '#DCEEF0',
            'border': 1, 'border_color': BORDER})
        none_fmt = F({
            'italic': True, 'font_size': 9, 'font_color': '#8A94A2',
            'valign': 'vcenter', 'bg_color': '#F7FAFB', 'indent': 1,
            'border': 1, 'border_color': BORDER})

        def req_cell(alt):
            return F({
                'font_size': 10, 'valign': 'vcenter', 'align': 'center',
                'text_wrap': True,
                'bg_color': '#F4F8F5' if alt else '#FFFFFF',
                'border': 1, 'border_color': BORDER})

        def wo_cell(alt):
            return F({
                'font_size': 9, 'valign': 'vcenter', 'align': 'center',
                'text_wrap': True,
                'bg_color': '#F1F8F9' if alt else '#FFFFFF',
                'border': 1, 'border_color': BORDER})

        rq = {a: req_cell(a) for a in (False, True)}
        wc = {a: wo_cell(a) for a in (False, True)}

        # ---- Columns (same structure as the original design) ----------
        columns = [
            ('S.No', 6), ('Sequence', 16), ('Equipment', 35), ('Category', 16),
            ('Maintenance Type', 15), ('Maintenance Kind', 15), ('Team', 18),
            ('Status', 17), ('Done By', 18), ('Scheduled Date', 17),
            ('Actual Work Start', 17), ('Actual Work End', 17),
            ('Duration (Hours)', 13),
        ]
        idx = {label: i for i, (label, _w) in enumerate(columns)}
        last_col = len(columns) - 1
        for i, (_label, w) in enumerate(columns):
            sheet.set_column(i, i, w)
        status_px = columns[idx['Status']][1] * 7 + 5

        def put_status(cell_row, cell_fmt, text, key, font_size, row_h):
            """Draw a rounded pill for the status, centered in its cell;
            fall back to a filled cell badge if Pillow/font unavailable."""
            fill = BADGE.get(key, BADGE['other'])
            pill = _make_status_pill(text, fill, font_size)
            if pill:
                sheet.write_blank(cell_row, idx['Status'], None, cell_fmt)
                bio, pw, ph = pill
                dw, dh = pw / _PILL_SCALE, ph / _PILL_SCALE
                rpx = int(row_h * 4 / 3)
                sheet.insert_image(cell_row, idx['Status'], 'pill.png', {
                    'image_data': bio,
                    'x_scale': 1.0 / _PILL_SCALE, 'y_scale': 1.0 / _PILL_SCALE,
                    'x_offset': int(max(1, (status_px - dw) / 2)),
                    'y_offset': int(max(1, (rpx - dh) / 2)),
                    'object_position': 2})
            else:
                sheet.write(cell_row, idx['Status'], text,
                            badge(key, font_size))

        act = (idx['Equipment'], idx['Category'])            # Activity merge
        rem = (idx['Maintenance Type'], idx['Team'])         # Remarks merge
        merged = {idx['Equipment'], idx['Category'],
                  idx['Maintenance Type'], idx['Maintenance Kind'],
                  idx['Team']}

        wo_state_sel = dict(
            self.env['work.order']._fields['state'].selection)

        # ---- Title & subtitle -----------------------------------------
        sheet.set_row(0, 26)
        sheet.merge_range(0, 0, 0, last_col,
                          'Preventive Maintenance Report', title_fmt)
        sheet.set_row(1, 18)
        sheet.merge_range(
            1, 0, 1, last_col,
            'Actual Work Start from %s    to    Actual Work End %s' % (
                self.start_date.strftime('%d/%m/%Y'),
                self.end_date.strftime('%d/%m/%Y')),
            subtitle_fmt)

        # ---- Request column header ------------------------------------
        header_row = 3
        sheet.set_row(header_row, 26)
        for col, (label, _w) in enumerate(columns):
            sheet.write(header_row, col, label, head_fmt)
        sheet.freeze_panes(header_row + 1, 0)

        # ---- Request rows + aligned work orders -----------------------
        row = header_row + 1
        for index, request in enumerate(requests, start=1):
            alt = index % 2 == 0
            values = {
                'S.No': index,
                'Sequence': request.sequence or '',
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
            sheet.set_row(row, 20)
            for label, _w in columns:
                if label == 'Status':
                    sheet.write_blank(row, idx[label], None, rq[alt])
                    put_status(row, rq[alt], values[label],
                               self._request_state_key(request), 10, 20)
                else:
                    sheet.write(row, idx[label], values[label], rq[alt])
            row += 1

            work_orders = self._get_work_orders(request)

            if work_orders:
                # aligned WO sub-header
                sheet.set_row(row, 20)
                heads = {
                    idx['S.No']: 'WO', idx['Sequence']: 'Reference',
                    idx['Status']: 'WO Status', idx['Done By']: 'Done By',
                    idx['Actual Work Start']: 'Work Start',
                    idx['Actual Work End']: 'Work End',
                    idx['Duration (Hours)']: 'Duration'}
                for col in range(last_col + 1):
                    if col in merged:
                        continue
                    sheet.write(row, col, heads.get(col, ''), wo_header_fmt)
                sheet.merge_range(row, act[0], row, act[1], 'Activity',
                                  wo_header_fmt)
                sheet.merge_range(row, rem[0], row, rem[1], 'Remarks',
                                  wo_header_fmt)
                row += 1

                for wo_idx, wo in enumerate(work_orders, start=1):
                    a2 = wo_idx % 2 == 0
                    sheet.set_row(row, 18)
                    for col in range(last_col + 1):
                        if col in merged:
                            continue
                        sheet.write(row, col, '', wc[a2])
                    sheet.write(row, idx['S.No'], '%d.%d' % (index, wo_idx),
                                subno_fmt)
                    sheet.write(row, idx['Sequence'], wo.number or '', wc[a2])
                    sheet.merge_range(row, act[0], row, act[1],
                                      wo.name or '', wc[a2])
                    sheet.merge_range(row, rem[0], row, rem[1],
                                      wo.remarks or '', wc[a2])
                    put_status(row, wc[a2],
                               wo_state_sel.get(wo.state, wo.state or ''),
                               wo.state or 'other', 9, 18)
                    sheet.write(row, idx['Done By'], wo.user_id.name or '',
                                wc[a2])
                    sheet.write(row, idx['Actual Work Start'],
                                self._fmt_dt(wo.date_start), wc[a2])
                    sheet.write(row, idx['Actual Work End'],
                                self._fmt_dt(wo.date_end), wc[a2])
                    sheet.write(row, idx['Duration (Hours)'],
                                self._fmt_duration(wo.duration), wc[a2])
                    row += 1
            else:
                sheet.set_row(row, 18)
                for col in range(last_col + 1):
                    sheet.write_blank(row, col, None, none_fmt)
                sheet.write(row, idx['S.No'], '%d.0' % index, subno_fmt)
                sheet.write(row, idx['Sequence'], 'No work orders', none_fmt)
                row += 1

        # ---- Total row -------------------------------------------------
        sheet.set_row(row, 20)
        sheet.merge_range(row, 0, row, last_col,
                          'Total Requests : %s' % len(requests), total_fmt)

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
    # BREAKDOWN REPORT  (add these methods inside maintenance.report.wizard)
    # ==================================================================
    def _get_breakdown_requests(self):
        """All breakdown requests created on/after Start Date and
        on/before End Date, in every state (no state filter)."""
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

    def _breakdown_columns(self):
        """Column spec: (Header, width, getter). Every field on the
        breakdown form. Missing fields are skipped automatically."""
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
            ('Requested Time', 18,lambda r: self._fmt_dt(r.requested_time)),
            ('Engineer Name', 20, lambda r: r.engineer_name or ''),
            ('Operated By', 20, lambda r: r.operated_by or ''),
            ('Attended By', 20,
             lambda r: r.attended_by.display_name or ''),
            ('Root Cause', 30, lambda r: r.root_cause or ''),
            ('Corrective Action', 30, lambda r: r.corrective or ''),
            ('Permanent Solution', 14,
             lambda r: self._breakdown_sel_label(r, 'solution_permanent')),
            ('Start Date', 18, lambda r: self._fmt_dt(r.start_date)),
            ('End Date', 18, lambda r: self._fmt_dt(r.end_date)),
            ('Down Time', 14, lambda r: r.duration_display or ''),
        ]
        # Optional Many2many "Done By" — only if the field is present.
        if has('user_ids'):
            columns.append(
                ('Done By', 24,
                 lambda r: ', '.join(r.user_ids.mapped('name'))))
        columns += [
            ('Remarks', 30, lambda r: r.remarks or ''),
            ('Created On', 18, lambda r: self._fmt_dt(r.create_date)),
            ('Status', 14,
             lambda r: self._breakdown_sel_label(r, 'state')),
        ]
        return columns

    def action_generate_breakdown_report(self):
        self.ensure_one()
        requests = self._get_breakdown_requests()

        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        sheet = workbook.add_worksheet('Breakdown')

        # ---- Formats: same blue/green theme as the PM report ----------
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

        columns = self._breakdown_columns()
        last_col = len(columns) - 1

        center_headers = {
            'S.No', 'Priority', 'Problem Category', 'Permanent Solution',
            'Down Time', 'Status',
        }
        center_cols = {
            i for i, c in enumerate(columns) if c[0] in center_headers
        }

        # ---- Title & subtitle -----------------------------------------
        sheet.set_row(0, 28)
        sheet.merge_range(0, 0, 0, last_col,
                          'Breakdown Request Report', title_fmt)
        sheet.set_row(1, 18)
        sheet.merge_range(
            1, 0, 1, last_col,
            'Created from %s    to    %s' % (
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
                if col in center_cols:
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