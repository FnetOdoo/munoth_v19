from odoo import models, fields

class BatteryCellLog(models.Model):
    _name = 'battery.cell.log'
    _description = 'Battery Cell Log'

    serial_number = fields.Char(required=True, string="Serial number")
    creation_time = fields.Datetime(string="Creation time")
    model_br = fields.Char(string="Model")
    battery_voltage_v = fields.Float(string="Battery Voltage (V)")
    voltage_pass_ng_br = fields.Char(string="Voltage Pass/NG")
    battery_weight_pass_ng = fields.Char(string="Battery Weight Pass/NG")
    encapsulation_id_br = fields.Char(string="Encapsulation ID")
    vsn_br = fields.Char(string="VSN")
    equipment_number = fields.Char(string="Equipment number")
    bar_code_pass_ng_br = fields.Char(string="Bar Code Pass/NG")
    status_br = fields.Char("Status")

    bar_code = fields.Char("Barcode") #Sample Data:
    side_voltage = fields.Char("Side voltage (v)") #Sample Data: 0.08152, 0.02391
    side_voltage_ng = fields.Char("Side voltage Pass/NG") #Sample Data: OK
    battery_weight = fields.Char(string="Battery Weight") #Sample Data:
    residual_liquid = fields.Char(string="Residual liquid") #Sample Data:
    residual_liquid_ng = fields.Char(string="Residual liquid Pass/NG") #Sample Data:
    package_upper = fields.Char("Package upper head temperature")  # Sample Data: 184.9, 185.1
    encapsulation_lower = fields.Char("Encapsulated lower head temperature")  # Sample Data: 184.8, 185.0
    encapsulation_pre = fields.Char("Encapsulation pressure")  # Sample Data: 5.57, 5.44
    packaging_time = fields.Char("Packaging time")  # Sample Data: 5.0
    encapsulation_vacuum = fields.Char("Encapsulation vacuum")  # Sample Data: 89.8, 83.8
    vacuum_time = fields.Char("Vacuum time")  # Sample Data: 5.0
    on_seal = fields.Char("Temperature on fine seal")  # Sample Data:  185.8, 184.9
    under_seal = fields.Char("Temperature under fine seal")  # Sample Data: 186.6, 184.5
    time_seal = fields.Char("Fine sealing time")  # Sample Data: 6.0




class InjectionCellLog(models.Model):
    _name = 'injection.cell.log'
    _description = 'Injection Cell Log'

    # ── Serial / Identity
    serial_number               = fields.Char(string="Serial Number")
    creation_time               = fields.Char(string="Creation Time")
    model                       = fields.Char(string="Model")

    # ── Battery Serial Number
    battery_serial_number       = fields.Char(string="Battery Serial Number")
    battery_serial_pass_ng      = fields.Char(string="Battery Serial Number Pass/NG")
    scan_workstation_number     = fields.Char(string="Scan to Workstation Number")

    # ── Pre-injection Weight
    weight_before_injection     = fields.Float(string="Weight Before Injection (g)")
    weight_before_pass_ng       = fields.Char(string="Weight Before Injection Pass/NG")
    front_scale_position        = fields.Char(string="Front Scale Position Number")

    # ── Post-injection Weight
    back_weighing_time          = fields.Char(string="Back Weighing Time")
    weight_after_injection      = fields.Float(string="Weight After Injection (g)")
    weight_after_pass_ng        = fields.Char(string="Weight After Injection Pass/NG")
    back_scale_position         = fields.Char(string="Back Scale Position Number")

    # ── Injection Volume
    injection_volume            = fields.Float(string="Volume of Injection (g)")
    injection_volume_pass_ng    = fields.Char(string="Injection Volume Pass/NG")
    injection_needle_number     = fields.Char(string="Injection Needle Number")

    # ── Injection Cavity
    injection_cavity_vacuum     = fields.Float(string="Injection Cavity Vacuum (Kpa)")
    injection_cavity_pressure_time = fields.Float(string="Pressure Retention Time of Injection Cavity (s)")

    # ── Electrolyte
    electrolyte_batch_number    = fields.Char(string="Electrolyte Batch Number")

    # ── Standing Segments
    standing_vacuum_seg1        = fields.Float(string="First Segment Standing Vacuum (Kpa)")
    standing_pressure_time_seg1 = fields.Float(string="First Segment Standing Pressure Holding Time (s)")
    standing_vacuum_seg2        = fields.Float(string="Second Segment Standing Vacuum (Kpa)")
    standing_pressure_time_seg2 = fields.Float(string="Second Segment Standing Pressure Holding Time (s)")
    standing_vacuum_seg3        = fields.Float(string="Third Segment Standing Vacuum (Kpa)")
    standing_pressure_time_seg3 = fields.Float(string="Third Segment Standing Pressure Holding Time (s)")

    # ── Sealing
    sealing_station_number      = fields.Char(string="Sealing Station Number")
    sealing_left_temperature    = fields.Float(string="Sealing Left Temperature (℃)")
    sealing_right_temperature   = fields.Float(string="Sealing Right Temperature (℃)")
    sealing_pressure            = fields.Float(string="Sealing Pressure (Mpa)")
    sealing_time                = fields.Float(string="Sealing Time (s)")
    sealing_vacuum              = fields.Float(string="Sealing Vacuum (Kpa)")
    sealing_pressure_holding_time = fields.Float(string="Sealing Pressure Holding Time (s)")

    # ── Material Tray
    material_tray_position      = fields.Char(string="Material Tray Position Number")
    material_tray_code          = fields.Char(string="Material Tray Code")

    # ── Work Info
    work_order                  = fields.Char(string="Work Order")
    shift                       = fields.Char(string="Shift")
    equipment_number            = fields.Char(string="Equipment Number")
    operator                    = fields.Char(string="Operator")

    # ── Result
    overall_judgment_result     = fields.Char(string="Overall Judgment Result")
    ng_description              = fields.Char(string="NG Description")


