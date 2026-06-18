# -*- coding: utf-8 -*-
"""
Migration Notes (v15 → v19)
============================

1.  hr.contract REMOVED AS SEPARATE SALARY-CONFIG MODEL in v17+
    ─────────────────────────────────────────────────────────────
    In Odoo 15/16 the Indian payroll module stored allowance/deduction
    configuration on hr.contract.  From v17 onward Odoo ships with a
    redesigned payroll where hr.contract still exists (for legal/date
    purposes) but ALL salary-structure fields are moved directly onto
    hr.employee so that HR managers can manage them without opening a
    separate contract record.

    Migration strategy used here:
        • All former hr.contract salary fields  →  hr.employee (this file)
        • hr.contract is still inherited only for the auto-expiry cron
          (which now only updates the contract state).
        • Views updated to show the new fields on the employee form.

2.  decimal_precision (dp.get_precision) REMOVED
    ─────────────────────────────────────────────
    odoo.addons.decimal_precision was removed in v17.
    Replace  digits=dp.get_precision('Payment Terms')
    with     digits=(16, 2)   or simply omit (Float defaults to 2 dp).

3.  @api.onchange('contract_id', ...) on hr.payslip
    ─────────────────────────────────────────────────
    hr.payslip no longer carries contract_id as a user-editable field
    from v17.  The onchange now targets employee_id / date_from / date_to.

4.  base64.encodestring REMOVED (Python 3.9+)
    ──────────────────────────────────────────
    Use base64.encodebytes() instead.

5.  hr_payroll_community → hr_payroll
    ────────────────────────────────────
    The community payroll module was merged into the standard hr_payroll
    addon starting from v16 Enterprise / v17 Community.

6.  XPath view references updated
    ─────────────────────────────────
    References to hr_payroll_community.* external IDs replaced with
    hr_payroll.* equivalents.
"""

import logging
from calendar import monthrange
from datetime import date
from odoo import models, fields, api

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# hr.payslip — keep lop_days / tot_month_days, fix onchange trigger
# ---------------------------------------------------------------------------

class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    lop_days = fields.Float('LOP Days')

    # In v17+ tot_month_days must NOT depend on contract_id (field gone).
    @api.depends('employee_id', 'date_from', 'date_to')
    def _get_tot_work_days(self):
        for rec in self:
            if rec.date_from:
                from_date = fields.Date.from_string(rec.date_from)
                rec.tot_month_days = monthrange(from_date.year, from_date.month)[1]
            else:
                rec.tot_month_days = 0.0

    tot_month_days = fields.Float(
        'Total days',
        compute='_get_tot_work_days',
        store=True,
    )

    # contract_id removed from depends/onchange – use employee_id & date fields
    @api.onchange('employee_id', 'date_from', 'date_to')
    def onchange_start_date(self):
        lop_days = 0
        if not self.date_from or not self.date_to:
            self.lop_days = 0
            return
        from_date = fields.Date.from_string(self.date_from)
        to_date = fields.Date.from_string(self.date_to)
        start = from_date.replace(day=1)
        end = from_date.replace(day=monthrange(from_date.year, from_date.month)[1])
        if from_date > start:
            lop_days += (from_date - start).days
        if to_date < end:
            lop_days += (end - to_date).days
        self.lop_days = lop_days


# ---------------------------------------------------------------------------
# hr.employee — salary structure fields (formerly on hr.contract in v15)
# ---------------------------------------------------------------------------

