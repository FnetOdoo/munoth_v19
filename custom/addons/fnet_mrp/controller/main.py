from odoo import http
from odoo.http import request
import json
import random


class ResPartnerController(http.Controller):
    @http.route('/custom_api/get_res_partners', type='http', auth='public', methods=['GET'])
    def get_res_partners_id(self, **kw):
        partner_records = request.env['res.partner'].sudo().search_read([], ['name', 'email', 'phone'])
        return json.dumps(partner_records)


class LoginOtpRequest(http.Controller):
    @http.route('/api/get_login_otp', type='http', auth='none', methods=['GET'])
    def get_res_partners(self, **kw):
        api_key = kw.get('api_key')  # Extract the API key from the GET parameters

        # Assuming you have a valid API key stored in Odoo (replace 'YOUR_STORED_API_KEY' with your actual stored key)
        stored_api_key = "aaa024eeb57e00da281a28205017f6397732548d"

        if api_key != stored_api_key:
            return json.dumps({"error": "Invalid API key"})
        account_type = kw.get('account_type')

        otp_length = 4
        # Generate a random OTP
        otp = ""
        for i in range(otp_length):
            otp += str(random.randint(0, 4))
        if account_type == 'GUEST':
            return json.dumps({'account_type': 'GUEST', 'OTP': otp})
        if account_type == 'MEMBER':
            return json.dumps({'account_type': 'MEMBER', 'OTP': otp})

        partner_records = request.env['res.partner'].sudo().search_read([], ['name', 'email', 'phone'])
        return json.dumps(partner_records)
