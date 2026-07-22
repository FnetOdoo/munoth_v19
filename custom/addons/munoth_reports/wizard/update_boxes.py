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
        rows_data = []

        try:
            wb = load_workbook(filename=io.BytesIO(file_data))
            sheet = wb.active
            rows_data = [
                row for row in sheet.iter_rows(min_row=2, values_only=True)
                if any(cell is not None and str(cell).strip() != '' for cell in row)
            ]
        except Exception:
            try:
                wb = xlrd.open_workbook(file_contents=file_data)
                sheet = wb.sheet_by_index(0)
                rows_data = [
                    sheet.row_values(r) for r in range(1, sheet.nrows)
                    if any(str(v).strip() != '' for v in sheet.row_values(r))
                ]
            except Exception:
                raise ValidationError(_('Upload a valid .xls or .xlsx file.'))

        move_lines = self.stock_picking_id.move_line_ids.sorted('id')

        if len(rows_data) > len(move_lines):
            raise ValidationError(_(
                'More rows in Excel (%s) than move lines (%s).'
            ) % (len(rows_data), len(move_lines)))

        move_lines.write({'boxes': False})

        missing_serials = []
        used_move_line_ids = set()

        for row in rows_data:
            # Column A = S.No (ignored), Column B = Lot/Serial Number, Column C = Boxes
            lot_serial = str(row[1]).strip() if len(row) > 1 and row[1] else ''
            raw_box_value = row[2] if len(row) > 2 else None
            boxes_value = str(raw_box_value).strip() if raw_box_value else ''

            if not lot_serial:
                continue

            lot = self.env['stock.lot'].search([
                ('name', '=', lot_serial),
                ('product_id', '=', self.stock_picking_id.move_lines[:1].product_id.id),
            ], limit=1)

            if not lot:
                missing_serials.append(lot_serial)
                continue

            move_line = move_lines.filtered(
                lambda ml: not ml.lot_id and ml.id not in used_move_line_ids
            )[:1]

            if not move_line:
                missing_serials.append(lot_serial)
                continue

            move_line.lot_id = lot.id
            move_line.boxes = boxes_value
            used_move_line_ids.add(move_line.id)

            print(f"[DEBUG] Lot: {lot_serial} → Box: {boxes_value}, Move Line ID: {move_line.id}")

        if missing_serials:
            raise ValidationError(
                _('The following serials could not be assigned (lot not found or no line available): %s')
                % ', '.join(missing_serials)
            )

        return {'type': 'ir.actions.client', 'tag': 'reload'}