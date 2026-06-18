from odoo import models, fields, api, _
from odoo.exceptions import ValidationError



class ProcessQualityCheck(models.Model):
    _name = 'process.quality.check'
    _description = 'Process Quality Check'
    _inherit = ['mail.thread']

    state = fields.Selection(
        [('draft', 'Draft'), ('request', 'Requested'), ('done', 'Done'), ('reject', 'Rejected'), ('cancel', 'Cancel')],
        string='Status', required=True, readonly=True,
        copy=False, tracking=True, default='draft')
    quality_time_start=fields.Float(string="Time",required=True,tracking=True,state={'done': [('readonly', True)]})
    quality_time_end=fields.Float(requried=True)
    process_date=fields.Date(string="Date",default=lambda self: fields.Date.today(),tracking=True,state={'done': [('readonly', True)]})
    part_no=fields.Char(string="Part No")
    part_desc=fields.Char(string="Part Description",state={'done': [('readonly', True)]})
    # product_model_id = fields.Many2one('product.model', string="Model")
    shift_process=fields.Char('Shift',tracking=True,state={'done': [('readonly', True)]})
    process_template_id = fields.Many2one('inspection.template', string="Process Quality Check Template",copy=False,required=True,state={'done': [('readonly', True)]})
    doc=fields.Char('Doc no',default=lambda x: _('New'), tracking=True,)
    process_line_ids = fields.One2many('stock.inspection.line', 'quality_check_id',required=True)
    opt_id = fields.Many2one('manufacturing.operation',string="Operation",required=True,state={'done': [('readonly', True)]})
    no_doc=fields.Char('Doc No')
    revision_date=fields.Date('Revision Date')
    revision_no=fields.Char('Revision No')
    other=fields.Char('Other',state={'done': [('readonly', True)]})
    origin = fields.Char("Source Document",required=True,state={'done': [('readonly', True)]})
    is_sent_alert = fields.Boolean()
    overall_quality_check = fields.Selection(
        [('pass', 'Pass'), ('fail', 'Fail'), ('pass_with_deviation', 'Pass with Deviation')],
        string='Overall Quality Check', required=True)
    text_process_line_ids = fields.One2many('stock.inspection.line', 'quality_check_id', string='Text Process Lines',compute='_compute_text_line_ids')
    numeric_process_line_ids = fields.One2many('stock.inspection.line', 'quality_check_id', string='NumericProcess Lines',compute='_compute_numeric_line_ids')


    @api.depends('process_line_ids')
    def _compute_text_line_ids(self):
        for rec in self:
            self.text_process_line_ids = False
            lines = []
            for item in self.process_template_id.item_ids.filtered(lambda x: x.field_type_view == 'text'):
                lines.append(
                    (0, 0, {
                        'name': item.name,
                        'parameter': item.parameter,
                        'field_type':item.field_type_view,
                        'from_value': item.from_value,
                        'to_value': item.to_value,
                        'sort': item.sort,
                        'test_method': item.test_method
                    }))

            rec.text_process_line_ids = lines

    @api.depends('process_line_ids')
    def _compute_numeric_line_ids(self):
        for rec in self:
            self.numeric_process_line_ids = False
            lines = []
            for item in self.process_template_id.item_ids.filtered(lambda x: x.field_type_view == 'numeric'):
                lines.append(
                    (0, 0, {
                        'name': item.name,
                        'parameter': item.parameter,
                        'field_type': item.field_type_view,
                        'from_value': item.from_value,
                        'to_value': item.to_value,
                        'sort': item.sort,
                        'test_method': item.test_method
                    }))

            rec.numeric_process_line_ids = lines

    def action_notify_production(self):
        subject = "%s's Probation Review" % self.employee_id.name
        body = """<p>Dear <strong>%s</strong>,</p>
                              <p>The Probation Review for %s has been approved. </br>
                              Further confirmation needed on approval for the probation period which ended on %s, Kindly confirm as soon as possible.</br></br>
                              Thank You.</br>
                              </p>
                              <div style="padding: 16px 8px 16px 8px;">
                                <a t-att-href= %s
                                   style="background-color: #875a7b; text-decoration: none; color: #fff; padding: 8px 16px 8px 16px; border-radius: 5px;">
                                    View Probation Review
                                </a>
                              </div>
                              <p>Sincerely,<br/>
                                 %s</p>""" % (
        self.employee_id.department_id.head_of_department.name, self.employee_id.name, self.probation_end_date,
        self.get_mail_url(), self.employee_id.parent_id.name)
        template_data = {
            'subject': subject,
            'body_html': body,
            'email_from': self.employee_id.parent_id.work_email,
            'email_to': self.employee_id.department_id.head_of_department.work_email,
        }
        self.message_post(body=body, subject=subject)
        template_id = self.env['mail.mail'].sudo().create(template_data)
        template_id.sudo().send()
        self.write({
            'state': 'manager_approve',
            'manager_sign': self.env.user.id,
            'manager_sign_date': fields.Datetime.now(),
            'is_sent_alert': True,
        })

    @api.model
    def default_get(self, fields):
        defaults = super(ProcessQualityCheck, self).default_get(fields)
        company_id = self.env.user.company_id or self.env['res.company'].search([])[0]
        defaults['no_doc'] = company_id.pqc_doc_no
        defaults['revision_no'] = company_id.pqc_rev_no
        defaults['revision_date'] = company_id.pqc_rev_date
        return defaults

    @api.onchange('process_template_id')
    def onchange_template_id(self):
        self.process_line_ids = False
        lines = []
        for item in self.process_template_id.item_ids.filtered(lambda x: x.field_type_view == 'numeric'):
            lines.append(
                (0, 0, {
                    'name': item.name,
                    'parameter': item.parameter,
                    'field_type':item.field_type_view,
                    'from_value': item.from_value,
                    'to_value': item.to_value,
                    'sort': item.sort,
                    'test_method': item.test_method
                }))
        self.process_line_ids = lines


    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if not vals.get('doc') or vals.get('doc') == _('New'):
                vals['doc'] = seq.next_by_code('process.quality.check') or _('New')
        return super().create(vals_list)

    def action_request(self):
        for rec in self:
            rec.write({
                'state': 'request',
            })

    def action_validate(self):
        for rec in self:
            for record in rec.process_line_ids:
                if not record.state or not record.sample_1 or not record.sample_2 or not record.sample_3 or not record.sample_4 or not record.sample_5 :
                    raise ValidationError(_("Please fill all the status and sample."))
            if rec.overall_quality_check == 'fail':
                raise ValidationError(
                    _("You have selected 'Fail' in the 'Overall Quality Check' field, so you can only reject this form. You cannot approve this PQC."))
            rec.write({
                'state': 'done',
            })

    def action_reject(self):
        for rec in self:
            rec.write({
                'state': 'reject',
            })

    def action_cancel(self):
        for rec in self:
            rec.write({
                'state': 'cancel',
            })

    def action_reset(self):
        for rec in self:
            rec.write({
                'state': 'draft'
            })

