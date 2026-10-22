from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class PaymentRequestLine(models.Model):
    _name = 'payment.request.line'
    _description = 'Payment Request Line'

    payment_request_id = fields.Many2one(
        'payment.request', string='Payment Request',
        required=True, ondelete='cascade',
    )
    account_move_id = fields.Many2one(
        'account.move', string='Bill',
        required=True, domain="[('move_type', '=', 'in_invoice'), ('state', '=', 'posted')]",
    )
    partner_id = fields.Many2one(
        'res.partner', string='Partner',
        related='account_move_id.partner_id', store=True,
    )
    bill_date = fields.Date(
        string='Bill Date',
        related='account_move_id.invoice_date', store=True,
    )
    invoice_date_due = fields.Date(
        string='Due Date',
        related='account_move_id.invoice_date_due', store=True,
    )
    amount_untaxed_signed = fields.Monetary(
        string='Tax Excluded',
        related='account_move_id.amount_untaxed_signed', store=True,
    )
    amount_total_signed = fields.Monetary(
        string='Total',
        related='account_move_id.amount_total_signed', store=True,
    )
    amount_total_in_currency_signed = fields.Monetary(
        string='Total in Currency',
        related='account_move_id.amount_total_in_currency_signed', store=True,
    )
    bill_amount = fields.Monetary(
        string='Amount Due',
        compute='_compute_bill_amount', store=True,
    )
    request_amount = fields.Monetary(
        string='Request Amount',
    )
    currency_id = fields.Many2one(
        'res.currency', string='Currency',
        related='payment_request_id.currency_id', store=True,
    )
    payment_state = fields.Selection(
        related='account_move_id.payment_state',
        string='Payment Status', store=True,
    )
    bill_state = fields.Selection(
        related='account_move_id.state',
        string='Status', store=True,
    )
    # Customer invoice related fields
    cust_invoice_partner_id = fields.Many2one(
        related='account_move_id.cust_invoice_partner_id',
        string='Invoice Customer', store=True,
    )
    cust_invoice_name = fields.Char(
        related='account_move_id.cust_invoice_name',
        string='Invoice Number', store=True,
    )
    reference_1 = fields.Char(
        related='account_move_id.reference_1',
        string='Reference', store=True,
    )
    cust_invoice_amount_residual = fields.Monetary(
        related='account_move_id.cust_invoice_amount_residual',
        string='Invoice Amount Due', store=True,
    )

    @api.depends('account_move_id', 'account_move_id.amount_residual_signed')
    def _compute_bill_amount(self):
        for line in self:
            line.bill_amount = abs(line.account_move_id.amount_residual_signed) if line.account_move_id else 0.0

    @api.constrains('request_amount')
    def _check_request_amount(self):
        for line in self:
            if line.request_amount < 0:
                raise ValidationError(_('Request amount cannot be negative for bill %s.') % line.account_move_id.name)
            # Only validate against bill_amount when PR is not yet paid
            if line.payment_request_id.state not in ('paid',) and line.bill_amount and line.request_amount > line.bill_amount:
                raise ValidationError(
                    _('Request amount (%.2f) cannot exceed the bill due amount (%.2f) for bill %s.')
                    % (line.request_amount, line.bill_amount, line.account_move_id.name)
                )

    def action_view_bill(self):
        """Open the corresponding bill in form view."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.account_move_id.id,
            'target': 'current',
        }

