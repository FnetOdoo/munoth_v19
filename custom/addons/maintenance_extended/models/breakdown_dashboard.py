# -*- coding: utf-8 -*-
from odoo import api, fields, models

# States we care about on breakdown.request
REQUEST_STATE = 'request'   # Requested
DONE_STATE = 'done'         # Closed

# Date field used for the range filter
DATE_FIELD = 'requested_time'


class BreakdownRequest(models.Model):
    _inherit = 'breakdown.request'

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @api.model
    def _breakdown_date_domain(self, date_start, date_end):
        """Build a date-range domain on requested_time (datetime)."""
        field = DATE_FIELD
        if field not in self._fields:
            field = 'create_date'

        domain = []
        is_dt = self._fields[field].type == 'datetime'
        if date_start:
            start = f"{date_start} 00:00:00" if is_dt else date_start
            domain.append((field, '>=', start))
        if date_end:
            end = f"{date_end} 23:59:59" if is_dt else date_end
            domain.append((field, '<=', end))
        return domain

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @api.model
    def get_breakdown_dashboard_data(self, filters=None):
        filters = filters or {}
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)

        start = filters.get('start') or str(month_start)
        end = filters.get('end') or str(today)

        date_domain = self._breakdown_date_domain(start, end)

        request_domain = [('state', '=', REQUEST_STATE)] + date_domain
        done_domain = [('state', '=', DONE_STATE)] + date_domain

        request_ids = self.search(request_domain).ids
        done_ids = self.search(done_domain).ids

        request_count = len(request_ids)
        done_count = len(done_ids)

        return {
            'max_value': max(request_count, done_count, 1),
            'filters': {
                'start': start,
                'end': end,
            },
            'bars': [
                {
                    'key': 'request',
                    'label': 'Requested',
                    'count': request_count,
                    'domain': request_domain,
                },
                {
                    'key': 'done',
                    'label': 'Closed',
                    'count': done_count,
                    'domain': done_domain,
                },
            ],
        }