
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class TrayProductLine(models.TransientModel):
    _name = 'tray.product.lot.line'
    _description = 'Insert Product Line'

    select_record = fields.Boolean()
    serial_number = fields.Char()
    tray_product_id = fields.Many2one('tray.product.lot')
    product_id = fields.Many2one('product.product')
    product_uom_id = fields.Many2one('uom.uom', 'Unit of Measure', domain="[('relative_uom_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.relative_uom_id')
    serial_number_id = fields.Many2one('product.serial.number')
    lot_id = fields.Many2one('stock.lot', domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]", check_company=True)


class StockMoveLIne(models.TransientModel):
    _name = 'tray.product.lot'
    _description = 'Tray Product Insert'

    product_tray_id = fields.Many2one('product.tray')
    tray_lot_ids = fields.One2many('tray.product.lot.line', 'tray_product_id')
    dest_location_id = fields.Many2one('stock.location')
    location_src_id = fields.Many2one('stock.location')
    product_id = fields.Many2one('product.product')
    cell_drying_id = fields.Many2one('cell.drying')
    aged_formation_id = fields.Many2one('aged.formation.cell')
    capacity_id = fields.Many2one('capacity.test')
    clamp_baking_id = fields.Many2one('cell.clamp.baking')
    degas_id = fields.Many2one('degas.cell')
    ht_cell_id = fields.Many2one('high.temperature.cell')
    injection_id = fields.Many2one('cell.injection')
    packing_id = fields.Many2one('package.move')
    pad_printing_id = fields.Many2one('pad.printing')
    voltage_test_id = fields.Many2one('voltage.test')

    @api.onchange('product_tray_id')
    def _onchange_of_product_id(self):
        child_records = []
        self.tray_lot_ids = False
        if self.product_tray_id:
            for line in self.product_tray_id.lot_ids:
                child_records.append((0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom_id.id,
                    'serial_number': line.name,
                    'serial_number_id': line.id,
                    'lot_id': line.lot_id.id
                }))
            self.tray_lot_ids = child_records

    def action_select_all(self):
        for rec in self.tray_lot_ids:
            rec.select_record = True
        return {
            'name': _('Update Lot'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'tray.product.lot',
            'res_id': self.id,
            'target': 'new',
        }

    def action_unselect_all(self):
        for rec in self.tray_lot_ids:
            rec.select_record = False
        return {
            'name': _('Update Lot'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'tray.product.lot',
            'res_id': self.id,
            'target': 'new',
        }

    def action_update_the_lot(self):
        child_records = []
        lot_ids = self.tray_lot_ids.filtered(lambda x: x.select_record)
        for lot_line in lot_ids:
            lot_id = lot_line.serial_number_id.lot_id
            child_records.append((0, 0, {
                'product_id': lot_line.product_id.id,
                'product_uom_id': lot_line.product_uom_id.id,
                'name': lot_line.product_id.name,
                'lot_id': lot_id.id if lot_id else False,
                'location_src_id': self.location_src_id.id,
                'location_dest_id': self.dest_location_id.id,
                'tray_id': self.product_tray_id.id,
                'product_qty': 1.0,
                'serial_number_id': lot_line.serial_number_id.id,
            }))

        if self.cell_drying_id:
            self.cell_drying_id.component_ids = child_records
        if self.aged_formation_id:
            self.aged_formation_id.component_ids = child_records
        if self.capacity_id:
            self.capacity_id.component_ids = child_records
        if self.clamp_baking_id:
            self.clamp_baking_id.component_ids = child_records
        if self.degas_id:
            self.degas_id.component_ids = child_records
        if self.ht_cell_id:
            self.ht_cell_id.component_ids = child_records
        if self.injection_id:
            self.injection_id.component_ids = child_records
        if self.packing_id:
            self.packing_id.component_ids = child_records
        if self.pad_printing_id:
            self.pad_printing_id.component_ids = child_records
        if self.voltage_test_id:
            self.voltage_test_id.component_ids = child_records
        serial_numbers = lot_ids.mapped('serial_number_id')
        # serial_numbers = self.env['product.serial.number'].search([('tray_id', '=', self.product_tray_id.id), ('name', 'in', serial_numbers)])
        serial_numbers.tray_id = False





