# controllers/main.py
import json
from odoo import http
from odoo.http import request
from odoo import models, fields, api, _
import json
import re
from odoo import http
from odoo.http import request
from odoo import http
from odoo.http import request
import json
import logging
from datetime import date, time, datetime


_logger = logging.getLogger(__name__)

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

# class CellClampBakingAPI(http.Controller):
#
#     @http.route(['/update_cell_clamp_baking', '/update_mes_formation'], type='json', auth='public', methods=['POST'], csrf=False)
#     def update_cell_clamp_baking(self, **kwargs):
#         _logger.warning("\n======================= CellClampBakingAPI Called =======================")
#
#         raw_data = request.httprequest.data
#         _logger.warning(f"Raw JSON Received: {raw_data}")
#
#         data = json.loads(raw_data)
#
#         _logger.warning(f"Raw JSON Received: {data}")
#         if data:
#             # Parse nested structure: CommandRequestJson → EquipmentInfo → data
#             command_request = data.get('CommandRequestJson', {})
#             equipment_info  = command_request.get('EquipmentInfo', [])
#
#             total_created = 0
#             for equipment in equipment_info:
#                 records = equipment.get('data', [])
#                 for record in records:
#                     _logger.warning("Creating Record:", record)
#                     request.env['cell.clamp.baking.log'].sudo().create(record)
#                     total_created += 1
#
#             _logger.warning(f"All records successfully created. Total: {total_created}")
#         else:
#             _logger.warning("No data found in request.")

