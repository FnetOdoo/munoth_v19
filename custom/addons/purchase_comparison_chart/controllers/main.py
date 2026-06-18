# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http
from odoo.http import request

class ValidateBid(http.Controller):
    @http.route(['/purchase_comparison_chart/purchase_comparison/<model("purchase.requisition"):purchase_requisition_id>'], type='http', auth='public', website=True)
    def purchase_comparison(self, purchase_requisition_id, **post):
        records = []
        rfq_ids = request.env['purchase.order'].sudo().search([('requisition_id', '=', purchase_requisition_id.id)])
        for vendor in rfq_ids.mapped('partner_id'):
            lines = rfq_ids.filtered(lambda x: x.partner_id.id == vendor.id).mapped('order_line')
            product_ids = lines.mapped('product_id')
            product_lines = []
            total_amount = 0
            for product in product_ids:
                agreement_line = purchase_requisition_id.line_ids.filtered(lambda x: x.product_id.id == product.id)
                po_line = lines.filtered(lambda x: x.product_id.id == product.id)
                rate = po_line[0].price_unit if po_line else 0
                qty = agreement_line[0].product_qty if agreement_line else 0
                product_lines.append({'name': product.name,
                                      'uom': agreement_line[0].product_uom_id.name if agreement_line else '',
                                      'qty': qty,
                                      'rate': rate,
                                      'amount': qty * rate
                                      })
                total_amount += qty * rate
            vendor_dict = {'vendor_name': vendor.name, 'product_lines': product_lines, 'total_amount': total_amount}
            records.append(vendor_dict)
        return request.render('purchase_comparison_chart.purchase_comparison', {'purchase_requisition_id':purchase_requisition_id, 'records': records})