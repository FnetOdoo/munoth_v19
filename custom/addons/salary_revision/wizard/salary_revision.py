# -*- coding: utf-8 -*-
"""
Migration Notes — salary_revision.py (v15 → v19)
==================================================

v15 design
───────────
  • Wizard opened from hr.contract form via action button
  • default_get() reads  active_model='hr.contract'
  • contract_id = Many2one('hr.contract')
  • update_salary() reads/writes  self.contract_id.<field>
  • Salary history line created with  contract_id=self.contract_id.id

v19 design
───────────
  • hr.contract does NOT exist → wizard opened from hr.employee form
  • default_get() reads  active_model='hr.employee'
  • employee_id = Many2one('hr.employee')
  • update_salary() reads/writes  self.employee_id.<field>
  • Salary history line created with  employee_id=self.employee_id.id

  Field-name mapping (contract → employee)
  ─────────────────────────────────────────
  contract.basic_percentage  → employee.basic_percentage
  contract.wage              → employee.wage
  contract.struct_id         → employee.struct_id
  contract.effective_date    → employee.effective_date
  contract.travel_allowance  → employee.travel_allowance
  contract.earning_alw       → employee.earning_alw
  contract.data_card_alw     → employee.data_card_alw
  contract.ot_allowance      → employee.ot_allowance
  contract.hra               → employee.hra  (or hra_amount depending on build)
  contract.bonus             → employee.bonus
  contract.medical_allowance → employee.medical_allowance
  contract.meal_allowance    → employee.meal_allowance
  contract.conveyance        → employee.conveyance
  contract.other_allowance   → employee.other_allowance
  contract.tds               → employee.tds
  contract.mobile_deduction  → employee.mobile_deduction
  contract.other_deduction   → employee.other_deduction
  contract.pf_amount         → employee.pf_amount
  contract.vpf_amount        → employee.vpf_amount
  contract.epf_amount        → employee.epf_amount
"""

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SalaryRevision(models.TransientModel):
    """
    Wizard to revise employee salary.
    Opens from the hr.employee form; snapshots current values into
    salary.history.line, then writes new values onto hr.employee.

    Changed from models.Model → models.TransientModel because this is a
    one-shot wizard; records can be cleaned up by the ORM automatically.
    """
    _name = "salary.revision"
    _description = "Salary Revision Wizard"

    # ── Identity ─────────────────────────────────────────────────────────────
    # v15: contract_id = Many2one('hr.contract')
    # v19: hr.contract removed → link to hr.employee
    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        readonly=True,
    )

    # ── New salary values ─────────────────────────────────────────────────────
    basic           = fields.Char('Basic Percentage')
    wage            = fields.Float('Wages', digits=(16, 5))
    effective_date  = fields.Date('Effective Date', required=True)
    structure_id    = fields.Many2one('hr.payroll.structure', 'Payroll Structure')

    # Allowances
    travel_allowance    = fields.Float('Travel Allowance',      digits=(16, 5))
    ea_allowance        = fields.Float('EA Allowance',          digits=(16, 5))
    data_allowance      = fields.Float('Data Card Allowance',   digits=(16, 5))
    overtime_allowance  = fields.Float('Overtime Allowance',    digits=(16, 5))
    hra                 = fields.Float('HRA',                   digits=(16, 5))
    bonus               = fields.Float('Bonus',                 digits=(16, 5))
    medical             = fields.Float('Medical',               digits=(16, 5))
    meal_allowance      = fields.Float('Meal Allowance',        digits=(16, 5))
    conveyance          = fields.Float('Conveyance',            digits=(16, 5))
    other               = fields.Float('Other Allowance',       digits=(16, 5))

    # Deductions
    pt                  = fields.Float('PT',                    digits=(16, 5))
    tds_deduction       = fields.Float('TDS',                   digits=(16, 5))
    mobile_deduction    = fields.Float('Mobile Deduction',      digits=(16, 5))
    other_deduction     = fields.Float('Other Deduction',       digits=(16, 5))
    employee_pf         = fields.Float('Employee PF',           digits=(16, 5))
    voluntary_pf        = fields.Float('Voluntary PF',          digits=(16, 5))
    employer_pf         = fields.Float('Employer PF',           digits=(16, 5))

    # ── Default values from hr.employee ──────────────────────────────────────

    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        ctx = dict(self._context or {})
        active_model = ctx.get('active_model')
        active_ids   = ctx.get('active_ids') or []

        if not active_model or not active_ids:
            raise UserError(_(
                "Programmer error: wizard opened without active_model "
                "or active_ids in context."
            ))

        # v19: active_model must be hr.employee (not hr.contract)
        if active_model != 'hr.employee':
            raise UserError(_(
                "This wizard must be opened from an Employee record.\n"
                "active_model received: %s"
            ) % active_model)

        employee = self.env['hr.employee'].browse(active_ids[0])
        if not employee.exists():
            raise UserError(_("Employee record not found."))

        rec.update({
            'employee_id':      employee.id,
            'basic':            getattr(employee, 'basic_percentage', False) or '',
            'wage':             getattr(employee, 'wage', 0.0),
            'structure_id':     getattr(employee.struct_id, 'id', False) if hasattr(employee, 'struct_id') else False,
            'travel_allowance': getattr(employee, 'travel_allowance', 0.0),
            'ea_allowance':     getattr(employee, 'earning_alw', 0.0),
            'data_allowance':   getattr(employee, 'data_card_alw', 0.0),
            'overtime_allowance': getattr(employee, 'ot_allowance', 0.0),
            'hra':              getattr(employee, 'hra', 0.0),
            'bonus':            getattr(employee, 'bonus', 0.0),
            'medical':          getattr(employee, 'medical_allowance', 0.0),
            'meal_allowance':   getattr(employee, 'meal_allowance', 0.0),
            'conveyance':       getattr(employee, 'conveyance', 0.0),
            'other':            getattr(employee, 'other_allowance', 0.0),
            'tds_deduction':    getattr(employee, 'tds', 0.0),
            'mobile_deduction': getattr(employee, 'mobile_deduction', 0.0),
            'other_deduction':  getattr(employee, 'other_deduction', 0.0),
            'employee_pf':      getattr(employee, 'pf_amount', 0.0),
            'voluntary_pf':     getattr(employee, 'vpf_amount', 0.0),
            'employer_pf':      getattr(employee, 'epf_amount', 0.0),
        })
        return rec

    # ── Apply revision ────────────────────────────────────────────────────────

    def update_salary(self):
        """
        1. Snapshot current employee salary into salary.history.line
        2. Write new salary values onto hr.employee
        """
        emp = self.employee_id
        if not emp:
            raise UserError(_("No employee linked to this revision."))

        # ── Step 1: snapshot current values into history ──────────────────
        history_vals = {
            'employee_id':      emp.id,
            'old_basic':        getattr(emp, 'basic_percentage', ''),
            'old_wage':         getattr(emp, 'wage', 0.0),
            'old_structure_id': getattr(emp.struct_id, 'id', False) if hasattr(emp, 'struct_id') else False,
            'travel_allowance': getattr(emp, 'travel_allowance', 0.0),
            'ea_allowance':     getattr(emp, 'earning_alw', 0.0),
            'data_allowance':   getattr(emp, 'data_card_alw', 0.0),
            'overtime_allowance': getattr(emp, 'ot_allowance', 0.0),
            'hra':              getattr(emp, 'hra', 0.0),
            'bonus':            getattr(emp, 'bonus', 0.0),
            'medical':          getattr(emp, 'medical_allowance', 0.0),
            'meal_allowance':   getattr(emp, 'meal_allowance', 0.0),
            'conveyance':       getattr(emp, 'conveyance', 0.0),
            'other':            getattr(emp, 'other_allowance', 0.0),
            'tds_deduction':    getattr(emp, 'tds', 0.0),
            'mobile_deduction': getattr(emp, 'mobile_deduction', 0.0),
            'other_deduction':  getattr(emp, 'other_deduction', 0.0),
            'effective_date':   getattr(emp, 'effective_date', False),
            'employee_pf':      getattr(emp, 'pf_amount', 0.0),
            'voluntary_pf':     getattr(emp, 'vpf_amount', 0.0),
            'employer_pf':      getattr(emp, 'epf_amount', 0.0),
        }
        self.env['salary.history.line'].create(history_vals)

        # ── Step 2: write new values onto hr.employee ─────────────────────
        new_vals = {}

        def _set(emp_field, wiz_val):
            if hasattr(emp, emp_field):
                new_vals[emp_field] = wiz_val

        _set('basic_percentage',  self.basic)
        _set('wage',              self.wage)
        _set('effective_date',    self.effective_date)
        _set('travel_allowance',  self.travel_allowance)
        _set('earning_alw',       self.ea_allowance)
        _set('data_card_alw',     self.data_allowance)
        _set('ot_allowance',      self.overtime_allowance)
        _set('hra',               self.hra)
        _set('bonus',             self.bonus)
        _set('medical_allowance', self.medical)
        _set('meal_allowance',    self.meal_allowance)
        _set('conveyance',        self.conveyance)
        _set('other_allowance',   self.other)
        _set('tds',               self.tds_deduction)
        _set('mobile_deduction',  self.mobile_deduction)
        _set('other_deduction',   self.other_deduction)
        _set('pf_amount',         self.employee_pf)
        _set('vpf_amount',        self.voluntary_pf)
        _set('epf_amount',        self.employer_pf)

        # struct_id is optional — only write if field exists on employee
        if hasattr(emp, 'struct_id') and self.structure_id:
            new_vals['struct_id'] = self.structure_id.id

        if new_vals:
            emp.write(new_vals)

        return {'type': 'ir.actions.act_window_close'}
