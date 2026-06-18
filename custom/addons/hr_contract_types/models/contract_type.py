# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


# MIGRATION NOTE (Odoo 15 → 19):
# In Odoo 15, this module DEFINED hr.contract.type from scratch (_name).
# In Odoo 19, hr.contract.type is already natively defined inside the 'hr' module
# with fields: name, code, sequence.
# We now INHERIT (_inherit) the existing model instead of redefining it,
# so we don't clash with the native definition and the native 'code' field is preserved.
class ContractType(models.Model):
    _inherit = 'hr.contract.type'
    # All original fields (name, sequence) already exist on the native model.
    # No additional fields to add here — the model extension is kept so future
    # custom fields can be added without breaking the module structure.


# MIGRATION NOTE (Odoo 15 → 19):
# In Odoo 15 this class inherited hr.contract to add type_id.
# hr.contract model was removed in Odoo 19.
# The type_id field is now placed on hr.employee instead.
class HrEmployeeInherit(models.Model):
    _inherit = 'hr.employee'

    type_id = fields.Many2one(
        'hr.contract.type',
        string="Employee Category",
        required=False,
        help="Employee category (formerly on hr.contract, moved to hr.employee in Odoo 19)",
        default=lambda self: self.env['hr.contract.type'].search([], limit=1),
    )
