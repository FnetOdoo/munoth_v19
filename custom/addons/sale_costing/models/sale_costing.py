from odoo import models, fields, api, _
from odoo.exceptions import UserError

STATES = [('draft', 'Draft'),
          ('confirm', 'Confirmed'),
          ('done', 'Done'),
          ('reject', 'Rejected'),
          ('cancel', 'Cancelled')]


class SaleCosting(models.Model):
    _name = "sale.costing"
    _description = 'Sale Costing'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _order = 'date desc, id desc'
    _check_company_auto = True

    @api.depends('line_ids.sale_price')
    def _amount_total(self):
        """
        Compute the total amounts of the SC.
        """
        for order in self:
            price_subtotal = 0.0
            for line in order.line_ids:
                price_subtotal += line.sale_price
            order.update({
                'price_subtotal': price_subtotal,
            })

    @api.depends('customs_duty_percentage', 'freight_charges', 'price_subtotal')
    def compute_customs_duty_total(self):
        for rec in self:
            rec.customs_duty_total = (rec.price_subtotal + rec.freight_charges) * (rec.customs_duty_percentage / 100)

    @api.depends('clg_fwd_percentage', 'customs_duty_total', 'price_subtotal')
    def compute_clg_insurance_total(self):
        for rec in self:
            rec.clg_insurance_total = (rec.price_subtotal + rec.freight_charges + rec.customs_duty_total) * (
                        rec.clg_fwd_percentage / 100)

    @api.depends('other_lines.selling_price_total', 'customs_duty_total', 'clg_insurance_total', 'freight_charges')
    def compute_other_charges(self):
        for order in self:
            other_charge_total = 0
            other_charge_total += order.freight_charges + order.customs_duty_total + order.clg_insurance_total
            for line in order.other_lines:
                other_charge_total += line.selling_price_total
            order.update({
                'additional_subtotal': other_charge_total,
            })

    @api.depends('price_subtotal', 'additional_subtotal')
    def compute_amount_total(self):
        for order in self:
            amount_total = 0
            amount_total += order.price_subtotal + order.additional_subtotal
            order.update({
                'amount_total': amount_total,
            })

    @api.depends('amount_total', 'margin_percentage')
    def _amount_all(self):
        for order in self:
            sale_amount_total = 0.0
            sale_amount_total += order.amount_total / (1 - (order.margin_percentage / 100))
            order.update({
                'sale_amount_total': sale_amount_total,
            })

    @api.depends('sale_amount_total', 'amount_total')
    def compute_margin_total(self):
        for order in self:
            margin_price_total = 0
            margin_price_total += order.sale_amount_total - order.amount_total
            order.update({
                'margin_price_total': margin_price_total,
            })

    @api.depends('sale_amount_total', 'price_subtotal')
    def get_pricing_factor(self):
        for order in self:
            pricing_factor = 0
            if order.price_subtotal > 0:
                pricing_factor += order.sale_amount_total / order.price_subtotal
            order.update({
                'pricing_factor': pricing_factor,
            })

    def get_sale_count(self):
        for rec in self:
            rec.sale_count = self.env['sale.order'].search_count([('sale_costing_id', '=', rec.id)])

    state = fields.Selection(STATES, string='Status', copy=False, index=True, tracking=3, default='draft')
    name = fields.Char(string='Reference', required=True, copy=False, readonly=True,
                       states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    date = fields.Datetime(string='Costing Date', required=True, readonly=True, index=True,
                           states={'draft': [('readonly', False)], 'sent': [('readonly', False)]}, copy=False,
                           default=fields.Datetime.now)
    agreement_id = fields.Many2one('purchase.requisition', string="Enquiry")
    opportunity_id = fields.Many2one('crm.lead', string="Opportunity", required=True)
    partner_id = fields.Many2one(
        'res.partner', string='Customer',
       required=True, change_default=True, index=True, tracking=1,
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]", )
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True,
                                 default=lambda self: self.env.company)
    line_ids = fields.One2many('sale.cost.line', 'costing_id', string='Costing Lines',
                             auto_join=True, copy=True)
    other_lines = fields.One2many('other.cost.line', 'costing_id', string='Additional Charges',
                                   auto_join=True, ondelete='cascade',
                                  copy=True)
    other_cost_template_id = fields.Many2one('other.salecost.template', string="Charges Template")
    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id, string="Base Currency", required=True)
    note = fields.Text('Notes')
    price_subtotal = fields.Monetary(compute='_amount_total', string='Without Charge Total', readonly=True, store=True)
    additional_subtotal = fields.Monetary(compute='compute_other_charges', string='Total Charges', readonly=True, store=True)
    amount_total = fields.Monetary(string='Total', store=True, compute='compute_amount_total', tracking=4)
    margin_percentage = fields.Float("Overall Margin(%)")
    finance_percentage = fields.Float("Finance(%)")
    margin_price_total = fields.Monetary(string='Total Margin', store=True, readonly=True, compute='compute_margin_total', tracking=4)
    # Converison Fields
    to_currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id, string="Selling Currency", related='pricelist_id.currency_id')
    conversion_rate = fields.Float("Conversion Rate", default=1.0)
    sale_amount_total = fields.Monetary(string='Sale Total', store=True, readonly=True, compute='_amount_all', tracking=4)
    revision_count = fields.Integer("Revision Count")
    pricelist_id = fields.Many2one('product.pricelist', string='Sale Pricelist', check_company=True,  # Unrequired company
                                   domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                   help="If you change the pricelist, only newly added lines will be affected.")
    sale_count = fields.Integer("Sales Count", compute='get_sale_count')
    # Revision Fields
    current_revision_id = fields.Many2one('sale.costing', 'Current revision', readonly=True, copy=True)
    old_revision_ids = fields.One2many('sale.costing', 'current_revision_id', 'Old revisions', readonly=True, context={'active_test': False})
    revision_number = fields.Integer('Revision', copy=False)
    unrevisioned_name = fields.Char('Order Reference', copy=False, readonly=True)
    active = fields.Boolean('Active', default=True, copy=True)
    revised_date = fields.Date(string='Revised On', index=True, copy=False)
    revised_user_id = fields.Many2one('res.users', string='Revised By', readonly=True, tracking=1,
                                      domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    parent_id = fields.Many2one('sale.costing', string='Revised From', index=True)
    cancel_reason = fields.Char("Cancel Reason")
    user_id = fields.Many2one('res.users', string='Responsible', required=False, default=lambda self: self.env.user)
    customs_duty_percentage = fields.Float(string='Customs Duty(%)')
    clg_fwd_percentage = fields.Float(string="Clg/Fwd(%)")
    freight_charges = fields.Float(string='Freight Amount')
    customs_duty_total = fields.Monetary(compute='compute_customs_duty_total', string='Customs Duty', readonly=True, store=True)
    clg_insurance_total = fields.Monetary(compute='compute_clg_insurance_total', string='Clg and Insurance', readonly=True, store=True)
    pricing_factor = fields.Float(string="Pricing Factor", compute='get_pricing_factor', readonly=True, store=True)

    def action_cancel(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('sale_costing.view_cost_cancel_request_form')
        view_id = view_ref and view_ref[1] or False,
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cancellation Reason'),
            'res_model': 'cost.cancel.request',
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'new',
        }

    def action_confirm(self):
        self.write({'state': 'confirm'})

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if 'unrevisioned_name' not in vals:
                if vals.get('name', 'New') in ('New', '', False, None):
                    vals['name'] = seq.next_by_code('sale.costing') or '/'
                vals['unrevisioned_name'] = vals['name']
        return super(SaleCosting, self).create(vals_list)

    def action_revision(self):
        self.ensure_one()
        sale_id = self.env['sale.order'].search([('sale_costing_id', '=', self.id), ('state', 'in', ('done', 'sale'))])
        if sale_id:
            raise UserError(_("You cannot create the revision. Sale order already has been done for this costing!"))
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('sale_costing.sale_costing_form')
        view_id = view_ref and view_ref[1] or False,
        old_costing_id = self.with_context(sale_revision_history=True).copy()
        self.write({
            'state': 'draft',
            'revised_date': fields.Date.today(),
            'revised_user_id': self.env.user.id,
            'parent_id': old_costing_id.id,
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Costing'),
            'res_model': 'sale.costing',
            'res_id': self.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,
        }

    def copy(self, defaults=None):
        if not defaults:
            defaults = {}
        if not self.unrevisioned_name:
            self.unrevisioned_name = self.name
        if self.env.context.get('sale_revision_history'):
            prev_name = self.name
            revno = self.revision_number
            self.write({'revision_number': revno + 1, 'name': '%s-%02d' % (self.unrevisioned_name, revno + 1)})
            defaults.update({'name': prev_name, 'revision_number': revno, 'active': True, 'state': 'cancel',
                             'current_revision_id': self.id, 'unrevisioned_name': self.unrevisioned_name, })
        return super(SaleCosting, self).copy(defaults)

    def action_view_sale(self):
        action = self.env.ref('sale.action_quotations_with_onboarding').sudo().read()[0]
        costing_ids = self.env['sale.order'].search([('sale_costing_id', '=', self.id)])
        if len(costing_ids) > 1:
            action['domain'] = [('sale_costing_id', '=', self.id)]
        else:
            action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = costing_ids.id
        return action

    @api.onchange('to_currency_id')
    def get_currency_rate(self):
        if self.to_currency_id:
            self.update({'conversion_rate': self.to_currency_id.rate})

    @api.onchange('margin_percentage')
    def onchange_margin(self):
        if not self.margin_percentage:
            return
        for line in self.line_ids:
            line.update({'margin_percentage': self.margin_percentage})

    @api.onchange('other_cost_template_id')
    def onchange_template_id(self):
        if not self.other_cost_template_id:
            return
        vals = []
        for line in self.other_cost_template_id.charge_ids:
            vals.append((0, 0, {'name': line.id, 'type': line.type, 'amount': line.amount}))
        self.update({'other_lines': vals})

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                seq_date = None
                if 'date' in vals:
                    seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(vals['date']))
                if 'company_id' in vals:
                    vals['name'] = self.env['ir.sequence'].with_company(vals['company_id']).next_by_code(
                        'sale.costing', sequence_date=seq_date) or _('New')
                else:
                    vals['name'] = self.env['ir.sequence'].next_by_code('sale.costing', sequence_date=seq_date) or _(
                        'New')
        return super(SaleCosting, self).create(vals_list)

    def action_create_quotation(self):
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('sale.view_order_form')
        view_id = view_ref and view_ref[1] or False
        product_model = self.env['product.model'].search([('lead_id', '=', self.opportunity_id.id)], limit=1)
        sale_id = self.env['sale.order'].create({
            'sale_costing_id': self.id,
            'partner_id': self.partner_id.id,
            # 'tender_id': self.agreement_id.id,
            'enquiry_id': self.opportunity_id.id,
            'currency_id': self.to_currency_id.id,
            'pricelist_id': self.pricelist_id.id,
            'model_id': product_model.id if product_model else False,
        })
        for line in self.line_ids.filtered(lambda x: not x.parent_id):
            order_line = self.env['sale.order.line'].create({
                            'order_id': sale_id.id,
                            'product_id': line.product_id.id,
                            'name': line.product_id.name,
                            'product_uom_qty': line.product_uom_qty,
                            'product_uom_id': line.product_uom.id,
                            'price_unit': line.factored_unit_sale_price,
                        })
            parent_ids = self.env['sale.cost.line'].search([('parent_id', '=', line.id)])
            for parent in parent_ids:
                self.env['sale.order.option'].create({
                    'line_id': order_line.id,
                    'order_id': sale_id.id,
                    'product_id': parent.product_id.id,
                    'name': parent.product_id.name,
                    'quantity': parent.product_uom_qty,
                    'uom_id': parent.product_uom.id,
                    'price_unit': parent.factored_unit_sale_price,
                })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Order'),
            'res_model': 'sale.order',
            'res_id': sale_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,
        }

    def action_sale_revision(self):
        # ToDo: Need to fix same product used in multiple times the last updated price only affected.
        """This function will used to revise the existing quotation"""
        view_ref = self.env['ir.model.data']._xmlid_to_res_model_res_id('sale.view_order_form')
        view_id = view_ref and view_ref[1] or False
        sale_id = self.env['sale.order'].search([('sale_costing_id', '=', self.id), ('state', '!=', 'cancel')], limit=1)
        old_sale = sale_id.with_context(sale_revision_history=True).copy()
        old_sale.update({'sale_costing_id': self.parent_id.id})
        sale_id.write({'state': 'draft'})
        sale_id.order_line.write({'state': 'draft'})
        costing_products = self.line_ids.mapped('product_id')
        for line in sale_id.order_line.filtered(lambda x: x.product_id not in costing_products):
            line.unlink()
        for line in self.line_ids:
            existing_line = sale_id.order_line.filtered(lambda x: x.product_id == line.product_id)
            if existing_line:
                existing_line[0].write({
                    'product_uom_qty': line.product_uom_qty,
                    'price_unit': line.factored_unit_sale_price,
                })
            else:
                self.env['sale.order.line'].create({
                    'order_id': sale_id.id,
                    'product_id': line.product_id.id,
                    'name': line.product_id.id,
                    'product_uom_qty': line.product_uom_qty,
                    'product_uom': line.product_uom.id,
                    'price_unit': line.factored_unit_sale_price,
                })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Sales Order'),
            'res_model': 'sale.order',
            'res_id': sale_id.id,
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': view_id,
            'target': 'current',
            'nodestroy': True,
        }


