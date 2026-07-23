from odoo import models, fields, api,_
import json
from num2words import num2words
import ast
import xlsxwriter
from reportlab.lib.pagesizes import letter
from reportlab.lib import pdfencrypt
from reportlab.pdfgen import canvas
import io
import base64

import PyPDF2

class SaleOrder(models.Model):
    _inherit="sale.order"

    amount_total_words = fields.Char("Total (In Words)", compute="_compute_amount_total_words")

    @api.depends('order_line.tax_ids', 'order_line.price_total')
    def _compute_tax_details(self):
        for order in self:
            tax_details = {}
            for line in order.order_line:
                for tax in line.tax_ids:
                    tax_amount = \
                        tax.compute_all(line.price_unit, line.currency_id, line.product_uom_qty,
                                        product=line.product_id)[
                            'taxes'][0]['amount']
                    tax_detail = {
                        'rate': tax.amount,
                        'amount': tax_amount,
                    }
                    tax_name = tax.name or 'No Tax'
                    if tax_name in tax_details:
                        tax_details[tax_name].append(tax_detail)
                    else:
                        tax_details[tax_name] = [tax_detail]
            order.tax_details = tax_details

    tax_details = fields.Text(string='Tax Details', compute='_compute_tax_details')

    def _compute_tax_percent(self, obj):
        for line in self:
            tax_details = {}
            return tax_details

    def _compute_tax_percent_1(self, obj):
        taxes = obj.order_line.mapped('tax_ids')
        tax_value=[]
        for tax in taxes:
            lines = obj.order_line.filtered(lambda x: tax.id in x.tax_ids.ids)
            # for line in lines:
            if tax.amount_type == 'group':
                for child in tax.children_tax_ids:
                    # dict_taxes = child.compute_all(lines.mapped('price_subtotal'), obj.currency_id)
                    tax_amt = 0
                    for line in lines:
                        tax_amt += child.compute_all(line.price_subtotal, line.order_id.currency_id, line.product_uom_qty)['taxes'][0]['amount']
                    tax_value.append({
                        'name':child.tax_group_id.name or tax.name,
                        'price_tax': child.amount,
                        'price_subtotal':tax_amt,
                    })
            else:
                tax_amt = 0
                for line in lines:
                    tax_amt += tax.compute_all(line.price_subtotal, line.order_id.currency_id, line.product_uom_qty)['taxes'][0]['amount']
                tax_value.append({
                    'name': tax.tax_group_id.name or tax.name,
                    'price_tax':tax.amount,
                    'price_subtotal':tax_amt,
                    })
        return tax_value



    # Migration v15→v19: tax_totals_json removed in v17+; replaced with tax_totals (dict)
    # @api.depends kept pointing to amount_total which still triggers correctly
    @api.depends('amount_total')
    def _compute_amount_total_words(self):
        for invoice in self:
            invoice.amount_total_words = invoice.currency_id.amount_to_text(invoice.amount_total)

