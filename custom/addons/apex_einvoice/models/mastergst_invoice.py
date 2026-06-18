from odoo import fields, models, api, _
from odoo.exceptions import UserError
import json
import pytz
import requests
import re
import qrcode
import base64
from io import BytesIO


def to_naive_utc(datetime, record):
    tz_name = record._context.get('tz') or record.env.user.tz
    tz = tz_name and pytz.timezone(tz_name) or pytz.UTC
    return tz.localize(datetime.replace(tzinfo=None), is_dst=False).astimezone(pytz.UTC).replace(tzinfo=None)


class AccountInvoice(models.Model):
    _inherit = 'account.move'

    enable_einv = fields.Boolean('Enable E-Invoice')
    einvoice_id = fields.Many2one('account.einvoice', 'Einvoice Details', copy=False)
    ewbno = fields.Char("EwbNo", related='einvoice_id.ewbno', store=True)
    ewbdt = fields.Datetime("EwbDt", related='einvoice_id.ewbdt', store=True)
    ewbstatus = fields.Selection([('ACT', 'Active'), ('CNL', 'Cancelled')], "Ewb Status", related='einvoice_id.ewbstatus', store=True)
    ewbvalidtill = fields.Datetime("EwbValidTill", related='einvoice_id.ewbvalidtill', store=True)
    remarks = fields.Char("Remarks", related='einvoice_id.remarks', store=True)
    ackno = fields.Char("Ack No", related='einvoice_id.ackno', store=True)
    ackdt = fields.Datetime("Ack Date", related='einvoice_id.ackdt', store=True)
    irn_cancel_date = fields.Datetime("Cancel Date", related='einvoice_id.cancel_date', store=True)
    irn = fields.Char("IRN Number", related='einvoice_id.irn', store=True)
    qr_image_1 = fields.Binary("QR Printed", store=True)
    einv_status = fields.Selection([('ACT', 'Active'), ('CNL', 'Cancelled')], string="E-Invoice Status", related='einvoice_id.status', store=True)
    tpt_name_id = fields.Many2one('res.partner', string="Transport")
    trans_id = fields.Char('TransID', related='tpt_name_id.vat')
    trans_distant = fields.Integer("Distance", related='partner_id.distance')
    trans_name = fields.Char('Trans Name', related='tpt_name_id.name')
    trans_number = fields.Char('TransDocNo')
    trans_date = fields.Date('TransDocDt')
    trans_vehicle_number = fields.Char('Vehicle No')
    trans_mode = fields.Selection([('1', 'Road'),('2', 'Rail'),('3', 'Air'),('4', 'Ship')], string='Trans Mode', default='1')
    trans_vehicle_type = fields.Selection([('R', 'Regular'), ('O', 'ODC')], string='Vehicle Type', default='R')

    def _validate_invoice_data(self):
        self.ensure_one()
        message = str()
        if not self.name or not re.match("^.{1,16}$", self.name):
            message += "\n- Invoice number should not be more than 16 charactor"
        for line in self.invoice_line_ids:
            if line.product_id and (
                not line.product_id.l10n_in_hsn_code
                or not re.match("^[0-9]+$", line.product_id.l10n_in_hsn_code)
            ):
                message += "\n- HSN code required for product %s" % (
                    line.product_id.name
                )

        if message:
            raise UserError(
                "Data not valid for the Invoice: %s\n%s" % (self.name, message)
            )

    def _extract_digits(self, string):
        matches = re.findall(r"\d+", string)
        result = "".join(matches)
        return result

    def _validate_legal_identity_data(self, partner, is_company=False):
        self.ensure_one()
        message = str()
        if not partner:
            raise UserError("Error: Customer not found!")
        if is_company and partner.country_id.code != "IN":
            message += "\n- Country should be India"
        if not re.match("^.{3,100}$", partner.street or ""):
            message += "\n- Street required min 3 and max 100 charactor"
        if partner.street2 and not re.match("^.{3,100}$", partner.street2):
            message += "\n- Street2 should be min 3 and max 100 charactor"
        if not re.match("^.{3,100}$", partner.city or ""):
            message += "\n- City required min 3 and max 100 charactor"
        if not re.match("^.{3,50}$", partner.state_id.name or ""):
            message += "\n- State required min 3 and max 50 charactor"
        if partner.country_id.code == "IN" and not re.match(
            "^[0-9]{6,}$", partner.zip or ""
        ):
            message += "\n- Zip code required 6 digites"
        # if partner.phone and not re.match(
        #     "^[0-9]{10,12}$", self._extract_digits(partner.phone)
        # ):
        #     message += "\n- Mobile number should be minimum 10 or maximum 12 digites"
        if partner.email and (
            not re.match(
                r"^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$", partner.email
            )
            or not re.match("^.{3,100}$", partner.email)
        ):
            message += (
                "\n- Email address should be valid and not more then 100 charactor"
            )

        if not is_company:
            # TODO: check customer specific details
            pass

        if message:
            raise UserError(
                "Data not valid for the %s: %s\n%s"
                % (is_company and "Company" or "Customer", partner.name, message)
            )

    def get_einvoice_config(self):
        config = self.env['einvoice.configuration'].search([('company_id', '=', self.company_id.id)], limit=1)
        if not config:
            raise UserError(_("Please Configure E-Invoice Settings for the company: %s" %(self.company_id.name)))
        return config

    def genarate_einvoice(self):
        config = self.get_einvoice_config()
        company = self.company_id.partner_id
        customer = self.partner_id
        self._validate_invoice_data()
        self._validate_legal_identity_data(company, is_company=True)
        self._validate_legal_identity_data(customer)
        config.check_matergst_api()
        url = config.url + '/einvoice/type/GENERATE/version/V1_03'
        prep_data = self._l10n_in_edi_generate_invoice_json(self)
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
        data = json.dumps(prep_data)
        response = requests.post(url, headers=headers, params=params, data=data).json()
        if response and response['status_cd'] == '1':
            dt = to_naive_utc(fields.Datetime.from_string(response['data']['AckDt']), self)
            res = self.env['account.einvoice'].create({
                'invoice_id': self.id,
                'ackno': response['data']['AckNo'],
                'ackdt': dt,
                'irn': response['data']['Irn'],
                'signedinvoice': response['data']['SignedInvoice'],
                'signedqrcode': response['data']['SignedQRCode'],
                'status': response['data']['Status'],
                'ewbno': response['data']['EwbNo'] if response['data']['EwbNo'] is not None else False,
                'ewbdt': response['data']['EwbDt'] if response['data']['EwbDt'] is not None else False,
                'ewbvalidtill': response['data']['EwbValidTill'] if response['data']['EwbValidTill'] is not None else False,
                'remarks': response['data']['Remarks'] if response['data']['Remarks'] is not None else False,
            })
            self.einvoice_id = res.id
        else:
            raise UserError(_("%s" % (response['status_desc'])))

    def generate_eway(self):
        config = self.get_einvoice_config()
        if not self.einvoice_id:
            raise UserError(_("Please generate eInvoice in order to generate eway bill...!"))
        config.check_matergst_api()
        url = config.url + '/einvoice/type/GENERATE_EWAYBILL/version/V1_03'
        headers = {
            'ip_address': config.public_ip,
            'client_id': config.client_id,
            'client_secret': config.client_secret,
            'username': config.inv_user,
            'auth-token': config.auth_key,
            'gstin': config.inv_gst_num,
            'Content-Type': 'application/json',
        }
        params = (('email', config.email),)
        data = json.dumps({
            "Irn": self.einvoice_id.irn or None,
            "Distance": self.trans_distant or None,
            "TransMode": self.trans_mode or None,
            "TransId": self.trans_id or None,
            "TransName": self.trans_name or None,
            "TransDocDt": fields.Date.from_string(self.trans_date).strftime("%d/%m/%Y") if self.trans_date else None,
            "TransDocNo": self.trans_number or None,
            "VehNo": self.trans_vehicle_number or None,
            "VehType": self.trans_vehicle_type or None
        })
        response = requests.post(url, headers=headers, params=params, data=data)
        response = response.json()
        if response and response['status_cd'] == '1':
            dt = to_naive_utc(fields.Datetime.from_string(response['data']['EwbDt']), self)
            valid_dt = to_naive_utc(fields.Datetime.from_string(response['data']['EwbValidTill']), self)
            self.einvoice_id.write({
                'ewbno': response['data']['EwbNo'] or False,
                'ewbdt': dt,
                'ewbvalidtill': valid_dt,
                'ewbstatus': 'ACT',
            })
        else:
            raise UserError(_("%s" % (response['status_desc'])))

    def check_eway_details(self):
        config = self.get_einvoice_config()
        config.check_matergst_api()
        url = config.url + '/einvoice/type/GETEWAYBILLIRN/version/V1_03'
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
            ('param1', self.irn),
            ('supplier_gstn', config.inv_gst_num),
            ('email', config.email),
        )
        response = requests.get(url, headers=headers, params=params)
        response = response.json()
        if response and response['status_cd'] == '1':
            dt = to_naive_utc(fields.Datetime.from_string(response['data']['EwbDt']), self)
            valid_dt = ''
            if response['data']['EwbValidTill']:
                valid_dt = to_naive_utc(fields.Datetime.from_string(response['data']['EwbValidTill']), self)
            self.einvoice_id.write({
                'ewbno': response['data']['EwbNo'] or '',
                'ewbdt': dt,
                'ewbvalidtill': valid_dt,
                'ewbstatus': response['data']['Status'],
            })
        else:
            raise UserError(_("%s" % (response['status_desc'])))

    @api.model
    def _l10n_in_prepare_edi_tax_details(self, move, in_foreign=False):
        def l10n_in_grouping_key_generator(tax_values):
            base_line = tax_values["base_line_id"]
            tax_line = tax_values["tax_line_id"]
            line_code = "other"
            tax_report_line_sc = self.env.ref("l10n_in.tax_report_line_state_cess", False)
            if any(tag in tax_line.tax_tag_ids for tag in self.env.ref("l10n_in.tax_report_line_cess").sudo().tag_ids):
                if tax_line.tax_line_id.amount_type != "percent":
                    line_code = "cess_non_advol"
                else:
                    line_code = "cess"
            elif tax_report_line_sc and any(tag in tax_line.tax_tag_ids for tag in tax_report_line_sc.sudo().tag_ids):
                if tax_line.tax_line_id.amount_type != "percent":
                    line_code = "state_cess_non_advol"
                else:
                    line_code = "state_cess"
            else:
                for gst in ["cgst", "sgst", "igst"]:
                    tag_ids = self.env.ref("l10n_in.tax_report_line_%s" % (gst)).sudo().tag_ids
                    if any(tag in tax_line.tax_tag_ids for tag in tag_ids):
                        line_code = gst
            return {
                "tax": tax_values["tax_id"],
                "base_product_id": base_line.product_id,
                "tax_product_id": tax_line.product_id,
                "base_product_uom_id": base_line.product_uom_id,
                "tax_product_uom_id": tax_line.product_uom_id,
                "line_code": line_code,
            }
        def l10n_in_filter_to_apply(tax_values):
            if tax_values["base_line_id"].is_rounding_line:
                return False
            return True

        return move._prepare_edi_tax_details(
            filter_to_apply=l10n_in_filter_to_apply,
            grouping_key_generator=l10n_in_grouping_key_generator,
        )

    @api.model
    def _get_l10n_in_tax_details_by_line_code(self, tax_details):
        l10n_in_tax_details = {}
        for tax_detail in tax_details.values():
            if tax_detail["tax"].l10n_in_reverse_charge:
                l10n_in_tax_details.setdefault("is_reverse_charge", True)
            l10n_in_tax_details.setdefault("%s_rate" % (tax_detail["line_code"]), tax_detail["tax"].amount)
            l10n_in_tax_details.setdefault("%s_amount" % (tax_detail["line_code"]), 0.00)
            l10n_in_tax_details.setdefault("%s_amount_currency" % (tax_detail["line_code"]), 0.00)
            l10n_in_tax_details["%s_amount" % (tax_detail["line_code"])] += tax_detail["tax_amount"]
            l10n_in_tax_details["%s_amount_currency" % (tax_detail["line_code"])] += tax_detail["tax_amount_currency"]
        return l10n_in_tax_details

    @api.model
    def _l10n_in_round_value(self, amount, precision_digits=2):
        """
            This method is call for rounding.
            If anything is wrong with rounding then we quick fix in method
        """
        return round(amount, precision_digits)

    def _l10n_in_edi_extract_digits(self, string):
        if not string:
            return string
        matches = re.findall(r"\d+", string)
        result = "".join(matches)
        return result

    def _get_l10n_in_edi_line_details(self, index, line, line_tax_details, sign):
        """
        Create the dictionary with line details
        return {
            account.move.line('1'): {....},
            account.move.line('2'): {....},
            ....
        }
        """
        tax_details_by_code = self._get_l10n_in_tax_details_by_line_code(line_tax_details.get("tax_details", {}))
        return {
            "SlNo": str(index),
            "PrdDesc": line.name.replace("\n", ""),
            # "IsServc": line.product_id.type == "service" and "Y" or "N",
            "IsServc": 'Y' if (line.product_id.is_service == True or line.product_id.type == 'service') else 'N',
            "HsnCd": self._l10n_in_edi_extract_digits(line.product_id.l10n_in_hsn_code),
            "Qty": self._l10n_in_round_value(line.quantity or 0.0, 3),
            "Unit": line.product_uom_id.l10n_in_code and line.product_uom_id.l10n_in_code.split("-")[0] or "OTH",
            # Unit price in company currency and tax excluded so its different then price_unit
            "UnitPrice": self._l10n_in_round_value(
                ((line.balance / (1 - (line.discount / 100))) / line.quantity) * sign, 3),
            # total amount is before discount
            "TotAmt": self._l10n_in_round_value((line.balance / (1 - (line.discount / 100))) * sign),
            "Discount": self._l10n_in_round_value(
                ((line.balance / (1 - (line.discount / 100))) - line.balance) * sign),
            "AssAmt": self._l10n_in_round_value(line.balance * sign),
            "GstRt": self._l10n_in_round_value(tax_details_by_code.get("igst_rate", 0.00) or (
                tax_details_by_code.get("cgst_rate", 0.00) + tax_details_by_code.get("sgst_rate", 0.00)), 3),
            "IgstAmt": self._l10n_in_round_value(tax_details_by_code.get("igst_amount", 0.00) * sign),
            "CgstAmt": self._l10n_in_round_value(tax_details_by_code.get("cgst_amount", 0.00) * sign),
            "SgstAmt": self._l10n_in_round_value(tax_details_by_code.get("sgst_amount", 0.00) * sign),
            "CesRt": self._l10n_in_round_value(tax_details_by_code.get("cess_rate", 0.00), 3),
            "CesAmt": self._l10n_in_round_value(tax_details_by_code.get("cess_amount", 0.00) * sign),
            "CesNonAdvlAmt": self._l10n_in_round_value(
                tax_details_by_code.get("cess_non_advol_amount", 0.00) * sign),
            "StateCesRt": self._l10n_in_round_value(tax_details_by_code.get("state_cess_rate_amount", 0.00), 3),
            "StateCesAmt": self._l10n_in_round_value(tax_details_by_code.get("state_cess_amount", 0.00) * sign),
            "StateCesNonAdvlAmt": self._l10n_in_round_value(
                tax_details_by_code.get("state_cess_non_advol_amount", 0.00) * sign),
            "OthChrg": self._l10n_in_round_value(tax_details_by_code.get("other_amount", 0.00) * sign),
            "TotItemVal": self._l10n_in_round_value(
                (line.balance + line_tax_details.get("tax_amount", 0.00)) * sign),
        }

    def generate_qr_code(self):
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=20,
            border=4,
        )
        if self.einvoice_id:
            qr.add_data(self.einvoice_id.signedqrcode)
            qr.make(fit=True)
            img = qr.make_image()
            temp = BytesIO()
            img.save(temp, format="PNG")
            qr_img = base64.b64encode(temp.getvalue())
            return qr_img
        else:
            return False

    def preview_qrcode(self):
        self.ensure_one()
        self.qr_image_1 = self.generate_qr_code()

    def print_json_file(self):
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/invoice/json?record=%s' % (self.id),
            'target': 'self',
        }

    def _get_l10n_in_edi_saler_buyer_party(self, move):
        return {
            "seller_details": move.company_id.partner_id,
            "dispatch_details": move._l10n_in_get_warehouse_address() or move.company_id.partner_id,
            "buyer_details": move.partner_id,
            "ship_to_details": move._l10n_in_get_shipping_partner(),
        }

    def _l10n_in_get_supply_type(self, move, tax_details_by_code):
        supply_type = "B2B"
        if move.l10n_in_gst_treatment in ("overseas", "special_economic_zone") and tax_details_by_code.get(
                "igst_amount"):
            supply_type = move.l10n_in_gst_treatment == "overseas" and "EXPWP" or "SEZWP"
        elif move.l10n_in_gst_treatment in ("overseas", "special_economic_zone"):
            supply_type = move.l10n_in_gst_treatment == "overseas" and "EXPWOP" or "SEZWOP"
        elif move.l10n_in_gst_treatment == "deemed_export":
            supply_type = "DEXP"
        return supply_type

    @api.model
    def _get_l10n_in_edi_partner_details(self, partner, set_vat=True, set_phone_and_email=True,
                                         is_overseas=False, pos_state_id=False):
        """
            Create the dictionary based partner details
            if set_vat is true then, vat(GSTIN) and legal name(LglNm) is added
            if set_phone_and_email is true then phone and email is add
            if set_pos is true then state code from partner or passed state_id is added as POS(place of supply)
            if is_overseas is true then pin is 999999 and GSTIN(vat) is URP and Stcd is .
            if pos_state_id is passed then we use set POS
        """
        partner_details = {
            "Addr1": partner.street or "",
            "Loc": partner.city or "",
            "Pin": int(self._l10n_in_edi_extract_digits(partner.zip)),
            "Stcd": partner.state_id.l10n_in_tin or "",
        }
        if partner.street2:
            partner_details.update({"Addr2": partner.street2})
        if set_phone_and_email:
            if partner.email:
                partner_details.update({"Em": partner.email})
            if partner.phone:
                partner_details.update({"Ph": self._l10n_in_edi_extract_digits(partner.phone)})
        if pos_state_id:
            partner_details.update({"POS": pos_state_id.l10n_in_tin or ""})
        if set_vat:
            partner_details.update({
                "LglNm": partner.commercial_partner_id.name,
                "GSTIN": partner.vat or "",
            })
        else:
            partner_details.update({"Nm": partner.name})
        if is_overseas:
            partner_details.update({
                "GSTIN": "URP",
                "Pin": 999999,
                "Stcd": "96",
                "POS": "96",
            })
        return partner_details
    
    def _l10n_in_edi_generate_invoice_json(self, invoice):
        tax_details = self._l10n_in_prepare_edi_tax_details(invoice)
        saler_buyer = self._get_l10n_in_edi_saler_buyer_party(invoice)
        tax_details_by_code = self._get_l10n_in_tax_details_by_line_code(tax_details.get("tax_details", {}))
        sign = invoice.is_inbound() and -1 or 1
        is_intra_state = invoice.l10n_in_state_id == invoice.company_id.state_id
        is_overseas = invoice.l10n_in_gst_treatment == "overseas"
        lines = invoice.invoice_line_ids.filtered(lambda line: not (line.display_type or line.is_rounding_line))
        invoice_line_tax_details = tax_details.get("invoice_line_tax_details")
        json_payload = {
            "Version": "1.1",
            "TranDtls": {
                "TaxSch": "GST",
                "SupTyp": self._l10n_in_get_supply_type(invoice, tax_details_by_code),
                "RegRev": tax_details_by_code.get("is_reverse_charge") and "Y" or "N",
                "IgstOnIntra": is_intra_state and tax_details_by_code.get("igst") and "Y" or "N"},
            "DocDtls": {
                "Typ": invoice.move_type == "out_refund" and "CRN" or "INV",
                "No": invoice.name,
                "Dt": invoice.invoice_date.strftime("%d/%m/%Y")},
            "SellerDtls": self._get_l10n_in_edi_partner_details(saler_buyer.get("seller_details")),
            "BuyerDtls": self._get_l10n_in_edi_partner_details(
                saler_buyer.get("buyer_details"), pos_state_id=invoice.l10n_in_state_id, is_overseas=is_overseas),
            "ItemList": [
                self._get_l10n_in_edi_line_details(index, line, invoice_line_tax_details.get(line, {}), sign)
                for index, line in enumerate(lines, start=1)
            ],
            "ValDtls": {
                "AssVal": self._l10n_in_round_value(tax_details.get("base_amount") * sign),
                "CgstVal": self._l10n_in_round_value(tax_details_by_code.get("cgst_amount", 0.00) * sign),
                "SgstVal": self._l10n_in_round_value(tax_details_by_code.get("sgst_amount", 0.00) * sign),
                "IgstVal": self._l10n_in_round_value(tax_details_by_code.get("igst_amount", 0.00) * sign),
                "CesVal": self._l10n_in_round_value((
                    tax_details_by_code.get("cess_amount", 0.00)
                    + tax_details_by_code.get("cess_non_advol_amount", 0.00)) * sign,
                ),
                "StCesVal": self._l10n_in_round_value((
                    tax_details_by_code.get("state_cess_amount", 0.00)
                    + tax_details_by_code.get("state_cess_non_advol_amount", 0.00)) * sign,
                ),
                "RndOffAmt": self._l10n_in_round_value(
                    sum(line.balance for line in invoice.invoice_line_ids if line.is_rounding_line)),
                "TotInvVal": self._l10n_in_round_value(
                    (tax_details.get("base_amount") + tax_details.get("tax_amount")) * sign),
            },
        }
        if invoice.company_currency_id != invoice.currency_id:
            json_payload["ValDtls"].update({
                "TotInvValFc": self._l10n_in_round_value(
                    (tax_details.get("base_amount_currency") + tax_details.get("tax_amount_currency")) * sign)
            })
        if saler_buyer.get("seller_details") != saler_buyer.get("dispatch_details"):
            json_payload.update({
                "DispDtls": self._get_l10n_in_edi_partner_details(saler_buyer.get("dispatch_details"),
                    set_vat=False, set_phone_and_email=False)
            })
        if saler_buyer.get("buyer_details") != saler_buyer.get("ship_to_details"):
            json_payload.update({
                "ShipDtls": self._get_l10n_in_edi_partner_details(saler_buyer.get("ship_to_details"))
            })
        if is_overseas:
            json_payload.update({
                "ExpDtls": {
                    "ShipBNo": invoice.l10n_in_shipping_bill_number or "",
                    "ShipBDt": invoice.l10n_in_shipping_bill_date
                       and invoice.l10n_in_shipping_bill_date.strftime("%d/%m/%Y") or "",
                    "Port": invoice.l10n_in_shipping_port_code_id.code or "",
                    "RefClm": tax_details_by_code.get("igst") and "Y" or "N",
                    "ForCur": invoice.currency_id.name,
                    "CntCode": saler_buyer.get("buyer_details").country_id.code or "",
                }
            })
        return json_payload

