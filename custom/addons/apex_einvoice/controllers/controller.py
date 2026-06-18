from odoo import http, fields
from odoo.http import content_disposition, request
import json


class InvoiceJson(http.Controller):
    @http.route('/web/invoice/json', type='http', auth="user")
    def print_txt(self, record, **kw):
        invoice = http.request.env['account.move'].search([('id', '=', record)])
        json_value = invoice._l10n_in_edi_generate_invoice_json(invoice)
        val = []
        val.append(json_value)
        with open('/tmp/result.json', 'w+') as fp:
            json.dump(val, fp)
            fp.seek(0)
            file_data = fp.read()
            fp.close()
        return request.make_response(file_data, headers=[
            ('Content-Disposition', content_disposition(invoice.name + '.json')),
            ('Content-Type', 'application/json'),
        ])
