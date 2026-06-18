from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import timedelta, datetime
import random




class StockMove(models.Model):
    _inherit = 'stock.move'

    quality_id = fields.Many2one('mrp.quality', string="Quality")


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    quality_id = fields.Many2one('mrp.quality', string="Quality")


class StockLocation(models.Model):
    _inherit = 'stock.location'

    rejected_location = fields.Boolean("Is Rejected Location")


class MrpQuality(models.Model):
    _name = "mrp.quality"
    _description = "Quality Check"
    _inherit = ['mail.thread']
    _rec_name = 'lot_id'
    _order = 'id DESC'

    name = fields.Char(string='Reference', required=True, copy=False, default='New', readonly=True)
    state = fields.Selection([('draft', 'New'), ('request', 'Requested'),('rework','Rework'),('scrap','Scrap'),('done', 'Done')], default='request', string="Status",tracking=True)
    decision = fields.Selection([('scrap', 'Scrap'), ('rework', 'Rework')])
    date = fields.Datetime('Date', default=fields.Datetime.now, required=True,tracking=True,states={'done': [('readonly', True)], 'request': [('readonly', True)]})
    production_plan_id = fields.Many2one('production.plan', string="Production Plan",tracking=True, states={'done': [('readonly', True)], 'request': [('readonly', True)]})
    operation_id = fields.Many2one('manufacturing.operation', string="Operation",tracking=True, states={'done': [('readonly', True)], 'request': [('readonly', True)]})
    product_id = fields.Many2one('product.product', required=True, string="Product",states={'done': [('readonly', True)], 'request': [('readonly', True)]})
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        domain="[('relative_uom_id', '=', product_uom_category_id)]")
    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        default=lambda self: self.env.company)
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.relative_uom_id')
    has_tracking = fields.Selection(related='product_id.tracking', readonly=True)
    location_src_id = fields.Many2one('stock.location', string="Source Location")
    location_dest_id = fields.Many2one('stock.location', string="Destination Location")
    lot_id = fields.Many2one('stock.lot', domain="[('product_id', '=', product_id), ('company_id', '=', company_id), ('final_location_id', '=', location_src_id)]", check_company=True,tracking=True,required=True)
    reason = fields.Text("Reason")
    quantity = fields.Float("Quantity")
    history_ids = fields.Many2many('mrp.quality', string="History", compute="_get_history")
    # scrap_date=fields.Datetime('Requested scrap Date')
    max_value=fields.Integer()
    mode = fields.Selection([('auto', 'Automatic'), ('manual', 'Manual')], default='auto', required=True, string="Mode",tracking=True,states={'done': [('readonly', True)], 'request': [('readonly', True)]})

    qr_code_printing_id = fields.Many2one('qr.code.printing', string="QR Code Printing")
    cell_drying_id = fields.Many2one('cell.drying', string="Cell Drying")
    injection_id = fields.Many2one('cell.injection', string="Injection")
    ht_cell_id = fields.Many2one('high.temperature.cell', string="High Temperature")
    clamp_baking_id = fields.Many2one('cell.clamp.baking')
    degas_id = fields.Many2one('degas.cell')
    pad_printing_id = fields.Many2one('pad.printing')
    capacity_id = fields.Many2one('capacity.test')
    voltage_test_id = fields.Many2one('voltage.test')
    powerbank_id = fields.Many2one('mrp.powerbank')
    manufacturing_process_id = fields.Many2one('manufacturing.process', string="Manufacturing Process")
    manufacturing_process_type_id = fields.Many2one(related='manufacturing_process_id.manufacturing_process_type_id', string="Manufacturing Process")

    def action_open_manufacturing_process(self):
        return {
            'name': self.manufacturing_process_id.manufacturing_process_type_id.name,
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'manufacturing.process',
            'res_id': self.manufacturing_process_id.id,
            'target': 'current',
        }

    @api.model_create_multi
    def create(self, vals_list):
        seq = self.env['ir.sequence']
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = seq.next_by_code('mrp.quality') or _('New')
        return super().create(vals_list)

    def _get_history(self):
        for rec in self:
            history = self.search([('product_id', '=', rec.product_id.id), ('lot_id', '=', rec.lot_id.id), ('operation_id', '=', rec.operation_id.id), ('id', '!=', rec.id)])
            rec.history_ids = history.ids

    def create_move(self, record, location_src_id, location_dest_id):
        rec = record
        stock_move = self.env['stock.move'].create({
            'inventory_name': rec.name,
            'product_id': rec.product_id.id,
            'product_uom': rec.product_uom_id.id,
            'product_uom_qty': 1,
            'location_id': location_src_id.id,
            'location_dest_id': location_dest_id.id,
            'manufacturing_process_id': self.manufacturing_process_id.id,
            'quality_id': rec.id,
        })

        # ✅ Confirm FIRST before assign
        stock_move._action_confirm()
        stock_move._action_assign()

        existing_move_lines = self.env['stock.move.line'].search([
            ('move_id', '=', stock_move.id)
        ])
        if not existing_move_lines:
            existing_move_lines = self.env['stock.move.line'].create({
                'product_id': rec.product_id.id,
                'product_uom_id': rec.product_id.uom_id.id,
                'location_id': location_src_id.id,  # ✅ .id not recordset
                'location_dest_id': location_dest_id.id,  # ✅ .id not recordset
                'company_id': rec.company_id.id,
                'lot_id': rec.lot_id.id,
                'move_id': stock_move.id,
                'manufacturing_process_id': self.manufacturing_process_id.id,
                'quality_id': rec.id,
            })

        existing_move_lines.write({
            'lot_id': rec.lot_id.id,
            'quantity': 1,
            'quality_id': rec.id,
        })
        existing_move_lines.picked = True
        stock_move._action_done()

    def action_submit(self):
        for rec in self:
            rec.write({'state': 'draft'})

    def action_rework(self):
        for rec in self:
            # if len(rec.history_ids) >= rec.operation_id.max_rework_count:
            #     raise UserError(_("Maximum allowed rework count exceeded. Please scrap the item."))
            # if rec.mode == 'manual':
            #     self.create_move(rec, rec.location_src_id, rec.operation_id.location_dest_id)
            # else:
            #     self.create_move(rec, rec.location_src_id, rec.operation_id.location_src_id)
            rec.write({
                'state': 'rework',
                'decision': 'rework'
            })

    def action_rework_complete(self):
        for rec in self:
            if len(rec.history_ids) >= rec.operation_id.max_rework_count:
                raise UserError(_("Maximum allowed rework count exceeded. Please scrap the item."))

            # ✅ Product is currently AT reject location, move it back
            reject_location = rec.operation_id.location_reject_id
            if not reject_location:
                raise UserError(_("Reject location not configured on operation."))

            if rec.mode == 'manual':
                self.create_move(rec, reject_location, rec.operation_id.location_dest_id)
            else:
                self.create_move(rec, reject_location, rec.operation_id.location_src_id)

            rec.write({'state': 'done'})

    def action_scrap_complete(self):
        for rec in self:
            location_scrap_id = rec.operation_id.location_reject_id
            if not location_scrap_id:
                location_scrap_id = self.env['stock.location'].search(
                    [('usage', '=', 'inventory')], limit=1
                )
            if not location_scrap_id:
                raise UserError(_("Scrap location not available."))
            # ✅ Move from original source to reject/scrap location
            self.create_move(rec, rec.location_src_id, location_scrap_id)
            if rec.manufacturing_process_id:
                serial_to_remove = rec.manufacturing_process_id.lot_ids.filtered(
                    lambda s: s.lot_id.id == rec.lot_id.id
                )
                if serial_to_remove:
                    serial_to_remove.unlink()

            rec.write({
                'state': 'done',
                'decision': 'scrap'
            })

    def action_scrap(self):
        for rec in self:
            # location_scrap_id = self.env['stock.location'].search([('scrap_location', '=', True)], limit=1)
            # if not location_scrap_id:
            #     raise UserError(_("Scrap location not available."))
            # self.create_move(rec, rec.location_src_id, location_scrap_id)
            rec.write({
                'state': 'scrap',
                'decision': 'scrap'
                })

    def action_view_product_move(self):
        return {
            'res_model': 'stock.move.line',
            'type': 'ir.actions.act_window',
            'name': _("Stock Move Line"),
            'domain': [('quality_id', '=', self.id)],
            'view_mode': 'list,form',
        }

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Record not in draft stage."))
        return super(MrpQuality, self).unlink()