class CellClampBakingLog(models.Model):
    _name = 'cell.clamp.baking.log'
    _description = 'Cell Clamp Baking Log (MES Formation)'

    # ── Session
    equipment_code       = fields.Char(string="Equipment Code")
    employee_no          = fields.Char(string="Employee No")
    schedule_start_time  = fields.Char(string="Schedule Start Time")
    schedule_end_time    = fields.Char(string="Schedule End Time")
    jig_num              = fields.Char(string="Jig Number")

    # ── Cell Info
    slot_id              = fields.Integer(string="Slot ID")
    barcode              = fields.Char(string="Barcode")
    pass_flag            = fields.Boolean(string="Pass Flag")

    # ── Step Info
    step_no              = fields.Integer(string="Step No")
    step_status          = fields.Char(string="Step Status")
    step_time            = fields.Char(string="Step Time")
    start_time           = fields.Char(string="Start Time")
    end_time             = fields.Char(string="End Time")
    alarm                = fields.Char(string="Alarm")

    # ── Electrical
    start_voltage        = fields.Float(string="Start Voltage")
    end_voltage          = fields.Float(string="End Voltage")
    start_current        = fields.Float(string="Start Current")
    end_current          = fields.Float(string="End Current")
    start_capacity       = fields.Float(string="Start Capacity")
    end_capacity         = fields.Float(string="End Capacity")
    start_energy         = fields.Float(string="Start Energy")
    end_energy           = fields.Float(string="End Energy")
    start_temp           = fields.Float(string="Start Temperature")
    end_temp             = fields.Float(string="End Temperature")
    end_position         = fields.Float(string="End Position")


class DegasMachineLog(models.Model):
    _name = 'degas.machine.log'
    _description = 'Degas Machine Log (二封机)'

    # ── Identity
    serial_number               = fields.Char(string="Serial Number")
    creation_time               = fields.Char(string="Creation Time")
    model                       = fields.Char(string="Model")
    battery_serial_number       = fields.Char(string="Battery Serial Number")
    scan_pass_ng                = fields.Char(string="Scan Pass/NG")
    scan_workstation_number     = fields.Char(string="Scan to Workstation Number")

    # ── Edge Resistance / Voltage
    edge_resistance             = fields.Float(string="Edge Resistance (MΩ)")
    edge_resistance_pass_ng     = fields.Char(string="Edge Resistance Pass/NG")
    voltage                     = fields.Float(string="Voltage (V)")
    edge_resistance_station     = fields.Char(string="Edge Resistance Measurement Workstation Number")
    edge_voltage                = fields.Float(string="Edge Voltage (V)")
    edge_voltage_pass_ng        = fields.Char(string="Edge Voltage Pass/NG")
    edge_voltage_station        = fields.Char(string="Edge Voltage Measurement Station Number")

    # ── Weight / Liquid
    battery_weight              = fields.Float(string="Battery Weight (g)")
    battery_weight_pass_ng      = fields.Char(string="Battery Weight Pass/NG")
    weighing_station            = fields.Char(string="Weighing Station Number")
    liquid_retention            = fields.Float(string="Liquid Retention Capacity (g)")
    liquid_retention_pass_ng    = fields.Char(string="Liquid Retention Pass/NG")

    # ── Sealing
    sealing_cavity_number       = fields.Char(string="Sealing Cavity Number")
    upper_sealing_temp          = fields.Float(string="Upper Sealing Head Temperature (℃)")
    lower_sealing_temp          = fields.Float(string="Lower Sealing Head Temperature (℃)")
    clamp_pressure              = fields.Float(string="Clamp Pressure (kgf)")
    sealing_pressure            = fields.Float(string="Sealing Pressure (Mpa)")
    sealing_time                = fields.Float(string="Sealing Time (s)")
    sealing_vacuum              = fields.Float(string="Sealing Vacuum Degree (Kpa)")
    vacuum_sealing_time         = fields.Float(string="Vacuum Sealing Time (s)")

    # ── Fine Sealing
    upper_fine_seal_temp        = fields.Float(string="Upper Fine Sealing Temperature (℃)")
    lower_fine_seal_temp        = fields.Float(string="Lower Fine Sealing Temperature (℃)")
    fine_sealing_time           = fields.Float(string="Fine Sealing Time (s)")
    fine_sealing_pressure       = fields.Float(string="Fine Sealing Pressure (Mpa)")
    fine_sealing_station        = fields.Char(string="Fine Sealing Station Number")

    # ── Front Fold
    front_fold_upper_temp       = fields.Float(string="Upper Sealing Head Temperature on Front Folded Edge (℃)")
    front_fold_lower_temp       = fields.Float(string="Lower Sealing Head Temperature on Front Folded Edge (℃)")
    front_fold_time             = fields.Float(string="Front Fold Time (s)")
    front_fold_station          = fields.Char(string="Front Fold Station Number")

    # ── Back Fold
    back_fold_upper_temp        = fields.Float(string="Upper Sealing Head Temperature on Back Folded Edge (℃)")
    back_fold_lower_temp        = fields.Float(string="Lower Sealing Head Temperature on Back Folded Edge (℃)")
    back_fold_time              = fields.Float(string="Back Fold Time (s)")
    back_fold_station           = fields.Char(string="Back Fold Station Number")

    # ── Work Info
    work_order                  = fields.Char(string="Work Order")
    shift                       = fields.Char(string="Shift")
    equipment_number            = fields.Char(string="Equipment Number")
    operator                    = fields.Char(string="Operator")

    # ── Result
    overall_judgment_result     = fields.Char(string="Overall Judgment Result")
    ng_description              = fields.Char(string="NG Description")


