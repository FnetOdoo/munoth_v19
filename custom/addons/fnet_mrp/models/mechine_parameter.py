from odoo import models, fields, api, _




class MachineData(models.Model):
    _name = 'machine.parameter'
    _description = 'Machine Parameter'
    _order = "id desc"

    # slitting


    date = fields.Datetime(default=fields.Datetime.now)
    slitting_speed = fields.Float()
    slitting_width = fields.Float()
    winding_tension = fields.Float()
    blade_condition = fields.Char()
    magnetic_filter_flux_density = fields.Char()
    setting_tension = fields.Char()
    current_meters = fields.Char()
    accumulated_electrode =fields.Char()
    slip_ring_qty = fields.Char()
    cutter_speed = fields.Char()
    brush_jogging = fields.Char()
    user_id = fields.Many2one(
        'res.users', 'Responsible', default=lambda self: self.env.user)

    # drying
    temperature = fields.Float()
    vacuum = fields.Float()


    # elecroode making

    electrode_length = fields.Float()
    electrode_width = fields.Float()
    electrode_winding_tension = fields.Float()

    # winding

    anode_length = fields.Float()
    cathode_length = fields.Float()
    anode_tension = fields.Float()
    cathode_tension = fields.Float()
    separator_length = fields.Float()
    separator_tension = fields.Float()
    cold_press_pressure = fields.Float()

    # hot press
    pressure = fields.Float()

    # assembly

    # injection

    injection_volume = fields.Float()
    sealing_temp = fields.Float()
    sealing_pressure = fields.Float()
    vac_sucker = fields.Float()
    vac_stewing_1 = fields.Float()
    vac_stewing_2 = fields.Float()
    vac_stewing_3 = fields.Float()
    vac_sealer = fields.Float()
    post_injection_stabilization_time = fields.Float()
    sealing_width = fields.Float()
    weight_before = fields.Float()
    weight_after = fields.Float()


    # voltage TEST
    voltage = fields.Float()
    resistance = fields.Float()

    # capacity

    rest_time = fields.Float()

    # constant voltage charge1

    cvc_voltage = fields.Float()
    cvc_current = fields.Float()
    cvc_cut_off = fields.Float()
    cvc_time = fields.Float()

    # constant current discharge

    ccd_current = fields.Float()
    ccd_limit_current = fields.Float()
    ccd_time = fields.Float()
    ccd_rest = fields.Float()
    # constant voltage charge2

    cvc_voltage_2 = fields.Float()
    cvc_current_2 = fields.Float()
    cvc_cut_off_2 = fields.Float()
    cvc_time_2 = fields.Float()
    cvc_test_2=fields.Float()

    # degas

    sealing_time = fields.Float()
    vacuum_holding_time = fields.Float()
    weight_before_degas = fields.Float()
    weight_after_degas = fields.Float()
    trimming = fields.Float()
    folding = fields.Float()