class SaleCostLine(models.Model):
    _name = 'sale.cost.line'
    _description = 'Sale Costing Line'

    @api.depends('product_uom_qty', 'price_unit', 'margin_percentage')
    def _compute_amount(self):
        for line in self:
            price = line.price_unit * line.product_uom_qty
            margin_total = price * (line.margin_percentage / 100.0)
            line.update({
                'price_subtotal': price,
                'price_total': price + margin_total,
            })

    @api.depends('price_subtotal', 'price_total', 'costing_id.other_lines.price_total', 'costing_id.conversion_rate',
                 'costing_id.to_currency_id')
    def get_selling_price(self):
        for line in self:
            other_charges = 0
            for charge in line.costing_id.other_lines:
                percentage = (line.price_total/(sum(line.costing_id.line_ids.mapped('price_total')) or 1))*100
                price = charge.price_total * (percentage / 100)
                other_charges += price
            line.amount_other_charge = other_charges
            line.amount_charge_selling = other_charges * line.costing_id.conversion_rate
            line.base_sale_price = line.price_total + other_charges
            line.unit_sale_price = (line.price_unit * line.costing_id.conversion_rate)
            line.sale_price = line.unit_sale_price * (line.product_uom_qty or 1)

    @api.depends('costing_id.pricing_factor', 'unit_sale_price', 'sale_price')
    def get_factored_selling_price(self):
        for line in self:
            line.factored_unit_sale_price = line.unit_sale_price * line.costing_id.pricing_factor
            line.factored_sale_price = line.sale_price * line.costing_id.pricing_factor


    def _get_domain(self):
        for rec in self:
            return [('id', 'in', rec.costing_id.line_ids.ids),('id', '!=', rec.id)]

    costing_id = fields.Many2one('sale.costing', string='Costing Reference', required=True, ondelete='cascade', index=True)
    company_id = fields.Many2one(related='costing_id.company_id', string='Company', store=True, readonly=True, index=True)
    product_id = fields.Many2one('product.product', string='Product',
                                 domain="[('sale_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                 ondelete='restrict', check_company=True)
    product_uom_qty = fields.Float(string='Quantity', digits='Product Unit of Measure', required=True, default=1.0)
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure', )
    price_unit = fields.Monetary('Unit Price', required=True, digits='Product Price', default=0.0)
    currency_id = fields.Many2one(related='costing_id.currency_id', depends=['costing_id'], store=True, string='Currency')

    margin_percentage = fields.Float("Margin(%)")
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal Price', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total Price', readonly=True, store=True)
    state = fields.Selection(STATES, related='costing_id.state', string='Status', readonly=True, copy=False, store=True, default='draft')
    # Currency and Conversion
    to_currency_id = fields.Many2one("res.currency", related='costing_id.to_currency_id', string="Selling Currency")
    conversion_rate = fields.Float("Conversion Rate", related='costing_id.conversion_rate')
    amount_other_charge = fields.Monetary(compute='get_selling_price', string='Other Charges', store=True)
    amount_charge_selling = fields.Monetary(compute='get_selling_price', string='Other Charges', store=True)
    base_sale_price = fields.Monetary(compute='get_selling_price', string='Base Sale Price', store=True)
    sale_price = fields.Monetary(compute='get_selling_price', string='Sale Price', store=True)
    unit_sale_price = fields.Monetary(compute='get_selling_price', string='Sale Price/Unit', store=True)
    factored_sale_price = fields.Monetary(compute='get_factored_selling_price', string='Factored Sale Price', store=True)
    factored_unit_sale_price = fields.Monetary(compute='get_factored_selling_price', string='Factored Sale Price/Unit', store=True)
    parent_id = fields.Many2one('sale.cost.line', string='Optional For', domain=_get_domain, ondelete='cascade', index=True)
    item_no = fields.Char('Item No')

    @api.onchange('product_id')
    def product_id_change(self):
        if not self.product_id:
            return
        vals = {}
        if not self.product_uom or (self.product_id.uom_id.id != self.product_uom.id):
            vals['product_uom'] = self.product_id.uom_id
            vals['product_uom_qty'] = self.product_uom_qty or 1.0
        self.update(vals)

    @api.depends('product_id', 'costing_id')
    def name_get(self):
        result = []
        for line in self:
            name = line.costing_id.name or ''
            if line.product_id:
                name += " - (%s)" % line.product_id.display_name
            result.append((line.id, name))
        return result


