# -*- coding: utf-8 -*-
from odoo import models


class MassConfirmPayslip(models.TransientModel):
    """Mass-confirm payslips wizard.

    Odoo 19 migration notes
    -----------------------
    * action_payslip_done() renamed to action_payslip_confirm() in v19.
    * Payslip state 'done' is still the final confirmed state;
      'cancel' is still the rejected state. Both remain valid filters.
    * hr.contract / hr.employee.base: not referenced in this wizard.
    """
    _name = 'payslip.confirm'
    _description = 'Mass Confirm Payslip'

    def confirm_payslip(self):
        """Confirm all selected payslips that are not already done/cancelled."""
        active_ids = self._context.get('active_ids', [])
        payslips = self.env['hr.payslip'].search([
            ('id', 'in', active_ids),
            ('state', 'not in', ['cancel', 'done']),
        ])
        # Odoo 19: action_payslip_confirm replaces action_payslip_done
        if payslips:
            payslips.action_payslip_confirm()
