from odoo import models, fields, api, _
import datetime
from lxml import etree
class ManufacturingOperation(models.Model):
    _name = 'manufacturing.operation'
    _description = 'Manufacturing Operation'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = ""

    next_operation_id             = fields.Many2one('manufacturing.operation')
    bom_id                        = fields.Many2one('manufacturing.bom')
    manufacturing_stages_id       = fields.Many2one('manufacturing.stages')
    manufacturing_process_type_id = fields.Many2one('manufacturing.process.type')
    is_power_bank                 = fields.Boolean(related='manufacturing_process_type_id.is_power_bank')

    type = fields.Selection([
        ('anode_slitting',          'Anode Slitting'),
        ('cathode_slitting',        'Cathode Slitting'),
        ('anode_drying',            'Anode Drying'),
        ('cathode_drying',          'Cathode Drying'),
        ('diaphragm_drying',        'Diaphragm Drying'),
        ('anode_electrode_making',  'Anode Electrode Making'),
        ('cathode_electrode_making','Cathode Electrode Making'),
        ('winding',                 'Winding'),
        ('hot_press_jelly',         'Hot Press Jelly'),
        ('assembly',                'Assembly'),
        ('qr_code_print',           'QR Code Printing'),
        ('cell_drying',             'Cell Drying'),
        ('injection',               'Injection'),
        ('high_temperature',        'High Temperature'),
        ('cell_clamp_baking',       'Cell Clamp Baking'),
        ('ht_clamp_baking',         'HT + Cell Clamp Baking'),
        ('aged_formation_cell',     'Aged Formation Cell'),
        ('degas',                   'Degas'),
        ('dsf',                     'Double Side Folding'),
        ('pad_printing',            'Pad Printing'),
        ('capacity_test',           'Capacity Test'),
        ('voltage_test',            'Voltage Test'),
        ('aged_formation_cell_2',   'Aged Formation Cell 2'),
        ('voltage_test_2',          'Voltage Test 2'),
        ('packing',                 'Packing'),
        ('powerbank',               'Power Bank'),
    ])

    show_injection        = fields.Boolean(related='manufacturing_process_type_id.show_injection',        store=True)
    show_degas            = fields.Boolean(related='manufacturing_process_type_id.show_degas',            store=True)
    show_packing          = fields.Boolean(related='manufacturing_process_type_id.show_packing',          store=True)
    show_cell_drying      = fields.Boolean(related='manufacturing_process_type_id.show_cell_drying',      store=True)
    show_high_temperature = fields.Boolean(related='manufacturing_process_type_id.show_high_temperature', store=True)
    show_cell_clamp_baking= fields.Boolean(related='manufacturing_process_type_id.show_cell_clamp_baking',store=True)
    show_capacity_test    = fields.Boolean(related='manufacturing_process_type_id.show_capacity_test',    store=True)
    show_voltage_test     = fields.Boolean(related='manufacturing_process_type_id.show_voltage_test',     store=True)
    show_pad_printing     = fields.Boolean(related='manufacturing_process_type_id.show_pad_printing',     store=True)
    show_aged_formation_1 = fields.Boolean(related='manufacturing_process_type_id.show_aged_formation_1', store=True)
    show_aged_formation_2 = fields.Boolean(related='manufacturing_process_type_id.show_aged_formation_2', store=True)
    show_slitting         = fields.Boolean(related='manufacturing_process_type_id.show_slitting_process', store=True)
    show_drying           = fields.Boolean(related='manufacturing_process_type_id.show_drying_process',   store=True)
    # type_id = fields.Many2one('bom.operation.type', 'Operation Type')

    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        default=lambda self: self.env.company)
    location_src_id = fields.Many2one('stock.location')
    location_dest_id = fields.Many2one('stock.location')
    location_reject_id = fields.Many2one('stock.location', string="Rejected Location")
    production_location_id = fields.Many2one('stock.location')
    bom_ids = fields.One2many('operation.bom.line', 'operation_id')
    sequence = fields.Integer(index=True, default=1)

    product_id = fields.Many2one('product.product', related='bom_id.product_id')
    vendor_id = fields.Many2one('res.partner')

    process_duration = fields.Float()
    product_model_id = fields.Many2one('product.model')
    reference = fields.Char()
    stage = fields.Selection([
        ('stage_0', 'Process Type 0'),
        ('stage_1', 'Process Type 1'),
        ('stage_2', 'Process Type 2'),
        ('stage_3', 'Process Type 3'),
        ('stage_4', 'Process Type 4'),
        ('stage_5', 'Process Type 5'),
        ('stage_6', 'Process Type 6')], default='stage_1', help='Choose stage of going to production', string="From Stage")
    machine_id = fields.Many2one('manufacturing.machine', string="Default Machine")
    allow_lot_create = fields.Boolean('Allow lot creation')
    max_rework_count = fields.Integer('Maximum Allowed Rework', default=3)

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

    #motor parameter

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
   # Anode Cathode Drying
    dry_min_temperature = fields.Float()
    dry_max_temperature = fields.Float()
    dry_min_vacuum = fields.Float()
    dry_max_vacuum = fields.Float()
    # utility
    min_temperature = fields.Float()
    max_temperature = fields.Float()
    min_humidity = fields.Float()
    max_humidity = fields.Float()
    compressed_air=fields.Float()
    nitrogen=fields.Float()

    # cell drying
    temperature = fields.Float()
    temperature_uom = fields.Char(default="°C")
    hour = fields.Char()
    hour_uom = fields.Char(default="hr")
    vaccum = fields.Char()
    vaccum_reading_uom = fields.Char(default="kpa")


    # voltage
    voltage = fields.Float()
    resistance = fields.Float()



    #insulation resistance test
    voltage_resist=fields.Float()
    resist_set=fields.Float()
    time=fields.Float()

    #injection
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
    sealing_thickness=fields.Float()
    weight_before = fields.Float()
    weight_after = fields.Float()

    # degas
    sealing_time = fields.Float()
    vacuum_holding_time = fields.Float()
    weight_before_degas = fields.Float()
    weight_after_degas = fields.Float()
    trimming = fields.Float()
    folding = fields.Float()
    ironing_temperature = fields.Char()
    cavity_sealing = fields.Char()
    fine_sealing = fields.Char()
    final_cell_weight = fields.Char()

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
    cvc_test_2 = fields.Float()

    # quality_parameter

    # drying
    moisture_content = fields.Float()
    color_shading = fields.Char()
    visual_examination = fields.Char()

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
    electrolyte_qty = fields.Char('Electrolyte Quantity')
    cell_weight_before_filling = fields.Char()
    humidity = fields.Char()
    vaccum_static_time = fields.Char()
    pressure = fields.Char()
    sealing_temperature = fields.Char()
    packing_time = fields.Char()
    side_sealing_pulling_force = fields.Char()
    cell_weight_after_filling = fields.Char()

    # voltage
    ocv = fields.Float()
    ir = fields.Float()
    visual_examination = fields.Float()
    min_voltage = fields.Char()
    min_ohm = fields.Char()
    ocv_voltage = fields.Char('Voltage')
    ocv_resistance = fields.Char('Resistance')

    # capacity
    ccv_discharge_amps = fields.Float()
    ccv_discharge_volts = fields.Float()
    ccv_discharge_physical = fields.Char()
    capacity = fields.Char()

    # packing

    printing_defects = fields.Char()
    visual_appearence = fields.Float()
    dimension_check = fields.Float()
    qty_verification = fields.Char()
    visual_check = fields.Char()

    # degas
    voltage = fields.Float()
    resistance = fields.Float()

    # high temperature standing 1 & 2
    temperature = fields.Float()
    hour = fields.Char()
    temperature_two = fields.Float()
    hour_two = fields.Char()

    # clamp baking formation
    heating_temperature = fields.Char()
    heating_pressure = fields.Char()
    # pad printing
    symbol = fields.Char()
    standard = fields.Char()
    charging_voltage=fields.Float()
    discharging_voltage=fields.Float()
    ocv=fields.Float()
    #rt standing room - 1
    room_temperature = fields.Char('Temperature')
    room_hour = fields.Char('Time')
    #rt standing room - 2
    room_temperature_two = fields.Char('Temperature')
    room_hour_two = fields.Char('Time')

    display_name = fields.Char(compute='_compute_display_name', store=False)


    @api.model
    def fields_view_get(
            self,
            view_id=None,
            view_type='form',
            toolbar=False,
            submenu=False
    ):

        res = super().fields_view_get(
            view_id=view_id,
            view_type=view_type,
            toolbar=toolbar,
            submenu=submenu
        )

        if view_type != 'form':
            return res

        doc = etree.XML(res['arch'])

        process_id = self.env.context.get(
            'default_manufacturing_process_type_id'
        )

        if process_id:

            process = self.env[
                'manufacturing.process.type'
            ].browse(process_id)

            visible_fields = process.field_config_ids.filtered(
                lambda x: x.is_visible
            ).mapped('field_name')

            skip_fields = [
                'id',
                'display_name',
                'create_uid',
                'create_date',
                'write_uid',
                'write_date',
                '__last_update',
                'manufacturing_process_type_id'
            ]

            for node in doc.xpath("//field"):

                field_name = node.get('name')

                if field_name in skip_fields:
                    continue

                if field_name not in visible_fields:

                    node.set('invisible', '1')

        res['arch'] = etree.tostring(
            doc,
            encoding='unicode'
        )

        return res
    @api.depends('product_model_id.name', 'vendor_id.name', 'reference', 'type')
    def _compute_display_name(self):
        for rec in self:
            field = rec._fields['type']
            label = dict(field.selection).get(rec.type)
            name_parts = []

            if rec.product_model_id.name:
                name_parts.append(rec.product_model_id.name)
            if rec.vendor_id.name:
                name_parts.append(rec.vendor_id.name)
            if rec.reference:
                name_parts.append(rec.reference)
            if label:
                name_parts.append(label)

            rec.display_name = ' : '.join(name_parts) if name_parts else ''

    @api.model
    def _search_display_name(self, operator, value):
        domain = ['|', ('type', operator, value), ('reference', operator, value)]
        return domain

class ProductBom(models.Model):
    _name = 'operation.bom.line'
    _description = 'Operation BOM Line'

    def _get_default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id').id
    operation_id = fields.Many2one('manufacturing.operation')
    product_id = fields.Many2one('product.product')
    product_qty = fields.Float(
        'Quantity', default=1.0,
        digits='Product Unit of Measure', required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        default=_get_default_product_uom_id,
        required=True,
        help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control",
        domain="[('relative_uom_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.relative_uom_id')

    product_model_id = fields.Many2one('product.model')


class ManufacturingOperationLine(models.Model):
    _name = 'manufacturing.operation.line'
    _description = "Operation Line"
