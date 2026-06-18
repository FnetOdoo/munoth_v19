# -*- coding: utf-8 -*-
import time
from calendar import monthrange
from datetime import date

from odoo import fields, models, tools


class HrPayrollReportView(models.Model):
    """SQL view model for monthly payslip analysis report - Odoo 19."""
    _name = 'hr.payroll.report'
    _auto = False
    _description = 'HR Payroll Monthly Report'

    now = date.today()
    month_day = monthrange(now.year, now.month)

    start_date = fields.Date(
        string="Start Date",
        default=time.strftime('%Y-%m-01'),
        invisible=True,
    )
    end_date = fields.Date(
        string="End Date",
        default=time.strftime('%Y-%m-' + str(month_day[1])),
        invisible=True,
    )
    name = fields.Many2one('hr.employee', string='Employee')
    date_from = fields.Date(string='From')
    date_to = fields.Date(string='To')
    state = fields.Selection(
        [('draft', 'Draft'), ('verified', 'Verified'),
         ('done', 'Done'), ('cancel', 'Rejected')],
        string='Status',
    )
    job_id = fields.Many2one('hr.job', string='Job Title')
    company_id = fields.Many2one('res.company', string='Company')
    department_id = fields.Many2one('hr.department', string='Department')
    rule_name = fields.Many2one('hr.salary.rule.category', string="Rule Category")
    rule_amount = fields.Float(string="Amount")
    struct_id = fields.Many2one('hr.payroll.structure', string="Salary Structure")
    rule_id = fields.Many2one('hr.salary.rule', string="Salary Rule")

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        # Odoo 19: department_id and job_id moved off hr_employee to
        # hr_employee_public (confirmed from information_schema query).
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW %s AS (
                SELECT
                    min(psl.id),
                    ps.id,
                    ps.number,
                    emp.id               AS name,
                    pub.department_id    AS department_id,
                    pub.job_id           AS job_id,
                    cmp.id               AS company_id,
                    ps.date_from,
                    ps.date_to,
                    ps.state,
                    rl.id                AS rule_name,
                    psl.total            AS rule_amount,
                    ps.struct_id,
                    rlu.id               AS rule_id
                FROM
                    hr_payslip_line psl
                    JOIN hr_payslip              ps  ON ps.id  = psl.slip_id
                    JOIN hr_salary_rule          rlu ON rlu.id = psl.salary_rule_id
                    JOIN hr_employee             emp ON emp.id = ps.employee_id
                    JOIN hr_salary_rule_category rl  ON rl.id  = psl.category_id
                    LEFT JOIN hr_employee_public pub ON pub.id = emp.id
                    LEFT JOIN hr_department      dp  ON dp.id  = pub.department_id
                    LEFT JOIN hr_job             jb  ON jb.id  = pub.job_id
                    JOIN res_company             cmp ON cmp.id = ps.company_id
                GROUP BY
                    ps.number, ps.id, emp.id,
                    pub.department_id, pub.job_id,
                    cmp.id,
                    ps.date_from, ps.date_to, ps.state,
                    psl.total, psl.name, psl.category_id, rl.id, rlu.id
            )
        """ % self._table)