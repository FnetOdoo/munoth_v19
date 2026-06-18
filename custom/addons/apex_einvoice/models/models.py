from odoo import models, fields, api


class AccountEinvoice(models.Model):
    _name = 'account.einvoice'
    _rec_name = 'invoice_id'
    _description = "Einvoice"

    status = fields.Selection([('ACT', 'Active'), ('CNL', 'Cancelled')], string="Status")
    invoice_id = fields.Many2one('account.move', string="Invoice")
    ackno = fields.Char("Ack No")
    ackdt = fields.Datetime("Ack Date")
    cancel_date = fields.Datetime("Cancel Date")
    reason = fields.Char('Cancel Reason')
    irn = fields.Char("IRN Number")
    signedinvoice = fields.Char("Signed Invoice")
    signedqrcode = fields.Char("Signed QR Code")
    ewbno = fields.Char("EwbNo")
    ewbstatus = fields.Selection([('ACT', 'Active'), ('CNL', 'Cancelled')], "Ewb Status")
    ewbdt = fields.Datetime("EwbDt")
    ewbvalidtill = fields.Datetime("EwbValidTill")
    remarks = fields.Char("Remarks")
    response = fields.Text("Response")


class ResPartner(models.Model):
    _inherit = 'res.partner'

    state_code = fields.Char("State Code")
    distance = fields.Integer("Distance")
