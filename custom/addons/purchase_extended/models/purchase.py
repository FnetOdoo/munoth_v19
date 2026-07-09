from odoo import api, fields, models, _, SUPERUSER_ID
from odoo.exceptions import UserError, AccessError
import io
import base64
from markupsafe import Markup
import PyPDF2



class DeliveryTerms(models.Model):
    _name = 'delivery.term'
    _description = "Delivery Terms"

    name = fields.Char("Name")


class Purchase(models.Model):
    _inherit = 'purchase.order'

    state = fields.Selection([
        ('draft', 'Draft PO'),
        ('sent', 'RFQ Sent'),
        ('bid received', 'Bid Received'),
        ('to approve', 'To Approve'),
        ('purchase', 'Purchase Order'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], string='Status', readonly=True, index=True, copy=False, default='draft')
    purchase_type = fields.Selection([('local', 'Local Purchase'), ('regular', 'Regular')], string="Purchase Type", default='regular')
    # quotation_number = fields.Char('RFQ Reference')
    quotation_number = fields.Char('RFQ Reference', required=True, index=True, copy=False, default='New')
    delivery_term_id = fields.Many2one('delivery.term', string="Delivery Terms")
    rev_no = fields.Char(string='PO Rev No')
    doc_no = fields.Char(string='PO Doc No')
    rev_date = fields.Date(string='PO Date')
    re_date = fields.Date(string='PO Date') #Todo: To be removed: added for avoid field not found issue

    po_rev_no = fields.Char(string='PO Terms & Condition Rev No')
    po_doc_no = fields.Char(string='PO Terms & Condition Doc No')
    po_rev_date = fields.Date(string='PO Terms & Condition Date')
    store_email = fields.Char()

    def action_rfq_send(self):
        for order in self:
            if not order.order_line:
                raise ValidationError(
                    "Please add product lines before sending the RFQ."
                )
            if not order.partner_id.email:
                raise ValidationError(
                    ("Vendor '%s' does not have an email address. "
                     "Please add an email address before sending the RFQ.")
                    % order.partner_id.name
                )

        res = super(Purchase, self).action_rfq_send()

        if self.state in ['draft', 'sent']:
            report = self.env.ref('munoth_reports.rfq_report')
        else:
            report = self.env.ref('munoth_reports.purchase_order_to_vendor_report')

        pdf_content, _ = report._render_qweb_pdf(
            report.report_name,
            res_ids=[self.id]
        )
        if self.state in ['draft', 'sent']:
            attachment_name = f"Request for Quotation - {self.name}.pdf"
        else:
            attachment_name = f"Purchase Order - {self.name}.pdf"
        attachment = self.env['ir.attachment'].create({
            'name': attachment_name,
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        if not res.get('context'):
            res['context'] = {}
        existing_attachments = res['context'].get('default_attachment_ids', [])
        if existing_attachments and isinstance(existing_attachments, list) and existing_attachments[0][0] == 6:
            res['context']['default_attachment_ids'][0][2].append(attachment.id)
        else:
            res['context']['default_attachment_ids'] = [(6, 0, [attachment.id])]

        res['context'].update({
            'default_partner_ids': [(6, 0, [self.partner_id.id])]
        })

        return res

    def _remind_mail_for_receipt_date(self):
        for rec in self:
            today_date = fields.Datetime.now()
            if today_date > rec.date_planned:
                subject = "%s's Material Not Received for Order " % self.partner_id.name
                body = """<p>Dear Team,</p>
                           <p>inform you that the material for <strong>%s</strong>was expected to be received on <strong>%s</strong>, but it has not been received yet.
                           <br/>
                           Thank You.</br>
                           </p>""" % (self.name,self.date_planned)
                message_body = body
                from_email = self.env.user.login
                template_data = {
                    'subject': subject,
                    'body_html': message_body,
                    'email_from': from_email,
                    'email_to': self.requested_by.name,
                    'email_cc': self.store_email,
                }
                template_id = self.env['mail.mail'].sudo().create(template_data)
                template_id.sudo().send()




    @api.model
    def default_get(self, fields):
        defaults = super(Purchase, self).default_get(fields)
        company_id = self.env.user.company_id or self.env['res.company'].search([])[0]
        defaults['store_email'] = company_id.store_mail_id
        defaults['rev_no'] = company_id.rev_no
        defaults['doc_no'] = company_id.doc_no
        defaults['rev_date'] = company_id.rev_date
        defaults['po_rev_no'] = company_id.po_rev_no
        defaults['po_doc_no'] = company_id.po_doc_no
        defaults['po_rev_date'] = company_id.po_rev_date
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                seq_date = None
                if vals.get('date_order'):
                    seq_date = fields.Datetime.context_timestamp(
                        self,
                        fields.Datetime.to_datetime(vals['date_order'])
                    )

                code = 'purchase.rfq.local' if vals.get('purchase_type') == 'local' else 'purchase.rfq'

                vals['name'] = self.env['ir.sequence'].next_by_code(
                    code,
                    sequence_date=seq_date
                ) or '/'

        return super().create(vals_list)

    def bid_received(self):
        bid_receive_obj = self.env['bid.received.line']
        if self.requisition_id:
            for line in self.order_line:
                bid_receive_obj.create({
                            'tender_id': self.requisition_id.id,
                            'purchase_order_id': self.id,
                            'purchase_order_line_id': line.id,
                            'vender_id': self.partner_id.id,
                            'product_id': line.product_id.id,
                            'quantity': line.product_qty,
                            'qty_selected': line.product_qty,
                            'purchase_unit_price': line.price_unit,
                            'unit_price': line.price_unit,
                            'purchase_total_price': line.price_subtotal,
                            'sub_total': line.price_subtotal,
                            'unit_measure': line.product_id.uom_id.id,
                        })
        self.write({'state': 'bid received'})

    def send_rfq(self):
        self.write({'state': 'sent'})

    def button_confirm(self):
        if self.purchase_order_approval_history:
            subject = 'RFQ Approved'
            last_approval_user = self.purchase_order_approval_history[-1].user
            body = f"""
            <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 14px; color: #222; background-color: #f4f6fa; padding: 32px 0;">
                <div style="max-width: 560px; margin: 0 auto; background-color: #ffffff; border-radius: 10px; overflow: hidden; border: 1px solid #dde2ef;">

                    <!-- Header -->
                    <div style="background-color: #1a6b3a; padding: 32px 40px 24px;">
                        <div style="margin-bottom: 16px;">
                            <span style="font-size: 11px; color: #a0e8c0; letter-spacing: 0.08em; text-transform: uppercase;">
                                Procurement
                            </span>
                        </div>
                        <h1 style="font-size: 22px; font-weight: 600; color: #ffffff; margin: 0 0 4px;">
                            RFQ Approved
                        </h1>
                        <p style="font-size: 13px; color: #7ad4a0; margin: 0;">
                            Action completed — please proceed further
                        </p>
                    </div>

                    <!-- Body -->
                    <div style="padding: 32px 40px;">
                        <p style="font-size: 15px; color: #111; font-weight: 600; margin: 0 0 12px;">
                            Hello {last_approval_user.name},
                        </p>

                        <p style="font-size: 14px; color: #444; line-height: 1.7; margin: 0 0 24px;">
                            Respective approval has been confirm the order 
                            <strong style="color: #111;">{self.name}</strong>. 
                            You may proceed further from your end.
                        </p>

                        <!-- Info Box -->
                        <div style="background-color: #f7f9fc; border-radius: 8px; padding: 16px 20px; margin-bottom: 28px; border-left: 3px solid #1a6b3a;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <tr>
                                    <td style="padding: 6px 0; width: 50%;">
                                        <p style="font-size: 11px; color: #888; margin: 0 0 2px; text-transform: uppercase;">
                                            Reference
                                        </p>
                                        <p style="font-size: 13px; font-weight: 600; color: #111; margin: 0;">
                                            {self.name}
                                        </p>
                                    </td>

                                    <td style="padding: 6px 0;">
                                        <p style="font-size: 11px; color: #888; margin: 0 0 2px; text-transform: uppercase;">
                                            Approved By
                                        </p>
                                        <p style="font-size: 13px; font-weight: 600; color: #111; margin: 0;">
                                            {self.env.user.name}
                                        </p>
                                    </td>
                                </tr>

                                <tr>
                                    <td style="padding: 6px 0;">
                                        <p style="font-size: 11px; color: #888; margin: 0 0 2px; text-transform: uppercase;">
                                            Status
                                        </p>
                                        <p style="margin: 0;">
                                            <span style="background-color: #d4edda; color: #155724; padding: 2px 10px; border-radius: 4px; font-size: 12px; font-weight: 500;">
                                                Approved
                                            </span>
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </div>

                        <!-- Button -->
                        <a href="{self.get_base_url()}/web#id={self.id}&model=purchase.order&view_type=form"
                           style="display: inline-block; background-color: #1a6b3a; color: #ffffff; text-decoration: none;
                                  font-size: 13px; font-weight: 600; padding: 10px 24px;
                                  border-radius: 6px;">
                            View Order →
                        </a>
                    </div>

                    <!-- Footer -->
                    <div style="border-top: 1px solid #eaecf0; padding: 16px 40px;">
                        <p style="font-size: 11px; color: #aaa; margin: 0;">
                            This is an automated notification.
                        </p>
                    </div>

                </div>
            </div>
            """

            self.message_post( body=Markup(body),subject=subject)
            template_data = {
                'subject': subject,
                'body_html': body,
                'email_from': self.env.user.login,
                'email_to': last_approval_user.login,
            }
            template_id = self.env['mail.mail'].sudo().create(template_data)
            template_id.sudo().send()
        for order in self:
            if order.requisition_id and order.requisition_id.state != 'open':
                raise UserError(_("Please validate the purchase agreement to confirm the RFQ."))
            if order.state not in ['draft', 'sent', 'bid received']:
                continue
            order._add_supplier_to_product()
            # Deal with double validation process
            if order._approval_allowed():
                order.button_approve()
            else:
                order.write({'state': 'to approve'})
            if order.partner_id not in order.message_partner_ids:
                order.message_subscribe([order.partner_id.id])
            seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(order.date_order))
            rfq_reference = order.name
            code = 'purchase.confirm'
            if order.purchase_type == 'local':
                code = 'purchase.confirm.local'
            if order.quotation_number == 'New':
                order.name = self.env['ir.sequence'].next_by_code(code, sequence_date=seq_date) or '/'
            order.write({
                'quotation_number': rfq_reference
            })
            for picking in order.picking_ids:
                picking.update({'origin': order.name})
        return True


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    requisition_line_id = fields.Many2one('purchase.requisition.line', string="Requisition Line")
    s_no = fields.Integer(string='S.No', compute='_compute_sequence', store=True, readonly=False)

    @api.depends('order_id.order_line')
    def _compute_sequence(self):
        for order in self.mapped('order_id'):
            idx = 1
            for line in order.order_line:
                if not line.display_type:
                    line.s_no = idx
                    idx += 1
                else:
                    line.s_no = 0


class StockPicking(models.Model):
    _inherit = "stock.picking"

    sale_id=fields.Many2one('sale.order')
    rev_no = fields.Char(string='Rev No')
    doc_no = fields.Char(string='Doc No')
    rev_date = fields.Date(string='Date')
    re_date = fields.Date(string='PO Date') #Todo: To be removed: added for avoid field not found issue
    invoice_date = fields.Date(string='Invoice Date')
    invoice_no = fields.Char(string='Invoice No')
    inward_date = fields.Date(string='Inward/Outward Date')
    checked_by = fields.Many2one('res.users', string='Checked By')
    reviewed_by = fields.Many2one('res.users', string='Reviewed By')
    received_by = fields.Many2one('res.users', string='Received By')
    prepared_by = fields.Many2one('res.users', default=lambda self: self.env.user,)

    items = fields.Boolean(string='Ordered Items')
    def get_total_pages2(self, obj):
        # Create a PDF canvas with dummy content to calculate the total pages
        # buffer = io.BytesIO()
        # pdf = canvas.Canvas(buffer, pagesize=letter)
        # pdf.drawString(100, 100, "Your Dummy Content Here")
        # pdf.save()
        report_name = "munoth_reports.good_received_report_1"
        report_output = self.env.ref('munoth_reports.good_received_report_1')._render_qweb_pdf(obj.id)

        # `report_output` is a tuple where `report_output[0]` is the binary output
        # and `report_output[1]` is the "converter" (in this case, "pdf").
        # report_output = report.render_qweb_pdf(obj)

        # Calculate the total pages
        # pdf_bytes = base64.b64encode(report_output[0])
        pdf_reader = PyPDF2.PdfFileReader(io.BytesIO(report_output[0]))
        # PyPDF2.PdfFileReader(file)
        total_pages = pdf_reader.numPages
        return total_pages

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('stock.picking')
        return super().create(vals_list)

    _sql_constraints = [
        ('name_uniq', 'CHECK(name != "New") AND unique(name, company_id)', 'Reference must be unique per company!'),
    ]

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        if self.name == 'New':
            if self.picking_type_id.sequence_id:
                self.name = self.picking_type_id.sequence_id.next_by_id()
        return res

    @api.model
    def default_get(self, fields):
        defaults = super(StockPicking, self).default_get(fields)
        company_id = self.env.user.company_id or self.env['res.company'].search([])[0]
        defaults['rev_no'] = company_id.picking_rev_no
        defaults['doc_no'] = company_id.picking_doc_no
        defaults['rev_date'] = company_id.picking_rev_date
        return defaults


class Company(models.Model):
    _inherit = 'res.company'

    store_mail_id = fields.Char(string='Store Mail')

    rev_no = fields.Char(string='PO Rev No')
    doc_no = fields.Char(string='PO Doc No')
    rev_date = fields.Date(string='PO Date')

    po_rev_no = fields.Char(string='PO Terms & Condition Rev No')
    po_doc_no = fields.Char(string='PO Terms & Condition Doc No')
    po_rev_date = fields.Date(string='PO Terms & Condition Date')

    picking_rev_no = fields.Char(string='Delivery Rev No')
    picking_doc_no = fields.Char(string='Delivery Doc No')
    picking_rev_date = fields.Date(string='Delivery Date')

    receipt_rev_no = fields.Char(string='Receipt Rev No')
    receipt_doc_no = fields.Char(string='Receipt Doc No')
    receipt_rev_date = fields.Date(string='Receipt Date')

    checklist_rev_no = fields.Char(string='Checklist Rev No')
    checklist_doc_no = fields.Char(string='Checklist Doc No')
    checklist_rev_date = fields.Date(string='Checklist Date')

    packing_rev_no = fields.Char(string='Packing List Rev No')
    packing_doc_no = fields.Char(string='Packing List Doc No')
    packing_rev_date = fields.Date(string='Packing List Date')

    gate_pass_rev_no = fields.Char(string='Gate Pass Rev No')
    gate_pass_doc_no = fields.Char(string='Gate Pass Doc No')
    gate_pass_rev_date = fields.Date(string='Gate Pass Date')


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    store_mail_id = fields.Char(string='Store Mail', related='company_id.store_mail_id', readonly=False)

    rev_no = fields.Char(string='PO Rev No', related='company_id.rev_no', readonly=False)
    doc_no = fields.Char(string='PO Doc No', related='company_id.doc_no', readonly=False)
    rev_date = fields.Date(string='PO Date', related='company_id.rev_date', readonly=False)

    po_rev_no = fields.Char(string='PO Terms & Condition Rev No', related='company_id.po_rev_no', readonly=False)
    po_doc_no = fields.Char(string='PO Terms & Condition Doc No', related='company_id.po_doc_no', readonly=False)
    po_rev_date = fields.Date(string='PO Terms & Condition Date', related='company_id.po_rev_date', readonly=False)

    picking_rev_no = fields.Char(string='Picking Rev No', related='company_id.picking_rev_no', readonly=False)
    picking_doc_no = fields.Char(string='Picking Doc No', related='company_id.picking_doc_no', readonly=False)
    picking_rev_date = fields.Date(string='Picking Date', related='company_id.picking_rev_date', readonly=False)

    receipt_rev_no = fields.Char(string='Receipt Rev No', related='company_id.receipt_rev_no', readonly=False)
    receipt_doc_no = fields.Char(string='Receipt Doc No', related='company_id.receipt_doc_no', readonly=False)
    receipt_rev_date = fields.Date(string='Receipt Date', related='company_id.receipt_rev_date', readonly=False)

    checklist_rev_no = fields.Char(string='Checklist Rev No',related='company_id.checklist_rev_no', readonly=False)
    checklist_doc_no = fields.Char(string='Checklist Doc No',related='company_id.checklist_doc_no',readonly=False)
    checklist_rev_date = fields.Date(string='Checklist Date',related='company_id.checklist_rev_date',readonly=False)

    packing_rev_no = fields.Char(string='Packing List Rev No', related='company_id.packing_rev_no', readonly=False)
    packing_doc_no = fields.Char(string='Packing List Doc No', related='company_id.packing_doc_no', readonly=False)
    packing_rev_date = fields.Date(string='Packing List Date', related='company_id.packing_rev_date', readonly=False)

    gate_pass_rev_no = fields.Char(string='Gate Pass Rev No', related='company_id.gate_pass_rev_no', readonly=False)
    gate_pass_doc_no = fields.Char(string='Gate Pass Doc No', related='company_id.gate_pass_doc_no', readonly=False)
    gate_pass_rev_date = fields.Date(string='Gate Pass Date', related='company_id.gate_pass_rev_date', readonly=False)


