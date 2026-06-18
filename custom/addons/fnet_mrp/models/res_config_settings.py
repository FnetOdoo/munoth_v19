from odoo import api, fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    maintenance_user_id = fields.Char(string = 'Maintenance Mail ID')




class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    maintenance_user = fields.Char(string = 'Maintenance Mail ID',related="company_id.maintenance_user_id",readonly=False)

