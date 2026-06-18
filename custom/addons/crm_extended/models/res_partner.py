from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #         if vals.get('name'):
    #             existing_customer = self.search([('name', '=', vals['name'])])
    #             if existing_customer:
    #                 raise UserError('Partner "%s" already exists!' % vals['name'])
    #     return super(ResPartner, self).create(vals_list)