from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # ══════════════════════════════════════════════════════════════════
    # SALE-SIDE BATCH CODE COMMENTED OUT
    # ══════════════════════════════════════════════════════════════════

    # batch_id = fields.Many2one('manufacturing.batch', string='Batch')

    # batch_available_qty = fields.Integer(
    #     string='Available Qty',
    #     compute='_compute_batch_cell_info',
    #     store=True,
    #     readonly=True,
    # )

    # batch_total_cell_weight = fields.Float(
    #     string='Total Cell Weight (g)',
    #     digits=(16, 4),
    #     compute='_compute_batch_cell_info',
    #     store=True,
    #     readonly=True,
    # )

    # @api.depends('batch_id', 'product_id', 'product_uom_qty', 'order_id.batch_location_id')
    # def _compute_batch_cell_info(self):
    #     ...

    # @api.onchange('batch_id')
    # def _onchange_batch_id(self):
    #     ...

    # @api.onchange('product_uom_qty')
    # def _onchange_qty_batch_check(self):
    #     ...

    # def _check_batch_qty(self):
    #     ...
    pass


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # batch_location_id = fields.Many2one(
    #     'stock.location',
    #     string='Source Location',
    #     domain="[('usage', 'in', ['internal', 'production'])]",
    # )

    # batch_total_cell_weight = fields.Float(
    #     string='Total Cell Weight (g)',
    #     digits=(16, 4),
    #     compute='_compute_order_total_weight',
    #     store=True,
    # )

    # @api.depends('order_line.batch_total_cell_weight')
    # def _compute_order_total_weight(self):
    #     ...

    # @api.onchange('batch_location_id')
    # def _onchange_batch_location_id(self):
    #     ...

    # def action_confirm(self):
    #     ...

    # def _sync_batch_to_moves(self):
    #     ...
    pass







