from odoo import models, fields, api


class ResPartner(models.Model):
    _inherit = 'res.partner'

    is_customer = fields.Boolean("Is Customer")
    is_vendor = fields.Boolean("Is Vendor")
    code = fields.Char("Code")
    vat = fields.Char(string="GST IN")


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    partner_id = fields.Many2one('res.partner', string='Customer', tracking=10, index=True,
                                 domain="['|',('company_id', '=', False), ('company_id', '=', company_id), ('is_customer', '=', True)]",
                                 help="Linked partner (optional). Usually created when converting the lead. You can find a partner by its Name, TIN, Email or Internal Reference.")


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    vendor_id = fields.Many2one('res.partner', string="Vendor", domain="['|', ('company_id', '=', False), ('company_id', '=', company_id), ('is_vendor', '=', True)]")

