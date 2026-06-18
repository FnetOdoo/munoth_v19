from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    batch_id = fields.Many2one('manufacturing.batch', string='Batch')

    batch_available_qty = fields.Integer(
        string='Available Qty',
        compute='_compute_batch_cell_info',
        store=True,
        readonly=True,
    )

    batch_total_cell_weight = fields.Float(
        string='Total Cell Weight (g)',
        digits=(16, 4),
        compute='_compute_batch_cell_info',
        store=True,
        readonly=True,
    )

    @api.depends('batch_id', 'product_id', 'product_uom_qty', 'order_id.batch_location_id')
    def _compute_batch_cell_info(self):
        for line in self:
            location = line.order_id.batch_location_id
            if not line.batch_id or not line.product_id or not location:
                line.batch_available_qty = 0
                line.batch_total_cell_weight = 0.0
                continue

            quants = self.env['stock.quant'].search([
                ('batch_id', '=', line.batch_id.id),
                ('product_id', '=', line.product_id.id),
                ('location_id', '=', location.id),
                ('quantity', '>', 0),
                ('lot_id', '!=', False),
            ])

            available = len(quants)
            avg_weight = (
                sum(quants.mapped('cell_weight')) / available
                if available else 0.0
            )

            line.batch_available_qty = available
            # ✅ fix: qty * avg cell weight
            line.batch_total_cell_weight = line.product_uom_qty * avg_weight

    @api.onchange('batch_id')
    def _onchange_batch_id(self):
        self._compute_batch_cell_info()
        if self.batch_id and self.batch_available_qty == 0:
            return {
                'warning': {
                    'title': _('No Cells Available'),
                    'message': _(
                        'Product "%s" has no cells available in Batch "%s" '
                        'at location "%s".'
                    ) % (
                        self.product_id.name or '—',
                        self.batch_id.name,
                        self.order_id.batch_location_id.name or '—',
                    ),
                }
            }
        if self.batch_id and self.product_uom_qty > self.batch_available_qty:
            return {
                'warning': {
                    'title': _('Insufficient Cells'),
                    'message': _(
                        'Product "%s" has only %s cells available in Batch "%s", '
                        'but you ordered %s.'
                    ) % (
                        self.product_id.name or '—',
                        self.batch_available_qty,
                        self.batch_id.name,
                        int(self.product_uom_qty),
                    ),
                }
            }

    @api.onchange('product_uom_qty')
    def _onchange_qty_batch_check(self):
        if not self.batch_id:
            return
        self._compute_batch_cell_info()
        if self.product_uom_qty > self.batch_available_qty:
            raise UserError(_(
                'Product "%s" has only %s cells available in Batch "%s", '
                'but you ordered %s.\n'
                'Please reduce the quantity or choose a different batch.'
            ) % (
                self.product_id.name or '—',
                self.batch_available_qty,
                self.batch_id.name,
                int(self.product_uom_qty),
            ))

    def _check_batch_qty(self):
        for line in self.filtered(lambda l: l.batch_id):
            if line.product_uom_qty > line.batch_available_qty:
                raise UserError(_(
                    'Product "%s" has only %s cells available in Batch "%s", '
                    'but you ordered %s.\n'
                    'Please reduce the quantity or choose a different batch.'
                ) % (
                    line.product_id.name or '—',
                    line.batch_available_qty,
                    line.batch_id.name,
                    int(line.product_uom_qty),
                ))


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    batch_location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        domain="[('usage', 'in', ['internal', 'production'])]",
    )

    batch_total_cell_weight = fields.Float(
        string='Total Cell Weight (g)',
        digits=(16, 4),
        compute='_compute_order_total_weight',
        store=True,
    )

    @api.depends('order_line.batch_total_cell_weight')
    def _compute_order_total_weight(self):
        for order in self:
            order.batch_total_cell_weight = sum(
                order.order_line.mapped('batch_total_cell_weight')
            )

    @api.onchange('batch_location_id')
    def _onchange_batch_location_id(self):
        for line in self.order_line:
            line._compute_batch_cell_info()

    def action_confirm(self):
        self.order_line._check_batch_qty()
        res = super().action_confirm()
        self._sync_batch_to_moves()
        return res

    def _sync_batch_to_moves(self):
        for order in self:
            for line in order.order_line.filtered(lambda l: l.batch_id):
                moves = self.env['stock.move'].search([
                    ('sale_line_id', '=', line.id),
                    ('state', 'not in', ('done', 'cancel')),
                ])
                write_vals = {'sale_batch_id': line.batch_id.id}
                # ✅ fix: map sale order location to delivery move
                if order.batch_location_id:
                    write_vals['location_id'] = order.batch_location_id.id
                moves.write(write_vals)
                moves._compute_move_batch_weight()

            # ✅ fix: also update picking location directly
            pickings = order.picking_ids.filtered(
                lambda p: p.state not in ('done', 'cancel')
            )
            if order.batch_location_id and pickings:
                pickings.write({
                    'location_id': order.batch_location_id.id,
                })


class StockMove(models.Model):
    _inherit = 'stock.move'

    sale_batch_id = fields.Many2one('manufacturing.batch', string='Batch')

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

    @api.depends('sale_batch_id', 'product_id', 'product_uom_qty', 'location_id')
    def _compute_move_batch_weight(self):
        for move in self:
            if not move.sale_batch_id or not move.product_id or not move.location_id:
                move.batch_total_cell_weight = 0.0
                move.batch_available_qty = 0
                continue

            quants = self.env['stock.quant'].search([
                ('batch_id', '=', move.sale_batch_id.id),
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
            # ✅ fix: qty * avg cell weight
            move.batch_total_cell_weight = move.product_uom_qty * avg_weight

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        vals = super()._prepare_move_line_vals(
            quantity=quantity, reserved_quant=reserved_quant
        )
        if self.sale_batch_id:
            vals['sale_batch_id'] = self.sale_batch_id.id
        if reserved_quant and reserved_quant.cell_weight:
            vals['cell_weight'] = reserved_quant.cell_weight
        return vals


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    sale_batch_id = fields.Many2one('manufacturing.batch', string='Batch')
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
                    if not rec.sale_batch_id and quant.batch_id:
                        rec.sale_batch_id = quant.batch_id.id


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    def button_validate(self):
        for picking in self:
            if picking.picking_type_id.code == 'outgoing':
                for move in picking.move_ids.filtered(
                    lambda m: m.sale_batch_id and m.state not in ('done', 'cancel')
                ):
                    picking._auto_assign_batch_lots(move)
        return super().button_validate()

    def _auto_assign_batch_lots(self, move):
        batch = move.sale_batch_id
        qty_needed = int(move.product_uom_qty)

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
                    'sale_batch_id': batch.id,
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
                    'sale_batch_id': batch.id,
                    'cell_weight': quant.cell_weight,
                    'picked': True,
                })

            # ✅ reduce quant quantity after assigning
            quant.sudo().write({
                'quantity': quant.quantity - 1,
            })