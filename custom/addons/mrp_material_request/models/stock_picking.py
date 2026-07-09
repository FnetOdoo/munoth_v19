from odoo import models,fields,api,_
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


class StockMove(models.Model):
    _inherit = 'stock.move'

    def unlink(self):
        for move in self:
            if move.picking_id.purchase_id.material_request_id:
                raise UserError(_('You cannot delete product line "%s" because it is linked to a Material Request PO Related.') % move.product_id.display_name)
            if move.picking_id.material_request_id:
                raise UserError(_( 'You cannot delete product line "%s" because it is linked to a Material Request.' ) % move.product_id.display_name)
        return super().unlink()

    custom_availability_state = fields.Selection([
        ('available', 'Available'),
        ('partial', 'Partially Available'),
        ('not_available', 'Not Available'),
    ], string="Availability", copy=False)

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    mrp_stock_request_id = fields.Many2one('mrp.request')
    material_request_id = fields.Many2one('mrp.material.request')
    material_return_id = fields.Many2one('mrp.material.request')
    mrp_request_count = fields.Integer(compute='_compute_mrp_request_count')
    mrp_material_request = fields.Many2one('mrp.material.request')
    is_product_qty_checked = fields.Boolean(string="Is Qty Checked",copy=False)
    mrp_request_id = fields.Many2one('mrp.material.request', string="Material Request")



    def action_view_mrp_request(self):
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

    def action_view_mrp_return(self):
        return {
            'name': _('Material Return'),
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.material.request',
            'view_mode': 'form',
            'res_id': self.material_return_id.id,
            'views': [(False, 'form')],
            'target': 'current',
        }

    def _compute_mrp_request_count(self):
        for rec in self:
            rec.mrp_request_count = self.env['mrp.request'].search_count([('picking_id', '=', rec.id)])

    # @api.constrains('move_ids', 'purchase_id')
    # def _check_products_match(self):
    #     for rec in self:
    #         is_po_receipt = bool(rec.purchase_id and rec.purchase_id.material_request_id)
    #         is_internal_transfer = bool(rec.material_request_id and not rec.purchase_id)
    #
    #         # Skip validation for MR-linked internal transfers
    #         # Quantities are set programmatically and should not be re-checked
    #         if is_internal_transfer:
    #             continue
    #
    #         if is_po_receipt:
    #             mr_product_ids = rec.purchase_id.material_request_id.request_line_ids.mapped('product_id')
    #         else:
    #             continue
    #
    #         for move in rec.move_ids:
    #             if not move.product_id:
    #                 continue
    #
    #             # For PO receipts, check product exists in MR
    #             if move.product_id not in mr_product_ids:
    #                 raise UserError(_(
    #                     'You cannot proceed with mismatched product.\n\n'
    #                     'Product "%s" is not part of the material request.'
    #                 ) % move.product_id.display_name)
    #
    #             # Check quantity: done must equal demand
    #             if move.quantity != move.product_uom_qty:
    #                 raise UserError(_(
    #                     "You cannot proceed with mismatched quantity.\n\n"
    #                     "Product: %s\n"
    #                     "Demand Quantity: %s\n"
    #                     "Done Quantity: %s\n\n"
    #                     "Both values must be equal."
    #                 ) % (
    #                                     move.product_id.display_name,
    #                                     move.product_uom_qty,
    #                                     move.quantity,
    #                                 ))
    def action_create_mrp_stock_request(self):
        for rec in self:
            return {
                'name': _('Mrp Stock Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mrp.request',
                'target': 'new',
                'context': {
                    'default_picking_id': rec.id,
                    'default_origin': rec.name,
                    'default_date': fields.Date.today(),
                },
            }

    def action_view_manufacturing_request(self):
        for rec in self:
            return {
                'name': _('Mrp Request'),
                'type': 'ir.actions.act_window',
                'view_mode': 'list,form',
                'res_model': 'mrp.request',
                'domain': [('picking_id', '=', rec.id)]
            }

    # def action_material_accept(self):
    #     for rec in self:
    #         mr = rec.material_request_id or (rec.purchase_id.material_request_id if rec.purchase_id else False)
    #         if not mr:
    #             continue
    #
    #         # Validate the picking first
    #         rec.sudo().button_validate()
    #
    #         # Compare MR product qty with picking move quantities
    #         all_qty_match = True
    #         for move in rec.move_ids:
    #             if not move.product_id:
    #                 continue
    #             mr_line = mr.request_line_ids.filtered(
    #                 lambda l: l.product_id == move.product_id and not l.display_type
    #             )[:1]
    #
    #             if not mr_line or mr_line.quantity != move.product_uom_qty:
    #                 all_qty_match = False
    #                 break
    #
    #         is_purchase_receipt = bool(rec.purchase_id)
    #
    #         if all_qty_match:
    #             # Full Match: Set to 'material_accept'
    #             mr.sudo().write({'state': 'material_accept'})
    #             rec._send_status_update_to_store("Accepted")
    #         elif is_purchase_receipt:
    #             # Partial PO Receipt: Set to 'received' (Purchased Material Received)
    #             mr.sudo().write({'state': 'material_accept'})
    #             rec._send_status_update_to_store("Accepted")
    #         else:
    #             # Partial Internal Transfer: Do NOT change state to 'material_accept'
    #             # Just notify that items were received/accepted
    #             rec._send_status_update_to_store("Partial Accepted")
    #             continue
    #
    # def action_material_reject(self):
    #     for rec in self:
    #         mr = rec.material_request_id or (rec.purchase_id.material_request_id if rec.purchase_id else False)
    #         if not mr:
    #             continue
    #
    #         is_receipt = bool(rec.purchase_id)
    #
    #         if is_receipt:
    #             # For PO Receipt reject: cancel the receipt and set MR to rejected
    #             mr.sudo().write({'state': 'material_reject'})
    #             rec.sudo().action_cancel()
    #         else:
    #             # For Internal Transfer reject: cancel transfer and set MR to rejected
    #             mr.sudo().write({'state': 'material_reject'})
    #             rec.sudo().action_cancel()
    #
    #         # Send notification to store
    #         rec._send_status_update_to_store("Rejected")
    #
    # def _send_status_update_to_store(self, status):
    #     store_group = self.env.ref('mrp_material_request.group_material_request_store_user')
    #     store_users = self.env['res.users'].sudo().search([('group_ids', 'in', [store_group.id]), ('active', '=', True)])
    #
    #     mr = self.material_request_id or self.purchase_id.material_request_id
    #     base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #     mr_url = f"{base_url}/web#id={mr.id}&view_type=form&model=mrp.material.request"
    #
    #     body_html = """
    #     <div style="font-family: Arial, sans-serif; margin: 0 auto; border: 1px solid #c0c0c0; border-radius: 8px; overflow: hidden;">
    #         <div style="background-color: %s; padding: 24px 32px;">
    #             <h2 style="color: #ffffff; margin: 0; font-size: 20px;">Material %s</h2>
    #         </div>
    #         <div style="padding: 32px; background-color: #ffffff;">
    #             <p>Dear Store Team,</p>
    #             <p>The materials for request <strong>%s</strong> have been <strong>%s</strong> by the requester.</p>
    #             <div style="background-color: #f8f9fa; border-left: 4px solid %s; border-radius: 4px; padding: 16px 20px; margin: 20px 0;">
    #                 <table style="width: 100%%;">
    #                     <tr><td width="40%%">MR Reference</td><td><b>%s</b></td></tr>
    #                     <tr><td>Requester</td><td><b>%s</b></td></tr>
    #                     <tr><td>Status</td><td><b>%s</b></td></tr>
    #                 </table>
    #             </div>
    #             <div style="margin: 24px 0;">
    #                 <a href="%s" style="display: inline-block; background-color: %s; color: #ffffff; text-decoration: none; padding: 10px 24px; border-radius: 6px; font-weight: 600;">
    #                     View Material Request
    #                 </a>
    #             </div>
    #         </div>
    #     </div>
    #     """ % (
    #         "#1a6b3c" if status == "Accepted" else "#c62828",
    #         status,
    #         mr.name,
    #         status.lower(),
    #         "#1a6b3c" if status == "Accepted" else "#c62828",
    #         mr.name,
    #         mr.user_id.name,
    #         status,
    #         mr_url,
    #         "#1a6b3c" if status == "Accepted" else "#c62828"
    #     )
    #
    #     for user in store_users:
    #         if not user.partner_id.email:
    #             continue
    #         self.env['mail.mail'].sudo().create({
    #             'subject': f'Material {status} - {mr.name}',
    #             'body_html': body_html,
    #             'email_to': user.partner_id.email,
    #             'email_from': self.env.user.email_formatted or self.company_id.partner_id.email_formatted,
    #         }).send()

    def send_material_received_notification(self):
        material_request = self.purchase_id.material_request_id
        if not material_request:
            return

        store_group = self.env.ref(
            'mrp_material_request.group_material_request_store_user'
        )

        store_users = self.env['res.users'].sudo().search([
            ('group_ids', 'in', store_group.id),
            ('active', '=', True),
        ])

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (
            material_request.id,
            material_request._name
        )

        for user in store_users:
            if not user.partner_id.email:
                continue

            body_html = """
            <div style="font-family: Arial, sans-serif; margin: 0 auto;
                        border: 1px solid #c0c0c0; border-radius: 8px; overflow: hidden;">

                <div style="background-color: #1a6b3c; padding: 24px 32px;">
                    <h2 style="color: #ffffff; margin: 0; font-size: 20px;">
                        Material Received - Stock Updated
                    </h2>
                </div>

                <div style="padding: 32px; background-color: #ffffff;">

                    <p style="font-size:15px;">
                        Dear <strong>%s</strong>,
                    </p>

                    <p style="font-size:14px; line-height:1.6;">
                        The purchased materials have been received and stock has been
                        updated successfully. Kindly proceed with the internal transfer
                        or distribution process.
                    </p>

                    <div style="background-color:#edf7f1;
                                border-left:4px solid #1a6b3c;
                                padding:16px 20px;
                                margin:20px 0;">

                        <table style="width:100%%;">

                            <tr>
                                <td><b>Material Request</b></td>
                                <td>%s</td>
                            </tr>

                            <tr>
                                <td><b>Purchase Order</b></td>
                                <td>%s</td>
                            </tr>

                            <tr>
                                <td><b>Requested By</b></td>
                                <td>%s</td>
                            </tr>

                            <tr>
                                <td><b>Received By</b></td>
                                <td>%s</td>
                            </tr>

                            <tr>
                                <td><b>Received Date</b></td>
                                <td>%s</td>
                            </tr>

                        </table>

                    </div>

                    <div style="margin:24px 0;">
                        <a href="%s"
                           style="display:inline-block;
                                  background-color:#1a6b3c;
                                  color:#ffffff;
                                  text-decoration:none;
                                  padding:10px 24px;
                                  border-radius:6px;">
                            View Material Request
                        </a>
                    </div>

                    <p>
                        Thanks & Regards,<br/>
                        <strong>%s</strong>
                    </p>

                </div>

                <div style="background-color:#1a6b3c;
                            padding:16px;
                            text-align:center;">

                    <p style="color:#ffffff;font-size:12px;margin:0;">
                        This is an automated notification from %s.
                    </p>

                </div>

            </div>
            """ % (
                user.name,
                material_request.name,  # Material Request name
                self.purchase_id.name,  # Purchase Order name
                material_request.user_id.name or '',
                self.env.user.name,
                fields.Date.today().strftime('%d-%m-%Y'),
                base_url,
                self.env.user.name,
                self.company_id.name or 'Odoo ERP'
            )

            self.env['mail.mail'].sudo().create({
                'auto_delete': False,
                'author_id': self.env.user.partner_id.id,
                'email_from': (
                        self.company_id.partner_id.email_formatted
                        or self.env.user.email_formatted
                        or self.env.ref('base.user_root').email_formatted
                ),
                'email_to': user.partner_id.email,
                'subject': 'Material Received - %s' % material_request.name,
                'body_html': body_html,
            }).send()

    def _send_material_sent_notification(self):
        self.ensure_one()
        material_request = self.material_request_id
        if not material_request:
            return
        if not material_request.user_id.partner_id.email:
            return

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        picking_url = f"{base_url}/web#id={self.id}&view_type=form&model=stock.picking"

        body_html = """
        <div style="font-family: Arial, sans-serif; margin: 0 auto;
                    border: 1px solid #c0c0c0; border-radius: 8px; overflow: hidden;">

            <div style="background-color: #1a6b3c; padding: 24px 32px;">
                <h2 style="color: #ffffff; margin: 0; font-size: 20px;">
                    Material Sent to You
                </h2>
            </div>

            <div style="padding: 32px; background-color: #ffffff;">

                <p style="font-size:15px;">
                    Dear <strong>%s</strong>,
                </p>

                <p style="font-size:14px; line-height:1.6;">
                    The materials requested in <strong>%s</strong> have been sent to you.
                </p>

                <div style="background-color:#edf7f1;
                            border-left:4px solid #1a6b3c;
                            padding:16px 20px;
                            margin:20px 0;">

                    <table style="width:100%%;">

                        <tr>
                            <td width="40%%"><b>MR Reference</b></td>
                            <td>%s</td>
                        </tr>
                        <tr>
                            <td><b>Transfer Ref</b></td>
                            <td>%s</td>
                        </tr>
                        <tr>
                            <td><b>Requested By</b></td>
                            <td>%s</td>
                        </tr>
                        <tr>
                            <td><b>Sent Date</b></td>
                            <td>%s</td>
                        </tr>
                    </table>
                </div>
                <p>
                    Thanks & Regards,<br/>
                    <strong>%s</strong>
                </p>

            </div>

            <div style="background-color:#1a6b3c;
                        padding:16px;
                        text-align:center;">

                <p style="color:#ffffff;font-size:12px;margin:0;">
                    This is an automated notification from %s.
                </p>

            </div>

        </div>
        """ % (
            material_request.user_id.name,  # Dear %s
            material_request.name,  # requested in %s
            material_request.name,  # MR Reference
            self.name,  # Transfer Ref
            material_request.user_id.name or '',  # Requested By
            fields.Date.today().strftime('%d-%m-%Y'),  # Sent Date
            self.env.user.name,  # Thanks & Regards
            self.company_id.name or 'Odoo ERP'  # footer
        )

        self.env['mail.mail'].sudo().create({
            'auto_delete': False,
            'author_id': self.env.user.partner_id.id,
            'subject': 'Material Sent: %s / %s' % (material_request.name, self.name),
            'body_html': body_html,
            'email_to': material_request.user_id.partner_id.email,
            'email_from': (
                    self.env.user.email_formatted
                    or self.company_id.partner_id.email_formatted
            ),
        }).send()

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        for rec in self:
            mr = rec.material_return_id or rec.material_request_id or (
                rec.purchase_id.material_request_id if rec.purchase_id else False)
            if not mr:
                continue

            # Send notifications BEFORE clearing
            if rec.material_request_id and not rec.purchase_id:
                rec._send_material_sent_notification()
            if rec.purchase_id and rec.purchase_id.material_request_id:
                rec.send_material_received_notification()
                rec.material_request_id = False

            # Material return picking: set state directly, skip line-satisfaction check
            if rec.material_return_id:
                mr.state = 'material_returned'
                mr.returned_date = fields.Date.today()
                continue

            # Check every line in the Material Request
            all_lines_satisfied = True
            mr_lines = mr.request_line_ids.filtered(lambda l: not l.display_type)
            if not mr_lines:
                continue

            for line in mr_lines:
                total_received = sum(self.env['stock.move'].search([
                    ('product_id', '=', line.product_id.id),
                    ('state', '=', 'done'),
                    '|',
                    ('picking_id.material_request_id', '=', mr.id),
                    ('picking_id.purchase_id.material_request_id', '=', mr.id),
                ]).mapped('quantity'))
                if total_received >= line.quantity:
                    if line.line_state != 'done' and not line.is_transfer_complete:
                        line.line_state = 'not_yet'
                else:
                    all_lines_satisfied = False

            # Transition MR state
            if all_lines_satisfied:
                if rec.picking_type_id.code == 'internal':
                    mr.state = 'material_accept'
                    mr.date_issued = fields.Date.today()
                elif mr.type == 'out_ward':
                    mr.state = 'material_returned'
                    mr.returned_date = fields.Date.today()
                elif rec.picking_type_id.code == 'incoming':
                    mr.state = 'received'
        return res

    def action_check_availability(self):
        for picking in self:
            if picking.backorder_id:
                if not picking.location_id.stock_location:
                    raise UserError(_("You must select a Material stock location"))
            if picking.picking_type_code != 'internal':
                continue
            for line in picking.move_ids:
                available_qty = line.product_id.get_available_quantity(picking.location_id)
                available_in_line_uom = line.product_id.uom_id._compute_quantity(
                    available_qty, line.product_uom
                )
                # Only set quantity if available meets demand, else keep original demand qty
                if available_in_line_uom >= line.product_uom_qty:
                    line.quantity = line.product_uom_qty
                    line.custom_availability_state = 'available'
                elif available_in_line_uom > 0:
                    line.quantity = available_in_line_uom
                    line.custom_availability_state = 'partial'
                else:
                    line.quantity = available_in_line_uom
                    line.custom_availability_state = 'not_available'

            has_available = any(
                line.quantity > 0
                for line in picking.move_ids
            )
            picking.is_product_qty_checked = has_available
            picking.action_confirm()

class StockReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def action_create_returns(self):
        res = super().action_create_returns()
        if res and res.get('res_id'):
            return_picking = self.env['stock.picking'].browse(res['res_id'])
            return_picking.material_request_id = False
        return res