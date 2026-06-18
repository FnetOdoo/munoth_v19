from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class ProductModel(models.Model):
    _name = 'product.model'
    _description = 'Product Models'


    name = fields.Char()
    line_number = fields.Char()
    note = fields.Char()
    product_model_bom_ids = fields.One2many('product.model.bom', 'product_model_id', copy=True)
    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        default=lambda self: self.env.company)
    operation_ids = fields.One2many('manufacturing.operation', 'product_model_id', copy=True)
    machine_ids = fields.One2many('machine.allocation', 'product_model_id')

    product_template_id = fields.Many2one('product.template', string="Product")
    product_id = fields.Many2one('product.product', string="Product Variant")
    state = fields.Selection([('draft', 'Draft'),
                              ('user_request', 'User Requested'),
                              ('design_user_request', 'Design User Requested'),
                              ('approve', 'Approved')], string="Status", default='draft')
    is_design_user = fields.Boolean(string="Is Design User", compute="check_user")
    #fai-final inspection quality-parameters
    fai_dimension = fields.Char('Dimension')
    fai_cutoff_voltage = fields.Char('Cutoff Voltage')
    fai_ir = fields.Char('IR')
    fai_visual_check = fields.Char('Visual Check')

    def check_user(self):
        for rec in self:
            if self.env.user.has_group('fnet_mrp.group_cell_design_user'):
                rec.is_design_user = True
            else:
                rec.is_design_user = False

    nmc = fields.Float()
    cathode_conductive_carbon = fields.Float()
    pvdf = fields.Float()
    graphite = fields.Float()
    anode_conductive_carbon = fields.Float()
    cmc = fields.Float()
    sbr = fields.Float()
    cathode_active_material = fields.Char()
    cathode_am_capacity = fields.Float()
    cathode_am = fields.Float()
    cathode_carbon = fields.Float()
    cathode_binder1 = fields.Float()
    cathode_binder2 = fields.Float()
    cathode_length_of_foil = fields.Float()
    cathode_width_of_foil = fields.Float()
    cathode_thickness_of_the_substrate = fields.Float()
    cathode_weight_of_the_foil = fields.Float()
    cathode_length_of_coating_side_a = fields.Float()
    cathode_length_of_coating_side_b = fields.Float()
    cathode_width_of_coating = fields.Float()
    cathode_coating_area = fields.Float()
    cathode_thickness_of_the_electrode = fields.Float()
    cathode_weight_of_coated_electrode_with_substrate = fields.Float()
    cathode_weight_of_coated_electrode_without_substrate = fields.Float()
    cathode_weight_ni_ai_tab = fields.Float()
    cathode_loading_single_side = fields.Float()
    cathode_length_of_separator = fields.Float()
    cathode_width_of_separator = fields.Float()
    cathode_n_p_ratio = fields.Float()

    anode_active_material = fields.Char()
    anode_am_capacity = fields.Float()
    anode_am = fields.Float()
    anode_carbon = fields.Float()
    anode_binder1 = fields.Float()
    anode_binder2 = fields.Float()
    anode_length_of_foil = fields.Float()
    anode_width_of_foil = fields.Float()
    anode_thickness_of_the_substrate = fields.Float()
    anode_weight_of_the_foil = fields.Float()
    anode_length_of_coating_side_a = fields.Float()
    anode_length_of_coating_side_b = fields.Float()
    anode_width_of_coating = fields.Float()
    anode_coating_area = fields.Float()
    anode_thickness_of_the_electrode = fields.Float()
    anode_weight_of_coated_electrode_with_substrate = fields.Float()
    anode_weight_of_coated_electrode_without_substrate = fields.Float()
    anode_weight_ni_ai_tab = fields.Float()
    anode_loading_single_side = fields.Float()
    anode_length_of_separator = fields.Float()
    anode_width_of_separator = fields.Float()
    anode_n_p_ratio = fields.Float()


    # cell specification

    nominal_capacity = fields.Char()
    nominal_voltage = fields.Char()
    internal_impedance = fields.Char()
    charge_voltage_charge_limit = fields.Char()
    shipment_voltage = fields.Char()
    standard_charge = fields.Text()
    standard_discharge = fields.Char()
    fast_charge = fields.Char()
    fast_discharge = fields.Char()
    weight = fields.Char()
    cycle = fields.Char()
    typical_capacity = fields.Char()
    charge_cut_off_voltage = fields.Char()
    discharge_cut_off_voltage = fields.Char()


    nominal_capacity_remark = fields.Char()
    nominal_voltage_remark = fields.Char()
    internal_impedance_remark = fields.Char()
    charge_voltage_charge_limit_remark = fields.Char()
    shipment_voltage_remark = fields.Char()
    standard_charge_remark = fields.Text()
    standard_discharge_remark = fields.Char()
    fast_charge_remark = fields.Char()
    fast_discharge_remark = fields.Char()
    weight_remark = fields.Char()
    cycle_remark = fields.Char()
    typical_capacity_remark = fields.Char()
    charge_cut_off_voltage_remark = fields.Char()
    discharge_cut_off_voltage_remark = fields.Char()

    storage_condition = fields.Text()

    standard_charge_ids = fields.One2many('standard.charge', 'model_id')

    def action_user_submit(self):
        for rec in self:
            rec.write({'state': 'user_request'})

    def action_design_user_submit(self):
        for rec in self:
            if rec.name == rec.product_template_id.name:
                raise UserError('Model name is same as the Product Name')
            if not rec.product_model_bom_ids:
                raise UserError('Add BOM Lines')
            rec.write({'state': 'design_user_request'})

    def action_approve(self):
        for rec in self:
            product_price = sum(rec.product_model_bom_ids.mapped('amount_total'))
            product_variant = self.env['product.product'].create({
                'name': rec.name,
                'type': rec.product_template_id.type,
                'lst_price': product_price,
                'uom_id': rec.product_template_id.uom_id.id,
            })
            rec.write({'product_id': product_variant.id, 'state': 'approve'})