class OtherCostLine(models.Model):
    _name = 'other.cost.line'
    _description = 'Sale Costing Other Lines'

    @api.depends('type', 'amount', 'costing_id.line_ids.price_total', 'include_margin', 'include_finance', 'costing_id.finance_percentage')
    def _compute_amount(self):
        for line in self:
            total_charges = 0.0
            for product in line.costing_id.line_ids:
                price = 0.0
                if line.type == 'fixed':
                    if line.include_margin:
                        percentage = (product.price_total / (sum(product.costing_id.line_ids.mapped('price_total')) or 1)) * 100
                        price += line.amount * (percentage / 100)
                    else:
                        percentage = (product.price_subtotal / (sum(product.costing_id.line_ids.mapped('price_subtotal')) or 1)) * 100
                        price += line.amount * (percentage / 100)
                else:
                    base_price_tot = product.price_total if line.include_margin else product.price_subtotal
                    price += base_price_tot * (line.amount / 100.0)
                total_charges += price
            if line.include_finance and line.costing_id.finance_percentage:
                total_charges += (total_charges * (line.costing_id.finance_percentage/100))
            line.update({
                'price_total': total_charges,
                'selling_price_total': total_charges * line.costing_id.conversion_rate,
            })

    costing_id = fields.Many2one('sale.costing', string='Costing Reference', required=True, ondelete='cascade',
                                 index=True)
    name = fields.Many2one('other.salecost', string="Name", required=True)
    type = fields.Selection([('fixed', 'Amount'), ('percentage', 'Percentage')], string="Amount in",
                            default='fixed', required=True)
    amount = fields.Float("Value", default=1.0, required=True)
    currency_id = fields.Many2one(related='costing_id.currency_id', depends=['costing_id'], store=True,
                                  string='Currency',
                                  readonly=True)
    to_currency_id = fields.Many2one(related='costing_id.to_currency_id')
    price_total = fields.Monetary(compute='_compute_amount', string='Base Price', readonly=True, store=True)
    selling_price_total = fields.Monetary(compute='_compute_amount', string='Selling Price', readonly=True, store=True)
    state = fields.Selection(STATES, related='costing_id.state', string='Status', readonly=True, copy=False, store=True,
                             default='draft')
    include_margin = fields.Boolean("Include Margin", default=True)
    include_finance = fields.Boolean("Apply Finance", default=True)
    cost_type = fields.Selection([('work', 'EX-Work'), ('landed', 'Landed'), ('other', 'Other')], string="Cost Type",
                                 related='name.cost_type', store=True)

    @api.onchange('name')
    def product_id_change(self):
        if not self.name:
            return
        self.update({'type': self.name.type, 'amount': self.name.amount})


