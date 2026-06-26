# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    def action_open_versions(self):
        """Override to fix AttributeError when employee_id is False.
        Using self.name and self.id directly is safer as it refers to the 
        employee record itself.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': self.name + self.env._(' Records'),
            'path': 'versions',
            'res_model': 'hr.version',
            'view_mode': 'list,graph,pivot',
            'views': [(self.env.ref('hr.hr_version_list_view').id, 'list'), (False, 'graph'), (False, 'pivot')],
            'domain': [('employee_id', '=', self.id)],
            'search_view_id': self.env.ref('hr.hr_version_search_view').id
        }