class StandardCharge(models.Model):
    _name = 'standard.charge'
    _description = 'Standard Charge'

    temperature = fields.Char()
    remark = fields.Char()
    model_id = fields.Many2one('product.model')



class ProductBom(models.Model):
    _name = 'product.model.bom'
    _description = 'Product Model BOM'
    _order = "id desc"

    def _get_default_product_uom_id(self):
        return self.env['uom.uom'].search([], limit=1, order='id').id

    product_id = fields.Many2one('product.product')
    product_qty = fields.Float(
        'Quantity', default=1.0,
        digits='Product Unit of Measure', required=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Product Unit of Measure',
        required=True,
        help="Unit of Measure (Unit of Measure) is the unit of measurement for the inventory control",
        domain="[('relative_uom_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.relative_uom_id')

    product_model_id = fields.Many2one('product.model')
    weight = fields.Float()
    thickness = fields.Float()
    length = fields.Float()
    width = fields.Float()
    measurement = fields.Selection([
        ('weight', 'Weight'),
        ('size', 'Size')
    ])
    amount_total = fields.Float(string="Amount")

    @api.onchange('product_id')
    def onchange_of_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id


class MachineAllocation(models.Model):
    _name = 'machine.allocation'
    _description = "Machine Allocation"

    product_model_id = fields.Many2one('product.model')
    type = fields.Selection([
        ('anode_slitting', 'Anode Slitting '),
        ('cathode_slitting', 'Cathode Slitting '),
        ('anode_drying', 'Anode Drying'),
        ('cathode_drying', 'Cathode Drying'),
        ('diaphragm_drying', 'Diaphragm Drying'),
        ('anode_electrode_making', 'Anode Electrode Making'),
        ('cathode_electrode_making', 'Cathode Electrode Making'),
        ('winding', 'Winding'),
        ('hot_press_jelly', 'Hot Press Jelly'),
        ('assembly', 'Assembly'),
        ('qr_code_print', 'QR Code Printing'),
        ('cell_drying', 'Cell Drying'),
        ('injection', 'Injection'),
        ('high_temperature', 'High Temperature'),
        ('cell_baking_formation', 'Cell Formation'),
        ('aged_formation_cell', 'Aged Formation Cell'),
        ('degas', 'Degas'),
        ('dsf', 'Double side Folding'),
        ('pad_printing', 'Pad Printing'),
        ('capacity_test', 'Capacity Test')
    ], default='anode_slitting')

    mrp_machine_ids = fields.Many2many('manufacturing.machine')













