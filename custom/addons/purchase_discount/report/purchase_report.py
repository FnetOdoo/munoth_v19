from odoo import fields, models
from odoo.tools import SQL


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    discount = fields.Float(
        string="Discount (%)", digits="Discount", group_operator="avg"
    )

    def _select(self):
        return SQL(
            "%s, l.discount AS discount",
            super()._select(),
        )

    def _group_by(self):
        return SQL(
            "%s, l.discount",
            super()._group_by(),
        )

    def _get_discounted_price_unit_exp(self):
        """Returns the SQL expression for unit price after applying discount."""
        return SQL("(1.0 - COALESCE(l.discount, 0.0) / 100.0) * l.price_unit")