class HrEmployee(models.Model):
    """
    In v17+ the recommended pattern is to store Indian-specific salary
    configuration directly on the employee record.  All fields that used to
    live on hr.contract are placed here so payslip salary rules can still
    reach them via  employee_id.<field>.

    If your payslip salary rules reference  contract_id.basic_percentage  etc.,
    update them to  employee_id.basic_percentage  instead.
    """
    _inherit = 'hr.employee'

    # ── Deductions ──────────────────────────────────────────────────────────
    tds = fields.Float('TDS')
    pf_amount = fields.Float("Employee PF")
    vpf_amount = fields.Float('Voluntary PF')
    epf_amount = fields.Float("Employer PF")
    other_deduction = fields.Float('Other Deduction')
    is_esi = fields.Boolean(string="IS ESI")
    is_pf = fields.Boolean(string="IS PF")
    pt = fields.Float(string="PT")
    mobile_deduction = fields.Float(string="Mobile Deduction")
    advance_salary = fields.Float(string="Advance Salary")
    pt_amount = fields.Float('PT')
    pt_amount_ap = fields.Float("PT(AP)")
    is_ap = fields.Boolean('Is AP?')

    # ── Allowances ──────────────────────────────────────────────────────────
    salary_arrears = fields.Float("Salary Arrears")
    ot_allowance = fields.Float(string="OT")
    data_card_alw = fields.Float(string="Data Card")
    bonus = fields.Float(string="Bonus")
    is_bonus = fields.Boolean(string="Is Bonus")
    is_conveyance = fields.Boolean(string="Is Conveyance")
    conveyance = fields.Float(string="Conveyance")
    earning_alw = fields.Float(string="Earned Allowance")
    # dp.get_precision removed in v17; use plain digits tuple
    basic_percentage = fields.Float(string="Basic %", digits=(16, 2))
    is_hra = fields.Boolean(string="Is HRA")
    is_travel_added = fields.Boolean(string="Is TA Not in Basic")
    is_other = fields.Boolean(string="Is Other")
    other_allowance = fields.Float(string="Other Allowance")
    consolidate_pay = fields.Float(string="Consolidate Pay")
    is_new_emp = fields.Boolean(string="Is New")
    new_employee = fields.Float(string="Worked days for New Employee")
    is_medical = fields.Boolean(string="Is Medical")
    medical = fields.Float(string="Medical")
    arrears = fields.Float(string="Arrears")
    is_arrear = fields.Boolean(string="Is Salary Revised")
    non_cash = fields.Float(string="Non Cash Component")

    # ── Indian statutory IDs (used in Excel report) ─────────────────────────
    # These may already exist on hr.employee in standard Odoo; add only if absent.
    esi_no = fields.Char('ESI Number')
    pf_no = fields.Char('PF Number')
    pf_uan_no = fields.Char('PF/UAN Number')
    joining_date = fields.Date('Date of Joining')
    # employee_id (emp code) may already exist; extend if not present
    emp_code = fields.Char('Employee ID / Code')


# ---------------------------------------------------------------------------
# hr.employee — contract-expiry scheduled action
# ---------------------------------------------------------------------------
# NOTE (v19): hr.contract does NOT exist in the v19 registry — the model was
# fully removed.  The contract-expiry logic is moved onto hr.employee so the
# cron job still works.  The cron.xml targets model_hr_employee accordingly.
# ---------------------------------------------------------------------------

class HrEmployeeContractExpiry(models.Model):
    """Contract-expiry helper moved to hr.employee (hr.contract removed v17+)."""
    _inherit = 'hr.employee'

    @api.model
    def _contract_expiry(self):
        """
        Odoo v19 manages contract state through hr.employee fields directly.
        If your v19 build still has a contract_ids or active_contract_id field
        on hr.employee, you can query it here.  Otherwise this method is a
        safe no-op placeholder until your HR workflow is confirmed.
        """
        # Attempt graceful handling if any contract-like field still exists
        # on hr.employee in this specific v19 build.
        if 'hr.contract' in self.env:
            # Defensive: if somehow hr.contract is present (enterprise build)
            expired = self.env['hr.contract'].search([
                ('date_end', '<', fields.Date.to_string(date.today())),
                ('state', '=', 'open'),
            ])
            if expired:
                expired.write({'state': 'close'})
        else:
            _logger.info(
                "hr_payroll_extended: _contract_expiry skipped — "
                "hr.contract not in registry (v19 community build)."
            )


# ---------------------------------------------------------------------------
# res.partner.bank — IFSC code (unchanged from v15)
# ---------------------------------------------------------------------------

class BankCode(models.Model):
    _inherit = 'res.partner.bank'

    ifsc_code = fields.Char('IFSC Code')
