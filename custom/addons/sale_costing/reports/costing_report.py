from odoo import models, fields, api
import xlsxwriter
from copy import deepcopy
import base64
from io import StringIO


class SaleCosting(models.Model):
    _inherit = 'sale.costing'

    def print_costing(self):
        output = StringIO()
        url = '/tmp/'
        report_name = "Sale Costing Sheet"
        workbook = xlsxwriter.Workbook(url + report_name + '.xlsx')
        worksheet = workbook.add_worksheet()
        border_width = 2
        merge_format1 = workbook.add_format({'font_size': 11, 'align': 'left', 'font_name': 'Liberation Serif', 'border': border_width, 'fg_color': 'yellow'})
        merge_format1_1 = workbook.add_format({'font_size': 11, 'align': 'left', 'font_name': 'Liberation Serif', 'border': border_width, 'fg_color': 'orange'})
        merge_format1_2 = workbook.add_format({'bold': 1, 'font_size': 11, 'align': 'left', 'font_name': 'Liberation Serif', 'border': border_width, 'fg_color': 'yellow'})
        merge_format2 = workbook.add_format({'font_size': 11, 'bold':1,  'align': 'center', 'font_name': 'Liberation Serif', 'border': border_width})
        merge_format2_1 = workbook.add_format({'font_size': 11, 'bold':1,  'align': 'center', 'font_name': 'Liberation Serif', 'border': border_width, 'fg_color': 'yellow'})
        merge_format2_2 = workbook.add_format({'font_size': 11, 'bold':1,  'align': 'left', 'font_name': 'Liberation Serif', 'border': border_width})
        merge_format3 = workbook.add_format({'font_size': 11, 'align': 'left', 'font_name': 'Liberation Serif', 'border': border_width})
        merge_format3_1 = workbook.add_format({'font_size': 11, 'align': 'center', 'font_name': 'Liberation Serif', 'border': border_width})
        merge_format3_2 = workbook.add_format({'num_format': '#,##0.00', 'font_size': 11, 'align': 'right', 'font_name': 'Liberation Serif', 'border': border_width})


        worksheet.set_column('A:A', 5)
        worksheet.set_column('B:B', 25)
        worksheet.set_column('C:C', 15)
        worksheet.set_column('D:G', 10)

        worksheet.write('B3', 'Dome EID No.:', merge_format1)
        worksheet.write('C3', self.agreement_id.name, merge_format2)
        worksheet.write('B4', 'Enquiry No.:', merge_format1)
        worksheet.write('C4', self.agreement_id.oppor_id.opportunity_name, merge_format2)
        worksheet.write('B5', 'Customer:', merge_format1)
        worksheet.write('C5', self.partner_id.name, merge_format2)
        worksheet.write('B6', 'Supplier:', merge_format1)
        worksheet.write('C6', self.partner_id.name, merge_format2)
        worksheet.write('B7', 'Basis FOB/CIF/Local:', merge_format1)
        worksheet.write('C7', '', merge_format2)
        worksheet.write('B8', 'Supplier Currency:', merge_format1)
        worksheet.write('C8', self.currency_id.name, merge_format2)
        worksheet.write('B9', 'Quoting Currency:', merge_format1)
        worksheet.write('C9', self.to_currency_id.name, merge_format2)
        worksheet.write('B10', 'Exchange Rate (Supplier:Quoting):', merge_format1)
        worksheet.write('C10', self.conversion_rate, merge_format2_1)
        worksheet.write('B11', 'Margin %:', merge_format1)
        worksheet.write('C11', self.margin_percentage, merge_format2_1)


        # worksheet.merge_range('E4:E5', 'Man hours used to date', merge_format2)
        worksheet.write('A13', "No", merge_format1_2)
        worksheet.write('B13', "Description", merge_format1_2)
        worksheet.write('C13', "Qty (KG)", merge_format1_2)
        worksheet.write('D13', "Unit CP", merge_format1_2)
        worksheet.write('E13', "Tot.CP(%s)" % self.currency_id.name, merge_format2)
        worksheet.write('F13', "U/ SP", merge_format2)
        worksheet.write('G13', "Tot.SP (%s)" % self.to_currency_id.name, merge_format2)
        n = 14
        count = 1
        for line in self.line_ids:
            worksheet.write('A' + str(n),count , merge_format3_1)
            worksheet.write('B' + str(n), line.product_id.name, merge_format3)
            worksheet.write('C' + str(n), line.product_uom_qty, merge_format3_1)
            worksheet.write('D' + str(n), line.price_unit, merge_format3_2)
            worksheet.write('E' + str(n), line.price_subtotal, merge_format3_2)
            worksheet.write('F' + str(n), line.unit_sale_price, merge_format3_2)
            worksheet.write('G' + str(n), line.sale_price, merge_format3_2)
            n += 1
            count += 1
        worksheet.write('D' + str(n), "Total", merge_format2)
        worksheet.write('E' + str(n), sum(self.line_ids.mapped('price_subtotal')), merge_format2)
        worksheet.write('F' + str(n), "Total", merge_format2)
        worksheet.write('G' + str(n), sum(self.line_ids.mapped('sale_price')), merge_format2)
        n += 1
        worksheet.write('B' + str(n), 'Total Ex-works', merge_format2_2)
        worksheet.write('C' + str(n), sum(self.line_ids.mapped('price_subtotal')), merge_format2)
        n += 1
        for other in self.other_lines.filtered(lambda x: x.cost_type == 'work'):
            worksheet.write('B' + str(n), other.name.name, merge_format3)
            worksheet.write('C' + str(n), other.price_total, merge_format3_2)
            n += 1
        worksheet.write('B' + str(n), "Total CIF(Supplier Currency)", merge_format2_2)
        total_ex_work = sum(self.line_ids.mapped('price_subtotal'))+sum(self.other_lines.filtered(lambda x: x.cost_type == 'work').mapped('price_total'))
        worksheet.write('C' + str(n), total_ex_work, merge_format3_2)
        n += 1
        work_cost_selling_currnecy = total_ex_work*self.conversion_rate
        worksheet.write('B' + str(n), "Total  CIF(Selling Currency) ", merge_format2_2)
        worksheet.write('C' + str(n), work_cost_selling_currnecy, merge_format3_2)
        n += 1
        for other in self.other_lines.filtered(lambda x: x.cost_type == 'landed'):
            worksheet.write('B' + str(n), other.name.name, merge_format3)
            worksheet.write('C' + str(n), other.selling_price_total, merge_format3_2)
            n += 1
        landed_cost = sum(self.other_lines.filtered(lambda x: x.cost_type == 'landed').mapped('selling_price_total')) + work_cost_selling_currnecy
        worksheet.write('B' + str(n), "Total Landed Cost", merge_format1_1)
        worksheet.write('C' + str(n), landed_cost, merge_format1_1)
        n += 1
        for other in self.other_lines.filtered(lambda x: x.cost_type == 'other'):
            worksheet.write('B' + str(n), other.name.name, merge_format3)
            worksheet.write('C' + str(n), other.price_total, merge_format3_2)
            n += 1
        other_cost = sum(self.other_lines.filtered(lambda x: x.cost_type == 'other').mapped(
            'selling_price_total')) + landed_cost
        worksheet.write('B' + str(n), "Total Cost", merge_format1_1)
        worksheet.write('C' + str(n), other_cost, merge_format1_1)
        n += 1
        worksheet.write('B' + str(n), "Margin", merge_format3)
        worksheet.write('C' + str(n), self.margin_price_total, merge_format3_2)
        n += 1
        worksheet.write('B' + str(n), "SELLING PRICE", merge_format2_2)
        worksheet.write('C' + str(n), self.sale_amount_total, merge_format2)
        n += 1
        worksheet.write('B' + str(n), "PRICING FACTOR", merge_format2_2)
        worksheet.write('C' + str(n), (self.sale_amount_total/(sum(self.line_ids.mapped('price_subtotal'))*self.conversion_rate)), merge_format2)
        workbook.close()
        fo = open(url + report_name +'.xlsx', "rb+")
        values = {
            'name': report_name + '.xlsx',
            'res_model': 'ir.ui.view',
            'res_id': False,
            'type': 'binary',
            'public': True,
            'datas': base64.encodestring(fo.read()),
        }
        attachment_id = self.env['ir.attachment'].sudo().create(values)
        download_url = '/web/content/' + str(attachment_id.id) + '?download=True'
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        return {
            "type": "ir.actions.act_url",
            "url": str(base_url) + str(download_url),
            "target": "new",
        }
