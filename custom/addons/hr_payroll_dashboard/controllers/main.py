from odoo import http
from odoo.http import request
from datetime import date, timedelta
import json


class PayrollDashboardController(http.Controller):

    @http.route('/hr_payroll_dashboard/data', type='json', auth='user', methods=['POST'])
    def get_dashboard_data(self):
        """Return all dashboard data: KPI counts + graph data"""
        today = date.today()
        Employee = request.env['hr.employee']
        Attendance = request.env['hr.attendance']
        Leave = request.env['hr.leave']
        Payslip = request.env['hr.payslip']

        # ── KPI Counts ──────────────────────────────────────────────────
        # Today's attendance
        today_start = today.strftime('%Y-%m-%d 00:00:00')
        today_end = today.strftime('%Y-%m-%d 23:59:59')
        attendance_count = Attendance.search_count([
            ('check_in', '>=', today_start),
            ('check_in', '<=', today_end),
        ])

        # Leave requests (all open/validate1)
        leave_count = Leave.search_count([
            ('state', 'in', ['confirm', 'validate1', 'validate']),
        ])

        # Payslips
        payslip_count = Payslip.search_count([])

        # Contracts (using hr.employee fields — Odoo 19, no hr.contract)
        running_domain = [
            ('contract_date_start', '<=', today),
            '|',
            ('contract_date_end', '=', False),
            ('contract_date_end', '>=', today),
        ]
        running_count = Employee.search_count(running_domain)

        expired_domain = [
            ('contract_date_end', '<', today),
            ('contract_date_end', '!=', False),
        ]
        expired_count = Employee.search_count(expired_domain)

        # Salary Rules
        salary_rule_count = request.env['hr.salary.rule'].search_count([])

        # Salary Structures
        salary_structure_count = request.env['hr.payroll.structure'].search_count([])

        # Total employees
        employee_count = Employee.search_count([])

        # ── Graph Data ───────────────────────────────────────────────────

        # 1. Employees by Department (bar chart)
        departments = request.env['hr.department'].search([])
        dept_data = []
        for dept in departments:
            count = Employee.search_count([('department_id', '=', dept.id)])
            if count > 0:
                dept_data.append({'label': dept.name, 'value': count})

        # 2. Attendance per Day (last 7 days, line chart)
        attendance_per_day = []
        for i in range(6, -1, -1):
            day = today - timedelta(days=i)
            day_start = day.strftime('%Y-%m-%d 00:00:00')
            day_end = day.strftime('%Y-%m-%d 23:59:59')
            count = Attendance.search_count([
                ('check_in', '>=', day_start),
                ('check_in', '<=', day_end),
            ])
            attendance_per_day.append({
                'label': day.strftime('%a %d'),
                'value': count,
            })

        # 3. Leave Distribution by type (pie chart)
        leave_types = request.env['hr.leave.type'].search([])
        leave_dist = []
        for lt in leave_types:
            count = Leave.search_count([
                ('holiday_status_id', '=', lt.id),
                ('state', 'in', ['confirm', 'validate1', 'validate']),
            ])
            if count > 0:
                leave_dist.append({'label': lt.name, 'value': count})

        # 4. Monthly Expense (payslips per month, last 6 months)
        monthly_expense = []
        for i in range(5, -1, -1):
            month_start = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
            if i == 0:
                month_end = today
            else:
                next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
                month_end = next_month - timedelta(days=1)

            slips = Payslip.search([
                ('date_from', '>=', month_start.strftime('%Y-%m-%d')),
                ('date_from', '<=', month_end.strftime('%Y-%m-%d')),
                ('state', 'in', ['done', 'paid']),
            ])
            total = 0
            for slip in slips:
                net_line = slip.line_ids.filtered(lambda l: l.code == 'NET')
                total += sum(net_line.mapped('total'))
            monthly_expense.append({
                'label': month_start.strftime('%b %Y'),
                'value': round(float(total), 2),
            })

        # 5. Payslip status (pie)
        payslip_done = Payslip.search_count([('state', 'in', ['done', 'paid'])])
        payslip_draft = Payslip.search_count([('state', '=', 'draft')])
        payslip_data = [
            {'label': 'Done', 'value': payslip_done},
            {'label': 'Draft', 'value': payslip_draft},
        ]

        # 6. Contract status (pie) — using employee contract fields
        new_count = Employee.search_count([
            ('contract_date_start', '>', today),
        ])
        cancelled_count = 0  # No cancelled state in Odoo 19 employee fields

        contract_data = [
            {'label': 'Running', 'value': running_count},
            {'label': 'New', 'value': new_count},
            {'label': 'Expired', 'value': expired_count},
        ]

        # 7. Recent Leave Requests (limit 6)
        recent_leaves = Leave.search([
            ('state', 'in', ['confirm', 'validate1', 'validate']),
        ], limit=6, order='date_from desc')

        leave_list = []
        for leave in recent_leaves:
            leave_list.append({
                'id': leave.id,
                'employee': leave.employee_id.name or '',
                'type': leave.holiday_status_id.name or '',
                'date_from': leave.date_from.strftime('%Y-%m-%d') if leave.date_from else '',
                'date_to': leave.date_to.strftime('%Y-%m-%d') if leave.date_to else '',
                'state': leave.state,
            })

        # Domain strings (for JS doAction)
        running_domain_str = [
            ('contract_date_start', '<=', today.strftime('%Y-%m-%d')),
            '|',
            ('contract_date_end', '=', False),
            ('contract_date_end', '>=', today.strftime('%Y-%m-%d')),
        ]
        expired_domain_str = [
            ('contract_date_end', '<', today.strftime('%Y-%m-%d')),
            ('contract_date_end', '!=', False),
        ]

        return {
            'kpis': {
                'attendance': attendance_count,
                'leave_requests': leave_count,
                'payslips': payslip_count,
                'running_contracts': running_count,
                'expired_contracts': expired_count,
                'salary_rules': salary_rule_count,
                'salary_structures': salary_structure_count,
                'employees': employee_count,
            },
            'graphs': {
                'dept_data': dept_data,
                'attendance_per_day': attendance_per_day,
                'leave_dist': leave_dist,
                'monthly_expense': monthly_expense,
                'payslip_data': payslip_data,
                'contract_data': contract_data,
            },
            'recent_leaves': leave_list,
            'domains': {
                'running_contracts': running_domain_str,
                'expired_contracts': expired_domain_str,
            },
            'today': today.strftime('%Y-%m-%d'),
        }
