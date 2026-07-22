from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
import xlrd
import base64


class UpdateBoxesWizard(models.TransientModel):
    _name = "update.boxes.wizard"

    upload_file = fields.Binary(string="Upload file", tracking=True)
    file_name = fields.Char('File Name', tracking=True)
    stock_picking_id = fields.Many2one('stock.picking', string='Stock Picking')

    def action_update_boxes_delivery(self):
        if not self.upload_file:
            raise ValidationError(_('The uploaded file is empty. Please upload a valid file.'))

        try:
            file_data = base64.b64decode(self.upload_file)
            wb = load_workbook(filename=io.BytesIO(file_data))
        except Exception:
            raise ValidationError(_('Upload a valid .xlsx file.'))

        sheet = wb.active
        move_lines = self.stock_picking_id.move_line_ids.sorted('id')

        rows = list(sheet.iter_rows(min_row=2, values_only=True))
        if len(rows) > len(move_lines):
            raise ValidationError(_('More rows in Excel than move lines.'))

        move_lines.write({'boxes': False})

        for idx, row in enumerate(rows):
            lot_serial = str(row[0]).strip() if row[0] else ''  # column A: Lot/Serial Number
            raw_box_value = row[2] if len(row) > 2 else None  # column C: Done? adjust index to your real "Boxes" column
            boxes_value = str(raw_box_value).strip() if raw_box_value else ''

            move_line = move_lines[idx]
            move_line.boxes = boxes_value

            # if you actually need to match/update lot on the move line:
            # matching_lot = self.env['stock.lot'].search([('name', '=', lot_serial), ...], limit=1)
            # if matching_lot:
            #     move_line.lot_id = matching_lot.id

            print(f"[DEBUG] Row {idx + 2} → Lot: {lot_serial}, Box: {boxes_value}, Move Line ID: {move_line.id}")

        return {'type': 'ir.actions.client', 'tag': 'reload'}
