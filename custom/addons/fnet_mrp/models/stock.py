from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class StockLocation(models.Model):
    _inherit = 'stock.location'

    stock_location = fields.Boolean(string='Is Stock Location?')
    temporary_location = fields.Boolean()
    consumed_location = fields.Boolean()


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def compute_inspection_count(self):
        for rec in self:
            rec.inspection_count = self.env['stock.inspection'].search_count([('picking_id', '=', rec.id)])

    inspection_team_id = fields.Many2one('inspection.team', string="Inspection Team")
    is_inspection_enabled = fields.Boolean("Inspection Enabled?", compute="check_inspection")
    inspection_count = fields.Integer("Inspection Count", compute='compute_inspection_count')
    # mrp_material_request = fields.Many2one('mrp.material.request')


    def check_inspection(self):
        for rec in self:
            rec.is_inspection_enabled = False
            if any(line.product_id.enable_inspection for line in rec.move_ids):
                rec.is_inspection_enabled = True

    def action_open_inspection(self):
        type = 'incoming'
        if self.picking_type_id.code == 'outgoing':
            type = 'outgoing'
        cnx = {'default_picking_id': self.id, 'default_type': type, 'default_team_id': self.inspection_team_id.id}
        return {
            'name': _('Inspection'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'stock.inspection',
            'context': cnx,
            'domain': [('picking_id', '=', self.id)]
        }

    def action_request_inspection(self):
        type = 'incoming'
        if self.picking_type_id.code == 'outgoing':
            type = 'audit'
        if not self.inspection_team_id:
            raise UserError(_("Please select inspection team."))
        if not self.move_ids.filtered(lambda x: x.product_id.enable_inspection):
            raise UserError("Please enable inspection at least for one product in master.")
        for line in self.move_ids.filtered(lambda x: x.product_id.enable_inspection):
            inspection_id = self.env['stock.inspection'].search([('move_id', '=', line.id)])
            if inspection_id:
                continue
            inspection_id = self.env['stock.inspection'].create({
                'product_id': line.product_id.id,
                'partner_id': self.partner_id.id,
                'quantity': line.product_uom_qty,
                'template_id': line.product_id.default_inspection_template.id,
                'type': type,
                'team_id': self.inspection_team_id.id,
                'picking_id': self.id,
                'move_id': line.id

            })
            inspection_id.onchange_template_id()
            inspection_id.onchange_type()
            # inspection_id.action_submit()

    def button_validate(self):
        for rec in self:
            if not rec.picking_type_code == 'internal':
                for line in rec.move_line_ids.filtered(lambda x: x.product_id.enable_inspection):
                    inspection_id = self.env['stock.inspection'].search(
                        [('picking_id', '=', rec.id), ('product_id', '=', line.product_id.id)])
                    if not inspection_id:
                        raise UserError(
                            _("Please create inspection request for %s to complete this operation." % line.product_id.name))
                    if inspection_id.filtered(lambda x: x.state not in ['done', 'cancel']):
                        raise UserError(
                            _("Inspection is not yet completed. Please contact the specific quality team to finalize the inspection."))
        return super(StockPicking, self).button_validate()


class StockInspection(models.Model):
    _name = 'stock.inspection'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'sequence.mixin']
    _order = 'date desc, name desc, id desc'
    _description = 'Inspection'

    name = fields.Char(copy=False, readonly=True, default=lambda x: _('New'), tracking=True)
    type = fields.Selection([('incoming', 'Incoming'), ('outgoing', 'Outgoing'), ('audit', 'Doc Audit')],
                            default='incoming',
                            string="Inspection Type")
    state = fields.Selection(
        [('draft', 'Draft'), ('request', 'Requested'), ('verify', 'Verified'), ('done', 'Inspected'),
         ('cancel', 'Canceled')], string='Status', required=True, readonly=True, copy=False, tracking=True,
        default='draft')
    partner_id = fields.Many2one(
        'res.partner', string='Customer', check_company=True, index=True, tracking=10,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        help="Customer: Inspection for Outgoing\n Vendor: Inspection for Receiving ")
    product_model_id = fields.Many2one('product.model', string="Model")
    product_id = fields.Many2one('product.product', string="Product/Model")
    quantity = fields.Float('Lot Qty')
    purpose = fields.Char("Regular / Replacement / Sample")
    sample_qty = fields.Float("Sample Qty")
    part_number = fields.Char("Part Number")
    part_description = fields.Char("Part Description")
    date_done = fields.Date("Inspected Date")
    date = fields.Date("Request Date")
    rev_doc_number = fields.Char("Revision Doc No")
    rev_number = fields.Char("Revision Number")
    rev_date = fields.Date("Revision Date")
    line_ids = fields.One2many('stock.inspection.line', 'inspection_id', string="Inspection")
    company_id = fields.Many2one('res.company', 'Company', index=True, default=lambda self: self.env.company)
    template_id = fields.Many2one('inspection.template', string="Inspection Template", copy=False)
    team_id = fields.Many2one('inspection.team', string="Inspection Team", required=1)
    user_id = fields.Many2one('res.users', string="Requested By")
    verify_user_id = fields.Many2one('res.users', string="Verified By")
    approve_user_id = fields.Many2one('res.users', string="Approved By")
    picking_id = fields.Many2one('stock.picking', string="Inward/Outward")
    standard = fields.Char(string="Standard")
    aql = fields.Char(string="AQL")
    invoice_number = fields.Char(string="Invoice No")
    batch_number = fields.Char(string="Batch No")
    move_id = fields.Many2one('stock.move', string="Move")
    form_state = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string="Status")

    @api.onchange('type')
    def onchange_type(self):
        company_id = self.env.user.company_id or self.env['res.company'].search([])[0]
        if self.type == 'incoming':
            self.rev_doc_number = company_id.in_ins_doc_no
            self.rev_number = company_id.in_ins_rev_no
            self.rev_date = company_id.in_ins_rev_date
        elif self.type == 'outgoing':
            self.rev_doc_number = company_id.out_ins_doc_no
            self.rev_number = company_id.out_ins_rev_no
            self.rev_date = company_id.out_ins_rev_date
        else:
            self.rev_doc_number = company_id.audit_ins_doc_no
            self.rev_number = company_id.audit_ins_rev_no
            self.rev_date = company_id.audit_ins_rev_date

    @api.onchange('template_id')
    def onchange_template_id(self):
        self.line_ids = False
        lines = []
        for item in self.template_id.item_ids:
            lines.append(
                (0, 0, {
                    'name': item.name,
                    'parameter': item.parameter,
                    'from_value': item.from_value,
                    'to_value': item.to_value,
                    'sort': item.sort,
                    'test_method': item.test_method
                }))
        self.line_ids = lines

    def action_submit(self):
        if not self.line_ids:
            raise ValidationError('Please add at least one inspection line before submitting the record.')
        else:
            for line in self.line_ids:
                if line.parameter and not line.sample_1:
                    raise ValidationError("Sample Missing: Sample one is required for parameter '%s'" % str(line.parameter))
                elif line.parameter and not line.sample_2:
                    raise ValidationError("Sample Missing: Sample two is required for parameter '%s'" % str(line.parameter))
                elif line.parameter and not line.sample_3:
                    raise ValidationError("Sample Missing: Sample three is required for parameter '%s'" % str(line.parameter))
                elif line.parameter and not line.sample_4:
                    raise ValidationError("Sample Missing: Sample four is required for parameter '%s'" % str(line.parameter))
                elif line.parameter and not line.sample_5:
                    raise ValidationError("Sample Missing: Sample five is required for parameter '%s'" % str(line.parameter))
        for rec in self:
            code = 'stock.inspection.audit'
            if rec.type == 'incoming':
                code = 'stock.inspection.incoming'
            if rec.type == 'outgoing':
                code = 'stock.inspection.outgoing'
            name = rec.name
            if rec.name == _('New'):
                name = self.env['ir.sequence'].next_by_code(code) or _('New')
            mail_content = "Dear Sir/Madam,<br/><br/> You have been requested to inspect the product.<br/><br/> Thanks & Regards,<br/> %s" % self.env.user.name
            main_content = {
                'subject': _('Inspection Request - %s') % rec.name,
                'email_from': self.env.user.login,
                'body_html': mail_content,
            }
            for user in rec.team_id.user_ids:
                main_content['email_to'] = user.login
                self.env['mail.mail'].sudo().create(main_content).send()
            rec.write({
                'name': name,
                'state': 'request',
                'date': fields.Date.today(),
                'user_id': self.env.user.id
            })

    def action_verify(self):
        for rec in self:
            mail_content = "Dear Sir/Madam,<br/><br/> You have been requested to approve the inspection.<br/><br/> Thanks & Regards,<br/> %s" % self.env.user.name
            main_content = {
                'subject': _('Inspection Request - %s') % rec.name,
                'email_from': self.env.user.login,
                'body_html': mail_content,
            }
            for user in rec.team_id.approve_user_ids:
                main_content['email_to'] = user.login
                self.env['mail.mail'].sudo().create(main_content).send()
            rec.write({
                'state': 'verify',
                'date_done': fields.Date.today(),
                'verify_user_id': self.env.user.id,
            })

    def action_validate(self):
        for rec in self:
            mail_content = "Dear Sir/Madam,<br/><br/> Your inspection request has been approved. Please proceed further.<br/><br/> Thanks & Regards,<br/> %s" % self.env.user.name
            main_content = {
                'subject': _('Inspection Request - %s') % rec.name,
                'email_from': self.env.user.login,
                'body_html': mail_content,
                'email_to': rec.user_id.login
            }
            self.env['mail.mail'].sudo().create(main_content).send()
            # purchase_user = self.env['purchase.order'].search([('name', '=', rec.picking_id.origin)], limit=1)
            # mail_content_return = "Dear Sir/Madam,<br/><br/> Your inspection request has been approved. Please proceed further.<br/><br/> Thanks & Regards,<br/> %s" % self.env.user.name
            # main_content_return = {
            #     'subject': _('Return of Product - %s') % rec.product_id.name,
            #     'email_from': self.env.user.login,
            #     'body_html': mail_content_return,
            #     'email_to': purchase_user.user_id.login if purchase_user else rec.user_id.login,
            # }
            # self.env['mail.mail'].sudo().create(main_content_return).send()
            rec.write({
                'state': 'done',
                'approve_user_id': self.env.user.id,
            })

    def action_cancel(self):
        for rec in self:
            mail_content = "Dear Sir/Madam,<br/><br/>Your inspection request was canceled.<br/><br/> Thanks & Regards,<br/> Odoo Bot"
            main_content = {
                'subject': _('Inspection Request - %s') % rec.name,
                'email_from': self.env.user.login,
                'body_html': mail_content,
                'email_to': rec.user_id.login
            }
            self.env['mail.mail'].sudo().create(main_content).send()
            rec.write({
                'state': 'cancel',
                'date': fields.Date.today(),
            })

    def action_reset(self):
        for rec in self:
            rec.write({'state': 'draft'})

    def unlink(self):
        for rec in self:
            if rec.state not in ['draft', 'cancel']:
                raise UserError(_("Only records in draft or canceled status can be deleted."))
        return super(StockInspection, self).unlink()


