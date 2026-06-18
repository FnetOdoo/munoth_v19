from odoo import models, api, fields, _
from odoo.exceptions import UserError


class EngineeringChangeRequest(models.Model):
    _name = "engineering.change.request"
    _description = 'Engineering Change Request'
    _inherit = ['mail.thread.cc', 'mail.activity.mixin']

    name = fields.Char('Reference', copy=False, readonly=True, default=lambda x: _('New'))
    eng_change_detail = fields.Char(string='Engineering Change Details')
    partner_id = fields.Many2one('res.partner',string='Initiated By')
    implement = fields.Selection([('immediate','Immediate'),('exhaust','On Exhaust of Inventory'),('start','Start of next batch')],string='Implementation')
    existing_stock = fields.Selection([('stock','Exhaust stock & change'),('use','Use 50/50'),('rework_use','Rework & Use'),('scrap','Scrap'),('not_applicable','Not applicable')],string='Action on Existing Stock')
    testing_done = fields.Selection([('verification','Verification by Engineering / QC'),('mechanical_safe','Mechanical Safety test by Engineering'),('electrical','Electrical / Safety tests by Engineering'),('validation','Verification / Validation by External Agency'),('other','Other')],string='Testing done')
    deliverables = fields.Selection([('ecn',' ECN Signed off'),('bom',' BOM'),('mechanical_drawings','Mechanical Drawings'),('label_artworks',' Label artworks'),('electrical_schematic','Electrical Schematic'),('sop_cp_wi_visuals',' SOP / CP / WI / Visuals'),('fqc','FQC'),('fai','FAI'),('packing','Packing & Accessories Checklist')],string='Deliverables')
    process = fields.Char(string = 'Process Revalidation only for special processes(if applicable)')
    backward_compatibility = fields.Selection([('yes','YES'),('no','NO')])
    backward_compatibility_details = fields.Char(string='Details')
    cft_reviewers = fields.Many2one('res.partner',string='CFT Reviewers')
    signing = fields.Selection([('engineering_npd','Engineering / NPD'),('manufacturing','Manufacturing'),('supply_chain','Supply Chain'),('qc','QC')],string='Signing authority for this ECN')
    cft_decision = fields.Selection([('approved','Approved'),('rejected','Rejected'),('on_hold','On hold')],string='CFT decision on this ECN')
    cft_comment=fields.Char()
    ecn = fields.Selection([('engineering_npd','Engineering / NPD'),('manufacturing','Manufacturing'),('supply_chain','Supply Chain'),('qc','QC')],string='ECN Distribution')
    doc_no = fields.Char(string='ECN')
    date_revision = fields.Date(string='ECN date')
    revision_no = fields.Char()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('engineering.change.request')
        return super().create(vals_list)
