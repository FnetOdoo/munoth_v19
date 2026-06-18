from odoo import api, fields, models

class CheckQuality(models.Model):
    _name = "check.quality"
    _description = "Check Quality"

    pcq_injection_id= fields.Many2one('quality.check.injection')
    # pcq_cdf_id=fields.Many2one('quality.check.cbf')
    # pcq_degas_id=fields.Many2one('quality.check.degas')
    date_from = fields.Char('Time')
    sample_qty = fields.Integer()


    injection_electrolyte_qty_actual = fields.Char(compute='get_model_values',string='STD')
    injection_electrolyte_qty_observation = fields.Char('actual')
    injection_cell_weight_before_filling_actual = fields.Char(compute='get_model_values',string='CWBI-(STD)')
    injection_cell_weight_before_filling_observation = fields.Char('CWBI-(actual)')
    injection_humidity_actual = fields.Char(compute='get_model_values')
    injection_humidity_observation = fields.Char()
    injection_vaccum_static_time_actual = fields.Char(compute='get_model_values')
    injection_vaccum_static_time_observation = fields.Char()
    injection_pressure_actual = fields.Char(compute='get_model_values')
    injection_pressure_observation = fields.Char()
    injection_sealing_temperature_actual = fields.Char(compute='get_model_values',string='STEMP-(STD)')
    injection_sealing_temperature_observation = fields.Char('STEMP-(actual)')
    injection_packing_time_actual = fields.Char(compute='get_model_values')
    injection_packing_time_observation = fields.Char()
    injection_side_sealing_pulling_force_actual = fields.Char(compute='get_model_values')
    injection_side_sealing_pulling_force_observation = fields.Char()
    injection_cell_weight_after_filling_actual = fields.Char(compute='get_model_values',string='CWAI-(STD)')
    injection_cell_weight_after_filling_observation = fields.Char(' CWAI-(actual)')
    injection_sealing_width = fields.Char('SW-(actual)')
    injection_sealing_width_actual = fields.Char(compute='get_model_values',string='SW-(STD)')
    injection_sealing_thickness = fields.Char('ST-(actual)')
    injection_sealing_thickness_actual = fields.Char(compute='get_model_values',string='ST-(STD)')
    injection_remarks = fields.Text('Remarks')

    @api.depends('pcq_injection_id.model_id', 'pcq_injection_id.model_id.operation_ids')
    def get_model_values(self):
        for rec in self:
            rec.injection_sealing_width_actual = False
            rec.injection_electrolyte_qty_actual = False
            rec.injection_cell_weight_before_filling_actual = False
            rec.injection_humidity_actual = False
            rec.injection_vaccum_static_time_actual = False
            rec.injection_pressure_actual = False
            rec.injection_sealing_temperature_actual = False
            rec.injection_packing_time_actual = False
            rec.injection_side_sealing_pulling_force_actual = False
            rec.injection_cell_weight_after_filling_actual = False
            rec.injection_sealing_thickness_actual = False
            if rec.pcq_injection_id.model_id.operation_ids:
                for operation in rec.pcq_injection_id.model_id.operation_ids:
                    # 3.injection
                    if operation.type == 'injection':
                        rec.injection_sealing_thickness_actual = operation.sealing_thickness
                        rec.injection_electrolyte_qty_actual = operation.electrolyte_qty
                        rec.injection_cell_weight_before_filling_actual = operation.cell_weight_before_filling
                        rec.injection_humidity_actual = operation.humidity
                        rec.injection_vaccum_static_time_actual = operation.vaccum_static_time
                        rec.injection_pressure_actual = operation.pressure
                        rec.injection_sealing_temperature_actual = operation.sealing_temperature
                        rec.injection_packing_time_actual = operation.packing_time
                        rec.injection_side_sealing_pulling_force_actual = operation.side_sealing_pulling_force
                        rec.injection_cell_weight_after_filling_actual = operation.cell_weight_after_filling
                        rec.injection_sealing_width_actual = operation.sealing_width



