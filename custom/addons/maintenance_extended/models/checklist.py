from odoo import models, api, fields


class EquipmentChecklist(models.Model):
    _name = "equipment.checklist"
    _description = "Checklist"

    name = fields.Char("Checkpoint", required=True)
    material_ids = fields.One2many('checklist.material', 'checklist_id', string="Checkpoints")
    company_id = fields.Many2one('res.company', string='Company', index=True, default=lambda self: self.env.company)
    category_id = fields.Many2one('maintenance.equipment.category', string='Equipment Category', tracking=True)
    duration = fields.Float("Duration")


class ChecklistLine(models.Model):
    _name = "checklist.material"
    _description = "Check Material"

    checklist_id = fields.Many2one('equipment.checklist', string="Checkpoints")
    work_order_id = fields.Many2one('work.order')
    product_id = fields.Many2one('product.product', required=True)
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure', required=True, domain="[('relative_uom_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.relative_uom_id')
    product_qty = fields.Float("Quantity", default=1.0)
    company_id = fields.Many2one(related='checklist_id.company_id')
    
    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id


