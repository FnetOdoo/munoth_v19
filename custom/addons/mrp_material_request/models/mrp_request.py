from odoo import api, fields, models,_
from odoo.exceptions import UserError


class MrpRequestLine(models.Model):
    _name = 'mrp.request.line'
    _description = "Manufacturing Request Line"

    product_id = fields.Many2one('product.product')
    def _get_default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id').id

    company_id = fields.Many2one(
        related='mrp_request_id.company_id', store=True, index=True, readonly=True)
    product_qty = fields.Float(
        'Quantity', default=1.0,
        digits='Product Unit of Measure', required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        default=_get_default_product_uom_id,
        required=True,
        help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control",
        )
    mrp_request_id = fields.Many2one('mrp.request')

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id

    @api.onchange('product_uom_id')
    def onchange_product_uom_id(self):
        res = {}
        if not self.product_uom_id or not self.product_id:
            return res
        if self.product_uom_id.uom_category_id != self.product_id.uom_id.category_id:
            self.product_uom_id = self.product_id.uom_id.id
            res['warning'] = {'title': _('Warning'), 'message': _(
                'The Product Unit of Measure you chose has a different category than in the product form.')}
        return res

    @api.model_create_multi
    def create(self, vals_list):
        for values in vals_list:
            if 'product_id' in values and 'product_uom_id' not in values:
                values['product_uom_id'] = self.env['product.product'].browse(values['product_id']).uom_id.id
        return super(MrpRequestLine, self).create(vals_list)


class MrpRequest(models.Model):
    _name = "mrp.request"
    _description = "Manufacturing Request"
    _order = "id desc"

    picking_id = fields.Many2one('stock.picking')
    location_id = fields.Many2one('stock.location')
    name = fields.Char(
        'Reference', copy=False, readonly=True, default=lambda x: _('New'))
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submit', 'Submit'),
        ('confirmed', 'Confirmed'),
        ('done', 'Done'),
        ('close', 'Close'),
        ('cancel', 'Cancelled')], string='State',
        copy=False, index=True, default='draft',
        store=True)

    request_ids = fields.One2many('mrp.request.line', 'mrp_request_id')
    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        default=lambda self: self.env.company)
    from_stock = fields.Boolean()
    production_plan_count = fields.Integer(compute='_compute_production_count')
    mrp_request_id = fields.Many2one('mrp.request')
    section = fields.Char("Production Section")
    department_id = fields.Many2one('hr.department', string="Department")
    date = fields.Date('Requested Date')
    user_id = fields.Many2one('res.users', 'Requested by', default=lambda self: self.env.user)
    responsible_user_id = fields.Many2one('res.users', 'Responsible')
    origin = fields.Char(
        'Source', copy=False,
        states={'confirm': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="Reference of the document that generated this request.")

    def _compute_production_count(self):
        for rec in self:
            rec.production_plan_count = self.env['production.plan'].search_count([('mrp_request_id', '=', rec.id)])


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('mrp.request') or _('New')
        return super().create(vals_list)

    def action_draft(self):
        for rec in self:
            rec.state ='draft'

    def action_submit(self):
        for rec in self:
            if not rec.request_ids:
                raise UserError(_("Please fill the product details"))
            rec.state = 'submit'

    def action_confirm(self):
        for rec in self:
            if not rec.request_ids:
                raise UserError(_("Please fill the product details"))
            rec.state = 'confirmed'

    def action_done(self):
        for rec in self:
            rec.state = 'done'

    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    def action_close(self):
        for rec in self:
            rec.state = 'close'


    def action_create_mrp_order(self):
        for rec in self:
            return {
                'name': _('Mrp Model'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'production.plan',
                'target': 'new',
                'context': {
                        'default_mrp_request_id': rec.id,
                },
            }

    def action_view_stock_picking(self):
        for rec in self:
            return {
                'name': _('Sale Order'),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'res_model': 'stock.picking',
                'domain': [('id', '=', rec.picking_id.id)],
                }
    def action_view_mrp_production(self):
        for rec in self:
            return {
                'name': _('Production'),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'res_model': 'production.plan',
                'domain': [('mrp_request_id', '=', rec.id)],
                }





class ProductionPlan(models.Model):
    _inherit = 'production.plan'

    mrp_request_id = fields.Many2one('mrp.request')

    def action_view_mrp_request(self):
        for rec in self:
            return {
                'name': _('Mrp Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'res_model': 'mrp.request',
                'domain': [('id', '=', rec.mrp_request_id.id)],
            }


class Request(models.Model):
    _name = 'mrp.stock.request'
    _description = "Manufacturing Stock request"




