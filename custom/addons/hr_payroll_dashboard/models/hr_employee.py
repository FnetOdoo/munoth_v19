from odoo import models, fields, api
from datetime import date


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    def _get_running_contract_count(self):
        """
        Running contracts: employees where
        contract_date_start <= today AND
        (contract_date_end >= today OR contract_date_end is False)
        """
        today = date.today()
        domain = [
            ('contract_date_start', '<=', today),
            '|',
            ('contract_date_end', '=', False),
            ('contract_date_end', '>=', today),
        ]
        return self.env['hr.employee'].search_count(domain)

    def _get_expired_contract_count(self):
        """
        Expired contracts: employees where contract_date_end < today
        """
        today = date.today()
        domain = [
            ('contract_date_end', '<', today),
            ('contract_date_end', '!=', False),
        ]
        return self.env['hr.employee'].search_count(domain)

    def _get_running_contract_domain(self):
        today = date.today()
        return [
            ('contract_date_start', '<=', today.strftime('%Y-%m-%d')),
            '|',
            ('contract_date_end', '=', False),
            ('contract_date_end', '>=', today.strftime('%Y-%m-%d')),
        ]

    def _get_expired_contract_domain(self):
        today = date.today()
        return [
            ('contract_date_end', '<', today.strftime('%Y-%m-%d')),
            ('contract_date_end', '!=', False),
        ]