class PurchaseOrder(models.Model):
    _inherit='purchase.order'

    amount_total_words = fields.Char("Total (In Words)", compute="_compute_amount_total_words")
    round_amount = fields.Char(string='Round Amount', compute='_compute_round_amount', )


    # Migration v15→v19: tax_totals_json removed in v17+; use amount_total as trigger
    @api.depends('amount_total')
    def _compute_amount_total_words(self):
        for invoice in self:
            invoice.amount_total_words = invoice.currency_id.amount_to_text(invoice.amount_in_company_currency)

    def _compute_tax_percent_2(self):
        taxes = self.order_line.mapped('taxes_id')
        tax_value = []
        for tax in taxes:
            lines = self.order_line.filtered(lambda x: tax.id in x.taxes_id.ids)
            # for line in lines:
            if tax.amount_type == 'group':
                for child in tax.children_tax_ids:
                    # dict_taxes = child.compute_all(lines.mapped('price_subtotal'), obj.currency_id)
                    tax_amt = 0
                    for line in lines:
                        tax_amt += child.compute_all(line.price_subtotal, line.order_id.currency_id, line.product_uom_qty)[
                            'taxes'][0]['amount']
                    tax_value.append({
                        'name': child.tax_group_id.name or tax.name,
                        'price_tax': child.amount,
                        'price_subtotal': tax_amt,
                    })
            else:
                tax_amt = 0
                for line in lines:
                    tax_amt += tax.compute_all(line.price_subtotal, line.order_id.currency_id, line.product_uom_qty)['taxes'][0][
                        'amount']
                tax_value.append({
                    'name': tax.tax_group_id.name or tax.name,
                    'price_tax': tax.amount,
                    'price_subtotal': tax_amt,
                })
        return tax_value

    def _compute_round_amount(self):
        for order in self:
            value= sum(order.order_line.mapped('dicount_amount'))
            return value

    def round_off(self, json_data):
        try:
            data_dict = json.loads(json_data)
            rounded_totals = []
            for item in data_dict.get('subtotal'):
                total_amount = sum(item.get('tax_amount', 0))
                rounded_total = round(total_amount)
                rounded_totals.append(rounded_total)
            return rounded_totals
        except json.JSONDecodeError as e:
            print(f"JSON decoding error: {e}")
            return None




    def get_total_pages(self, obj):
        # Create a PDF canvas with dummy content to calculate the total pages
        # buffer = io.BytesIO()
        # pdf = canvas.Canvas(buffer, pagesize=letter)
        # pdf.drawString(100, 100, "Your Dummy Content Here")
        # pdf.save()
        report_name = "munoth_reports.po_to_vendor_report1"
        report_output =self.env.ref('munoth_reports.po_to_vendor_report1')._render_qweb_pdf(obj.id)

        # `report_output` is a tuple where `report_output[0]` is the binary output
        # and `report_output[1]` is the "converter" (in this case, "pdf").
        # report_output = report.render_qweb_pdf(obj)


        # Calculate the total pages
        # pdf_bytes = base64.b64encode(report_output[0])
        # Migration v15→v19: PyPDF2.PdfFileReader.numPages renamed to len(reader.pages) in PyPDF2 v3+
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(report_output[0]))
        total_pages = len(pdf_reader.pages)
        return total_pages

class PurchaseOrderLine(models.Model):
    _inherit='purchase.order.line'

    dicount_amount=fields.Integer(string="% Discount Amount")


class StockMove(models.Model):
    _inherit='stock.move'

    final_description=fields.Char(string="Final Package Dimension")
    total_gross=fields.Char(string="Total Gross Weight")
    net_weight=fields.Char(string="Net Weight")
    total_net_weight=fields.Char(string="Total Net Weight")
    remarks=fields.Char(string='Remarks')

