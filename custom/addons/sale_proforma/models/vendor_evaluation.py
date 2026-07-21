from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class PartnerEvaluation(models.Model):
    _name = "partner.evaluation"
    _description = "Vendor Evaluation"
    _rec_name = 'vendor_code'

    vendor_code = fields.Char(string="Vendor Code")
    gst_in = fields.Char(string='GST IN')
    gst_treatment = fields.Selection([
        ('regular', 'Registered Business - Regular'),
        ('composition', 'Registered Business - Composition'),
        ('unregistered', 'Unregistered Business'),
        ('consumer', 'Consumer'),
        ('overseas', 'Overseas'),
        ('special_economic_zone', 'Special Economic Zone'),
        ('deemed_export', 'Deemed Export')
    ], string="GST Treatment",store=True, readonly=False)
    name_of_supplier = fields.Char(string="Name of the Supplier", required=True)
    street1 = fields.Char(string="street1")
    street2 = fields.Char(string="street2")
    city = fields.Char(string="city")
    years = fields.Char(string="Year Established")
    address = fields.Char(string="Address")
    zip = fields.Char(string="Zip")
    state_id = fields.Many2one('res.country.state', string="state")
    country_id = fields.Many2one('res.country', string="Country")
    organisation_name = fields.Char(string="Nature of Organisation")
    contact_no = fields.Char(string="Contact No")
    pan_no = fields.Char(string="PAN NO")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('validate1', 'Reviewed'),
        ('validate2', 'First Approved'),
        ('validate3', 'Final Approved'),
        ('done', 'done'),
        ('cancel', 'Cancel'),
    ], string="state", default="draft")
    bussiness_name = fields.Char(string="Type of Bussiness")
    annual_profit = fields.Char(string="Average Annual Turnover")
    registered = fields.Char(string="Registered under MSME")
    udyam_no = fields.Char(string="Udyam Registered No")
    description = fields.Char(string="Description of Goods & Services Supplied")
    bank_name = fields.Many2one('res.bank',string="Bank Name")
    account_no = fields.Char(string="Account No")
    ifsc_code = fields.Char(string="IFSC Code")
    mail = fields.Char(string="Email")
    website = fields.Char(string="Website")
    legal_name = fields.Char(string="Legal Name of the Supplier")
    representative_name = fields.Char("Representative of the Supplier")
    # vendor_details_ids=fields.One2many("vendor.details","vendor_id")
    sample = fields.Boolean(string="Sample Submitted")
    all_matched = fields.Boolean(string="All Specification matched")
    trial = fields.Boolean(string="Trial Order Issued")
    performance_review = fields.Boolean(string="a)All Supplied items are meeting specification.")
    material_review = fields.Boolean(string="b)Material received on time.")
    supplies_review = fields.Boolean(string="c)Supplied can be continued.")
    pricing = fields.Boolean(string="Pricing is comparable with market & on lower side.")
    Re_ability = fields.Text(string="Reliability of materials supplied.")
    over_all = fields.Text(string="Overall Rating of Supplier.")
    partner_id = fields.Many2one('res.partner')


    sample_remarks = fields.Text(string="Remarks")
    all_matched_remarks = fields.Text(string="Remarks")
    trial_remarks = fields.Text(string="Remarks")
    performance_review_remarks = fields.Text(string="Remarks")
    material_review_remarks = fields.Text(string="Remarks")
    supplies_review_remarks = fields.Text(string="Remarks")
    pricing_remarks = fields.Text(string="Remarks")

    # reviewed_suggest=fields.Text(string="Review Suggested")
    requested_by = fields.Many2one('res.users', string="Requested By", default=lambda self: self.env.user,
                                   readonly=True)

    # def check_user(self):
    #     for rec in self:
    #         if self.env.user.has_group('base.group_system'):
    #             rec.is_check = True
    #         else:
    #             rec.is_check = False

    # @api.constrains('reviewed_suggest')
    # def _check_name(self):
    #     for record in self:
    #         if not record.reviewed_suggest:
    #             raise ValidationError(("Please fill the Review Suggested."))

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('vendor_code'):
                vals['vendor_code'] = self.env['ir.sequence'].next_by_code('purchase.sequence') or '/'
        return super(PartnerEvaluation, self).create(vals_list)

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_sent(self):
        reviwer_users = ''
        users = self.env['res.users'].search([])
        for user in users:
            if user.has_group('sale_proforma.group_reviewer_evaluation_reviewer'):
                reviwer_users += user.login
                reviwer_users += ', '

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)

        subject = "%s's Vendor Evaluation Review" % self.name_of_supplier
        body = """<p>Dear Reviewers,</p>
                                        <p>Please review and approve the Vendor Evaluation form of <b>%s</b>
                                        <br/>
                                        <br/>
                                        <a href="%s" style="display:inline-block; padding:10px 24px; background-color:#1a6b72; color:#ffffff; text-decoration:none; font-size:14px; font-weight:600; border-radius:5px;">Review Now</a>
                                        <br/><br/>
                                        Thank &amp; Regards,<br/>
                                        <strong>%s</strong>
                                        </p>""" % (self.vendor_code, base_url, self.env.user.name)
        message_body = body
        from_email = self.requested_by.login
        # to_email = self.employe_id.parent_id.work_email
        template_data = {
            'subject': subject,
            'body_html': message_body,
            'email_from': from_email,
            'email_to': reviwer_users,
        }
        # self.message_post(body=message_body, subject=subject)
        template_id = self.env['mail.mail'].sudo().create(template_data)
        template_id.sudo().send()
        self.state = 'sent'

    def action_validate1(self):
        officer_users = ''
        users = self.env['res.users'].search([])
        for user in users:
            if user.has_group('sale_proforma.group_customer_evaluation_officer'):
                officer_users += user.login
                officer_users += ', '

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)

        subject = "%s's Vendor Evaluation Review" % self.name_of_supplier
        body = """<p>Dear Officers,</p>
                                                <p>Please review and approve the Vendor Evaluation form of <b>%s</b>
                                                <br/>
                                                <br/>
                                                <a href="%s" style="display:inline-block; padding:10px 24px; background-color:#1a6b72; color:#ffffff; text-decoration:none; font-size:14px; font-weight:600; border-radius:5px;">Review Now</a>
                                                <br/><br/>
                                                Thank &amp; Regards,<br/>
                                                <strong>%s</strong>
                                                </p>""" % (self.vendor_code, base_url, self.env.user.name)
        message_body = body
        from_email = self.env.user.login
        # to_email = self.employe_id.parent_id.work_email
        template_data = {
            'subject': subject,
            'body_html': message_body,
            'email_from': from_email,
            'email_to': officer_users,
            'email_cc': self.requested_by.name
        }
        # self.message_post(body=message_body, subject=subject)
        template_id = self.env['mail.mail'].sudo().create(template_data)
        template_id.sudo().send()
        self.state = 'validate1'

    def action_validate2(self):
        manager_users = ''
        users = self.env['res.users'].search([])
        for user in users:
            if user.has_group('sale_proforma.group_customer_evaluation_manager'):
                manager_users += user.login
                manager_users += ', '

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)

        subject = "%s's Vendor Evaluation Review" % self.name_of_supplier
        body = """<p>Dear Manager,</p>
                                                        <p>Please review and approve the Vendor Evaluation form of <b>%s</b>
                                                        <br/>
                                                        <br/>
                                                        <a href="%s" style="display:inline-block; padding:10px 24px; background-color:#1a6b72; color:#ffffff; text-decoration:none; font-size:14px; font-weight:600; border-radius:5px;">Review Now</a>
                                                        <br/><br/>
                                                        Thank &amp; Regards,<br/>
                                                        <strong>%s</strong>
                                                        </p>""" % (self.vendor_code, base_url, self.env.user.name)
        message_body = body
        from_email = self.env.user.login
        # to_email = self.employe_id.parent_id.work_email
        template_data = {
            'subject': subject,
            'body_html': message_body,
            'email_from': from_email,
            'email_to': manager_users,
            'email_cc': self.requested_by.name
        }
        # self.message_post(body=message_body, subject=subject)
        template_id = self.env['mail.mail'].sudo().create(template_data)
        template_id.sudo().send()
        self.state = 'validate2'

    def action_validate3(self):
        for rec in self:
            vals = {
                'pan_no': self.pan_no,
                'name': self.name_of_supplier,
                'street': self.street1,
                'street2': self.street2,
                'state_id': self.state_id.id,
                'country_id': self.country_id.id,
                'vat': self.gst_in,
                'l10n_in_gst_treatment': self.gst_treatment,
                'zip': self.zip,
                'city': self.city,
                'vendor_id': self.id,
                'email': self.mail,
                'phone': self.contact_no,
                'code': self.vendor_code,
                'website': self.website,
                'is_vendor': True,
                'company_type': 'company',
            }
            partner = self.env['res.partner'].create(vals)
            partner.bank_ids.create({
                'acc_number': rec.account_no,
                'partner_id': partner.id,
                'bank_id': rec.bank_name.id, })
            # if rec.bank_name and rec.account_on:
            #     bank = self.env['res.bank'].search([('name', '=', rec.bank_name)], limit=1)
            #     if bank:
            #         partner.create({
            #             'bank_ids': [(0, 0, {
            #                 'bank_id': bank.id,
            #                 'acc_number': rec.account_on,
            #             })]
            #         })

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)

            subject = "%s's Vendor Evaluation Review" % self.name_of_supplier
            body = """<p>Dear %s,</p>
                                                   <p>Vendor Form has been approved <b>%s</b>
                                                   <br/>
                                                   <br/>
                                                   <a href="%s" style="display:inline-block; padding:10px 24px; background-color:#1a6b72; color:#ffffff; text-decoration:none; font-size:14px; font-weight:600; border-radius:5px;">View Record</a>
                                                   <br/><br/>
                                                   Thank &amp; Regards,<br/>
                                                   <strong>%s</strong>
                                                   </p>""" % (self.requested_by.name, self.vendor_code, base_url,
                                                              self.env.user.name)
            message_body = body
            from_email = self.env.user.login
            # to_email = self.employe_id.parent_id.work_email
            template_data = {
                'subject': subject,
                'body_html': message_body,
                'email_from': from_email,
                'email_to': self.requested_by.name,
            }
            template_id = self.env['mail.mail'].sudo().create(template_data)
            template_id.sudo().send()
        rec.state = 'validate3'

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def action_open_vendor(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'vendor',
            'view_mode': 'list,form',
            'res_model': 'res.partner',
            'domain': [('vendor_id', '=', self.id)],
            'target': 'current',
        }


