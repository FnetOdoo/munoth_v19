# -*- coding: utf-8 -*-
from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _default_is_storable(self):
        # "Track Inventory" ticked by default for goods; services/combos cannot be tracked
        return self.env.context.get('default_type', 'consu') == 'consu'

    is_storable = fields.Boolean(default=_default_is_storable)
