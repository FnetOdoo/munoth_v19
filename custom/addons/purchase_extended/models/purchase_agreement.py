from odoo import models, fields,api,_
from odoo.exceptions import UserError, ValidationError

class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    @api.model
    def _get_picking_in(self):
        type_obj = self.env['stock.picking.type']
        company_id = self.env.context.get('company_id') or self.env.user.company_id.id
        types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id.company_id', '=', company_id)])

        if not types:
            types = type_obj.search([('code', '=', 'incoming'), ('warehouse_id', '=', False)])

        return types[:1]

    lead_id = fields.Many2one('crm.lead', 'Enquiry Reference')
    bid_received_line = fields.One2many('bid.received.line', 'tender_id', 'Sale Quotes')
    customer_id = fields.Many2one('res.partner', 'Customer Name')
    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type', required=False, default=_get_picking_in)
    schedule_date = fields.Date(string='Delivery Date')

    @api.model_create_multi
    def create(self, vals_list):
        records = super(PurchaseRequisition, self).create(vals_list)
        for record in records:
            record.name = self.env['ir.sequence'].next_by_code('new.purchase.requisition') or 'New'
        return records

    def create_rfq(self):
        if not self.line_ids:
            raise UserError("No Products Found..!")

        vendors = self.line_ids.mapped('vendor_ids')
        for vendor in vendors:
            lines = self.line_ids.filtered(lambda x: vendor.id in x.vendor_ids.ids)
            if lines:
                fpos = self.env['account.fiscal.position'].sudo()._get_fiscal_position(vendor)

                po_creation = {
                    'partner_id': vendor.id,
                    'fiscal_position_id': fpos.id if fpos else False,
                    'payment_term_id': vendor.property_supplier_payment_term_id.id or False,
                    'company_id': self.company_id.id,
                    'currency_id': self.company_id.currency_id.id,
                    'origin': self.name,
                    'partner_ref': self.name,
                    # 'notes': self.description,
                    # 'date_order': self.date_end or fields.Datetime.now(),
                    'picking_type_id': self.picking_type_id.id,
                    'requisition_id': self.id,
                }
                order = self.env['purchase.order'].create(po_creation)

                for line in lines:
                    seller = line.product_id.seller_ids.filtered(
                        lambda s: s.partner_id.id == vendor.id  # ✅ fixed
                    )
                    price_unit = seller[0].price if seller else 0.0

                    order_lines = {
                        'name': line.product_id.description or line.product_id.name,
                        'product_id': line.product_id.id,
                        'product_uom_id': line.product_uom_id.id,
                        'product_qty': line.product_qty,
                        'price_unit': price_unit,
                        'date_planned': self.schedule_date or fields.Date.today(),
                        'analytic_distribution': line.analytic_distribution or {},
                        'requisition_line_id': line.id,
                        'order_id': order.id,
                    }
                    self.env['purchase.order.line'].create(order_lines)

    def action_open(self):
        if not self.bid_received_line:
            raise UserError(_('No bids available for validate.'))
        for bid in self.bid_received_line:
            if bid.valid_qoute and bid.qty_selected <= 0:
                raise UserError(_("Selected bid must have the confirm qty."))
        not_selected_bids = self.bid_received_line.filtered(lambda x: not x.valid_qoute or x.qty_selected == 0)
        selected_bids = self.bid_received_line.filtered(lambda x: x.valid_qoute)
        for line in self.line_ids:
            bids = selected_bids.filtered(lambda x: x.requisition_line_id.id == line.id)
            if bids and line.product_qty != sum(
                    selected_bids.filtered(lambda x: x.requisition_line_id.id == line.id).mapped('qty_selected')):
                raise UserError(_("Product quantity and Bid confirmed quantity must be same."))
        for line in selected_bids:
            if line.purchase_order_line_id:
                line.purchase_order_line_id.update({'product_qty': line.qty_selected})
        for bid in not_selected_bids:  # Canceling whole po if not used otherwise remove not selected line
            if bid.purchase_order_id:
                if selected_bids.filtered(lambda x: x.purchase_order_id.id == bid.purchase_order_id.id):
                    if bid.purchase_order_line_id:
                        bid.purchase_order_line_id.unlink()
                    continue
                bid.purchase_order_id.button_cancel()
        self.state = 'open'

    def action_done(self):
        res = super(PurchaseRequisition, self).action_done()
        for rec in self:
            if any(po.state not in ['purchase', 'done', 'cancel'] for po in rec.purchase_ids):
                raise UserError(_("Please cancel or confirm the RFQ to close the agreement."))


class BidReceivedLine(models.Model):
    _name = 'bid.received.line'
    _description = 'bid_received_line'

    tender_id = fields.Many2one('purchase.requisition', 'Tender Reference')
    valid_qoute = fields.Boolean('Select')
    purchase_order_id = fields.Many2one('purchase.order', 'Purchase Quotes', readonly=True)
    purchase_order_line_id = fields.Many2one('purchase.order.line', 'Purchase Line', readonly=True)
    vender_id = fields.Many2one('res.partner', 'Supplier', readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    quantity = fields.Float('Quantity', readonly=True)
    unit_measure = fields.Many2one('uom.uom', 'Unit of Measure', readonly=True)
    purchase_unit_price = fields.Float('Purchase Unit Price', readonly=True)
    unit_price = fields.Float('Unit Price', readonly=True)
    purchase_total_price = fields.Float('Purchase Price', readonly=True)
    sub_total = fields.Float('Sub Total', readonly=True)
    qty_selected = fields.Float('Confirm Qty')
    requisition_line_id = fields.Many2one('purchase.requisition.line', string="Requisition Line",
                                          related='purchase_order_line_id.requisition_line_id')


class PurchaseRequisitionLine(models.Model):
    _inherit = 'purchase.requisition.line'

    vendor_ids = fields.Many2many('res.partner', string="Vendor")

