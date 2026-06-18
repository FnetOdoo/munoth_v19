from odoo import fields, models, api, _
from odoo.exceptions import UserError
import requests
import pytz
from datetime import datetime, timezone


def to_naive_utc(datetime, record):
    tz_name = record._context.get('tz') or record.env.user.tz
    tz = tz_name and pytz.timezone(tz_name) or pytz.UTC
    return tz.localize(datetime.replace(tzinfo=None), is_dst=False).astimezone(pytz.UTC).replace(tzinfo=None)


class EinvoiceConfiguration(models.Model):
    _name = "einvoice.configuration"
    _description = "Einvoice Config"

    # Genral Fields
    active = fields.Boolean("Active", default=True)
    name = fields.Char("Name", required=1)
    url = fields.Char("API URL", default="https://api.mastergst.com")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.user.company_id)
    public_ip = fields.Char("Public IP")
    email = fields.Char("Email")
    client_id = fields.Char("Client ID", required=1)
    client_secret = fields.Char("Client Secret", required=1)
    # app_key = fields.Char("App Key", required=1, help="Randomly generated 32 bit key")
    # Response
    auth_key = fields.Char("Authentication Key", readonly=1, store=True, copy=False)
    sek = fields.Char("Sek", readonly=1, store=True, copy=False)
    date_expiry = fields.Datetime("Token Expiry", readonly=1, store=True, copy=False)

    # E-Invoice Related Fields
    inv_gst_num = fields.Char("GST No")
    inv_user = fields.Char("User Name")
    inv_password = fields.Char("Password")
    einv_public_key = fields.Char("E-Invoice Public Key", help="Copy and paste the Einvoice public key here...")

    # EwayBill Related Fields
    eway_gst_num = fields.Char("GST No")
    eway_user = fields.Char("User Name")
    eway_password = fields.Char("Password")
    ewaybill_public_key = fields.Char("EWay Public Key", help="Copy and paste the public key here...")

    def is_token_expired(self):
        datetime_ist = datetime.now(pytz.timezone('Asia/Kolkata'))
        form_dt = datetime_ist.strftime('%Y:%m:%d %H:%M:%S')
        if self.date_expiry and str(form_dt) > str(self.date_expiry):
            return True
        else:
            return False

    def check_publicip(self):
        if not self.public_ip:
            try:
                res = requests.get('https://checkip.amazonaws.com').text.strip()
                self.public_ip = res
            except Exception as E:
                raise UserError(_("Failed to get Public IP: %s.\nPlease enter your Public IP manually in E-invoice Configuration" %(E)))

    def check_matergst_api(self):
        if self.date_expiry and not self.is_token_expired():
            return
        self.check_publicip()
        headers = {
            'username': self.inv_user,
            'password': self.inv_password,
            'ip_address': self.public_ip,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'gstin': self.inv_gst_num,
        }

        params = (
            ('email', self.email),
        )
        url = self.url + '/einvoice/authenticate'
        response = requests.get(url, headers=headers, params=params).json()
        if response and response['status_cd'] == 'Sucess':
            # utc_tz = to_naive_utc(fields.Datetime.from_string(response['data']['TokenExpiry']), self)
            self.write({
                'auth_key': response['data']['AuthToken'],
                'sek': response['data']['Sek'],
                'date_expiry': fields.Datetime.from_string(response['data']['TokenExpiry']),
            })
        else:
            raise UserError(_("%s" % (response['status_desc'])))