class ResPartner(models.Model):
    _inherit = 'res.partner'

    vendor_id = fields.Many2one('partner.evaluation')

    def action_vendor_evaluation(self):
        return {
            "name": _("Vendor Evaluation"),
            "type": "ir.actions.act_window",
            "res_model": "partner.evaluation",
            "view_mode": "list,form",
            'domain': [('name_of_supplier', '=', self.name)],
            'target': 'current',
        }
class RackList(models.Model):
    _name = 'rack.list'

    name = fields.Char()


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    security_inward = fields.Boolean(string="Security Inward Stamp")
    purchase_order = fields.Boolean("Purchase Order")
    commercial_invoice = fields.Boolean(string="Commercial Invoice")
    verify_code = fields.Boolean(string="Verify Vendor Details")
    grn = fields.Boolean(string="GRN")
    purchase_descrip = fields.Boolean(string="Goods received are according to the description in PO.")
    quantity_measure = fields.Boolean(
        string="Quantity, Weights, Measurements and specifications of goods received are same to those indicated in PO and in invoice.(Note: In some cases, drawings/specifications data sheets can be referred).")
    supplies_review = fields.Boolean(
        string="The goods and quantities received fully tally with those mentioned in delivery challan.")
    inspect = fields.Boolean(string="Inspection of goods")
    invoice_value = fields.Boolean(string="Invoice value is agreeing with that in PO.")
    entry_details = fields.Boolean(string="Entry of details of goods received in your purchase & stock register.")
    account_depart = fields.Boolean(string="Handover the invoice to accounts department")
    certificate = fields.Boolean(string='Certificate')
    notify_goods = fields.Boolean(string="Notify the concerned department regarding receipt of goods.")
    storage = fields.Boolean(string="Storage of goods")
    returnable_items = fields.Selection([
        ('return_item', 'Returnable Item'),
        ('nonreturn_item', 'Non-Returnable Item')], string='Item', related='picking_type_id.return_items')
    transporter_name = fields.Char(string='Driver Name')
    vehicle_no = fields.Char(string='Vehicle No')
    purpose = fields.Char(string='Purpose')
    gate_doc = fields.Char(string='Gate Doc No')
    type_vehicle = fields.Char(string='Type of Vehicle')
    transporter = fields.Char(string='Transporter')

    security_inward_remarks = fields.Text(string="Remarks")
    purchase_order_remarks = fields.Text(string="Remarks")
    commercial_invoice_remarks = fields.Text(string="Remarks")
    verify_code_remarks = fields.Text(string="Remarks")
    grn_remarks = fields.Text(string="Remarks")
    purchase_descrip_remarks = fields.Text(string="Remarks")
    quantity_measure_remarks = fields.Text(string="Remarks")
    supplies_review_remarks = fields.Text(string="Remarks")
    inspect_remarks = fields.Text(string="Remarks")
    invoice_value_remarks = fields.Text(string="Remarks")
    entry_details_remarks = fields.Text(string="Remarks")
    account_depart_remarks = fields.Text(string="Remarks")
    certificate_remarks = fields.Text(string="Remarks")
    notify_goods_remarks = fields.Text(string="Remarks")
    storage_remarks = fields.Text(string="Remarks")


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    return_items = fields.Selection([
        ('return_item', 'Returnable Item'),
        ('nonreturn_item', 'Non-Returnable Item')], string='Returnable Item')


