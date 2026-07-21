# -*- coding: utf-8 -*-

from odoo import models, fields
from odoo.orm.fields_temporal import Date


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    custom_requisition_id = fields.Many2one(
        'material.purchase.requisition',
        string='Purchase Requisition',
        readonly=True,
        copy=True
    )

    def action_view_pr(self):
        self.ensure_one()

        if not self.custom_requisition_id:
            return False

        return {
            'name': 'Purchase Requisition',
            'type': 'ir.actions.act_window',
            'res_model': 'material.purchase.requisition',
            'view_mode': 'form',
            'res_id': self.custom_requisition_id.id,
            'views': [(False, 'form')],
            'target': 'current',
            'context': {'create': False},
        }

    def button_validate(self):
        res = super(StockPicking, self).button_validate()

        for picking in self:
            # Purchase receipt check
            if picking.picking_type_id.code == 'incoming':
                purchase_order = picking.purchase_id

                if purchase_order:
                    requisition = purchase_order.custom_requisition_id

                    if requisition:
                        all_pos = self.env['purchase.order'].search([
                            ('custom_requisition_id', '=', requisition.id)
                        ])

                        if all_pos:
                            fully_received = True
                            partially_received = False

                            for po in all_pos:
                                for po_line in po.order_line:
                                    if po_line.qty_received > 0:
                                        partially_received = True

                                    if po_line.product_qty - po_line.qty_received > 0.0001:
                                        fully_received = False

                            # Some quantity received but not complete
                            if partially_received and not fully_received:
                                requisition.write({
                                    'state': 'partial_receive'
                                })
                                picking._send_partial_receive_notification(requisition)

                            # All quantity received
                            elif fully_received:
                                requisition.write({
                                    'state': 'receive',
                                    'receive_date': Date.today()
                                })
                                picking._send_fully_receive_notification(requisition)

            # --- Internal picking check (independent, always runs) ---
            internal_requisition = picking.custom_requisition_id
            if internal_requisition and internal_requisition.state != 'done':
                all_pickings = self.env['stock.picking'].search([
                    ('custom_requisition_id', '=', internal_requisition.id)
                ])
                if all_pickings:
                    fully_done = True
                    for pick in all_pickings:
                        for move in pick.move_ids:
                            if move.product_uom_qty - move.quantity > 0.0001:
                                fully_done = False
                                break
                        if not fully_done:
                            break
                    if fully_done:
                        internal_requisition.write({'state': 'done'})
        return res

    def _send_partial_receive_notification(self, requisition):
        """Send email to Store group when material is PARTIALLY received."""
        self.ensure_one()
        store_group = self.env.ref(
            'material_purchase_requisitions.group_purchase_requisition_store'
        )
        store_users = self.env['res.users'].sudo().search([
            ('group_ids', 'in', store_group.id),
            ('active', '=', True),
        ])
        if not store_users:
            return

        # ✅ Build URL pointing to the requisition form
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        requisition_url = base_url + '/web#id=%d&view_type=form&model=%s' % (
            requisition.id, requisition._name
        )

        body_html = """
        <div style="font-family: Arial, sans-serif; margin: 0 auto;
                    border: 1px solid #c0c0c0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #e67e22; padding: 24px 32px;">
                <h2 style="color: #ffffff; margin: 0; font-size: 20px;">
                    &#9888; Material Partially Received
                </h2>
            </div>
            <div style="padding: 32px; background-color: #ffffff;">
                <p style="font-size:15px;">Dear <strong>Store Team</strong>,</p>
                <p style="font-size:14px; line-height:1.6;">
                    Materials for requisition <strong>%s</strong> have been
                    <strong>partially received</strong> in stock.
                    Some quantities are still pending from the vendor.
                </p>
                <div style="background-color:#fef9f0;
                            border-left:4px solid #e67e22;
                            padding:16px 20px; margin:20px 0;">
                    <table style="width:100%%;">
                        <tr>
                            <td width="40%%"><b>Requisition Ref</b></td>
                            <td>%s</td>
                        </tr>
                        <tr>
                            <td><b>Transfer Ref</b></td>
                            <td>%s</td>
                        </tr>
                        <tr>
                            <td><b>Received Date</b></td>
                            <td>%s</td>
                        </tr>
                        <tr>
                            <td><b>Validated By</b></td>
                            <td>%s</td>
                        </tr>
                    </table>
                </div>
                <p style="font-size:13px; color:#888;">
                    Please follow up with the vendor for the remaining quantities.
                </p>

                <!-- ✅ View Requisition Button -->
                <div style="text-align:center; margin: 24px 0;">
                    <a href="%s"
                       style="background-color:#e67e22;
                              color:#ffffff;
                              padding:12px 32px;
                              border-radius:6px;
                              text-decoration:none;
                              font-size:14px;
                              font-weight:bold;
                              display:inline-block;">
                        &#128065; View Requisition
                    </a>
                </div>

                <p>
                    Thanks &amp; Regards,<br/>
                    <strong>%s</strong>
                </p>
            </div>
            <div style="background-color:#e67e22; padding:16px; text-align:center;">
                <p style="color:#ffffff; font-size:12px; margin:0;">
                    This is an automated notification from %s.
                </p>
            </div>
        </div>
        """ % (
            requisition.name,  # paragraph bold
            requisition.name,  # Requisition Ref
            self.name,  # Transfer Ref
            fields.Date.today().strftime('%d-%m-%Y'),  # Received Date
            self.env.user.name,  # Validated By
            requisition_url,  # ✅ Button href
            self.env.user.name,  # Thanks & Regards
            self.company_id.name or 'Odoo ERP',  # footer
        )

        for user in store_users:
            self.env['mail.mail'].sudo().create({
                'auto_delete': False,
                'author_id': self.env.user.partner_id.id,
                'subject': 'Partial Material Received: %s / %s' % (requisition.name, self.name),
                'body_html': body_html,
                'email_to': user.partner_id.email,
                'email_from': (
                        self.env.user.email_formatted
                        or self.company_id.partner_id.email_formatted
                ),
            }).send()

    def _send_fully_receive_notification(self, requisition):
        """Send email to Store group when material is FULLY received."""
        self.ensure_one()
        store_group = self.env.ref(
            'material_purchase_requisitions.group_purchase_requisition_store'
        )
        store_users = self.env['res.users'].sudo().search([
            ('group_ids', 'in', store_group.id),
            ('active', '=', True),
        ])
        if not store_users:
            return

        # ✅ Build URL pointing to the requisition form
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        requisition_url = base_url + '/web#id=%d&view_type=form&model=%s' % (
            requisition.id, requisition._name
        )

        body_html = """
        <div style="font-family: Arial, sans-serif; margin: 0 auto;
                    border: 1px solid #c0c0c0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #1a6b3c; padding: 24px 32px;">
                <h2 style="color: #ffffff; margin: 0; font-size: 20px;">
                    &#10003; Material Fully Received
                </h2>
            </div>
            <div style="padding: 32px; background-color: #ffffff;">
                <p style="font-size:15px;">Dear <strong>Store Team</strong>,</p>
                <p style="font-size:14px; line-height:1.6;">
                    All materials for requisition <strong>%s</strong> have been
                    <strong>fully received</strong> in stock.
                </p>
                <div style="background-color:#edf7f1;
                            border-left:4px solid #1a6b3c;
                            padding:16px 20px; margin:20px 0;">
                    <table style="width:100%%;">
                        <tr>
                            <td width="40%%"><b>Requisition Ref</b></td>
                            <td>%s</td>
                        </tr>
                        <tr>
                            <td><b>Transfer Ref</b></td>
                            <td>%s</td>
                        </tr>
                        <tr>
                            <td><b>Received Date</b></td>
                            <td>%s</td>
                        </tr>
                        <tr>
                            <td><b>Validated By</b></td>
                            <td>%s</td>
                        </tr>
                    </table>
                </div>
                <p style="font-size:13px; color:#888;">
                    All quantities have been received. No further follow-up needed.
                </p>

                <!-- ✅ View Requisition Button -->
                <div style="text-align:center; margin: 24px 0;">
                    <a href="%s"
                       style="background-color:#1a6b3c;
                              color:#ffffff;
                              padding:12px 32px;
                              border-radius:6px;
                              text-decoration:none;
                              font-size:14px;
                              font-weight:bold;
                              display:inline-block;">
                        &#128065; View Requisition
                    </a>
                </div>

                <p>
                    Thanks &amp; Regards,<br/>
                    <strong>%s</strong>
                </p>
            </div>
            <div style="background-color:#1a6b3c; padding:16px; text-align:center;">
                <p style="color:#ffffff; font-size:12px; margin:0;">
                    This is an automated notification from %s.
                </p>
            </div>
        </div>
        """ % (
            requisition.name,  # paragraph bold
            requisition.name,  # Requisition Ref
            self.name,  # Transfer Ref
            fields.Date.today().strftime('%d-%m-%Y'),  # Received Date
            self.env.user.name,  # Validated By
            requisition_url,  # ✅ Button href
            self.env.user.name,  # Thanks & Regards
            self.company_id.name or 'Odoo ERP',  # footer
        )

        for user in store_users:
            self.env['mail.mail'].sudo().create({
                'auto_delete': False,
                'author_id': self.env.user.partner_id.id,
                'subject': 'Material Fully Received: %s / %s' % (requisition.name, self.name),
                'body_html': body_html,
                'email_to': user.partner_id.email,
                'email_from': (
                        self.env.user.email_formatted
                        or self.company_id.partner_id.email_formatted
                ),
            }).send()


class StockMove(models.Model):
    _inherit = 'stock.move'
    
    custom_requisition_line_id = fields.Many2one(
        'material.purchase.requisition.line',
        string='Requisitions Line',
        copy=True
    )
