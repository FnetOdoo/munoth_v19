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

        file_data = base64.b64decode(self.upload_file)

        rows_data = []  # list of row-value-tuples, 0-indexed, header excluded

        # Try xlsx (openpyxl) first
        try:
            wb = load_workbook(filename=io.BytesIO(file_data))
            sheet = wb.active
            rows_data = list(sheet.iter_rows(min_row=2, values_only=True))
        except Exception:
            # Fall back to legacy .xls (xlrd)
            try:
                wb = xlrd.open_workbook(file_contents=file_data)
                sheet = wb.sheet_by_index(0)
                rows_data = [sheet.row_values(r) for r in range(1, sheet.nrows)]
            except Exception:
                raise ValidationError(_('Upload a valid .xls or .xlsx file.'))

        move_lines = self.stock_picking_id.move_line_ids.sorted('id')

        if len(rows_data) > len(move_lines):
            raise ValidationError(_('More rows in Excel than move lines.'))

        move_lines.write({'boxes': False})

        for idx, row in enumerate(rows_data):
            lot_serial = str(row[0]).strip() if row[0] else ''
            raw_box_value = row[1] if len(row) > 1 else None
            boxes_value = str(raw_box_value).strip() if raw_box_value else ''

            move_line = move_lines[idx]
            move_line.boxes = boxes_value

            print(f"[DEBUG] Row {idx + 2} → Lot: {lot_serial}, Box: {boxes_value}, Move Line ID: {move_line.id}")

        return {'type': 'ir.actions.client', 'tag': 'reload'}