class AssemblyMachineLog(models.Model):
    _name = 'assembly.machine.log'
    _description = 'Assembly Machine Log (包装机)'

    # ── Identity
    serial_number               = fields.Char(string="Serial Number")
    creation_time               = fields.Char(string="Creation Time")
    model                       = fields.Char(string="Model")
    battery_serial_number       = fields.Char(string="Battery Serial Number")
    battery_serial_pass_ng      = fields.Char(string="Battery Serial Number Pass/NG")
    vsn                         = fields.Char(string="VSN")

    # ── Tab / Film Resistance
    tab_alum_film_resistance    = fields.Float(string="Tab Aluminum Film Resistance (MΩ)")
    tab_alum_film_pass_ng       = fields.Char(string="Tab Aluminum Film Resistance Pass/NG")
    alum_film_station           = fields.Char(string="Aluminum Foil Resistance Measurement Station Number")
    tab_resistance              = fields.Float(string="Tab Resistance (MΩ)")
    tab_resistance_pass_ng      = fields.Char(string="Tab Resistance Pass/NG")
    tab_resistance_station      = fields.Char(string="Tab Resistance Measurement Station Number")

    # ── Top Seal
    top_seal_upper_temp         = fields.Float(string="Upper Top Seal Temperature (℃)")
    top_seal_lower_temp         = fields.Float(string="Lower Top Seal Temperature (℃)")
    top_seal_pressure           = fields.Float(string="Top Seal Pressure (Kgf)")
    top_seal_time               = fields.Float(string="Top Seal Time (s)")

    # ── Corner Seal
    corner_seal_upper_temp      = fields.Float(string="Upper Corner Sealing Temperature (℃)")
    corner_seal_lower_temp      = fields.Float(string="Lower Corner Sealing Temperature (℃)")
    corner_seal_time            = fields.Float(string="Corner Sealing Time (s)")

    # ── Side Seal
    side_seal_upper_temp        = fields.Float(string="Upper Side Sealing Temperature (℃)")
    side_seal_lower_temp        = fields.Float(string="Lower Side Sealing Temperature (℃)")
    side_seal_pressure          = fields.Float(string="Side Seal Pressure (Kgf)")
    side_seal_time              = fields.Float(string="Side Sealing Time (s)")

    # ── Work Info
    work_order                  = fields.Char(string="Work Order")
    alum_plastic_film_lot       = fields.Char(string="Aluminum Plastic Film Lot Number")
    shift                       = fields.Char(string="Shift")
    equipment_number            = fields.Char(string="Equipment Number")
    operator                    = fields.Char(string="Operator")

    # ── Result
    overall_judgment_result     = fields.Char(string="Overall Judgment Result")
    ng_description              = fields.Char(string="NG Description")



class OCVMachineLog(models.Model):
    _name = 'ocv.machine.log'
    _description = 'OCV Machine Log'

    # ── Session
    software                    = fields.Char(string="Software")
    employee_no                 = fields.Char(string="Employee No")
    current_time                = fields.Char(string="Current Time")

    # ── Equipment / Cell
    equipment_code              = fields.Char(string="Equipment Code")
    container                   = fields.Char(string="Container")
    slot_id                     = fields.Char(string="Slot ID")
    serial_no                   = fields.Char(string="Serial No")
    pass_flag                   = fields.Boolean(string="Pass Flag")

    # ── Parameters
    ocv_value                   = fields.Char(string="OCV Value")
    ocv_upper                   = fields.Char(string="OCV Upper Limit")
    ocv_lower                   = fields.Char(string="OCV Lower Limit")
    ocv_result                  = fields.Char(string="OCV Result")
    ocv_defect_code             = fields.Char(string="OCV Defect Code")

    ir_value                    = fields.Char(string="IR Value")
    ir_upper                    = fields.Char(string="IR Upper Limit")
    ir_lower                    = fields.Char(string="IR Lower Limit")
    ir_result                   = fields.Char(string="IR Result")
    ir_defect_code              = fields.Char(string="IR Defect Code")

    temp1_value                 = fields.Char(string="Temp1 Value")
    temp1_upper                 = fields.Char(string="Temp1 Upper Limit")
    temp1_lower                 = fields.Char(string="Temp1 Lower Limit")
    temp1_result                = fields.Char(string="Temp1 Result")
    temp1_defect_code           = fields.Char(string="Temp1 Defect Code")

    temp2_value                 = fields.Char(string="Temp2 Value")
    temp2_upper                 = fields.Char(string="Temp2 Upper Limit")
    temp2_lower                 = fields.Char(string="Temp2 Lower Limit")
    temp2_result                = fields.Char(string="Temp2 Result")
    temp2_defect_code           = fields.Char(string="Temp2 Defect Code")

    temp3_value                 = fields.Char(string="Temp3 Value")
    temp3_upper                 = fields.Char(string="Temp3 Upper Limit")
    temp3_lower                 = fields.Char(string="Temp3 Lower Limit")
    temp3_result                = fields.Char(string="Temp3 Result")
    temp3_defect_code           = fields.Char(string="Temp3 Defect Code")

    temp4_value                 = fields.Char(string="Temp4 Value")
    temp4_upper                 = fields.Char(string="Temp4 Upper Limit")
    temp4_lower                 = fields.Char(string="Temp4 Lower Limit")
    temp4_result                = fields.Char(string="Temp4 Result")
    temp4_defect_code           = fields.Char(string="Temp4 Defect Code")

    temp5_value                 = fields.Char(string="Temp5 Value")
    temp5_upper                 = fields.Char(string="Temp5 Upper Limit")
    temp5_lower                 = fields.Char(string="Temp5 Lower Limit")
    temp5_result                = fields.Char(string="Temp5 Result")
    temp5_defect_code           = fields.Char(string="Temp5 Defect Code")


