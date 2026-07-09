from odoo import models, fields, api, _
from odoo.exceptions import UserError


# class MaterialRequest(models.Model):
#     _inherit = 'mrp.material.request'

    # anode_slitting_id = fields.Many2one('anode.slitting')
    # cathode_slitting_id = fields.Many2one('cathode.slitting')
    # anode_drying_id = fields.Many2one('anode.drying')
    # cathode_drying_id = fields.Many2one('cathode.drying')
    # anode_electrode_making_id = fields.Many2one('anode.electrode.making')
    # cathode_electrode_making_id = fields.Many2one('cathode.electrode.making')
    # diaphragm_drying_id = fields.Many2one('diaphragm.drying')
    # winding_id = fields.Many2one('winding')
    # hot_press_id = fields.Many2one('hot.press.jelly')
    # assembly_id = fields.Many2one('assembly.cell')
    # cell_drying_id = fields.Many2one('cell.drying')
    # injection_id = fields.Many2one('cell.injection')
    # ht_cell_id = fields.Many2one('high.temperature.cell')
    # clamp_baking_id = fields.Many2one('cell.clamp.baking')
    # # aged_formation_id = fields.Many2one('aged.formation.cell')
    # degas_id = fields.Many2one('degas.cell')
    # pad_printing_id = fields.Many2one('pad.printing')
    # capacity_id = fields.Many2one('capacity.test')
    # voltage_test_id = fields.Many2one('voltage.test')
    # packing_id = fields.Many2one('package.move')


class AnodeSlitting(models.Model):
    _inherit = "anode.slitting"
    _description = 'Material Request'

    request_count = fields.Integer(compute='_compute_request_count')
    #
    # def check_stock_available(self):
    #     if not self.component_ids:
    #         raise UserError(_("Please fill in the materials"))
    #     for rec in self.component_ids:
    #         if rec.product_id and rec.product_qty:
    #             lot_id = self.env['stock.production.lot'].search([('name', '=', rec.lot_number), ('product_id', '=', rec.product_id.id)])
    #             stock_quant = self.env['stock.quant'].search([
    #                 ('product_id', '=', rec.product_id.id),
    #                 ('location_id', '=', rec.location_src_id.id),
    #                 ('lot_id', '=', lot_id.id)
    #             ])
    #             available_quantity = sum(stock_quant.mapped('quantity'))
    #             rec.available_qty = available_quantity
    #             rec.check_available = True

    def _compute_request_count(self):
        for rec in self:
            rec.request_count = self.env['mrp.material.request'].search_count([('anode_slitting_id', '=', rec.id)])

    def action_material_request(self):
        child_records = []
        for line in self.component_ids:
            child_records.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'quantity': line.product_qty,
                'product_uom': line.product_id.uom_id.id,
            }))
        return {
            'name': _('Material Request'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.material.request',
            'target': 'new',
            'context': {
                'default_anode_slitting_id': self.id,
                'default_operation_id': self.operation_id.id,
                'default_request_line_ids': child_records,
                'default_location_id': self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1).lot_stock_id.id,
            },
        }

    def action_view_material_request(self):
        records = self.env['mrp.material.request'].search([('anode_slitting_id', '=', self.id)])

        if len(records) == 1:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mrp.material.request',
                'res_id': records.id,  # Assuming records is a single record
            }
        else:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'res_model': 'mrp.material.request',
                'domain': [('anode_slitting_id', '=', self.id)],
            }


class CathodeSlitting(models.Model):
    _inherit = "cathode.slitting"
    _description = 'Cathode Slitting'

    request_count = fields.Integer(compute='_compute_request_count')

    def _compute_request_count(self):
        for rec in self:
            rec.request_count = self.env['mrp.material.request'].search_count([('cathode_slitting_id', '=', rec.id)])

    def action_material_request(self):
        child_records = []
        for line in self.component_ids:
            child_records.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'quantity': line.product_qty,
                'product_uom': line.product_id.uom_id.id,
            }))
        return {
            'name': _('Material Request'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.material.request',
            'target': 'new',
            'context': {
                'default_cathode_slitting_id': self.id,
                'default_operation_id': self.operation_id.id,
                'default_request_line_ids': child_records,
                'default_location_id': self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1).lot_stock_id.id,
            },
        }

    def action_view_material_request(self):
        records = self.env['mrp.material.request'].search([('cathode_slitting_id', '=', self.id)])

        if len(records) == 1:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mrp.material.request',
                'res_id': records.id,  # Assuming records is a single record
            }
        else:

            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'res_model': 'mrp.material.request',
                'domain': [('cathode_slitting_id', '=', self.id)]
            }


