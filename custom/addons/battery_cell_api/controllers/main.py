# controllers/main.py
import json
from odoo import http
from odoo.http import request


class BatteryCellAPI(http.Controller):

    @http.route('/update_battery_cell', type='json', auth='public', methods=['POST'], csrf=False)
    def update_battery_cell(self, **kwargs):
        data = json.loads(request.httprequest.data)
        if data:
            battery_data_list = data.get('data', [])
            for battery_data in battery_data_list:
                request.env['battery.cell.log'].sudo().create(battery_data)
            return request
        else:
            print("\n ---------------------Data Not Fount In BatteryCellAPI------------------------- \n")




class InjectionCellAPI(http.Controller):

    @http.route('/update_injection_cell', type='json', auth='public', methods=['POST'], csrf=False)
    def update_injection_cell(self, **kwargs):
        print("\n======================= InjectionCellAPI Called =======================")

        raw_data = request.httprequest.data
        print("Raw JSON Received:", raw_data)

        data = json.loads(raw_data)

        if data:
            injection_data_list = data.get('data', [])
            print("Parsed Injection Data List:", injection_data_list)

            if injection_data_list:
                for injection_data in injection_data_list:
                    print("Creating Record:", injection_data)
                    request.env['injection.cell.log'].sudo().create(injection_data)
                print("All records successfully created.")
            else:
                print("'data' key is present but list is empty.")
        else:
            print("No data found in request.")





class CellClampBakingAPI(http.Controller):

    @http.route('/update_cell_clamp_baking', type='json', auth='public', methods=['POST'], csrf=False)
    def update_cell_clamp_baking(self, **kwargs):
        print("\n======================= CellClampBakingAPI Called =======================")

        raw_data = request.httprequest.data
        print("Raw JSON Received:", raw_data)

        data = json.loads(raw_data)

        if data:
            baking_data_list = data.get('data', [])
            print("Parsed Baking Data List:", baking_data_list)

            if baking_data_list:
                for baking_data in baking_data_list:
                    print("Creating Record:", baking_data)
                    request.env['cell.clamp.baking.log'].sudo().create(baking_data)
                print("All records successfully created.")
            else:
                print("'data' key is present but list is empty.")
        else:
            print("No data found in request.")


class DummyPartnerAPI(http.Controller):

    @http.route('/create_dummy_partner', type='json', auth='public', methods=['POST'], csrf=False)
    def create_dummy_partner(self, **kwargs):
        partner_data_list = kwargs.get('data', [])
        if partner_data_list:
            for partner_data in partner_data_list:
                request.env['dummy.partner'].sudo().create(partner_data)
            return {"status": "success", "created": len(partner_data_list)}
        else:
            print("\n ---------------------Data Not Found In DummyPartnerAPI------------------------- \n")
            return {"status": "error", "message": "Data Not Found"}