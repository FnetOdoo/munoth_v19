from odoo import models, fields, api, _


class AmbientCondition(models.Model):
    _name = 'ambient.condition'
    _description = 'Ambient Condition'

    temperature = fields.Float()
    humidity = fields.Float()
    date = fields.Datetime()


class Utilities(models.Model):
    _name = 'utility.parameter'
    _description = 'Utility Parameter'

    date = fields.Datetime(default=fields.Datetime.now)
    compressed_air = fields.Float()
    nitrogen = fields.Float()
    vacuum_section_pressure = fields.Float()
    temperature = fields.Float()
    humidity = fields.Float()
    user_id = fields.Many2one(
        'res.users', 'Responsible', default=lambda self: self.env.user)


    # winding

    welding_time = fields.Float()
    welding_amplitude = fields.Float()




