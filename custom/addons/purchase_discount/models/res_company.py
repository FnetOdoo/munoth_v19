
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    purchase_supplier_discount_real = fields.Boolean(
        string="Real Purchase Supplier Discount", default=False
    )
