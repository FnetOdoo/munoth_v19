from odoo import models, fields, api, _
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta






class QualityCheckClambBanking(models.Model):
    _name = 'quality.check.cbf'
    _description = "Quality Check Clamb Baking Formation"




    pcq_cdf_id = fields.Many2one('quality.check.injection')

    date_from = fields.Char('Time')
    sample_qty = fields.Integer()
    cbf_heating_temperature_actual = fields.Char(compute='get_model_values',string='HT-(STD)')
    cbf_heating_temperature_observation = fields.Char(string='HT-(actual)')
    cbf_heating_pressure_actual = fields.Char(compute='get_model_values',string='HP-(STD)')
    cbf_heating_pressure_observation = fields.Char(string='HP-(actual)')

    cbf_dv_actual = fields.Char(compute='get_model_values',string='DV-(STD)')
    cbf_dv_observation = fields.Char(string='DV-(actual)')
    cbf_cv_actual = fields.Char(compute='get_model_values',string='CV-(STD)')
    cbf_cv_observation = fields.Char(string='CV-(actual)')
    cbf_ocv_actual = fields.Char(compute='get_model_values',string='OCV-(STD)')
    cbf_ocv_observation = fields.Char(string='OCV-(actual)')
    ht_cbf_remarks = fields.Text('Remarks')


    @api.depends('pcq_cdf_id.model_id', 'pcq_cdf_id.model_id.operation_ids')
    def get_model_values(self):
        for rec in self:
            # CBF
            rec.cbf_heating_temperature_actual = False
            rec.cbf_heating_pressure_actual = False
            rec.cbf_dv_actual = False
            rec.cbf_ocv_actual = False
            rec.cbf_cv_actual = False
            if rec.pcq_cdf_id.model_id.operation_ids:
                for operation in rec.pcq_cdf_id.model_id.operation_ids:
                        # 5.cell clamp baking
                        if operation.type == 'cell_clamp_baking':
                            rec.cbf_dv_actual=operation.charging_voltage
                            rec.cbf_cv_actual=operation.discharging_voltage
                            rec.cbf_ocv_actual=operation.ocv
                            rec.cbf_heating_temperature_actual = operation.heating_temperature
                            rec.cbf_heating_pressure_actual = operation.heating_pressure



    def name_get(self):
        result = []
        for rec in self:
            name = (rec.model_id.name or '')
            result.append((rec.id, name))
        return result