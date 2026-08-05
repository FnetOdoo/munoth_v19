# -*- coding: utf-8 -*-
# models/res_config_settings.py  (import in models/__init__.py:
#   from . import res_config_settings)
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    pm_document_no = fields.Char(string='Preventive Maintenance Document No')
    br_document_no = fields.Char(string='Breakdown Document No')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    pm_document_no = fields.Char(
        string='Preventive Maintenance Document No',
        related='company_id.pm_document_no', readonly=False)
    br_document_no = fields.Char(
        string='Breakdown Document No',
        related='company_id.br_document_no', readonly=False)