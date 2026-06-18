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

    time = fields.Datetime(string="Time") #Sample Data: 2025-02-19 10:18:48, 2025-02-19 10:18:50
    id_device = fields.Char(string="Device ID") #Sample Data: HB-ZYJ
    work_order_no = fields.Char(string="Work order number") #Sample Data: 02122024
    shift = fields.Char(string="Shift") #Sample Data: night_shift
    product_no = fields.Char(string="Product number") #Sample Data: 1260110 1c
    cell_barcode = fields.Char(string="Cell barcode") #Sample Data: M095111B01$0001536, M095111B01$0002449
    before_weight = fields.Char(string="Before the battery cell weighs") #Sample Data: 145.40, 145.79
    after_weight = fields.Char(string="After injection weighing") #Sample Data: 171.63, 173.21
    volume = fields.Char(string="Liquid injection volume") #Sample Data: 25.84, 27.81
    ok_ng = fields.Char(string="OK/NG") #Sample Data: OK, NG
    injection_needle = fields.Char(string="Injection Needle") #Sample Data: 3, 4
    lot_no = fields.Char(string="Electrolyte lot number") #Sample Data: HS3098

    number = fields.Char("Number") #Sample Data: 1, 2
    operator = fields.Char("Operator") #Sample Data: suresh, mahi
    vacuum = fields.Char("Vacuum") #Sample Data: 0
    temperature = fields.Char("Temperature") #Sample Data: 1502, 1527
    injection_cavity = fields.Char("Liquid injection cavity vacuum") #Sample Data: 50, 100
    seal_pressure = fields.Char("Seal head Pressure") #Sample Data: 414, 422
    sealing = fields.Char("Pre-sealing time") #Sample Data: 30
    pressure = fields.Char("Compressed air Pressure") #Sample Data: -7 -720
    pressure_holding_time = fields.Char("Pressure holding time") #Sample Data: -29, -442
    pre_sealed_vacuum = fields.Char("Pre-sealed vacuum") #Sample Data: -507 , -500
    seal_pressure_time = fields.Char("Pre-seal pressure holding time") #Sample Data: 0
    pressure_holding_time_inj = fields.Char("Pressure holding time of liquid injection chamber") #Sample Data: 0


class CellClampBakingLog(models.Model):
    _name = 'cell.clamp.baking.log'
    _description = 'Cell Clamp Baking Log'

    # ── New fields (previously missing) ─────────────────────────
    engineer_name      = fields.Char(string="Engineer Name")
    operator_name      = fields.Char(string="Operator Name")
    cycle_start_time   = fields.Char(string="Cycle Start Time")
    cycle_end_time     = fields.Char(string="Cycle End Time")
    oven_time          = fields.Char(string="Oven Time")
    oven_name          = fields.Char(string="Oven Name")

    step_time          = fields.Float(string="Step Time (Min)")
    start_time         = fields.Float(string="Start Time (Min)")
    end_time           = fields.Float(string="End Time (Min)")

    start_temp_left    = fields.Float(string="Start Temp Left (℃)")
    end_temp_left      = fields.Float(string="End Temp Left (℃)")
    start_temp_right   = fields.Float(string="Start Temp Right (℃)")
    end_temp_right     = fields.Float(string="End Temp Right (℃)")
    start_temp_avg     = fields.Float(string="Start Temp Avg (℃)")
    end_temp_avg       = fields.Float(string="End Temp Avg (℃)")

    start_pressure     = fields.Float(string="Start Pressure (kgf)")
    end_pressure       = fields.Float(string="End Pressure (kgf)")
    start_position     = fields.Float(string="Start Position (mm)")
    end_position       = fields.Float(string="End Position (mm)")

    # ── Existing fields ─────────────────────────────────────────
    unit               = fields.Char(string="Unit")
    step_no            = fields.Integer(string="Step No")
    step_status        = fields.Char(string="Step Status")

    start_voltage      = fields.Float(string="Start Voltage (mV)")
    end_voltage        = fields.Float(string="End Voltage (mV)")
    start_current      = fields.Float(string="Start Current (mA)")
    end_current        = fields.Float(string="End Current (mA)")
    start_capacity     = fields.Float(string="Start Capacity (mAH)")
    end_capacity       = fields.Float(string="End Capacity (mAH)")
    start_energy       = fields.Float(string="Start Energy (mWH)")
    end_energy         = fields.Float(string="End Energy (mWH)")

    mean_voltage       = fields.Float(string="Mean Volt (mV)")
    avg_voltage        = fields.Float(string="Average Volt (mV)")
    cc_time            = fields.Float(string="CC Time (Min)")
    cc_capacity        = fields.Float(string="CC Capacity (mAH)")
    cv_time            = fields.Float(string="CV Time (Min)")
    cv_capacity        = fields.Float(string="CV Capacity (mAH)")
    cc_percent         = fields.Float(string="CC Percent (%)")

    barcode            = fields.Char(string="Barcode")
    condition_end      = fields.Char(string="Condition of End")
    cycle_no           = fields.Integer(string="Cycle No")