class SlittingMachineLog(models.Model):
    _name = 'slitting.machine.log'
    _description = 'Slitting Machine Log (MES数据定义表)'

    # ── Manual Entry
    equipment_number        = fields.Char(string="Equipment Number")
    process_code            = fields.Char(string="Process Code")
    employee_id             = fields.Char(string="Employee ID")
    film_roll_number        = fields.Char(string="Film Roll Number")
    batch_code              = fields.Char(string="Batch Code")
    blade_set_number        = fields.Char(string="Blade Set Number")

    # ── Device Reading – General
    current_recipe          = fields.Char(string="Current Recipe")
    equipment_status        = fields.Float(string="Equipment Status")
    mes_status              = fields.Float(string="MES Status")
    production_rate         = fields.Float(string="Production Rate")
    current_output          = fields.Float(string="Current Output")

    # ── Device Reading – Tension
    unwind_tension          = fields.Float(string="Unwind Tension")
    tension_increase_up     = fields.Float(string="Increase the Tension Upwards")
    tension_reduce          = fields.Float(string="Reduce Tension")

    # ── Device Reading – Width
    total_electrode_width   = fields.Float(string="Total Width of the Electrode Sheet")
    extremity_width_1       = fields.Float(string="Extremity Width 1")
    extremity_width_2       = fields.Float(string="Extremity Width 2")
    extremity_width_3       = fields.Float(string="Extremity Width 3")
    extremity_width_4       = fields.Float(string="Extremity Width 4")
    extremity_width_5       = fields.Float(string="Extremity Width 5")
    extremity_width_6       = fields.Float(string="Extremity Width 6")
    material_zone_width_1   = fields.Float(string="Material Zone Width 1")
    material_zone_width_2   = fields.Float(string="Material Zone Width 2")
    material_zone_width_3   = fields.Float(string="Material Zone Width 3")
    material_zone_width_4   = fields.Float(string="Material Zone Width 4")
    material_zone_width_5   = fields.Float(string="Material Zone Width 5")
    material_zone_width_6   = fields.Float(string="Material Zone Width 6")
    material_zone_width_7   = fields.Float(string="Material Zone Width 7")
    material_zone_width_8   = fields.Float(string="Material Zone Width 8")

    # ── Fault Information
    fault_info_1            = fields.Integer(string="Fault Information 1")
    fault_info_2            = fields.Integer(string="Fault Information 2")
    fault_info_3            = fields.Integer(string="Fault Information 3")
    fault_info_4            = fields.Integer(string="Fault Information 4")
    fault_info_5            = fields.Integer(string="Fault Information 5")
    fault_info_6            = fields.Integer(string="Fault Information 6")
    fault_info_7            = fields.Integer(string="Fault Information 7")
    fault_info_8            = fields.Integer(string="Fault Information 8")


class DryingOvenLog(models.Model):
    _name = 'drying.oven.log'
    _description = 'Drying Oven Log (Electrode & Cell)'

    oven_type                 = fields.Char(string="Oven Type")
    product_barcode           = fields.Char(string="Product Barcode")
    baking_start_time         = fields.Char(string="Baking Start Time")
    baking_end_time           = fields.Char(string="Baking End Time")
    baking_result_moisture    = fields.Char(string="Baking Result (Moisture)")
    tray_no                   = fields.Char(string="Tray No. during Baking")
    oven_shelf_no             = fields.Char(string="Oven Shelf No. during Baking")
    tray_position             = fields.Char(string="Position on Tray during Baking")
    oven_id                   = fields.Char(string="Oven ID during Baking")
    scheduled_baking_duration = fields.Char(string="Scheduled Baking Duration")
    baking_serial_no          = fields.Char(string="Baking Serial No.")
    oven_realtime_temp        = fields.Float(string="Oven Real-time Temperature")
    current_process_stage     = fields.Char(string="Current Process Stage")