class AnodeElectrodeMaking(models.Model):
    _inherit = "anode.electrode.making"

    request_count = fields.Integer(compute='_compute_request_count')

    def _compute_request_count(self):
        for rec in self:
            rec.request_count = self.env['mrp.material.request'].search_count([('anode_electrode_making_id', '=', rec.id)])

    def action_material_request(self):
        child_records = []
        for line in self.component_ids:
            child_records.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'quantity': line.product_qty,
                'product_uom': line.product_id.uom_id.id,
            }))
        return {
            'name': _('Material Request'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.material.request',
            'target': 'new',
            'context': {
                'default_anode_electrode_making_id': self.id,
                'default_operation_id': self.operation_id.id,
                'default_request_line_ids': child_records,
                'default_location_id': self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1).lot_stock_id.id,
            },
        }

    def action_view_material_request(self):
        records = self.env['mrp.material.request'].search([('anode_electrode_making_id', '=', self.id)])

        if len(records) == 1:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mrp.material.request',
                'res_id': records.id,  # Assuming records is a single record
            }
        else:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'res_model': 'mrp.material.request',
                'domain': [('anode_electrode_making_id', '=', self.id)]
            }


class CathodeElectrodeMaking(models.Model):
    _inherit = "cathode.electrode.making"

    request_count = fields.Integer(compute='_compute_request_count')

    def _compute_request_count(self):
        for rec in self:
            rec.request_count = self.env['mrp.material.request'].search_count([('cathode_electrode_making_id', '=', rec.id)])

    def action_material_request(self):
        child_records = []
        for line in self.component_ids:
            child_records.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'quantity': line.product_qty,
                'product_uom': line.product_id.uom_id.id,
            }))
        return {
            'name': _('Material Request'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.material.request',
            'target': 'new',
            'context': {
                'default_cathode_electrode_making_id': self.id,
                'default_operation_id': self.operation_id.id,
                'default_request_line_ids': child_records,
                'default_location_id': self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1).lot_stock_id.id,
            },
        }

    def action_view_material_request(self):
        records = self.env['mrp.material.request'].search([('cathode_electrode_making_id', '=', self.id)])
        if len(records) == 1:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mrp.material.request',
                'res_id': records.id,  # Assuming records is a single record
            }
        else:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'res_model': 'mrp.material.request',
                'domain': [('cathode_electrode_making_id', '=', self.id)]
            }


class DiaphragmDrying(models.Model):
    _inherit = "diaphragm.drying"

    request_count = fields.Integer(compute='_compute_request_count')

    def _compute_request_count(self):
        for rec in self:
            rec.request_count = self.env['mrp.material.request'].search_count(
                [('diaphragm_drying_id', '=', rec.id)])

    def action_material_request(self):
        child_records = []
        for line in self.component_ids:
            child_records.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'quantity': line.product_qty,
                'product_uom': line.product_id.uom_id.id,
            }))
        return {
            'name': _('Material Request'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.material.request',
            'target': 'new',
            'context': {
                'default_diaphragm_drying_id': self.id,
                'default_operation_id': self.operation_id.id,
                'default_request_line_ids': child_records,
                'default_location_id': self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)],
                                                                          limit=1).lot_stock_id.id,
            },
        }

    def action_view_material_request(self):
        records = self.env['mrp.material.request'].search([('diaphragm_drying_id', '=', self.id)])
        if len(records) == 1:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mrp.material.request',
                'res_id': records.id,  # Assuming records is a single record
            }
        else:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'res_model': 'mrp.material.request',
                'domain': [('diaphragm_drying_id', '=', self.id)]
            }


class Winding(models.Model):
    _inherit = 'winding'

    request_count = fields.Integer(compute='_compute_request_count')

    def _compute_request_count(self):
        for rec in self:
            rec.request_count = self.env['mrp.material.request'].search_count(
                [('winding_id', '=', rec.id)])

    def action_material_request(self):
        child_records = []
        for line in self.component_ids:
            child_records.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'quantity': line.product_qty,
                'product_uom': line.product_id.uom_id.id,
            }))
        return {
            'name': _('Material Request'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.material.request',
            'target': 'new',
            'context': {
                'default_winding_id': self.id,
                'default_operation_id': self.operation_id.id,
                'default_request_line_ids': child_records,
                'default_location_id': self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)],
                                                                          limit=1).lot_stock_id.id,
            },
        }

    def action_view_material_request(self):
        records = self.env['mrp.material.request'].search([('winding_id', '=', self.id)])
        if len(records) == 1:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mrp.material.request',
                'res_id': records.id,  # Assuming records is a single record
            }
        else:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'res_model': 'mrp.material.request',
                'domain': [('winding_id', '=', self.id)]
            }