class StockMove(models.Model):
    _inherit = 'stock.move'

    # ══════════════════════════════════════════════════════════════════
    # Batch is now a STOCK-NATIVE concept — selected directly here,
    # not received from Sale anymore (sale_batch_id removed/unlinked).
    # ══════════════════════════════════════════════════════════════════

    batch_id = fields.Many2one('manufacturing.batch', string='Batch')

    batch_total_cell_weight = fields.Float(
        string='Total Cell Weight (g)',
        digits=(16, 4),
        compute='_compute_move_batch_weight',
        store=True,
        readonly=True,
    )

    batch_available_qty = fields.Integer(
        string='Available Qty',
        compute='_compute_move_batch_weight',
        store=True,
        readonly=True,
    )

    @api.depends('batch_id', 'product_id', 'product_uom_qty', 'location_id')
    def _compute_move_batch_weight(self):
        for move in self:
            if not move.batch_id or not move.product_id or not move.location_id:
                move.batch_total_cell_weight = 0.0
                move.batch_available_qty = 0
                continue

            quants = self.env['stock.quant'].search([
                ('batch_id', '=', move.batch_id.id),
                ('product_id', '=', move.product_id.id),
                ('location_id', '=', move.location_id.id),
                ('quantity', '>', 0),
                ('lot_id', '!=', False),
            ])
            available = len(quants)
            avg_weight = (
                sum(quants.mapped('cell_weight')) / available
                if available else 0.0
            )
            move.batch_available_qty = available
            move.batch_total_cell_weight = move.product_uom_qty * avg_weight

    @api.onchange('batch_id')
    def _onchange_batch_id_check(self):
        self._compute_move_batch_weight()
        if self.batch_id and self.batch_available_qty == 0:
            return {
                'warning': {
                    'title': _('No Cells Available'),
                    'message': _(
                        'Product "%s" has no cells available in Batch "%s" at location "%s".'
                    ) % (
                        self.product_id.name or '—',
                        self.batch_id.name,
                        self.location_id.name or '—',
                    ),
                }
            }
        if self.batch_id and self.product_uom_qty > self.batch_available_qty:
            return {
                'warning': {
                    'title': _('Insufficient Cells'),
                    'message': _(
                        'Product "%s" has only %s cells available in Batch "%s", but you need %s.'
                    ) % (
                        self.product_id.name or '—',
                        self.batch_available_qty,
                        self.batch_id.name,
                        int(self.product_uom_qty),
                    ),
                }
            }

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super()._prepare_move_line_vals(
            quantity=quantity, reserved_quant=reserved_quant
        )
        if self.batch_id:
            vals['batch_id'] = self.batch_id.id
        if reserved_quant and reserved_quant.cell_weight:
            vals['cell_weight'] = reserved_quant.cell_weight
        return vals


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    batch_id = fields.Many2one('manufacturing.batch', string='Batch')
    cell_weight = fields.Float(string='Cell Weight (g)', digits=(16, 4))

    @api.onchange('lot_id')
    def _onchange_lot_fill_weight(self):
        for rec in self:
            if rec.lot_id and rec.product_id and rec.location_id:
                quant = self.env['stock.quant'].search([
                    ('lot_id', '=', rec.lot_id.id),
                    ('product_id', '=', rec.product_id.id),
                    ('location_id', '=', rec.location_id.id),
                ], limit=1)
                if quant:
                    rec.cell_weight = quant.cell_weight
                    if not rec.batch_id and quant.batch_id:
                        rec.batch_id = quant.batch_id.id


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        for picking in self:
            if picking.picking_type_id.code == 'outgoing':
                for move in picking.move_ids.filtered(
                        lambda m: m.batch_id and m.state not in ('done', 'cancel')
                ):
                    picking._auto_assign_batch_lots(move)
        return super().button_validate()

    def _auto_assign_batch_lots(self, move):
        batch = move.batch_id
        qty_needed = int(move.product_uom_qty)

        # Check what's already been assigned via manual entry or the Excel upload wizard
        already_assigned = move.move_line_ids.filtered(lambda ml: ml.lot_id)

        if already_assigned:
            # ── Custom flow: user uploaded specific serials ──────────────────
            # Respect what's already assigned. Only auto-fill the remaining gap.
            qty_remaining = qty_needed - len(already_assigned)

            if qty_remaining <= 0:
                return  # fully specified already, nothing more to do

            already_used_lot_ids = already_assigned.mapped('lot_id').ids

            quants = self.env['stock.quant'].search([
                ('product_id', '=', move.product_id.id),
                ('batch_id', '=', batch.id),
                ('location_id', '=', move.location_id.id),
                ('quantity', '>', 0),
                ('lot_id', '!=', False),
                ('lot_id', 'not in', already_used_lot_ids),
            ], order='id asc', limit=qty_remaining)

            if len(quants) < qty_remaining:
                raise UserError(_(
                    'Product "%s" has only %s additional cells available in Batch "%s".\n'
                    'Required: %s  |  Available: %s'
                ) % (
                                    move.product_id.name,
                                    len(quants),
                                    batch.name,
                                    qty_remaining,
                                    len(quants),
                                ))

            for quant in quants:
                self.env['stock.move.line'].create({
                    'move_id': move.id,
                    'product_id': move.product_id.id,
                    'product_uom_id': move.product_uom.id,
                    'quantity': 1,
                    'lot_id': quant.lot_id.id,
                    'location_id': move.location_id.id,
                    'location_dest_id': move.location_dest_id.id,
                    'company_id': self.company_id.id,
                    'batch_id': batch.id,
                    'cell_weight': quant.cell_weight,
                    'picked': True,
                })

        else:
            # ── Default flow: nothing uploaded — original behavior, unchanged ──
            quants = self.env['stock.quant'].search([
                ('product_id', '=', move.product_id.id),
                ('batch_id', '=', batch.id),
                ('location_id', '=', move.location_id.id),
                ('quantity', '>', 0),
                ('lot_id', '!=', False),
            ], order='id asc', limit=qty_needed)

            if len(quants) < qty_needed:
                raise UserError(_(
                    'Product "%s" has only %s cells available in Batch "%s".\n'
                    'Required: %s  |  Available: %s'
                ) % (
                                    move.product_id.name,
                                    len(quants),
                                    batch.name,
                                    qty_needed,
                                    len(quants),
                                ))

            move.move_line_ids.filtered(lambda ml: not ml.lot_id).unlink()

            for quant in quants:
                existing = move.move_line_ids.filtered(
                    lambda ml, q=quant: ml.lot_id == q.lot_id
                )
                if existing:
                    existing.write({
                        'quantity': 1,
                        'batch_id': batch.id,
                        'cell_weight': quant.cell_weight,
                        'picked': True,
                    })
                else:
                    self.env['stock.move.line'].create({
                        'move_id': move.id,
                        'product_id': move.product_id.id,
                        'product_uom_id': move.product_uom.id,
                        'quantity': 1,
                        'lot_id': quant.lot_id.id,
                        'location_id': move.location_id.id,
                        'location_dest_id': move.location_dest_id.id,
                        'company_id': self.company_id.id,
                        'batch_id': batch.id,
                        'cell_weight': quant.cell_weight,
                        'picked': True,
                    })

            # ❌ REMOVE THIS — Odoo's own _action_done() will deduct the quant
            # automatically once the move validates. This manual write causes
            # a double deduction, which is exactly what's tripping the
            # stock_no_negative constraint you're seeing.
            #
            # quant.sudo().write({
            #     'quantity': quant.quantity - 1,
            # })