class WindingMachineLog(models.Model):
    _name = 'winding.machine.log'
    _description = 'Winding Machine Log (SZB_SFC_DATA / SZB_PROCESS_DATA / SZB_BOM_DATA)'

    # ── Record Type (sfc / process / bom)
    record_type  = fields.Char(string="Record Type (sfc / process / bom)")

    # ── Common Header (shared by SFC and Process)
    SFC          = fields.Char(string="Cell Barcode")
    SFC_1        = fields.Char(string="Electrode Barcode")
    MODEL        = fields.Char(string="Production Model")
    BATCH        = fields.Char(string="Production Batch Number")
    result       = fields.Char(string="Judgment Result (OK/NG)")
    user_name    = fields.Char(string="Operator User ID")
    test_time    = fields.Char(string="Data Acquisition Time")
    create_time  = fields.Char(string="Data Write Time to DB")
    NG_CODE      = fields.Char(string="Bad Code")

    # ── BOM / Feeding Fields (SZB_BOM_DATA)
    DATA01 = fields.Char(string="Feeding Time")
    DATA02 = fields.Char(string="Feeding User")
    DATA03 = fields.Char(string="Cell Model")
    DATA04 = fields.Char(string="Battery Cell Batch Number")
    DATA05 = fields.Char(string="Cell Barcode (BOM)")
    DATA06 = fields.Char(string="Jier Barcode")
    DATA07 = fields.Char(string="Material Loading Station")
    DATA08 = fields.Char(string="Material Batch")
    DATA09 = fields.Char(string="Material Number")
    DATA10 = fields.Char(string="Material Description")
    DATA11 = fields.Char(string="Device ID")
    DATA12 = fields.Char(string="Material Barcode / Neg tab film upper edge to electrode edge (mm)")

    # ── SFC Data Fields (SZB_SFC_DATA – Neg tab/tape)
    DATA13  = fields.Char(string="Neg tab protective adhesive beyond top (mm)")
    DATA14  = fields.Char(string="Neg tab protective adhesive beyond bottom (mm)")
    DATA15  = fields.Char(string="Neg electrode front 2 from top of sheet")
    DATA16  = fields.Char(string="Neg electrode front 2 from bottom of sheet")
    DATA17  = fields.Char(string="Tape beyond top of neg electrode side (mm)")
    DATA18  = fields.Char(string="Tape beyond bottom of neg electrode side (mm)")
    DATA19  = fields.Char(string="Neg side tape beyond top of sheet 2")
    DATA20  = fields.Char(string="Neg side tape beyond bottom of sheet 2")

    # ── SFC – Pos tab/tape
    DATA22  = fields.Char(string="Pos tab film upper edge to electrode edge (mm)")
    DATA23  = fields.Char(string="Pos tab tape beyond insulating sheet (mm)")
    DATA24  = fields.Char(string="Pos tab tape beyond insulating sheet 2 (mm)")
    DATA25  = fields.Char(string="Tape beyond bottom of pos tab (mm)")
    DATA26  = fields.Char(string="Pos/neg tab tape beyond bottom of electrode (mm)")
    DATA27  = fields.Char(string="Pos tab to edge of tab tape (mm)")
    DATA28  = fields.Char(string="Pos tab to edge of tab tape 2 (mm)")
    DATA29  = fields.Char(string="Pos electrode front-side tape cover material (mm)")
    DATA30  = fields.Char(string="Tape cover at rear end of pos electrode front (mm)")
    DATA31  = fields.Char(string="Pos electrode reverse side tape cover (mm)")
    DATA32  = fields.Char(string="Tape cover at reverse side rear of pos electrode (mm)")
    DATA33  = fields.Char(string="Tape beyond top of pos electrode front (mm)")
    DATA34  = fields.Char(string="Tape beyond bottom of pos electrode front (mm)")
    DATA35  = fields.Char(string="Tape beyond top of pos electrode reverse (mm)")
    DATA36  = fields.Char(string="Tape beyond bottom of pos electrode reverse (mm)")
    DATA37  = fields.Char(string="Tape beyond top at rear of pos electrode front (mm)")
    DATA38  = fields.Char(string="Tape beyond bottom at rear of pos electrode front (mm)")
    DATA39  = fields.Char(string="Tape beyond top at rear of pos electrode reverse (mm) / Diaphragm single roll length")
    DATA40  = fields.Char(string="Tape beyond bottom at rear of pos electrode reverse (mm)")

    # ── SFC – Uniformity
    DATA41  = fields.Char(string="Max distance: pos electrode to separator (mm)")
    DATA42  = fields.Char(string="Min distance: pos electrode to separator (mm)")
    DATA43  = fields.Char(string="Max distance: neg electrode to separator (mm)")
    DATA44  = fields.Char(string="Min distance: neg electrode to separator (mm)")
    DATA45  = fields.Char(string="Max distance: neg to pos electrode (mm) / Diaphragm single roll speed")
    DATA46  = fields.Char(string="Min distance: neg to pos electrode (mm) / Electrode single roll speed")

    # ── SFC – High voltage
    DATA47  = fields.Char(string="High-voltage impulse voltage (V)")
    DATA48  = fields.Char(string="High-pressure impact time during winding (s)")
    DATA49  = fields.Char(string="Withstand voltage test leakage current (mA) / Main winding neg initial winding angle")
    DATA50  = fields.Char(string="Main winding pos initial winding angle")
    DATA51  = fields.Char(string="Initial winding speed (neg pole)")
    DATA52  = fields.Char(string="Main winding speed")
    DATA53  = fields.Char(string="Initial roll speed (pos pole)")

    # ── SFC – Electrode core
    DATA56  = fields.Char(string="Pos tab left film exposed height (mm)")
    DATA57  = fields.Char(string="Pos tab right film exposed height (mm)")
    DATA58  = fields.Char(string="Neg tab left film exposed height (mm)")
    DATA59  = fields.Char(string="Neg tab right film exposed height (mm)")
    DATA60  = fields.Char(string="Positive electrode ear distance (mm)")
    DATA61  = fields.Char(string="Negative electrode ear distance (mm)")
    DATA62  = fields.Char(string="Core width (mm)")

    # ── SFC – Pos-to-separator distances 1–30
    DATA64=fields.Char(string="Pos to separator 1 (mm)"); DATA65=fields.Char(string="Pos to separator 2 (mm)")
    DATA66=fields.Char(string="Pos to separator 3 (mm)"); DATA67=fields.Char(string="Pos to separator 4 (mm)")
    DATA68=fields.Char(string="Pos to separator 5 (mm)"); DATA69=fields.Char(string="Pos to separator 6 (mm) / Current value: neg cutting plate upper blade")
    DATA70=fields.Char(string="Pos to separator 7 (mm) / Current value: neg cutting plate lower blade")
    DATA71=fields.Char(string="Pos to separator 8 (mm) / Current value: pos cutting plate upper blade")
    DATA72=fields.Char(string="Pos to separator 9 (mm) / Current value: pos cutting blade")
    DATA73=fields.Char(string="Pos to separator 10 (mm) / Service life: neg cutting plate upper blade")
    DATA74=fields.Char(string="Pos to separator 11 (mm) / Service life: neg cutting blade")
    DATA75=fields.Char(string="Pos to separator 12 (mm) / Service life: pos cutting plate upper blade")
    DATA76=fields.Char(string="Pos to separator 13 (mm) / Service life: pos lower cutter")
    DATA77=fields.Char(string="Pos to separator 14 (mm)"); DATA78=fields.Char(string="Pos to separator 15 (mm)")
    DATA79=fields.Char(string="Pos to separator 16 (mm)"); DATA80=fields.Char(string="Pos to separator 17 (mm)")
    DATA81=fields.Char(string="Pos to separator 18 (mm) / Upper limit: lower diaphragm main winding tension")
    DATA82=fields.Char(string="Pos to separator 19 (mm) / Lower limit: lower diaphragm main winding tension")
    DATA83=fields.Char(string="Pos to separator 20 (mm) / Upper limit: neg electrode main winding tension")
    DATA84=fields.Char(string="Pos to separator 21 (mm) / Upper limit: upper diaphragm main winding tension")
    DATA85=fields.Char(string="Pos to separator 22 (mm) / Lower limit: neg electrode main winding tension")
    DATA86=fields.Char(string="Pos to separator 23 (mm) / Lower limit: upper diaphragm main winding tension")
    DATA87=fields.Char(string="Pos to separator 24 (mm) / Upper limit: pos electrode main winding tension")
    DATA88=fields.Char(string="Pos to separator 25 (mm) / Lower limit: pos electrode main winding tension")
    DATA89=fields.Char(string="Pos to separator 26 (mm) / Upper diaphragm pre-wound setting tension")
    DATA90=fields.Char(string="Pos to separator 27 (mm)"); DATA91=fields.Char(string="Pos to separator 28 (mm)")
    DATA92=fields.Char(string="Pos to separator 29 (mm)"); DATA93=fields.Char(string="Pos to separator 30 (mm)")

    # ── SFC – Neg-to-separator distances 1–30
    DATA94=fields.Char(string="Neg to separator 1 (mm) / Upper diaphragm main winding tension setting")
    DATA95=fields.Char(string="Neg to separator 2 (mm)"); DATA96=fields.Char(string="Neg to separator 3 (mm)")
    DATA97=fields.Char(string="Neg to separator 4 (mm)"); DATA98=fields.Char(string="Neg to separator 5 (mm)")
    DATA99=fields.Char(string="Neg to separator 6 (mm)")
    DATA100=fields.Char(string="Neg to separator 7 (mm) / Lower diaphragm pre-wound tension setting")
    DATA101=fields.Char(string="Neg to separator 8 (mm)"); DATA102=fields.Char(string="Neg to separator 9 (mm)")
    DATA103=fields.Char(string="Neg to separator 10 (mm)"); DATA104=fields.Char(string="Neg to separator 11 (mm)")
    DATA105=fields.Char(string="Neg to separator 12 (mm) / Lower diaphragm main winding tension setting")
    DATA106=fields.Char(string="Neg to separator 13 (mm)"); DATA107=fields.Char(string="Neg to separator 14 (mm)")
    DATA108=fields.Char(string="Neg to separator 15 (mm)"); DATA109=fields.Char(string="Neg to separator 16 (mm)")
    DATA110=fields.Char(string="Neg to separator 17 (mm)"); DATA111=fields.Char(string="Neg to separator 18 (mm)")
    DATA112=fields.Char(string="Neg to separator 19 (mm) / Neg electrode pre-winding tension setting")
    DATA113=fields.Char(string="Neg to separator 20 (mm)"); DATA114=fields.Char(string="Neg to separator 21 (mm)")
    DATA115=fields.Char(string="Neg to separator 22 (mm)")
    DATA116=fields.Char(string="Neg to separator 23 (mm) / Neg main winding tension setting")
    DATA117=fields.Char(string="Neg to separator 24 (mm)"); DATA118=fields.Char(string="Neg to separator 25 (mm)")
    DATA119=fields.Char(string="Neg to separator 26 (mm)"); DATA120=fields.Char(string="Neg to separator 27 (mm)")
    DATA121=fields.Char(string="Neg to separator 28 (mm)"); DATA122=fields.Char(string="Neg to separator 29 (mm)")
    DATA123=fields.Char(string="Neg to separator 30 (mm) / Pos pre-winding tension setting")

    # ── SFC – Neg-to-pos distances 1–30
    DATA124=fields.Char(string="Neg to pos 1 (mm)"); DATA125=fields.Char(string="Neg to pos 2 (mm)")
    DATA126=fields.Char(string="Neg to pos 3 (mm)"); DATA127=fields.Char(string="Neg to pos 4 (mm) / Pos main winding tension setting")
    DATA128=fields.Char(string="Neg to pos 5 (mm)"); DATA129=fields.Char(string="Neg to pos 6 (mm)")
    DATA130=fields.Char(string="Neg to pos 7 (mm)"); DATA131=fields.Char(string="Neg to pos 8 (mm)")
    DATA132=fields.Char(string="Neg to pos 9 (mm)")
    DATA133=fields.Char(string="Neg to pos 10 (mm) / Upper diaphragm turret tension setting")
    DATA134=fields.Char(string="Neg to pos 11 (mm) / Lower diaphragm turret tension setting")
    DATA135=fields.Char(string="Neg to pos 12 (mm) / Neg turret setting tension")
    DATA136=fields.Char(string="Neg to pos 13 (mm) / Pos turret setting tension")
    DATA137=fields.Char(string="Neg to pos 14 (mm) / Warning lifespan: neg cutting plate upper blade")
    DATA138=fields.Char(string="Neg to pos 15 (mm) / Warning lifespan: neg cutting blade")
    DATA139=fields.Char(string="Neg to pos 16 (mm) / Warning lifespan: pos cutting plate upper blade")
    DATA140=fields.Char(string="Neg to pos 17 (mm) / Warning lifespan: pos cutting blade")
    DATA141=fields.Char(string="Neg to pos 18 (mm)"); DATA142=fields.Char(string="Neg to pos 19 (mm)")
    DATA143=fields.Char(string="Neg to pos 20 (mm)"); DATA144=fields.Char(string="Neg to pos 21 (mm)")
    DATA145=fields.Char(string="Neg to pos 22 (mm) / Warning lifespan: neg electrode welding tip")
    DATA146=fields.Char(string="Neg to pos 23 (mm) / Warning lifespan: pos electrode welding tip")
    DATA147=fields.Char(string="Neg to pos 24 (mm) / Warning lifespan: neg electrode tab cutter")
    DATA148=fields.Char(string="Neg to pos 25 (mm) / Warning lifespan: neg adhesive 1 lower cutter")
    DATA149=fields.Char(string="Neg to pos 26 (mm) / Warning lifespan: neg adhesive 2 upper blade")
    DATA150=fields.Char(string="Neg to pos 27 (mm) / Warning lifespan: neg adhesive 2 lower cutter")
    DATA151=fields.Char(string="Neg to pos 28 (mm) / Warning lifespan: pos electrode tab cutter")
    DATA152=fields.Char(string="Neg to pos 29 (mm) / Warning lifespan: pos adhesive 1 cutting blade")
    DATA153=fields.Char(string="Neg to pos 30 (mm) / Warning lifespan: pos adhesive 1 lower cutter")

    # ── SFC/Process – Shared DATA154 onwards
    DATA154=fields.Char(string="Warning lifespan: pos adhesive 2 upper blade")
    DATA155=fields.Char(string="Neg electrode plate length (mm) / Warning lifespan: pos adhesive 2 lower cutter")
    DATA156=fields.Char(string="Pos electrode front unfilled foil length (mm) / Warning lifespan: pos adhesive 3 upper blade")
    DATA157=fields.Char(string="Pos electrode plate length (mm) / Warning lifespan: pos adhesive 3 lower cutter")
    DATA158=fields.Char(string="Pos electrode reverse unfilled foil length (mm) / Pos electrode welding tip lifespan")
    DATA159=fields.Char(string="Pos electrode tab cutter lifespan")
    DATA160=fields.Char(string="Neg electrode front unfilled foil length (mm) / Lifespan: pos adhesive 1 upper blade")
    DATA161=fields.Char(string="Neg electrode reverse unfilled foil length (mm) / Lifespan: pos adhesive 1 lower cutter")
    DATA162=fields.Char(string="Pos electrode front coating length (mm) / Lifespan: pos adhesive 2 upper blade")
    DATA163=fields.Char(string="Pos electrode reverse coating length (mm) / Lifespan: pos adhesive 2 lower cutter")
    DATA164=fields.Char(string="Neg electrode front coating length (mm) / Lifespan: pos adhesive 3 upper blade")
    DATA165=fields.Char(string="Neg electrode reverse coating length (mm) / Lifespan: pos adhesive 3 lower cutter")
    DATA166=fields.Char(string="Pos electrode feeding QR code / Current value: pos electrode welding head")
    DATA167=fields.Char(string="Ear QR code level / Current value: pos electrode tab cutter")
    DATA168=fields.Char(string="Pos electrode barcode scanning failure / Current value: pos adhesive 1 lower cutter")
    DATA169=fields.Char(string="Shift (A: Day / B: Night) / Current value: pos adhesive 1 upper blade")
    DATA170=fields.Char(string="Number of qualified windings / Current value: pos adhesive 2 upper blade")
    DATA171=fields.Char(string="Pos electrode production number / Current value: pos adhesive 2 lower cutter")
    DATA172=fields.Char(string="Neg electrode production number / Current value: pos adhesive 3 upper blade")
    DATA173=fields.Char(string="Defective pos electrode single coil count / Current value: pos adhesive 3 lower cutter")
    DATA174=fields.Char(string="Defective neg electrode single roll count / Neg electrode welding tip lifespan")
    DATA175=fields.Char(string="Defective pos terminal count / Neg electrode tab cutter lifespan")
    DATA176=fields.Char(string="Defective neg terminal count / Lifespan: neg adhesive 1 upper blade")
    DATA177=fields.Char(string="Defective neg electrode blue label count / Lifespan warning: neg adhesive 1 upper blade")
    DATA178=fields.Char(string="Defective pos electrode blue label count / Lifespan: neg adhesive 1 lower cutter")
    DATA179=fields.Char(string="Defective pos electrode adhesive count / Lifespan: neg adhesive 2 upper blade")
    DATA180=fields.Char(string="Defective neg electrode adhesive count / Lifespan: neg adhesive 2 lower cutter")
    DATA181=fields.Char(string="High-pressure impact failure count / Current value: neg electrode welding head")
    DATA182=fields.Char(string="Termination tape defective count / Current value: neg electrode tab cutter")
    DATA183=fields.Char(string="Unevenness CCD defect count / Current value: neg adhesive 1 upper blade")
    DATA184=fields.Char(string="Defective data from loading tab barcode scan / Current value: neg adhesive 1 lower cutter")
    DATA185=fields.Char(string="Defective data from feed position barcode scan / Current value: neg adhesive 2 upper blade")
    DATA186=fields.Char(string="Equipment number (Labie) / Current value: neg adhesive 2 lower cutter")
    DATA187=fields.Char(string="Number of poor electrode spacing / Electrode length setting (pos electrode)")
    DATA189=fields.Char(string="Neg tab top to upper film edge")
    DATA191=fields.Char(string="Pos tab top to upper film edge")
    DATA193=fields.Char(string="Neg electrode tab exposed length")
    DATA194=fields.Char(string="Neg electrode front tape to slurry pulling edge (mm)")
    DATA195=fields.Char(string="Neg electrode reverse tape to slurry pulling edge (mm)")
    DATA198=fields.Char(string="Pos electrode tab exposed length")
    DATA199=fields.Char(string="Process standards")
    DATA200=fields.Char(string="Equipment adjustment flag (1=adjusting, 0=normal)")
    DATA201=fields.Char(string="Neg electrode feeding QR code")
    DATA202=fields.Char(string="Reserved")
    DATA203=fields.Char(string="Neg protective adhesive 1 overlap with electrode (mm)")
    DATA204=fields.Char(string="Neg protective adhesive 2 overlap with electrode (mm)")
    DATA205=fields.Char(string="Pos protective adhesive 1 overlap with electrode (mm)")
    DATA206=fields.Char(string="Pos protective adhesive 2 overlap with electrode (mm)")
    DATA207=fields.Char(string="Neg protective adhesive 1 beyond top (mm)")
    DATA208=fields.Char(string="Neg protective adhesive 1 beyond bottom (mm)")
    DATA209=fields.Char(string="Neg protective adhesive 2 beyond top (mm)")
    DATA210=fields.Char(string="Neg protective adhesive 2 beyond bottom (mm)")
    DATA211=fields.Char(string="Pos protective adhesive 1 beyond top (mm)")
    DATA212=fields.Char(string="Pos protective adhesive 1 beyond bottom (mm)")
    DATA213=fields.Char(string="Pos protective adhesive 2 beyond top (mm)")
    DATA214=fields.Char(string="Pos protective adhesive 2 beyond bottom (mm)")
    DATA215=fields.Char(string="Neg tab center adhesive 1 bottom cover (mm)")
    DATA216=fields.Char(string="Neg tab center adhesive 2 bottom cover (mm)")
    DATA217=fields.Char(string="Pos tab center adhesive 1 bottom cover (mm)")
    DATA218=fields.Char(string="Pos tab center adhesive 2 bottom cover (mm)")
    DATA219=fields.Char(string="Neg tab center adhesive 1 side cover (mm)")
    DATA220=fields.Char(string="Neg tab center adhesive side cover (mm)")
    DATA221=fields.Char(string="Pos tab center adhesive side cover (mm)")
    DATA222=fields.Char(string="Pos tab center side cover dimensions (mm)")
    DATA223=fields.Char(string="Winding state")
    DATA251=fields.Char(string="Electrode length measurement (pos electrode)")
    DATA256=fields.Char(string="Max tension value: upper diaphragm")
    DATA257=fields.Char(string="Min tension value: upper diaphragm")
    DATA258=fields.Char(string="Max tension value: lower diaphragm")
    DATA259=fields.Char(string="Min tension value: lower diaphragm")
    DATA260=fields.Char(string="Max tension: neg electrode")
    DATA261=fields.Char(string="Min tension: neg electrode")
    DATA262=fields.Char(string="Max tension: pos electrode")
    DATA263=fields.Char(string="Min tension: pos electrode")
    DATA277=fields.Char(string="Equipment adjustment flag (1=adjusting, 0=normal)")
    DATA278=fields.Char(string="Pos electrode grooving cutter lifespan")
    DATA279=fields.Char(string="Pos electrode slotting cutter warning lifespan")


class OCVMESLog(models.Model):
    _name = 'ocv.mes.log'
    _description = 'OCV MES Log (MES API - ProductionGroupInfo)'

    # ── Top-level fields
    machine_id   = fields.Char(string="Machine ID")
    group_code   = fields.Char(string="Group Code")
    test_result  = fields.Char(string="Test Result")
    timestamp    = fields.Char(string="Timestamp")
    product_sn   = fields.Char(string="Product SN")
    operator_id  = fields.Char(string="Operator ID")
    sn_type      = fields.Char(string="SN Type")
    ng_code      = fields.Char(string="NG Code")

    # ── TestData items (flattened from ItemCode/Value array)
    pallet            = fields.Char(string="Pallet")
    card              = fields.Char(string="Card")
    voltage           = fields.Char(string="Voltage")
    actual_voltage    = fields.Char(string="Actual Voltage")
    resistance        = fields.Char(string="Resistance")
    k_value           = fields.Char(string="K Value")
    temperature       = fields.Char(string="Temperature")
    end_date_time     = fields.Char(string="End Date Time")
    test_date         = fields.Char(string="Test Date")