class AssemblyCell(models.Model):
    _inherit = 'assembly.cell'

    request_count = fields.Integer(compute='_compute_request_count')

    def _compute_request_count(self):
        for rec in self:
            rec.request_count = self.env['mrp.material.request'].search_count(
                [('assembly_id', '=', rec.id)])

    def action_material_request(self):
        child_records = []
        for line in self.component_ids:
            child_records.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'quantity': line.product_qty,
                'product_uom': line.product_id.uom_id.id,
            }))
        return {
            'name': _('Material Request'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.material.request',
            'target': 'new',
            'context': {
                'default_assembly_id': self.id,
                'default_operation_id': self.operation_id.id,
                'default_request_line_ids': child_records,
                'default_location_id': self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)],
                                                                          limit=1).lot_stock_id.id,
            },
        }

    def action_view_material_request(self):
        records = self.env['mrp.material.request'].search([('assembly_id', '=', self.id)])
        if len(records) == 1:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mrp.material.request',
                'res_id': records.id,  # Assuming records is a single record
            }
        else:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'res_model': 'mrp.material.request',
                'domain': [('assembly_id', '=', self.id)]
            }


class Injection(models.Model):
    _inherit = 'cell.injection'

    request_count = fields.Integer(compute='_compute_request_count')

    def _compute_request_count(self):
        for rec in self:
            rec.request_count = self.env['mrp.material.request'].search_count(
                [('injection_id', '=', rec.id)])

    def action_material_request(self):
        child_records = []
        for line in self.component_ids:
            child_records.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'quantity': line.product_qty,
                'product_uom': line.product_id.uom_id.id,
            }))
        return {
            'name': _('Material Request'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.material.request',
            'target': 'new',
            'context': {
                'default_injection_id': self.id,
                'default_operation_id': self.operation_id.id,
                'default_request_line_ids': child_records,
                'default_location_id': self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)],
                                                                          limit=1).lot_stock_id.id,
            },
        }

    def action_view_material_request(self):
        records = self.env['mrp.material.request'].search([('injection_id', '=', self.id)])
        if len(records) == 1:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mrp.material.request',
                'res_id': records.id,  # Assuming records is a single record
            }
        else:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'res_model': 'mrp.material.request',
                'domain': [('injection_id', '=', self.id)]
            }


# class ClampBaking(models.Model):
#     _inherit = 'cell.clamp.baking'
#
#     request_count = fields.Integer(compute='_compute_request_count')
#
#     def _compute_request_count(self):
#         for rec in self:
#             rec.request_count = self.env['mrp.material.request'].search_count(
#                 [('clamp_baking_id', '=', rec.id)])
#
#     def action_material_request(self):
#         child_records = []
#         for line in self.component_ids:
#             child_records.append((0, 0, {
#                 'product_id': line.product_id.id,
#                 'name': line.product_id.name,
#                 'quantity': line.product_qty,
#                 'product_uom': line.product_id.uom_id.id,
#             }))
#         return {
#             'name': _('Material Request'),
#             'type': 'ir.actions.act_window',
#             'view_mode': 'form',
#             'res_model': 'mrp.material.request',
#             'target': 'new',
#             'context': {
#                 'default_clamp_baking_id': self.id,
#                 'default_operation_id': self.operation_id.id,
#                 'default_request_line_ids': child_records,
#                 'default_location_id': self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)],
#                                                                           limit=1).lot_stock_id.id,
#             },
#         }
#
#     def action_view_material_request(self):
#         records = self.env['mrp.material.request'].search([('clamp_baking_id', '=', self.id)])
#         if len(records) == 1:
#             return {
#                 'name': _('Material Request'),
#                 'type': 'ir.actions.act_window',
#                 'view_mode': 'form',
#                 'res_model': 'mrp.material.request',
#                 'res_id': records.id,  # Assuming records is a single record
#             }
#         else:
#             return {
#                 'name': _('Material Request'),
#                 'type': 'ir.actions.act_window',
#                 'view_mode': 'list,form',
#                 'res_model': 'mrp.material.request',
#                 'domain': [('clamp_baking_id', '=', self.id)]
#             }

