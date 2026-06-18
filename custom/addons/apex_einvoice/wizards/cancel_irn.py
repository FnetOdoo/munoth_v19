from odoo import models, fields, api, _
from odoo.exceptions import UserError
import json
import requests


class AccountEinvoice(models.TransientModel):
    _name = 'einvoice.cancel.wizard'
    _description = "Cance Wizard"

    invoice_id = fields.Many2one('account.move', string='Invoice')
    einvoice_id = fields.Many2one('account.einvoice', string='E-invoice', related='invoice_id.einvoice_id')
    irn = fields.Char("IRN", related='einvoice_id.irn')
    reason = fields.Text("Reason", required=True)
    type = fields.Selection([('irn', 'IRN'), ('eway', 'EWay')], string="Cancel Request of", default='irn')

    def process(self):
        if self.type == 'irn':
            self.cancel_irn()
        else:
            self.cancel_eway()

    def cancel_irn(self):
        config = self.invoice_id.get_einvoice_config()
        if not config:
            raise UserError(_("Please Configure Settings!"))
        url = config.url + '/einvoice/type/CANCEL/version/V1_03'
        config.check_matergst_api()
        headers = {
            'ip_address': config.public_ip,
            'client_id': config.client_id,
            'client_secret': config.client_secret,
            'username': config.inv_user,
            'auth-token': config.auth_key,
            'gstin': config.inv_gst_num,
            'Content-Type': 'application/json',
        }

        params = (
            ('email', config.email),
        )
        data = {
            "Irn": self.irn,
            "CnlRsn": "1",
            "CnlRem": self.reason
        }
        response = requests.post(url, headers=headers, params=params, data=json.dumps(data)).json()
        if response and response['status_cd'] == '1':
            # utc_tz = to_naive_utc(fields.Datetime.from_string(response['data']['TokenExpiry']), self)
            self.einvoice_id.write({
                'cancel_date': response['data']['CancelDate'],
                'status': 'CNL',
                'reason': self.reason
            })
        else:
            raise UserError(_("%s" % (response['status_desc'])))

    def cancel_eway(self):
        config = self.invoice_id.get_einvoice_config()
        if not self.einvoice_id:
            raise UserError(_("Please generate eInvoice in order to generate eway bill...!"))
        url = config.url + '/ewaybillapi/v1.03/ewayapi/canewb'
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'ip_address': config.public_ip,
            'client_id': config.client_id,
            'client_secret': config.client_secret,
            'gstin': config.inv_gst_num,
        }

        params = {
            'email': config.email,
        }

        data = {
            "ewbNo": int(self.einvoice_id.ewbno),
            "cancelRsnCode": 1,
            "cancelRmrk": self.reason
            }
        result = requests.post(url, headers=headers, params=params, data=data)
        response = result.json()
        if response and response['status_cd'] == '1':
            # utc_tz = to_naive_utc(fields.Datetime.from_string(response['data']['TokenExpiry']), self)
            # self.einvoice_id.write({
            #     'cancel_date': response['data']['CancelDate'],
            #     'status': 'CNL',
            #     'reason': self.reason
            # })
            pass
        else:
            raise UserError(_("%s" % (response['error'])))