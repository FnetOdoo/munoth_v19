from odoo import models,fields,api,_
from odoo.exceptions import UserError


class ProductionProcess(models.Model):
    _inherit = 'manufacturing.process'

    material_request_id = fields.Many2one('mrp.material.request')
    need_material_request = fields.Boolean(string="Need Material Request", default=False)

    def action_view_material_request(self):
        self.ensure_one()
        return {
            'name': _('Material Request'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.material.request',
            'view_mode': 'form',
            'res_id': self.material_request_id.id,
            'views': [(False, 'form')],
            'target': 'current',
        }

    def action_create_material_request(self):
        self.ensure_one()

        request_lines = []
        for line in self.input_material_lines:
            available_qty = line.product_id.get_available_quantity(line.location_src_id)

            if available_qty < line.product_qty:
                shortfall = line.product_qty - available_qty
                request_lines.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom_id.id,
                    'name': line.product_id.display_name,
                    'quantity': shortfall,  # only the missing amount, not the full product_qty
                }))

        if not request_lines:
            return

        request = self.env['mrp.material.request'].create({
            'type': 'in_ward',
            'operation_id': self.operation_id.id if self.operation_id else False,
            'origin': self.name,
            'production_process_id': self.id,
            'responsible_user_id': self.user_id.id,
            'location_dest_id': self.location_src_id.id,
            'request_line_ids': request_lines,
        })
        self.material_request_id = request.id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Material Request'),
            'res_model': 'mrp.material.request',
            'res_id': request.id,
            'view_mode': 'form',
            'target': 'current',
        }