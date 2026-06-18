from odoo import models, fields, api,_

class SaleType(models.Model):
    _name='sale.type'
    _description = 'Sale Type'

    declaration = fields.Html()


