# -*- coding: utf-8 -*-
from odoo import api, fields, models

# ----------------------------------------------------------------------
# Work Order configuration
# ----------------------------------------------------------------------
WORKORDER_MODEL = 'work.order'
WORKORDER_M2O = 'maintenance_id'
WO_STATE_FIELD = 'state'

WO_DONE_STATES = ('done', 'completed', 'pm_completed')
WO_CANCEL_STATES = ('cancel', 'cancelled')

# ----------------------------------------------------------------------
# Date filter configuration
# ----------------------------------------------------------------------
OPEN_DATE_FIELD = 'create_date'
DONE_DATE_START_FIELD = 'actual_start_date'
DONE_DATE_END_FIELD = 'actual_end_date'


class MaintenanceRequest(models.Model):
    _inherit = 'maintenance.request'

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _get_dashboard_domains(self):
        """Base stage domains for the dashboard."""
        return {
            'open': [('stage_id.is_draft_state', '=', True)],
            'progress': [('stage_id.is_progress_state', '=', True)],   # NEW
            'done': [('stage_id.is_done_state', '=', True)],
        }

    @api.model
    def _dashboard_date_domain(self, start_field, end_field,
                               date_start, date_end):
        """Build a date-range domain (unchanged)."""
        if start_field not in self._fields:
            start_field = 'create_date'
        if end_field not in self._fields:
            end_field = 'create_date'

        domain = []
        if date_start:
            if self._fields[start_field].type == 'datetime':
                date_start = f"{date_start} 00:00:00"
            domain.append((start_field, '>=', date_start))
        if date_end:
            if self._fields[end_field].type == 'datetime':
                date_end = f"{date_end} 23:59:59"
            domain.append((end_field, '<=', date_end))
        return domain

    @api.model
    def _dashboard_workorder_model(self):
        WorkOrder = self.env.get(WORKORDER_MODEL)
        if WorkOrder is not None and WORKORDER_M2O in WorkOrder._fields:
            return WorkOrder
        return None

    @api.model
    def _dashboard_wo_state_domains(self):
        WorkOrder = self._dashboard_workorder_model()
        if WorkOrder is None or WO_STATE_FIELD not in WorkOrder._fields:
            return [], []
        open_domain = [
            (WO_STATE_FIELD, 'not in', list(WO_DONE_STATES + WO_CANCEL_STATES)),
        ]
        done_domain = [
            (WO_STATE_FIELD, 'in', list(WO_DONE_STATES)),
        ]
        return open_domain, done_domain

    @api.model
    def _count_workorders(self, request_ids, state_domain):
        WorkOrder = self._dashboard_workorder_model()
        if WorkOrder is None or not request_ids:
            return 0, []

        domain = [(WORKORDER_M2O, 'in', request_ids)] + state_domain
        grouped = WorkOrder._read_group(
            domain=domain,
            groupby=[],
            aggregates=['id:array_agg'],
        )
        ids = grouped[0][0] if grouped else []
        return len(ids), ids

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @api.model
    def get_dashboard_data(self, filters=None):
        filters = filters or {}
        today = fields.Date.context_today(self)
        month_start = today.replace(day=1)

        open_start = filters.get('open_start') or str(month_start)
        open_end = filters.get('open_end') or str(today)
        done_start = filters.get('done_start') or str(month_start)
        done_end = filters.get('done_end') or str(today)

        base = self._get_dashboard_domains()
        open_domain = base['open'] + self._dashboard_date_domain(
            OPEN_DATE_FIELD, OPEN_DATE_FIELD, open_start, open_end)
        done_domain = base['done'] + self._dashboard_date_domain(
            DONE_DATE_START_FIELD, DONE_DATE_END_FIELD,
            done_start, done_end)

        # ---- NEW: In Progress (stage_id.is_progress_state) -------------
        # Uses the same date range as the open filter (on create_date).
        progress_domain = base['progress'] + self._dashboard_date_domain(
            OPEN_DATE_FIELD, OPEN_DATE_FIELD, open_start, open_end)

        open_request_ids = self.search(open_domain).ids
        progress_request_ids = self.search(progress_domain).ids     # NEW
        done_request_ids = self.search(done_domain).ids

        open_count = len(open_request_ids)
        progress_count = len(progress_request_ids)                  # NEW
        done_count = len(done_request_ids)

        # ---- Related Work Orders (via maintenance_id) ------------------
        wo_open_domain, wo_done_domain = self._dashboard_wo_state_domains()
        wo_open_count, open_wo_ids = self._count_workorders(
            open_request_ids, wo_open_domain)
        # NEW: work orders of in-progress requests (active = not done/cancel)
        wo_progress_count, progress_wo_ids = self._count_workorders(
            progress_request_ids, wo_open_domain)
        wo_done_count, done_wo_ids = self._count_workorders(
            done_request_ids, wo_done_domain)

        return {
            'workorder_model': WORKORDER_MODEL,
            'has_workorders': self._dashboard_workorder_model() is not None,
            'max_value': max(open_count, progress_count, done_count,
                             wo_open_count, wo_progress_count,
                             wo_done_count, 1),
            'filters': {
                'open_start': open_start,
                'open_end': open_end,
                'done_start': done_start,
                'done_end': done_end,
            },
            'bars': [
                {
                    'key': 'open',
                    'label': 'Pending Maintenance Requests',
                    'request_count': open_count,
                    'request_domain': open_domain,
                    'workorder_label': 'Pending Work Orders',
                    'workorder_count': wo_open_count,
                    'workorder_ids': open_wo_ids,
                },
                {
                    'key': 'progress',                               # NEW
                    'label': 'In Progress',
                    'request_count': progress_count,
                    'request_domain': progress_domain,
                    'workorder_label': 'In Progress Work Orders',
                    'workorder_count': wo_progress_count,
                    'workorder_ids': progress_wo_ids,
                },
                {
                    'key': 'done',
                    'label': 'PM Completed',
                    'request_count': done_count,
                    'request_domain': done_domain,
                    'workorder_label': 'Done Work Orders',
                    'workorder_count': wo_done_count,
                    'workorder_ids': done_wo_ids,
                },
            ],
        }