from odoo import models, fields, api, _





class InsulationResistance(models.Model):
    _name='insulation.resistance.test'
    _description='Insulation Resistance Test'

    degas_id = fields.Many2one('degas.cell')
    voltage=fields.Float()
    resistance_set=fields.Float()
    resist_time=fields.Float()


class QualityDetails(models.Model):
    _name = 'quality.parameter'
    _description = 'Quality Parameter'

    name = fields.Char()

    # slitting
    thickness = fields.Char()
    peel_off = fields.Char()
    width = fields.Char()
    burrs = fields.Char()
    cross_cutting = fields.Char()
    damages = fields.Char()
    exterior = fields.Char()
    ambient_temperature = fields.Char()
    date = fields.Datetime(default=fields.Datetime.now)
    user_id = fields.Many2one(
        'res.users', 'Responsible', default=lambda self: self.env.user)

    # drying
    moisture_content = fields.Float()
    color_shading = fields.Char()
    visual_examination = fields.Char()
    quality_remarks = fields.Char(string='Remarks')



    # elecrode making

    tab_dimension = fields.Char()
    productive_tape = fields.Char()
    tab_tape = fields.Char()
    tensile_strength_weld = fields.Char()


    # winding

    ccd_dimension = fields.Char()
    hi_pot_test = fields.Char()
    x_ray_check = fields.Char()

    caliper_check = fields.Char()

    # hot press

    pressure = fields.Float()
    temperature = fields.Float()

    # assembly
    weight = fields.Float()
    sealing_adhesion = fields.Char()

    # injection

    moisture_in_electrolyte = fields.Float()
    dimension = fields.Float()

    # voltage
    ocv = fields.Float()
    ir = fields.Float()
    visual_examination=fields.Float()

    # capacity
    ccv_discharge_amps = fields.Float()
    ccv_discharge_volts = fields.Float()
    ccv_discharge_physical = fields.Char()

    #packing

    printing_defects = fields.Char()
    visual_appearence=fields.Float()
    dimension_check=fields.Float()

    #degas
    voltage = fields.Float()
    resistance = fields.Float()







