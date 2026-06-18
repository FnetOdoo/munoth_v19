
from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    purchase_supplier_discount_real = fields.Boolean(
        string="Real Purchase Supplier Discount",
        related="company_id.purchase_supplier_discount_real",
        store=True,
        readonly=False,
    )