class StockMoveLine(models.Model):
    _inherit='stock.move.line'

    boxes = fields.Char()
    box_count = fields.Char()
    update_boxes = fields.Many2one('gate.pass.boxes')
    pallets_ids = fields.One2many('pallets', 'stock_move_line_id', string="Pallets")

    @api.model
    def create(self, vals_list):
        # Ensure vals_list is always a list
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        move_lines = super(StockMoveLine, self).create(vals_list)

        for move_line, vals in zip(move_lines, vals_list):
            qty = vals.get('boxes', 0)

            for i in range(int(qty)):
                self.env['pallets'].create({
                    'stock_move_line_id': move_line.id,
                    'product_id': move_line.product_id.id,
                    'qty_done': move_line.qty_done,
                    'product_uom_id': move_line.product_uom_id.id,
                    'stock_picking_id': move_line.picking_id.id,
                })

        return move_lines

    # def write(self, vals):
    #     res = super(StockMoveLine, self).write(vals)
    #     if 'boxes' in vals:
    #         qty = vals.get('boxes', 0)
    #         print("-----------", qty,"-----qty------\n")
    #         self.pallets_ids.unlink()
    #         for rec in range(int(qty)):
    #             print("-----------", rec,"-----rec------\n")
    #             self.env['pallets'].create({
    #                 'stock_move_line_id': self.id,
    #                 'product_id': self.product_id.id,
    #                 'qty_done': self.qty_done,
    #                 'product_uom_id': self.product_uom_id.id,
    #                 'stock_picking_id': self.picking_id.id,
    #             })
    #     return res

    # def write(self, vals):
    #     print("--------", 44444444444,"----44444444444---\n")
    #     res = super(StockMoveLine, self).write(vals)
    #
    #     if 'boxes' in vals:
    #         qty = int(vals.get('boxes', 0))
    #         pallets_obj = self.env['pallets']
    #
    #         for move_line in self:
    #             # Unlink existing pallets in one go
    #             move_line.pallets_ids.unlink()
    #             print("--------", move_line.pallets_ids.ids,"----move_line.pallets_ids.ids---\n")
    #
    #             # Create all pallet records in batch (more efficient than inside loop)
    #             pallet_vals = [{
    #                 'stock_move_line_id': move_line.id,
    #                 'product_id': move_line.product_id.id,
    #                 'qty_done': move_line.qty_done,
    #                 'product_uom_id': move_line.product_uom_id.id,
    #                 'stock_picking_id': move_line.picking_id.id,
    #             } for _ in range(qty)]
    #             print("--------", pallet_vals,"----pallet_vals---\n")
    #             pallets_obj.create(pallet_vals)
    #         print("--------", 222222222222222222,"----Finished---\n")
    #     return res

    def action_update_boxes(self):
        view_id = self.env.ref('munoth_reports.gate_pass_boxes_wizard', False)
        if not self.update_boxes:
            self.update_boxes = self.env['gate.pass.boxes'].create({
                'stock_move_line': self.id
            })

        return {
            'name': _('Boxes'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'gate.pass.boxes',
            'views': [(view_id.id, 'form')],
            'view_id': view_id.id,
            'target': 'new',
            'res_id': self.update_boxes.id,
            'context': {
                'default_stock_move_line': self.id,
            },
        }

class Pallets(models.Model):
    _name = 'pallets'

    stock_move_line_id = fields.Many2one('stock.move.line')
    stock_picking_id = fields.Many2one('stock.picking')


    product_id = fields.Many2one('product.product')
    qty_done = fields.Float()
    product_uom_id = fields.Many2one('uom.uom')


class StockPicking(models.Model):
    _inherit='stock.picking'

    items=fields.Boolean(string='Ordered Items')
    pallets_ids = fields.One2many('pallets','stock_picking_id')

    def action_update_boxes(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Update Boxes Wizard',
            'res_model': 'update.boxes.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_stock_picking_id': self.id},
        }

    # def action_download_sample_format(self):
    #     output = io.BytesIO()
    #     workbook = xlsxwriter.Workbook(output)
    #     sheet = workbook.add_worksheet('Sample Format')
    #
    #     # Write headers
    #     sheet.write(0, 0, 'Stock Move Line ID')
    #     sheet.write(0, 1, 'Boxes')
    #
    #     workbook.close()
    #
    #     sample_file = base64.b64encode(output.getvalue())
    #     output.close()
    #
    #     return {
    #         'type': 'ir.actions.act_url',
    #         'url': f'/web/content?model=update.boxes.wizard&id={self.id}&field=upload_file&filename_field=file_name&download=true',
    #         'target': 'self',
    #     }

    def action_pallet_details(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Pallet Product Wizard',
            'res_model': 'pallet.product',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_wizard_id': self.id,
            }
        }

    # def get_total_pages2(self, obj):
    #     # Create a PDF canvas with dummy content to calculate the total pages
    #     # buffer = io.BytesIO()
    #     # pdf = canvas.Canvas(buffer, pagesize=letter)
    #     # pdf.drawString(100, 100, "Your Dummy Content Here")
    #     # pdf.save()
    #     report_name = "munoth_reports.good_received_report_1"
    #     report_output =self.env.ref('munoth_reports.good_received_report_1')._render_qweb_pdf(obj.id)
    #
    #     # `report_output` is a tuple where `report_output[0]` is the binary output
    #     # and `report_output[1]` is the "converter" (in this case, "pdf").
    #     # report_output = report.render_qweb_pdf(obj)
    #
    #
    #     # Calculate the total pages
    #     # pdf_bytes = base64.b64encode(report_output[0])
    #     pdf_reader = PyPDF2.PdfFileReader(io.BytesIO(report_output[0]))
    #     # PyPDF2.PdfFileReader(file)
    #     total_pages = pdf_reader.numPages
    #     return total_pages
    def action_download_update_boxes(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet("Update Boxes")

        format_header = workbook.add_format({'bold': True, 'bg_color': '#486646', 'font_color': 'white'})
        format_text = workbook.add_format({'font_name': 'Arial'})

        sheet.set_row(0, 20)
        sheet.set_column('B:B', 30)
        # sheet.set_column('C:C', 30)
        # sheet.set_column('D:G', 30)
        # sheet.set_column('H:H', 30)
        # sheet.set_column('I:I', 30)
        # Writing headers
        sheet.write(0, 0, 'S.No', format_header)
        sheet.write(0, 1, 'Lot/Serial Number', format_header)
        sheet.write(0, 2, 'Boxes', format_header)
        sheet.write(0, 3, 'Done', format_header)
        # sheet.write(0, 2, 'Location', format_header)
        # sheet.write(0, 4, 'Boxes', format_header)
        # sheet.write(0, 5, 'Reserved', format_header)
        # sheet.write(0, 6, 'Done', format_header)
        # sheet.write(0, 7, 'Unit', format_header)

        s_no = 1
        row = 1  # Start from row 1 (row 0 is for headers)

        for rec in self.move_line_ids:
            sheet.write(row, 0, s_no, format_text)  # Column 0 -> 'S.No'
            sheet.write(row, 1, rec.lot_id.name if rec.lot_id.name else '', format_text)
            sheet.write(row, 2, rec.boxes if rec.boxes else False, format_text)
            sheet.write(row, 3, rec.quantity if rec.quantity else False, format_text)
            # sheet.write(row, 1, rec.product_id.name if rec.product_id.name else '', format_text)  # Column 1 -> 'Boxes'
            # sheet.write(row, 2, rec.location_id.name if rec.location_id.name else '', format_text)  # Column 1 -> 'Boxes'
            # sheet.write(row, 3, rec.lot_id.name if rec.lot_id.name else '', format_text)  # Column 1 -> 'Boxes'
            # sheet.write(row, 4, rec.boxes if rec.boxes else False, format_text)  # Column 1 -> 'Boxes'
            # sheet.write(row, 5, rec.product_uom_qty if rec.product_uom_qty else False, format_text)  # Column 1 -> 'Boxes'
            # sheet.write(row, 6, rec.qty_done if rec.qty_done else False, format_text)  # Column 1 -> 'Boxes'
            # sheet.write(row, 7, rec.product_uom_id.name if rec.product_uom_id.name else '', format_text)  # Column 1 -> 'Boxes'
            s_no += 1
            row += 1

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.getvalue())

        attachment = self.env['ir.attachment'].create({
            'name': 'Delivered Cells.xlsx',
            'datas': file_data,
            'res_model': 'stock.move',
            'type': 'binary',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_download_update_boxes_sample(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)
        sheet = workbook.add_worksheet("Update Boxes")

        format_header = workbook.add_format({'bold': True, 'bg_color': '#486646', 'font_color': 'white'})
        format_text = workbook.add_format({'font_name': 'Arial'})

        sheet.set_row(0, 20)
        sheet.set_column('B:B', 30)

        # Match the columns the upload wizard actually expects
        sheet.write(0, 0, 'S.No', format_header)
        sheet.write(0, 1, 'Lot/Serial Number', format_header)
        sheet.write(0, 2, 'Boxes', format_header)

        s_no = 1
        row = 1

        for rec in self.move_line_ids:
            sheet.write(row, 0, s_no, format_text)
            sheet.write(row, 1, rec.lot_id.name if rec.lot_id.name else '', format_text)
            sheet.write(row, 2, rec.boxes if rec.boxes else False, format_text)
            s_no += 1
            row += 1

        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.getvalue())

        attachment = self.env['ir.attachment'].create({
            'name': 'Sample File.xlsx',
            'datas': file_data,
            'res_model': 'stock.move',
            'type': 'binary',
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

class MrpRequestMaterial(models.Model):
    _inherit='mrp.material.request'


    def get_total_pages2(self, obj):
        report_output =self.env.ref('munoth_reports.material_request_report_1')._render_qweb_pdf(obj.id)
        # Migration v15→v19: PyPDF2.PdfFileReader.numPages → len(reader.pages) (PyPDF2 v3+)
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(report_output[0]))
        total_pages = len(pdf_reader.pages)
        return total_pages


class HrPayslip(models.Model):
    _inherit='hr.payslip'

    def get_amount_in_words(self):
        return self.env.user.company_id.currency_id.amount_to_text(
            self.line_ids.filtered(lambda x: x.code == 'NET').total)

    def calculate_deductions(self):
        total_deductions = sum(self.line_ids.filtered(lambda x: x.category_id.code == 'DED').mapped('total'))
        return total_deductions



class AccountMove(models.Model):
    _inherit="account.move"

    # Migration v15→v19: states= parameter removed from fields in v17+
    # states={'draft': [('readonly', False)]} → removed; use readonly on view instead
    tds_ids = fields.Many2one('account.tax', string='TCS')
    tds_added = fields.Monetary(string='TCS Amount added',
                                store=True, readonly=True, compute='_compute_amount')
    total_tds = fields.Monetary(string='Total Amount',
                                store=True, readonly=True, compute='_compute_amount')
    total_tds_amount = fields.Monetary(string='Total Amount After TCS',
                                       store=True, readonly=True, compute='_compute_amount')
    display_declaration = fields.Boolean('Display Declaration Content')

    sale_type_id = fields.Many2one('sale.type', string="Sale Type")
    proforma_no = fields.Char(compute='_compute_proforma_invoice_no')
    proforma_date = fields.Date(compute='_compute_proforma_invoice_no')
    letter_credit = fields.Char(string='Letter of Credit Reference no')
    date_lc = fields.Date(string='Date of LC')
    buyer = fields.Char(string="Buyer's PO No")
    buyer_date = fields.Date(string="Buyer's PO Date")
    amount_total_words = fields.Char("Total (In Words)", compute="_compute_amount_total_words")

    @api.depends('amount_total', 'currency_id')
    def _compute_amount_total_words(self):
        for invoice in self:
            try:
                if invoice.currency_id.name == 'INR':  # Process only if currency is INR
                    total_amount = invoice.amount_total

                    # Separate rupees and paise
                    rupees = int(total_amount)  # Whole number part
                    paise = int(round((total_amount - rupees) * 100))  # Get paise part

                    # Convert rupees to words
                    rupees_in_words = num2words(rupees, lang='en_IN').title()

                    # Convert paise if any
                    if paise > 0:
                        paise_in_words = num2words(paise, lang='en_IN').title()
                        invoice.amount_total_words = f"{rupees_in_words} Rupees and {paise_in_words} Paise Only"
                    else:
                        invoice.amount_total_words = f"{rupees_in_words} Rupees Only"
                else:
                    invoice.amount_total_words = invoice.currency_id.amount_to_text(invoice.amount_total)
            except:
                invoice.amount_total_words = "Conversion Error"


    # def get_tax_amt(self, obj, amount):
    #     amt = num2words(amount, lang='en_IN')
    #     return amt

    def get_tax_totals(self, obj):
        # Migration v15→v19: tax_totals_json (string) removed in v17+
        # tax_totals is now a dict field directly on account.move
        tax_totals = obj.tax_totals
        values = []
        cgst = 0.0
        sgst = 0.0
        igst = 0.0
        if tax_totals and isinstance(tax_totals, dict):
            groups = tax_totals.get('groups_by_subtotal', {}).get('Untaxed Amount', [])
        else:
            groups = []
        for tax in groups:
            if tax['tax_group_name'] == 'CGST':
                cgst += tax['tax_group_amount']
            elif tax['tax_group_name'] == 'SGST':
                sgst += tax['tax_group_amount']
            elif tax['tax_group_name'] == 'IGST':
                igst += tax['tax_group_amount']
        values.append({'cgst': cgst, 'sgst': sgst, 'igst': igst})
        return values


    def turnover_compute(self, partner_id, limit, total_tds):
        # Migration v15→v19: account_id.internal_type removed in v16+
        # Use account_id.account_type instead
        # 'payable' internal_type → account_type = 'liability_payable'
        account_move = self.env['account.move.line'].search(
            [
                ('partner_id', '=', partner_id),
                ('account_id.account_type', '=', 'liability_payable'),
                ('account_id.reconcile', '=', True),
                ('move_id.state', '=', 'posted')
            ])
        account_credit = sum([account.credit for account in account_move])
        account_credit = account_credit + total_tds
        if account_credit < limit:
            return False
        else:
            return True

    @api.depends('line_ids.debit', 'line_ids.credit', 'line_ids.currency_id', 'line_ids.amount_currency',
                 'line_ids.amount_residual', 'line_ids.amount_residual_currency', 'line_ids.payment_id.state',
                 'tds_ids')
    def _compute_amount(self):
        res = super(AccountMove, self)._compute_amount()
        for account_move in self:
            account_move.tds_added = (account_move.tds_ids.amount * (account_move.total_tds / 100))
            account_move.total_tds = account_move.amount_untaxed + account_move.amount_tax
            account_move.total_tds_amount = account_move.amount_untaxed + account_move.amount_tax + account_move.tds_added
            account_move.amount_total = account_move.amount_untaxed + account_move.amount_tax + account_move.tds_added
            tds_applicable = True
            if account_move.partner_id and account_move.tds_ids:
                tds_applicable = account_move.turnover_compute(account_move.partner_id.id,
                                                               account_move.tds_ids.excess_of,
                                                               account_move.total_tds)
            if not tds_applicable:
                account_move.tds_added = 0
        return res

    # def get_tax_amt(self, obj, amount):
    #     amt = obj.currency_id.amount_to_text(amount)
    #     return amt

    # @staticmethod
    # def convert_to_inr_words(amount):
    #     amount = round(amount, 2)  # Ensure two decimal places
    #     integer_part = int(amount)
    #     decimal_part = int(round((amount - integer_part) * 100))  # Convert decimals to paise
    #
    #     words = []
    #     units = ["", "Thousand", "Lakh", "Crore", "Arab"]  # Added "Arab" to prevent index error
    #     num_parts = []
    #
    #     # Extract parts based on Indian numbering system
    #     num_parts.append(integer_part % 1000)  # Last 3 digits
    #     integer_part //= 1000
    #
    #     i = 1
    #     while integer_part > 0:
    #         num_parts.append(integer_part % 100)  # Next 2 digits
    #         integer_part //= 100
    #         i += 1
    #
    #     # Ensure index does not go out of range
    #     for index, part in enumerate(num_parts):
    #         if part and index < len(units):
    #             words.append(num2words(part, lang='en').title() + " " + units[index])
    #
    #     # Join words in reverse order (Indian format)
    #     amount_in_words = ", ".join(reversed(words)).strip()
    #
    #     # Add currency and paise part
    #     if decimal_part > 0:
    #         return f"{amount_in_words} Rupees And {num2words(decimal_part, lang='en').title()} Paise Only"
    #     return f"{amount_in_words} Rupees Only"
    #
    # def get_tax_amt(self, obj, amount):
    #     return self.convert_to_inr_words(amount)

    def _compute_proforma_invoice_no(self):
        for record in self:
            sale_order = self.env['sale.order'].search([('invoice_ids', '=', record.id)], limit=1)
            if sale_order:
                if sale_order.proforma_no:
                    record.proforma_no = sale_order.proforma_no
                else:
                    record.proforma_no = False

                if sale_order.buyer:
                    record.buyer = sale_order.buyer
                else:
                    record.buyer = False

                if sale_order.buyer_date:
                    record.buyer_date = sale_order.buyer_date
                else:
                    record.buyer_date = False

                if sale_order.proforma_invoice:
                    record.proforma_date = sale_order.proforma_invoice
                else:
                    record.proforma_date = False
            else:
                record.proforma_no = False
                record.proforma_date = False




    def get_tax_des(self, obj):
        # Migration v15→v19: account_tax_group.name is now JSONB in Odoo 19.
        # All satg.name = 'X' comparisons must use satg.name->>'en_US' = 'X'
        self.env.cr.execute('''
        SELECT hsn, price_subtotal, SUM(cgst_val) AS cgst_val, SUM(sgst_val) AS sgst_val, SUM(igst_val) AS igst_val,
        COALESCE(ROUND(SUM(cgst),2), '0') AS cgst,
        COALESCE(ROUND(SUM(sgst),2), 0) AS sgst,
        COALESCE(ROUND(SUM(igst),2),0) AS igst FROM
        (SELECT hsn, SUM(price_subtotal) AS price_subtotal,
        COALESCE(SUM((cgst * price_subtotal) / 100), 0) AS cgst_val,
        COALESCE(SUM((sgst * price_subtotal) / 100),0) AS sgst_val,
        COALESCE(SUM((igst * price_subtotal) / 100), 0) AS igst_val,
        cgst,sgst,igst FROM
        (SELECT pt.l10n_in_hsn_code AS hsn, aml.price_subtotal,        CASE WHEN at.amount_type != 'group' THEN 0 ELSE
        (SELECT atc.amount FROM account_tax_filiation_rel atf
        JOIN account_tax atc ON (atc.id = atf.child_tax)
        JOIN account_tax_group satg ON (satg.id = atc.tax_group_id)
        AND at.id = atf.parent_tax AND satg.name->>\'en_US\' = \'CGST\') END AS cgst,
        CASE WHEN at.amount_type != 'group' THEN 0 ELSE
        (SELECT atc.amount FROM account_tax_filiation_rel atf
        JOIN account_tax atc ON (atc.id = atf.child_tax)
        JOIN account_tax_group satg ON (satg.id = atc.tax_group_id)
        AND at.id = atf.parent_tax AND satg.name->>\'en_US\' = \'SGST\') END AS sgst,
        CASE WHEN at.amount_type != 'group' THEN
        (SELECT atco.amount FROM account_tax atco
        JOIN account_tax_group satgo ON (satgo.id = atco.tax_group_id)
        WHERE atco.id = at.id AND satgo.name->>\'en_US\' = \'IGST\') ELSE 0 END AS igst
        FROM account_move_line aml
        JOIN product_product pp ON (pp.id = aml.product_id)
        JOIN product_template pt ON (pt.id = pp.product_tmpl_id)
        JOIN account_move_line_account_tax_rel amr ON (amr.account_move_line_id = aml.id)
        JOIN account_tax at ON (at.id = amr.account_tax_id)
        JOIN account_tax_group atg ON (atg.id = at.tax_group_id)
        WHERE move_id = %s)temp
        GROUP BY hsn, price_subtotal, cgst, sgst, igst)temp1
        GROUP BY hsn, price_subtotal ''', (obj.id,))
        line_data = [i for i in self.env.cr.dictfetchall()]
        if line_data:
            return line_data
        else:
            return [{'price_total': 0.00, 'description': ''}]

    def get_tds_des(self, obj):
        # Migration v15→v19: account_tax_group.name is now JSONB in Odoo 19.
        # atg.name = 'TDS' → atg.name->>'en_US' = 'TDS'
        self.env.cr.execute('''
        SELECT COALESCE(SUM((at.amount * aml.price_subtotal) / 100), 0) AS total
        FROM account_move_line aml
        JOIN product_product pp ON (pp.id = aml.product_id)
        JOIN product_template pt ON (pt.id = pp.product_tmpl_id)
        JOIN account_move_line_account_tax_rel amr ON (amr.account_move_line_id = aml.id)
        JOIN account_tax at ON (at.id = amr.account_tax_id)
        JOIN account_tax_group atg ON (atg.id = at.tax_group_id)
        WHERE move_id = %s AND atg.name->>\'en_US\' = \'TDS\' ''', (obj.id,))
        line_data = [i for i in self.env.cr.fetchall()]
        if line_data:
            return line_data[0][0]
        else:
            return 0.0

    def get_tax_tot_des(self, obj):
        # Migration v15→v19: account_tax_group.name is now JSONB in Odoo 19.
        # All satg.name = 'X' comparisons must use satg.name->>'en_US' = 'X'
        self.env.cr.execute('''
        SELECT SUM(price_subtotal) AS price_subtotal, SUM(cgst_val) AS cgst_val, SUM(sgst_val) AS sgst_val, SUM(igst_val) AS igst_val FROM
        (SELECT hsn, sum(price_subtotal) as price_subtotal, SUM(cgst_val) AS cgst_val, SUM(sgst_val) AS sgst_val, SUM(igst_val) AS igst_val,
        COALESCE(ROUND(SUM(cgst),2), '0') AS cgst,
        COALESCE(ROUND(SUM(sgst),2), 0) AS sgst,
        COALESCE(ROUND(SUM(igst),2),0) AS igst FROM
        (SELECT hsn, SUM(price_subtotal) AS price_subtotal,
        COALESCE(SUM((cgst * price_subtotal) / 100), 0) AS cgst_val,
        COALESCE(SUM((sgst * price_subtotal) / 100),0) AS sgst_val,
        COALESCE(SUM((igst * price_subtotal) / 100), 0) AS igst_val,
        cgst,sgst,igst FROM
        (SELECT pt.l10n_in_hsn_code AS hsn, aml.price_subtotal,        CASE WHEN at.amount_type != 'group' THEN 0 ELSE
        (SELECT atc.amount FROM account_tax_filiation_rel atf
        JOIN account_tax atc ON (atc.id = atf.child_tax)
        JOIN account_tax_group satg ON (satg.id = atc.tax_group_id)
        AND at.id = atf.parent_tax AND satg.name->>\'en_US\' = \'CGST\') END AS cgst,
        CASE WHEN at.amount_type != 'group' THEN 0 ELSE
        (SELECT atc.amount FROM account_tax_filiation_rel atf
        JOIN account_tax atc ON (atc.id = atf.child_tax)
        JOIN account_tax_group satg ON (satg.id = atc.tax_group_id)
        AND at.id = atf.parent_tax AND satg.name->>\'en_US\' = \'SGST\') END AS sgst,
        CASE WHEN at.amount_type != 'group' THEN
        (SELECT atco.amount FROM account_tax atco
        JOIN account_tax_group satgo ON (satgo.id = atco.tax_group_id)
        WHERE atco.id = at.id AND satgo.name->>\'en_US\' = \'IGST\') ELSE 0 END AS igst
        FROM account_move_line aml
        JOIN product_product pp ON (pp.id = aml.product_id)
        JOIN product_template pt ON (pt.id = pp.product_tmpl_id)
        JOIN account_move_line_account_tax_rel amr ON (amr.account_move_line_id = aml.id)
        JOIN account_tax at ON (at.id = amr.account_tax_id)
        JOIN account_tax_group atg ON (atg.id = at.tax_group_id)
        WHERE move_id = %s)temp
        GROUP BY hsn, price_subtotal, cgst, sgst, igst)temp1
        GROUP BY hsn, price_subtotal)temp2
        ''', (obj.id,))
        line_data = [i for i in self.env.cr.dictfetchall()]
        if line_data:
            return line_data
        else:
            return [{'price_total': 0.00, 'description': ''}]


    def get_tax_ids_igst(self, obj):
        # Migration v15→v19: tax_group_id.name is now a JSONB translated field.
        # Cannot compare directly with == 'IGST'; use ORM name access which handles translation.
        tax_ids_igst = []
        for i in obj.invoice_line_ids.tax_ids:
            # tax_group_id.name returns the translated string via ORM — safe to compare
            group_name = i.tax_group_id.name
            if isinstance(group_name, dict):
                group_name = group_name.get('en_US', '')
            if group_name == 'IGST':
                tax_ids_igst.append(i.display_name)
        return tax_ids_igst

    def get_tax_ids_gst(self, obj):
        # Migration v15→v19: same JSONB handling as get_tax_ids_igst
        tax_ids_gst = []
        for i in obj.invoice_line_ids.tax_ids:
            group_name = i.tax_group_id.name
            if isinstance(group_name, dict):
                group_name = group_name.get('en_US', '')
            if group_name == 'GST':
                tax_ids_gst.append(i.display_name)
        return tax_ids_gst

    def get_bank(self, obj):
        final = []
        data = {}
        for i in obj.company_id.partner_id.bank_ids:
            data['bank_holder'] = i.acc_holder_name
            data['bank_number'] = i.acc_number
            data['bank_name'] = i.bank_id.name
            data['bank_ifsc'] = i.bank_id.bic
        final.append(data)
        return final

    def get_partner_bank(self, obj):
        final = []
        data = {}
        for i in obj.partner_id.bank_ids:
            data['street2'] = i.bank_id.street2
            data['street'] = i.bank_id.street
            data['state'] = i.bank_id.state.name
            data['city'] = i.bank_id.city
            data['country'] = i.bank_id.country.name
            data['bank_name'] = i.bank_id.name
            data['zip'] = i.bank_id.zip
        final.append(data)
        return final

    # def amount_total_in_words(self):
    #     """
    #     Converts the total amount into words in title case and appends the Abu Dhabi currency (AED) with Fils.
    #     """
    #     try:
    #         amount_in_words = amount_to_text(self.amount_total, lang=self.env.user.lang, currency=self.currency_id.name)
    #         return amount_in_words.replace(',', '') if amount_in_words else ''
    #     except Exception as e:
    #         return _("Error converting amount to text: %s") % str(e)

class HrEmployee(models.Model):
    _inherit='hr.employee'

    mode_of_payment=fields.Selection(string="Mode of Payment", selection=[("cash", "Cash"), ("bank", "Bank")])
    pf_uan_no=fields.Char(string='PF/UAN No')
    esi_no=fields.Char(string='ESI NO')
    employee_id=fields.Char(string='Employee ID',tracking=True,readonly=True)
    pf_no=fields.Char(string='PF NO')
    joining_date=fields.Date()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['employee_id'] = self.env['ir.sequence'].next_by_code('hr.employee')
        return super(HrEmployee, self).create(vals_list)

class SaleOrder(models.Model):
    _inherit='sale.order'

    def get_tax_amt(self, obj, amount):
        amt = num2words(amount,lang='en_IN')
        return amt

    def get_bank(self, obj):
        final = []
        data = {}
        for i in obj.company_id.partner_id.bank_ids:
            data['bank_holder'] = i.acc_holder_name
            data['bank_number'] = i.acc_number
            data['bank_name'] = i.bank_id.name
            data['bank_ifsc'] = i.bank_id.bic
        final.append(data)
        return final

    def get_tax_totals(self, obj):
        # Migration v15→v19: tax_totals_json (string) removed in v17+
        # tax_totals is now a dict field directly on account.move / sale.order
        tax_totals = obj.tax_totals
        values = []
        cgst = 0.0
        sgst = 0.0
        igst = 0.0
        if tax_totals and isinstance(tax_totals, dict):
            groups = tax_totals.get('groups_by_subtotal', {}).get('Untaxed Amount', [])
        else:
            groups = []
        for tax in groups:
            if tax['tax_group_name'] == 'CGST':
                cgst += tax['tax_group_amount']
            elif tax['tax_group_name'] == 'SGST':
                sgst += tax['tax_group_amount']
            elif tax['tax_group_name'] == 'IGST':
                igst += tax['tax_group_amount']
        values.append({'cgst': cgst, 'sgst': sgst, 'igst': igst})
        return values