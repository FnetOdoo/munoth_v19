# -*- coding: utf-8 -*-
"""
Migration Notes — models.py (v15 → v19)
=========================================

v15 design
───────────
  HrContract(_inherit='hr.contract')
    • history_line  One2many → salary.history.line.contract_id
    • effective_date

  SalaryHistoryLine(_name='salary.history.line')
    • contract_id   Many2one('hr.contract')   ← BROKEN in v19

v19 design
───────────
  hr.contract does NOT exist in v19 community registry.

  Strategy: link salary history directly to hr.employee.
  ─────────────────────────────────────────────────────
  • SalaryHistoryLine.contract_id  renamed to  employee_id  Many2one('hr.employee')
  • HrEmployee(_inherit='hr.employee') gets:
      - history_line   One2many('salary.history.line', 'employee_id')
      - effective_date Date
  • All salary allowance/deduction fields assumed to already exist on
    hr.employee via hr_payroll_extended (the companion module).
    If hr_payroll_extended is NOT installed, uncomment the fallback
    fields block marked below.
"""

from odoo import models, fields


# ── Salary History Line ──────────────────────────────────────────────────────

class SalaryHistoryLine(models.Model):
    _name = 'salary.history.line'
    _description = 'Salary History Line'
    _order = 'effective_date desc, id desc'

    # v15: contract_id = Many2one('hr.contract')
    # v19: hr.contract gone → link to hr.employee instead
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        ondelete='cascade',
    )

    # Snapshot of salary at revision time
    old_basic       = fields.Char('Basic Percentage')
    old_wage        = fields.Float('Wages', digits=(16, 5))
    old_structure_id = fields.Many2one('hr.payroll.structure', 'Salary Structure')

    # Allowances snapshot
    hra                 = fields.Float('HRA')
    travel_allowance    = fields.Float('Travel Allowance')
    meal_allowance      = fields.Float('Meal Allowance')
    medical             = fields.Float('Medical Allowance')
    overtime_allowance  = fields.Float('Overtime Allowance')
    bonus               = fields.Float('Bonus')
    conveyance          = fields.Float('Conveyance')
    data_allowance      = fields.Float('Data Card Allowance')
    ea_allowance        = fields.Float('EA Allowance')
    learning_development = fields.Float('Learning and Development')
    other               = fields.Float('Other Allowance')

    # Deductions snapshot
    tds_deduction       = fields.Float('TDS')
    mobile_deduction    = fields.Float('Mobile Deduction')
    other_deduction     = fields.Float('Other Deduction')

    # PF snapshot
    employee_pf         = fields.Float('Employee PF')
    voluntary_pf        = fields.Float('Voluntary PF')
    employer_pf         = fields.Float('Employer PF')

    effective_date      = fields.Date('Effective Date')


# ── hr.employee extension ────────────────────────────────────────────────────

class HrEmployee(models.Model):
    """
    Adds salary history and effective_date to hr.employee.

    All salary allowance/deduction fields (basic_percentage, wage,
    travel_allowance, hra, tds, pf_amount, etc.) are expected to already
    exist on hr.employee via the hr_payroll_extended module.

    If hr_payroll_extended is NOT installed alongside this module,
    uncomment the FALLBACK FIELDS block below to avoid AttributeError.
    """
    _inherit = 'hr.employee'

    history_line = fields.One2many(
        'salary.history.line',
        'employee_id',
        string='Salary History',
    )
    effective_date = fields.Date('Effective Date')

    # ── FALLBACK FIELDS ──────────────────────────────────────────────────────
    # Uncomment if hr_payroll_extended is NOT installed.
    # These mirror the fields from hr_payroll_extended/models/models.py.
    #
    # basic_percentage    = fields.Float('Basic %', digits=(16, 2))
    # wage                = fields.Float('Wage')
    # struct_id           = fields.Many2one('hr.payroll.structure', 'Salary Structure')
    # travel_allowance    = fields.Float('Travel Allowance')
    # earning_alw         = fields.Float('EA Allowance')
    # data_card_alw       = fields.Float('Data Card Allowance')
    # ot_allowance        = fields.Float('Overtime Allowance')
    # hra_amount          = fields.Float('HRA')
    # bonus               = fields.Float('Bonus')
    # medical_allowance   = fields.Float('Medical Allowance')
    # meal_allowance      = fields.Float('Meal Allowance')
    # conveyance          = fields.Float('Conveyance')
    # other_allowance     = fields.Float('Other Allowance')
    # tds                 = fields.Float('TDS')
    # mobile_deduction    = fields.Float('Mobile Deduction')
    # other_deduction     = fields.Float('Other Deduction')
    # pf_amount           = fields.Float('Employee PF')
    # vpf_amount          = fields.Float('Voluntary PF')
    # epf_amount          = fields.Float('Employer PF')
    # ─────────────────────────────────────────────────────────────────────────
