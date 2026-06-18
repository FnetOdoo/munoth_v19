from odoo import models, fields, api, _
from datetime import timedelta, datetime
from dateutil.relativedelta import relativedelta






class QualityCheckInjection(models.Model):
    _name = 'quality.check.injection'
    _description = "Quality Check Injection"




    date = fields.Date('Date')
    pcq_injection_ids = fields.One2many(
        'check.quality','pcq_injection_id')
    pcq_degas_ids =fields.One2many('quality.check.degas','pcq_degas_id')
    pcq_cdf_ids = fields.One2many(
        'quality.check.cbf', 'pcq_cdf_id')
    doc_no = fields.Char(copy=False, readonly=True, default=lambda x: _('New'), tracking=True,string='Doc No')



    model_id = fields.Many2one('product.model', 'Model')
    product_id = fields.Many2one(related='model_id.product_template_id', string='Product')

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if not vals.get('doc_no') or vals.get('doc_no') == _('New'):
                vals['doc_no'] = seq.next_by_code('quality.check.injection') or _('New')
        return super().create(vals_list)


    def name_get(self):
        result = []
        for rec in self:
            name = (rec.model_id.name or '')
            result.append((rec.id, name))
        return result