#
# class DegasCell(models.Model):
#     _inherit = 'degas.cell'
#
#     request_count = fields.Integer(compute='_compute_request_count')
#
#     def _compute_request_count(self):
#         for rec in self:
#             rec.request_count = self.env['mrp.material.request'].search_count(
#                 [('degas_id', '=', rec.id)])
#
#     def check_stock_available(self):
#         if not self.component_ids:
#             raise UserError(_("Please fill in the materials"))
#         for rec in self.component_ids:
#             if rec.product_id and rec.product_qty:
#                 lot_id = self.env['stock.production.lot'].search([('name', '=', rec.lot_number), ('product_id', '=', rec.product_id.id)])
#                 stock_quant = self.env['stock.quant'].search([
#                     ('product_id', '=', rec.product_id.id),
#                     ('location_id', '=', rec.location_src_id.id),
#                     ('lot_id', '=', lot_id.id)
#                 ])
#                 available_quantity = sum(stock_quant.mapped('quantity'))
#                 rec.available_qty = available_quantity
#                 rec.check_available = True
#
#     def action_material_request(self):
#         child_records = []
#         for line in self.component_ids:
#             child_records.append((0, 0, {
#                 'product_id': line.product_id.id,
#                 'name': line.product_id.name,
#                 'quantity': line.product_qty,
#                 'product_uom': line.product_id.uom_id.id,
#             }))
#         return {
#             'name': _('Material Request'),
#             'type': 'ir.actions.act_window',
#             'view_mode': 'form',
#             'res_model': 'mrp.material.request',
#             'target': 'new',
#             'context': {
#                 'default_degas_id': self.id,
#                 'default_operation_id': self.operation_id.id,
#                 'default_request_line_ids': child_records,
#                 'default_location_id': self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)],
#                                                                           limit=1).lot_stock_id.id,
#             },
#         }
#
#     def action_view_material_request(self):
#         records = self.env['mrp.material.request'].search([('degas_id', '=', self.id)])
#         if len(records) == 1:
#             return {
#                 'name': _('Material Request'),
#                 'type': 'ir.actions.act_window',
#                 'view_mode': 'form',
#                 'res_model': 'mrp.material.request',
#                 'res_id': records.id,  # Assuming records is a single record
#             }
#         else:
#             return {
#                 'name': _('Material Request'),
#                 'type': 'ir.actions.act_window',
#                 'view_mode': 'list,form',
#                 'res_model': 'mrp.material.request',
#                 'domain': [('degas_id', '=', self.id)]
#             }


class PadPrinting(models.Model):
    _inherit = 'pad.printing'

    request_count = fields.Integer(compute='_compute_request_count')

    def _compute_request_count(self):
        for rec in self:
            rec.request_count = self.env['mrp.material.request'].search_count(
                [('pad_printing_id', '=', rec.id)])

    def action_material_request(self):
        child_records = []
        for line in self.component_ids:
            child_records.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'quantity': line.product_qty,
                'product_uom': line.product_id.uom_id.id,
            }))
        return {
            'name': _('Material Request'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.material.request',
            'target': 'new',
            'context': {
                'default_pad_printing_id': self.id,
                'default_operation_id': self.operation_id.id,
                'default_request_line_ids': child_records,
                'default_location_id': self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)],
                                                                          limit=1).lot_stock_id.id,
            },
        }

    def action_view_material_request(self):
        records = self.env['mrp.material.request'].search([('pad_printing_id', '=', self.id)])
        if len(records) == 1:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mrp.material.request',
                'res_id': records.id,  # Assuming records is a single record
            }
        else:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'res_model': 'mrp.material.request',
                'domain': [('pad_printing_id', '=', self.id)]
            }


class CellDrying(models.Model):
    _inherit = 'cell.drying'

    request_count = fields.Integer(compute='_compute_request_count')

    def _compute_request_count(self):
        for rec in self:
            rec.request_count = self.env['mrp.material.request'].search_count(
                [('cell_drying_id', '=', rec.id)])

    def action_material_request(self):
        child_records = []
        for line in self.component_ids:
            child_records.append((0, 0, {
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'quantity': line.product_qty,
                'product_uom': line.product_id.uom_id.id,
            }))
        return {
            'name': _('Material Request'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.material.request',
            'target': 'new',
            'context': {
                'default_cell_drying_id': self.id,
                'default_operation_id': self.operation_id.id,
                'default_request_line_ids': child_records,
                'default_location_dest_id': self.location_dest_id.id,
                'default_location_id': self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)],
                                                                          limit=1).lot_stock_id.id,
            },
        }

    def action_view_material_request(self):
        records = self.env['mrp.material.request'].search([('cell_drying_id', '=', self.id)])
        if len(records) == 1:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mrp.material.request',
                'res_id': records.id,  # Assuming records is a single record
            }
        else:
            return {
                'name': _('Material Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'res_model': 'mrp.material.request',
                'domain': [('cell_drying_id', '=', self.id)]
            }

