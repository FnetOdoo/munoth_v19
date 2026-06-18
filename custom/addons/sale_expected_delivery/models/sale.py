# -*- coding: utf-8 -*-

from odoo import models, fields, api
from datetime import timedelta


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    model_id = fields.Many2one('product.model', string="Model")
    delivery_id = fields.Many2one('mrp.delivery', string="Estimation Plan")
    bom_line_ids = fields.One2many('sale.bom.line', 'sale_id', string="BOM Lines")
    required_qty = fields.Float('Required Qty', digits='Product Unit of Measure')
    date_start = fields.Date('Start Date')
    date_end = fields.Date('Expected Delivery Date')
    stock_status = fields.Selection([('full', 'Fully Available'), ('no', 'Not Available'), ('partial', 'Partially Available')], string="Stock Status(MRP)")
    delivery_date_request_count = fields.Integer(compute='_compute_mrp_request_count')
    purchase_order_attachment_ids = fields.Many2many('ir.attachment')
    quotation_sent_date = fields.Date()

    def _compute_mrp_request_count(self):
        for rec in self:
            rec.delivery_date_request_count = self.env['mrp.estimation'].search_count([('sale_order_id', '=', rec.id)])


    def action_view_delivery_date_request(self):
        records = self.env['mrp.estimation'].search([('sale_order_id', '=', self.id)])

        if len(records) == 1:
            return {
                'name': ('Delivery Date Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mrp.estimation',
                'res_id': records.id,  # Assuming records is a single record
            }
        else:
            return {
                'name': ('Delivery Date Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'res_model': 'mrp.estimation',
                'domain': [('sale_order_id', '=', self.id)]
            }

    def message_post(self, **kwargs):
        res = super(SaleOrder, self).message_post(**kwargs)
        if self.env.context.get('mark_so_as_sent'):
            self.quotation_sent_date = fields.Date.today()

        return res

    @api.onchange('model_id')
    def onchange_model_id(self):
        self.ensure_one()
        if self.model_id:
            delivery_id = self.env['mrp.delivery'].search([('model_id', '=', self.model_id.id)], limit=1)
            self.delivery_id = delivery_id.id if delivery_id else False
            if delivery_id:
                bom_line_ids = self.bom_line_ids.browse([])
                for r in delivery_id.line_ids:
                    bom_line_ids += bom_line_ids.new({
                        'product_id': r.product_id.id,
                        'product_uom_id': r.product_uom_id.id,
                        'product_qty': r.product_qty
                    })
                self.bom_line_ids = bom_line_ids
        else:
            self.bom_line_ids = False


class MrpDeliveryLine(models.Model):
    _name = 'sale.bom.line'
    _description = 'Sales BOM Line'

    sale_id = fields.Many2one('sale.order', 'Sale')
    product_id = fields.Many2one('product.product', 'Product', check_company=True, required=True)
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.relative_uom_id', readonly=True)
    product_uom_id = fields.Many2one('uom.uom', string='Unity of measure', required=True,
                                     domain="[('relative_uom_id', '=', product_uom_category_id)]")
    product_qty = fields.Float('Required Qty', digits='Product Unit of Measure', compute='_get_qty')
    company_id = fields.Many2one('res.company', string="Company", related='sale_id.company_id')
    available_qty = fields.Float('Available Qty', digits='Product Unit of Measure', compute='_get_qty', store=True)
    status = fields.Selection([('full', 'Fully Available'), ('no', 'Not Available'), ('partial', 'Partially Available')], default='no', compute='_get_qty', store=True)

    @api.depends('product_id', 'product_qty', 'product_uom_id', 'sale_id.required_qty')
    def _get_qty(self):
        for rec in self:
            product_qty = 0
            available_qty = 0
            status = 'no'
            locations = self.env['stock.location'].search([('usage', '=', 'internal'), ('company_id', '=', rec.company_id.id)], limit=1)
            for location in locations:
                available_qty += self.env['stock.quant']._get_available_quantity(rec.product_id, location, strict=True)
            if rec.sale_id.delivery_id:
                for line in rec.sale_id.delivery_id.line_ids.filtered(lambda x: x.product_id.id == rec.product_id.id):
                    product_qty += ((rec.sale_id.required_qty / rec.sale_id.delivery_id.product_qty or 1)*line.product_qty)
            if product_qty <= available_qty:
                status = 'full'
            elif available_qty > 0:
                status = 'partial'
            rec.product_qty = product_qty
            rec.status = status
            rec.available_qty = available_qty


class SaleOrderLIne(models.Model):
    _inherit = 'sale.order.line'
    _description = 'Sale Order Line'

    expected_delivery_date = fields.Date(string='Delivery Date')

    def estimate_delivery_date_calculation(self):
        for rec in self:
            production_estimation = self.env['mrp.estimation'].create({
                'product_id': rec.product_id.id,
                'qty': rec.product_uom_qty,
                'sale_order_id' : rec.order_id.id,
                'sale_order_line_id': rec.id,
                'sale_state': rec.state
            })
            for estimate in production_estimation:
                warehouse_id = self.env['stock.warehouse'].search([('company_id', '=', estimate.company_id.id)], limit=1)
                estimate.location_id = warehouse_id.lot_stock_id.id
                estimate.action_update_stock_qty()
                in_process = self.env['production.plan'].search(
                    [('product_id', '=', estimate.product_id.id), ('state', '=', 'in_production')])
                if in_process:
                    qty = sum(in_process.mapped('expected_production_qty'))
                    estimate.in_process_qty = qty


class MrpEstimation(models.Model):
    _inherit = 'mrp.estimation'

    sale_order_id = fields.Many2one('sale.order')
    sale_order_line_id = fields.Many2one('sale.order.line')
    sale_state = fields.Selection([
        ('draft', 'Quotation'),
        ('sent', 'Quotation Sent'),
        ('sale', 'Sales Order'),
        ('done', 'Locked'),
        ('cancel', 'Cancelled'),
    ], string='Sale Status', readonly=True, copy=False, index=True, default='draft', related='sale_order_id.state')


    def action_confirm_delivery_date(self):
        for rec in self:
            if rec.sale_order_line_id:
                end_dates = rec.stage_ids.mapped('expected_end_date')
                if end_dates:
                    max_date = max(end_dates)
                    rec.sale_order_line_id.expected_delivery_date = max_date
                    rec.sale_order_line_id.order_id.stock_status = rec.stock_status
                    rec.state= 'delivery_date_sent'
                    rec.production_date_reserved = True
                # rec.sale_order_line_id.order_id.date_start = rec.start_date
                # rec.sale_order_line_id.order_id.date_end = rec.expected_end_date

    def action_create_mrp_plan(self):
        for rec in self:
            if rec.stage_ids:
                for stage in rec.stage_ids:
                    model_id = self.env['product.model'].search([('product_id', '=', rec.product_id.id)], limit=1)
                    production_create = self.env['production.plan'].create(
                        {
                            'product_id': rec.product_id.id,
                            'mrp_stage_estimation_id': rec.id,
                            'expected_production_qty': stage.production_qty,
                            'date_start': stage.start_date,
                            'expected_end_date': stage.expected_end_date,
                            'model_id': model_id.id
                        }
                    )
                    rec.state = 'production_created'

    def action_expiry_estimation(self):
        estimation_ids = self.env['mrp.estimation'].search([('state', 'in', ['draft', 'delivery_date_sent'])])
        for estimate in estimation_ids:
            if estimate.sale_order_line_id:
                if estimate.sale_order_line_id.state in ['sent', 'draft'] and estimate.sale_order_line_id.expected_delivery_date:
                    if estimate.sale_order_line_id.expected_delivery_date < fields.Date.today():
                        estimate.production_date_reserved = False
                        estimate.state = 'expired'
                        estimate.sale_order_line_id.expected_delivery_date = False
                # if estimate.sale_order_line_id.state == 'sale' and estimate.sale_order_line_id.expected_delivery_date:

    def action_production_block_remove(self):
        estimation_ids = self.env['mrp.estimation'].search([('state', 'in', ['draft', 'delivery_date_sent']), ('sale_state', '=', 'sent')])
        for estimate in estimation_ids:
            today = fields.Date.today()
            if estimate.sale_order_id.quotation_sent_date:
                if estimate.sale_order_id.quotation_sent_date + timedelta(days=15) < today:
                    estimate.production_date_reserved = False
                    estimate.state = 'expired'
                    estimate.sale_order_line_id.expected_delivery_date = False

