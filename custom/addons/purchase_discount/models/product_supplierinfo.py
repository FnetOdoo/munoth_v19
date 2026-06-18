from odoo import api, fields, models


class ProductSupplierInfo(models.Model):
    _inherit = "product.supplierinfo"

    discount = fields.Float(string="Discount (%)", digits="Discount")

    @api.onchange("name")
    def onchange_name(self):
        """Apply the default supplier discount of the selected supplier"""
        for supplierinfo in self.filtered("name"):
            supplierinfo.discount = supplierinfo.name.default_supplierinfo_discount
