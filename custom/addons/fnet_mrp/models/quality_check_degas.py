from odoo import models, fields, api, _
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta






class QualityCheckDegas(models.Model):
    _name = 'quality.check.degas'
    _description = "Quality Check Degas"

    pcq_degas_id = fields.Many2one('quality.check.injection')

    # degas
    date_from = fields.Char('Time')
    sample_qty = fields.Integer()
    degas_final_cell_weight_actual = fields.Char(compute='get_model_values', string='STD')
    degas_final_cell_weight_observation = fields.Char(string='actual')
    degas_voltage_actual = fields.Char(compute='get_model_values', string='OCV-(STD)')
    degas_voltage_observance = fields.Char(string='OCV-(actual)')
    degas_trimming_actual = fields.Char(compute='get_model_values', string='SWAT-(STD)')
    degas_trimming_observance = fields.Char(string='SWAT-(actual)')
    degas_fd_t = fields.Char('T')
    degas_fd_w = fields.Char('W')
    degas_fd_l = fields.Char('L')
    tool_used = fields.Text('Tools Used')
    degas_remarks = fields.Text("Remarks")




    @api.depends('pcq_degas_id.model_id', 'pcq_degas_id.model_id.operation_ids')
    def get_model_values(self):
        for rec in self:
            # Degas

            rec.degas_final_cell_weight_actual = False
            rec.degas_voltage_actual = False
            rec.degas_trimming_actual = False

            # rec.fai_dimension_actual = False
            # rec.fai_cutoff_voltage_actual = False
            # rec.fai_ir_actual = False
            # rec.fai_visual_check_actual = False
            # clamp_baking_ids = self.env['cell.clamp.baking'].search([('model_id', '=', rec.model_id.id), ('state', '=', 'progress')], limit=1)
            if rec.pcq_degas_id.model_id.operation_ids:
                for operation in rec.pcq_degas_id.model_id.operation_ids:
                        if operation.type == 'degas':
                            rec.degas_trimming_actual = operation.trimming
                            rec.degas_voltage_actual = operation.voltage
                            rec.degas_final_cell_weight_actual = operation.final_cell_weight


    def name_get(self):
        result = []
        for rec in self:
            name = (rec.model_id.name or '')
            result.append((rec.id, name))
        return result