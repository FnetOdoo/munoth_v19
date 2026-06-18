from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = "sale.order"

    proforma_invoice = fields.Date("Proforma Date", )
    proforma_no = fields.Char("Proforma Number")
    company_details = fields.Many2one('res.partner.bank', string="Bank Details")
    sample_sale = fields.Boolean()
    buyer = fields.Char(string="Buyer's PO No",requried=True)
    buyer_date = fields.Date(string="Buyer's PO Date",requried=True)

    def action_generate(self):
        for rec in self:
            rec.proforma_invoice = fields.Date.today()
            rec.proforma_no = self.env['ir.sequence'].next_by_code('proforma.invoice')
            return rec.proforma_no


class ResPartner(models.Model):
    _inherit = "res.partner"

    pan_no = fields.Char("PAN NO")

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    total_value_of_goods = fields.Char()



