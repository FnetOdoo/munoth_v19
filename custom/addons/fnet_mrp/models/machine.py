from odoo import models, fields, api, _


class ManufacturingMachine(models.Model):
    _name = 'manufacturing.machine'
    _description = 'Manufacturing Machine'
    _order = "id desc"

    name = fields.Char()
    manufacturing_process_type_id = fields.Many2one('manufacturing.process.type')
    is_anode_slitting_process = fields.Boolean(related='manufacturing_process_type_id.is_anode_slitting_process', store=True)
    is_cathode_slitting_process = fields.Boolean(related='manufacturing_process_type_id.is_cathode_slitting_process', store=True)
    type = fields.Selection([
        ('anode_slitting', 'Anode Slitting '),
        ('cathode_slitting', 'Cathode Slitting '),
        ('anode_drying', 'Anode Drying'),
        ('cathode_drying', 'Cathode Drying'),
        ('diaphragm_drying', 'Diaphragm Drying'),
        ('anode_electrode_making', 'Anode Electrode Making'),
        ('cathode_electrode_making', 'Cathode Electrode Making'),
        ('winding', 'Winding'),
        ('hot_press_jelly', 'Hot Press Jelly'),
        ('assembly', 'Assembly'),
        ('qr_code_print', 'QR Code Printing'),
        ('cell_drying', 'Cell Drying'),
        ('injection', 'Injection'),
        ('high_temperature', 'High Temperature'),
        ('cell_clamp_baking', 'Cell Clamp Baking'),
        ('ht_clamp_baking', 'HT + Cell Clamp Baking'),
        ('aged_formation_cell', 'Aged Formation Cell'),
        ('degas', 'Degas'),
        ('dsf', 'Double side Folding'),
        ('pad_printing', 'Pad Printing'),
        ('capacity_test', 'Capacity Test'),
        ('voltage_test', 'Voltage Test'),
        ('aged_formation_cell_2', 'Aged Formation Cell 2'),
        ('voltage_test_2', 'Voltage Test 2'),
        ('packing', 'Packing')
    ])

    # sliting machine parameter - monitor parameter

    unwinding_diameter_diameter = fields.Char()
    unwinding_diameter_actual_tension = fields.Char()
    unwinding_diameter_setting_tension = fields.Char()
    upper_rewinding_diameter_diameter = fields.Char()
    upper_rewinding_diameter_actual_tension = fields.Char()
    upper_rewinding_diameter_setting_tension = fields.Char()
    down_rewinding_diameter_diameter = fields.Char()
    down_rewinding_diameter_actual_tension = fields.Char()
    down_rewinding_diameter_setting_tension = fields.Char()
    unwinding_setting_tension = fields.Char()
    upper_rewinding_setting_tension = fields.Char()
    rewinding_setting_tension = fields.Char()
    current_meter = fields.Char()
    accumulated_meter = fields.Char()
    current_electrode = fields.Char()
    accumulated_electrode = fields.Char()
    setting_production_meter = fields.Char()
    setting_production_electrode = fields.Char()
    upper_rewinding_slip_ring_qty = fields.Char()
    lower_rewinding_slip_ring_qty = fields.Char()

    # operation parameter

    traction_jogging_speed = fields.Char()
    upper_cutting_jogging_speed = fields.Char()
    lower_cutting_jogging_speed = fields.Char()
    upper_rewinder_jogging_speed = fields.Char()
    lower_rewinder_jogging_speed = fields.Char()
    os_edge_cut_jogging_speed_1 = fields.Char()
    os_edge_cut_jogging_speed_2 = fields.Char()
    brush_jogging = fields.Char()
    proximity_roller_jogging_speed = fields.Char()

    # set parameter

    low_speed = fields.Char()
    high_speed = fields.Char()
    guiding_speed = fields.Char()
    os_edge_cut_torque = fields.Char()
    ds_edge_cut_torque = fields.Char()
    brush_speed_ratio = fields.Char()
    edge_cut_ratio = fields.Char()
    unwinding_tension_display = fields.Char()
    set_unwinding_setting_tension = fields.Char()
    upper_rewinding_tension_display = fields.Char()
    upper_rewinding_setting_display = fields.Char()
    lower_rewinding_tension_display = fields.Char()
    lower_rewinding_setting_display = fields.Char()
    alcohol_valve_current_meter = fields.Char()
    alcohol_valve_enable_meter = fields.Char()
    alcohol_valve_operation_time = fields.Char()
    upper_cutter_speed_ratio = fields.Char()
    lower_cutter_sped_ratio = fields.Char()
    rewinding_speed_ratio = fields.Char()

    # Tension PID
    unwinding_start_p = fields.Char()
    unwinding_end_p = fields.Char()
    unwinding_speed_min = fields.Char()
    unwinding_speed_max = fields.Char()
    upper_rewinding_start_p = fields.Char()
    upper_rewinding_end_p = fields.Char()
    upper_rewinding_speed_min = fields.Char()
    upper_rewinding_speed_max = fields.Char()
    lower_rewinding_start_p = fields.Char()
    lower_rewinding_end_p = fields.Char()
    lower_rewinding_speed_min = fields.Char()
    lower_rewinding_speed_max = fields.Char()

    unwinding_valve_pid_proportion = fields.Char()
    unwinding_valve_pid_differentiate = fields.Char()
    unwinding_valve_pid_weight = fields.Char()
    unwinding_valve_pid_tension = fields.Char()
    unwinding_valve_pid_points = fields.Char()
    unwinding_valve_pid_setting_tension = fields.Char()

    upper_rewinding_valve_pid_proportion = fields.Char()
    upper_rewinding_valve_pid_differentiate = fields.Char()
    upper_rewinding_valve_pid_weight = fields.Char()
    upper_rewinding_valve_pid_tension = fields.Char()
    upper_rewinding_valve_pid_points = fields.Char()
    upper_rewinding_valve_pid_setting_tension = fields.Char()
    upper_rewinding_valve_pid_friction = fields.Char()
    upper_rewinding_valve_pid_slip_ring = fields.Char()
    upper_rewinding_valve_pid_slip_press = fields.Char()
    upper_rewinding_valve_pid_out = fields.Char()

    lower_rewinding_valve_pid_proportion = fields.Char()
    lower_rewinding_valve_pid_differentiate = fields.Char()
    lower_rewinding_valve_pid_weight = fields.Char()
    lower_rewinding_valve_pid_tension = fields.Char()
    lower_rewinding_valve_pid_points = fields.Char()
    lower_rewinding_valve_pid_setting_tension = fields.Char()
    lower_rewinding_valve_pid_friction = fields.Char()
    lower_rewinding_valve_pid_slip_ring = fields.Char()
    lower_rewinding_valve_pid_slip_press = fields.Char()
    lower_rewinding_valve_pid_out = fields.Char()

    # diameter parameter

    unwinding_measured_roll_diameter = fields.Char()
    unwinding_max_roll_diameter = fields.Char()
    unwinding_min_roll_diameter = fields.Char()
    unwinding_warnig_roll_diameter = fields.Char()
    unwinding_tension_top_limit = fields.Char()
    unwinding_tension_bottom_limit = fields.Char()

    upper_unwinding_measured_roll_diameter = fields.Char()
    upper_unwinding_max_roll_diameter = fields.Char()
    upper_unwinding_min_roll_diameter = fields.Char()
    upper_unwinding_warnig_roll_diameter = fields.Char()
    upper_unwinding_tension_top_limit = fields.Char()
    upper_unwinding_tension_bottom_limit = fields.Char()
    upper_unwinding_taper_type = fields.Char()
    upper_unwinding_taper_diameter = fields.Char()
    upper_unwinding_taper_coefficient = fields.Char()
    upper_unwinding_taper_value = fields.Char()

    lower_unwinding_measured_roll_diameter = fields.Char()
    lower_unwinding_max_roll_diameter = fields.Char()
    lower_unwinding_min_roll_diameter = fields.Char()
    lower_unwinding_warnig_roll_diameter = fields.Char()
    lower_unwinding_tension_top_limit = fields.Char()
    lower_unwinding_tension_bottom_limit = fields.Char()
    lower_unwinding_taper_type = fields.Char()
    lower_unwinding_taper_diameter = fields.Char()
    lower_unwinding_taper_coefficient = fields.Char()
    lower_unwinding_taper_value = fields.Char()

    calibration_of_roll_dia = fields.Char()
    front_end_calibration = fields.Char()
    rear_end_calibration = fields.Char()

    # motor parameter

    unwinding_shaft_related_speed = fields.Char()
    unwinding_shaft_reduction_ratio = fields.Char()
    unwinding_shaft_operation_parameter = fields.Char()
    unwinding_shaft_line_speed_setting = fields.Char()
    unwinding_shaft_rotation_speed_setting = fields.Char()

    traction_shaft_related_speed = fields.Char()
    traction_shaft_reduction_ratio = fields.Char()
    traction_shaft_operation_parameter = fields.Char()
    traction_shaft_line_speed_setting = fields.Char()
    traction_shaft_rotation_speed_setting = fields.Char()

    upper_cutter_shaft_related_speed = fields.Char()
    upper_cutter_shaft_reduction_ratio = fields.Char()
    upper_cutter_shaft_operation_parameter = fields.Char()
    upper_cutter_shaft_line_speed_setting = fields.Char()
    upper_cutter_shaft_rotation_speed_setting = fields.Char()

    lower_cutter_shaft_related_speed = fields.Char()
    lower_cutter_shaft_reduction_ratio = fields.Char()
    lower_cutter_shaft_operation_parameter = fields.Char()
    lower_cutter_shaft_line_speed_setting = fields.Char()
    lower_cutter_shaft_rotation_speed_setting = fields.Char()

    upper_rewinding_shaft_related_speed = fields.Char()
    upper_rewinding_shaft_reduction_ratio = fields.Char()
    upper_rewinding_shaft_operation_parameter = fields.Char()
    upper_rewinding_shaft_line_speed_setting = fields.Char()
    upper_rewinding_shaft_rotation_speed_setting = fields.Char()

    lower_rewinding_shaft_related_speed = fields.Char()
    lower_rewinding_shaft_reduction_ratio = fields.Char()
    lower_rewinding_shaft_operation_parameter = fields.Char()
    lower_rewinding_shaft_line_speed_setting = fields.Char()
    lower_rewinding_shaft_rotation_speed_setting = fields.Char()

    edge_shaft_related_speed = fields.Char()
    edge_shaft_reduction_ratio = fields.Char()
    edge_shaft_operation_parameter = fields.Char()
    edge_shaft_line_speed_setting = fields.Char()
    edge_shaft_rotation_speed_setting = fields.Char()

    brush_shaft_related_speed = fields.Char()
    brush_shaft_reduction_ratio = fields.Char()
    brush_shaft_operation_parameter = fields.Char()
    brush_shaft_line_speed_setting = fields.Char()
    brush_shaft_rotation_speed_setting = fields.Char()

    accelerate_time = fields.Char()
    decelerate_time = fields.Char()
    fast_decelerate_time = fields.Char()
    max_line_speed = fields.Char()
    rewinding_accelerate_time = fields.Char()
    rewinding_decelerate_time = fields.Char()
    meter_count_coefficient = fields.Char()
    proximity_roller_speed = fields.Char()

