from odoo import models, fields, api, _


class ComplaintRegister(models.Model):
    _name='complaint.register'
    _description='Complaint Register'

    name=fields.Char(default=lambda x: _('New'), tracking=True)
    customer_id=fields.Many2one('res.partner',string='Customer',required=True)
    customer_loc_street=fields.Char(string='Street')
    customer_loc_street2=fields.Char(string='Street2')
    customer_city=fields.Char(string='City')
    customer_country=fields.Many2one('res.country',string='Country')
    customer_state = fields.Many2one('res.country.state',string='State')
    customer_zip=fields.Char(string='Zip')
    product_id = fields.Many2one('product.product', string="Product")
    product_model_id = fields.Many2one('product.model', string="Model")
    modality=fields.Selection([('in_person','In Person'),('system','Communication via Call or Email')])
    call_date=fields.Datetime(string='Call Date',default=fields.Datetime.now)
    # call_status=fields.Selection([('yes','Yes'),('no','No')],string="Call Received")
    received_on=fields.Date('Received On')
    completed_on=fields.Date('Completed On')
    complaint_details=fields.Text()
    lot_qty=fields.Float(string='Lot Quantity')
    defect_qty=fields.Float(string='Defect Quantity')
    repeated_complain=fields.Selection([('yes','Yes'),('no','No')])
    attended_by=fields.Many2one('res.users')
    call_solved=fields.Selection([('in_person','In Person'),('remote','Remote')],string='Call Solved')
    status=fields.Selection([('in_progress','In Progress'),('completed','Completed'),('in_completed','In Completed'),('yet','Yet to do')],string='Call Closure Status')
    remark=fields.Text()
    doc_no = fields.Char('Doc No')
    date_revision = fields.Date('Revision Date')
    no_revision = fields.Char('Revision No')

    @api.model
    def default_get(self, fields):
        defaults = super(ComplaintRegister, self).default_get(fields)
        company_id = self.env.user.company_id or self.env['res.company'].search([])[0]
        defaults['doc_no'] = company_id.ccr_doc_no
        defaults['no_revision'] = company_id.ccr_rev_no
        defaults['date_revision'] = company_id.ccr_rev_date
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'complaint.register'
                ) or _('New')
        return super().create(vals_list)

    @api.onchange('customer_id')
    def onchange_customer_address(self):
        if self.customer_id:
            self.customer_loc_street = self.customer_id.street
            self.customer_loc_street2 = self.customer_id.street2
            self.customer_city = self.customer_id.city
            self.customer_country = self.customer_id.country_id
            self.customer_state = self.customer_id.state_id
            self.customer_zip = self.customer_id.zip









