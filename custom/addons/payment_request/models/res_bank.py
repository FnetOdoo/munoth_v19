from odoo import models, fields


class ResBank(models.Model):
    _inherit = 'res.bank'

    bic = fields.Char('Bank IFSC Code')


class ResPartner(models.Model):
    _inherit = 'res.partner'

    payment_receipt_email_to = fields.Char()
    payment_receipt_email_cc = fields.Char()
