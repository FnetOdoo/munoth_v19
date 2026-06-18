# -*- coding: utf-8 -*-
import logging

from odoo import fields, models, _

_logger = logging.getLogger(__name__)


class HrPayslip(models.Model):
    """Inherit hr.payslip for send-mail functionality.

    Odoo 19 migration notes
    -----------------------
    * hr.employee.base has been removed; hr.employee is now the single
      employee model. All employee field access remains via self.employee_id.
    * hr.contract has been removed. Contract data (wage, structure type, etc.)
      is stored directly on hr.employee. Use employee_id.wage,
      employee_id.struct_type_id, etc. instead of employee_id.contract_id.*
    * action_payslip_done() has been renamed to action_payslip_confirm() in
      the v19 payroll module. The override is updated accordingly.
    * private_email is still accessible on hr.employee in v19 community;
      adjust if your v19 build moves it to hr.employee.private.
    * Payslip state 'verify' renamed to 'verified' — see wizard as well.
    """
    _inherit = 'hr.payslip'

    is_send_mail = fields.Boolean(
        string="Is Send Mail",
        help="Tracks whether the payslip email has been sent.")

    # ------------------------------------------------------------------
    # Odoo 19: override action_payslip_confirm (was action_payslip_done)
    # ------------------------------------------------------------------
    def action_payslip_confirm(self):
        """Send payslip email on confirmation if the setting is enabled.

        Called automatically when a payslip is confirmed. Replaces the
        Odoo 18 action_payslip_done override.
        """
        config = self.env['ir.config_parameter'].sudo()
        auto_send = config.get_param('send_payslip_by_email')
        if auto_send:
            self.write({'is_send_mail': True})

        res = super().action_payslip_confirm()

        if auto_send:
            template = self.env.ref(
                'hr_payslip_monthly_report.email_template_payslip',
                raise_if_not_found=False,
            )
            if template:
                for payslip in self:
                    # Odoo 19: private_email is on hr.employee directly.
                    # If your v19 build uses work_email, replace below.
                    if payslip.employee_id.private_email:
                        template.sudo().send_mail(payslip.id, force_send=True)
                        _logger.info(
                            "Payslip email sent for %s",
                            payslip.employee_id.name,
                        )
        return res

    def action_payslip_send(self):
        """Open the email compose wizard with the payslip template."""
        self.ensure_one()
        self.write({'is_send_mail': True})
        ir_model_data = self.env['ir.model.data']
        try:
            template_id = ir_model_data._xmlid_lookup(
                'hr_payslip_monthly_report.email_template_payslip')[1]
        except ValueError:
            template_id = False
        try:
            compose_form_id = ir_model_data._xmlid_lookup(
                'mail.email_compose_message_wizard_form')[1]
        except ValueError:
            compose_form_id = False
        ctx = {
            'default_model': 'hr.payslip',
            'default_res_ids': self.ids,
            'default_template_id': template_id,
            'default_composition_mode': 'comment',
            'force_email': True,
        }
        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form_id, 'form')],
            'view_id': compose_form_id,
            'target': 'new',
            'context': ctx,
        }