class StockInspectionLine(models.Model):
    _name = 'stock.inspection.line'
    _description = 'Inspection Line'

    inspection_id = fields.Many2one('stock.inspection', string="Inspection")
    quality_check_id = fields.Many2one('process.quality.check')
    name = fields.Char('Characteristics', required=True)
    parameter = fields.Char("Standard Parameter")
    from_value = fields.Float("From")
    to_value = fields.Float("To")
    sort = fields.Char("Sort")
    test_method = fields.Char("Tools")
    sample_1 = fields.Float("1")
    sample_2 = fields.Float("2")
    sample_3 = fields.Float("3")
    sample_4 = fields.Float("4")
    sample_5 = fields.Float("5")
    min_value = fields.Float('Min', compute='compute_min_max', store=True)
    max_value = fields.Float('Max', compute='compute_min_max', store=True)
    state = fields.Selection([('pass', 'Pass'), ('fail', 'Fail'),('pass_with_deviation', 'Pass with Deviation')], string="Status")
    field_type =fields.Selection([('numeric','Numeric'),('text','Text')],string='Type')
    remark = fields.Char('Remarks')

    @api.depends('sample_1', 'sample_2', 'sample_3', 'sample_4', 'sample_5')
    def compute_min_max(self):
        for rec in self:
            samples = [sample for sample in [rec.sample_1, rec.sample_2, rec.sample_3, rec.sample_4, rec.sample_5] if
                       sample != 0]
            if samples:
                rec.min_value = min(samples)
                rec.max_value = max(samples)
            else:
                rec.min_value = 0
                rec.max_value = 0


class InspectionTemplate(models.Model):
    _name = 'inspection.template'
    _description = 'Inspection Template'

    name = fields.Char("Name", required=True)
    type = fields.Selection([('incoming', 'Incoming'), ('pqc', 'PQC'), ('iqc', 'IQC'), ('oqc', 'OQC'),
                             ('process_approval', 'Process Approval'), ('fai', 'FAI'), ('fpa', 'FPA'), ('dai', 'DAI')],
                            default='incoming', string="Inspection Type")
    item_ids = fields.One2many('inspection.item', 'template_id', string="Inspection Items")


class InspectionItem(models.Model):
    _name = 'inspection.item'
    _description = 'Inspection Items'

    template_id = fields.Many2one('inspection.template', string="Template")
    name = fields.Char("Characteristics", required=True)
    field_type_view = fields.Selection([('text','Text'),('numeric','Numeric')])
    parameter = fields.Char("Standard Parameter")
    from_value = fields.Float("From")
    to_value = fields.Float("To")
    sort = fields.Char("Sort")
    test_method = fields.Char("Tools")