class PurchaseTerms(models.Model):
    _name = 'purchase.terms'
    _description = 'Purchase Terms'

    # value_id=fields.Many2one('purchase.order')
    name = fields.Char()


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    caliberate_certificate = fields.Boolean(string="Caliberation Certificate")
    test_report = fields.Boolean(string='Test Report')
    warranty_certificate = fields.Boolean(string="Warranty Certificate")
    certifi_analysis = fields.Boolean(string="Certificate of Analysis")
    machine_part = fields.Boolean(string="Machine/Part Drawings")
    tech_machine = fields.Boolean(string="Tech Manual/Documents")
    material_data = fields.Boolean(string='Material Safety Data Sheet(MSDS)')
    Technical_data = fields.Boolean(string="Technical Data Sheet")
    terms_ids = fields.Many2many('purchase.terms')
    others = fields.Char(string='Others')
    # value_ids=fields.One2many('purchase.terms','value_id')


class StockMove(models.Model):
    _inherit = 'stock.move'

    reversed_quality = fields.Float("Test")
    reversed_quantity = fields.Float(compute='_compute_return_quantity')
    reason = fields.Text(string='Reason For Return')
    rack_list_id = fields.Many2one('rack.list')

    @api.depends('picking_id', 'picking_id.name', 'product_id')
    def _compute_return_quantity(self):
        for rec in self:
            if not rec.picking_id or not rec.picking_id.name:
                rec.reversed_quantity = 0
                continue

            return_picking = self.env['stock.picking'].search([
                ('origin', '=', 'Return of ' + rec.picking_id.name)
            ])
            quantity_done = 0
            for picking in return_picking:
                quantity_done += sum(
                    picking.move_ids.filtered(
                        lambda x: x.product_id.id == rec.product_id.id
                    ).mapped('quantity')
                )
            rec.reversed_quantity = quantity_done