class CellClampBakingAPI(http.Controller):

    @http.route(['/update_cell_clamp_baking', '/update_mes_formation'], type='json', auth='public', methods=['POST'],
                csrf=False)
    def update_cell_clamp_baking(self, **kwargs):
        # print("\n======================= CellClampBakingAPI Called ===================")
        raw_data = request.httprequest.data
        # print("Raw JSON Received:", raw_data)


        _logger.warning("\n======================= CellClampBakingAPI Called ===================")
        _logger.warning("Something seems off: %s", raw_data)  # warnings

        def success_response(message="Formation data received successfully"):
            return {
                "status": True,
                "Message": message,
                "Res_Time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000")
            }

        def failure_response(message="Invalid barcode or missing required field"):
            return {
                "status": False,
                "Message": message,
                "Res_Time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S.000")
            }

        try:
            data = json.loads(raw_data)
        except Exception as e:
            # print("JSON parse error:", e)
            _logger.warning("JSON parse error:", e)
            return failure_response("Invalid JSON")

        if not data:
            # print("No data found in request.")
            _logger.warning("No data found in request.")
            return failure_response("Empty request")

        # Handle both JSON-RPC wrapped and direct payloads
        if 'params' in data:
            payload = data['params']
        else:
            payload = data

        command_request = payload.get('CommandRequestJson', {})
        equipment_info = command_request.get('EquipmentInfo', {})

        # EquipmentInfo can be either a DICT or a LIST — handle both
        if isinstance(equipment_info, dict):
            all_record_lists = [equipment_info.get('data', [])]
        elif isinstance(equipment_info, list):
            all_record_lists = [e.get('data', []) for e in equipment_info if isinstance(e, dict)]
        else:
            # print(f"Unexpected EquipmentInfo type: {type(equipment_info)}")
            _logger.warning(f"Unexpected EquipmentInfo type: {type(equipment_info)}")
            return failure_response("Unexpected EquipmentInfo format")

        total_created = 0
        for records in all_record_lists:
            for record in records:
                if not isinstance(record, dict):
                    # print(f"Skipping non-dict record: {record}")
                    _logger.warning(f"Skipping non-dict record: {record}")
                    continue
                try:
                    # print("Creating Record:", record)
                    _logger.warning("Creating Record:", record)
                    request.env['cell.clamp.baking.log'].sudo().create(record)
                    total_created += 1
                except Exception as e:
                    # print(f"Failed to create record: {e}\nRecord: {record}")
                    _logger.warning(f"Failed to create record: {e}\nRecord: {record}")
                    return failure_response(f"Failed to save record: {str(e)}")

        _logger.warning(f"All records successfully created. Total: {total_created}")
        return request

    # @http.route(['/update_cell_clamp_baking', '/update_mes_formation'], type='http', auth='public', methods=['POST'], csrf=False)
    # def update_cell_clamp_baking(self, **kwargs):
    #     print("\n======================= CellClampBakingAPI Called ===========2222222222222============")
    #     print(type,"Type .......................")
    #     # 1. Grab raw bytes data from incoming request
    #     raw_bytes = request.httprequest.data
    #     if not raw_bytes:
    #         print("No data found in request.")
    #         return request.make_response(
    #             json.dumps({'status': 'error', 'message': 'Empty payload'}),
    #             headers=[('Content-Type', 'application/json')]
    #         )
    #
    #     # 2. Decode payload safely into string format
    #     raw_data = raw_bytes.decode('utf-8', errors='ignore').strip()
    #     print(f"Raw Data Received (Length): {len(raw_data)}")
    #
    #     # 3. FIX HARDWARE NUMBER FORMATS FIRST (e.g., ': 0. ,' -> ': 0.0,')
    #     raw_data = re.sub(r'([:,\[])\s*(-?\d+)\.\s*([,}\]\r\n])', r'\1 \2.0\3', raw_data)
    #
    #     # 4. FIX UNEXPECTED TRUNCATION BY EXTRACTING VALID COMPLETED SLOTS ONLY
    #     if not (raw_data.endswith('}]}}') or raw_data.endswith('}]]}}') or raw_data.endswith('}')):
    #         print("⚠️ Truncated payload detected from hardware. Reconstructing valid blocks using regex extraction...")
    #
    #         # Escape illegal raw machine backslashes inside fields so regex doesn't choke
    #         raw_data = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', raw_data)
    #
    #         # IMPROVED REGEX: Match non-greedily from {"equipment_code" up to a valid closing object brace
    #         # Ensure it strictly looks for a balanced properties group ending with a valid number/string/bool token closure
    #         valid_blocks = re.findall(r'(\{"equipment_code".*?\})', raw_data)
    #
    #         # Filter out any blocks that are themselves structurally truncated inside the regex catch
    #         sanitized_blocks = []
    #         for block in valid_blocks:
    #             # If the block was cut off mid-way through a property string (e.g., ends in the middle of a key name/value), drop it
    #             if block.count('{') == block.count('}') and not block.endswith(':"}') and not block.endswith(',}'):
    #                 sanitized_blocks.append(block)
    #
    #         if sanitized_blocks:
    #             print(f"♻️ Isolated {len(sanitized_blocks)} complete records. Discarding broken trailing fragment.")
    #             # Forcefully assemble a beautifully formed, syntactically perfect JSON tree structure
    #             clean_string = (
    #                     '{"CommandID": "update_mes_formation_repaired", '
    #                     '"CommandRequestJson": {"EquipmentInfo": [{"data": [' +
    #                     ','.join(sanitized_blocks) +
    #                     ']}]}}'
    #             )
    #         else:
    #             print("❌ Payload was cut off so early that no single object block survived validation.")
    #             return request.make_response(
    #                 json.dumps({'status': 'error',
    #                             'message': 'Payload critically corrupted prior to identifiable block arrays.'}),
    #                 headers=[('Content-Type', 'application/json')]
    #             )
    #     else:
    #         print("📦 Payload structural format naturally intact. Running standard text cleanup.")
    #         # Standard cleanup for intact payloads
    #         raw_data = re.sub(r',\s*(?=[\]}])', '', raw_data)
    #         clean_string = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\', raw_data)
    #
    #     # 5. Attempt JSON parsing
    #     try:
    #         data = json.loads(clean_string)
    #     except Exception as e:
    #         print(f"❌ JSON Parsing critically failed: {str(e)}")
    #         error_char = getattr(e, 'pos', len(clean_string) - 50)
    #         snippet_start = max(0, error_char - 50)
    #         snippet_end = min(len(clean_string), error_char + 50)
    #         print("Error context snippet around failure:", clean_string[snippet_start:snippet_end])
    #
    #         return request.make_response(
    #             json.dumps({'status': 'error', 'message': f'Malformed JSON formatting string: {str(e)}'}),
    #             headers=[('Content-Type', 'application/json')]
    #         )
    #
    #     # 6. Loop data and create Odoo database records
    #     total_created = 0
    #     if data:
    #         command_request = data.get('CommandRequestJson', {})
    #         equipment_info = command_request.get('EquipmentInfo', {})
    #
    #         if isinstance(equipment_info, dict):
    #             equipment_list = [equipment_info]
    #         elif isinstance(equipment_info, list):
    #             equipment_list = equipment_info
    #         else:
    #             equipment_list = []
    #
    #         for equipment in equipment_list:
    #             records = equipment.get('data', [])
    #             for record in records:
    #                 # Scrub jig_num key
    #                 record.pop('jig_num', None)
    #
    #                 try:
    #                     # Direct database save loop
    #                     request.env['cell.clamp.baking.log'].sudo().create(record)
    #                     total_created += 1
    #                 except Exception as creation_error:
    #                     _logger.warning(f"Failed to create log entry row: {str(creation_error)}")
    #
    #         print(f"✅ Success! Data isolated and scrubbed. Total records added: {total_created}")
    #         return request.make_response(
    #             json.dumps({'status': 'success', 'created': total_created}),
    #             headers=[('Content-Type', 'application/json')]
    #         )
    #     else:
    #         print("❌ Processing aborted: Parsed data object mapping was empty.")
    #         return request.make_response(
    #             json.dumps({'status': 'error', 'message': 'No structured object context body found'}),
    #             headers=[('Content-Type', 'application/json')]
    #         )


class DegasMachineAPI(http.Controller):

    @http.route('/update_degas_machine', type='json', auth='public', methods=['POST'], csrf=False)
    def update_degas_machine(self, **kwargs):
        print("\n======================= DegasMachineAPI Called =======================")
        data = json.loads(request.httprequest.data)
        if data:
            records = data.get('data', [])
            for rec in records:
                request.env['degas.machine.log'].sudo().create(rec)
            print("All degas records created.")
        else:
            print("No data found in request.")


