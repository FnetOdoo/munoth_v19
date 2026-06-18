# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    def create_cell_design(self):
        if not self.model_line_ids:
            raise UserError('Add Model lines')
        for line in self.model_line_ids:
            self.env['product.model'].create({
                'lead_id': self.id,
                'name': line.product_id.name,
                'product_template_id': line.product_id.id,
            })
        return {
            'name': _('Cell Design'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.model',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
        }

    def create_costing(self):
        if not self.product_line_ids:
            raise UserError('Add Product Lines')

        pricelist = self.env['product.pricelist'].search([
            ('currency_id', '=', self.env.company.currency_id.id)
        ])

        costing = self.env['sale.costing'].create({
            'opportunity_id': self.id,
            'partner_id': self.partner_id.id,
            'pricelist_id': pricelist[0].id if pricelist else self.env['product.pricelist'].search([], limit=1).id,
        })

        s_no = 1
        for line in self.product_line_ids:
            costing.update({
                'line_ids': [(0, 0, {
                    'item_no': s_no,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_qty,
                    'product_uom': line.product_uom.id,
                    'price_unit': line.product_id.lst_price,
                })]
            })
            s_no += 1

        return {
            'name': _('Sale Costing'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.costing',
            'view_mode': 'list,form',
            'domain': [('opportunity_id', '=', self.id)],
        }

    model_line_ids = fields.One2many('crm.model.line', 'lead_id', string="Model Lines")
    product_line_ids = fields.One2many('crm.product.line', 'lead_id', string="Product Lines")
    cell_design_count = fields.Integer(string="Cell Design Count", compute='compute_cell_design_count')
    sale_costing_count = fields.Integer(string="Sale Costing Count", compute='compute_sale_costing_count')

    def open_cell_design(self):
        return {
            'name': _('Cell Design'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.model',
            'view_mode': 'list,form',
            'domain': [('lead_id', '=', self.id)],
        }

    def compute_cell_design_count(self):
        for rec in self:
            rec.cell_design_count = self.env['product.model'].search_count([('lead_id', '=', rec.id)])

    def open_sale_costing(self):
        return {
            'name': _('Sale Costing'),
            'type': 'ir.actions.act_window',
            'res_model': 'sale.costing',
            'view_mode': 'list,form',
            'domain': [('opportunity_id', '=', self.id)],
        }

    def compute_sale_costing_count(self):
        for rec in self:
            rec.sale_costing_count = self.env['sale.costing'].search_count([('opportunity_id', '=', rec.id)])




class CrmModelLine(models.Model):
    _name = 'crm.model.line'
    _description = 'CRM Model Lines'

    lead_id = fields.Many2one('crm.lead', string="Lead")
    product_id = fields.Many2one('product.template', string='Product')
    product_description = fields.Text(string="Description")
    product_qty = fields.Char(string="Quantity")
    product_uom = fields.Many2one('uom.uom', string="Unit Of Measure")

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id if self.product_id.uom_id else False
        else:
            self.product_uom = False


class CrmProductLine(models.Model):
    _name = 'crm.product.line'
    _description = 'CRM Product Lines'

    lead_id = fields.Many2one('crm.lead', string="Lead")
    product_id = fields.Many2one('product.product', string='Product')
    product_description = fields.Text(string="Description")
    product_qty = fields.Char(string="Quantity")
    product_uom = fields.Many2one('uom.uom', string="Unit Of Measure")

    @api.onchange('product_id')
    def onchange_product(self):
        if self.product_id:
            self.product_uom = self.product_id.uom_id.id if self.product_id.uom_id else False
        else:
            self.product_uom = False