class AssemblyMachineAPI(http.Controller):

    @http.route('/update_assembly_machine', type='json', auth='public', methods=['POST'], csrf=False)
    def update_assembly_machine(self, **kwargs):
        print("\n======================= AssemblyMachineAPI Called =======================")
        data = json.loads(request.httprequest.data)
        if data:
            records = data.get('data', [])
            for rec in records:
                request.env['assembly.machine.log'].sudo().create(rec)
            print("All assembly records created.")
        else:
            print("No data found in request.")



class OCVMachineAPI(http.Controller):

    @http.route('/update_ocv_machine', type='json', auth='public', methods=['POST'], csrf=False)
    def update_ocv_machine(self, **kwargs):
        print("\n======================= OCVMachineAPI Called =======================")
        data = json.loads(request.httprequest.data)
        if data:
            records = data.get('data', [])
            for rec in records:
                request.env['ocv.machine.log'].sudo().create(rec)
            print("All OCV records created.")
        else:
            print("No data found in request.")


class SlittingMachineAPI(http.Controller):

    @http.route('/update_slitting_machine', type='json', auth='public', methods=['POST'], csrf=False)
    def update_slitting_machine(self, **kwargs):
        print("\n======================= SlittingMachineAPI Called =======================")
        raw_data = request.httprequest.data
        print("Raw JSON Received:", raw_data)
        data = json.loads(raw_data)
        if data:
            records = data.get('data', [])
            for rec in records:
                print("Creating Record:", rec)
                request.env['slitting.machine.log'].sudo().create(rec)
            print("All slitting records created.")
        else:
            print("No data found in request.")


class DryingOvenAPI(http.Controller):

    @http.route('/update_drying_oven', type='json', auth='public', methods=['POST'], csrf=False)
    def update_drying_oven(self, **kwargs):
        print("\n======================= DryingOvenAPI Called =======================")
        raw_data = request.httprequest.data
        print("Raw JSON Received:", raw_data)
        data = json.loads(raw_data)
        if data:
            records = data.get('data', [])
            for rec in records:
                print("Creating Record:", rec)
                request.env['drying.oven.log'].sudo().create(rec)
            print("All drying oven records created.")
        else:
            print("No data found in request.")


class WindingMachineAPI(http.Controller):

    @http.route('/update_winding_machine', type='json', auth='public', methods=['POST'], csrf=False)
    def update_winding_machine(self, **kwargs):
        print("\n======================= WindingMachineAPI Called =======================")
        raw_data = request.httprequest.data
        print("Raw JSON Received:", raw_data)
        data = json.loads(raw_data)
        if data:
            records = data.get('data', [])
            for rec in records:
                print("Creating Record:", rec)
                request.env['winding.machine.log'].sudo().create(rec)
            print("All winding machine records created.")
        else:
            print("No data found in request.")


class OCVMESLogAPI(http.Controller):

    @http.route('/update_ocv_mes', type='json', auth='public', methods=['POST'], csrf=False)
    def update_ocv_mes(self, **kwargs):
        print("\n======================= OCVMESLogAPI Called =======================")
        raw_data = request.httprequest.data
        print("Raw JSON Received:", raw_data)
        data = json.loads(raw_data)
        if data:
            records = data if isinstance(data, list) else data.get('data', [])
            for rec in records:
                # Flatten TestData array (ItemCode/Value pairs) into top-level fields
                test_data_map = {
                    item['ItemCode'].upper(): item['Value']
                    for item in rec.get('TestData', [])
                    if 'ItemCode' in item and 'Value' in item
                }
                flat_rec = {
                    'machine_id'    : rec.get('MachineId', ''),
                    'group_code'    : rec.get('GroupCode', ''),
                    'test_result'   : rec.get('TestResult', ''),
                    'timestamp'     : rec.get('TimeStamp', ''),
                    'product_sn'    : rec.get('ProductSn', ''),
                    'operator_id'   : rec.get('OperatorId', ''),
                    'sn_type'       : rec.get('SnType', ''),
                    'ng_code'       : rec.get('NgCode', ''),
                    'pallet'        : test_data_map.get('PALLET', ''),
                    'card'          : test_data_map.get('CARD', ''),
                    'voltage'       : test_data_map.get('VOLTAGE', ''),
                    'actual_voltage': test_data_map.get('ACTUALVOLTAGE', ''),
                    'resistance'    : test_data_map.get('RESISTANCE', ''),
                    'k_value'       : test_data_map.get('K_VALUE', ''),
                    'temperature'   : test_data_map.get('TEMPERATURE', ''),
                    'end_date_time' : test_data_map.get('END_DATE_TIME', ''),
                    'test_date'     : test_data_map.get('TEST_DATE', ''),
                }
                print("Creating OCV MES Record:", flat_rec)
                request.env['ocv.mes.log'].sudo().create(flat_rec)
            print(f"All OCV MES records created. Total: {len(records)}")
        else:
            print("No data found in request.")
