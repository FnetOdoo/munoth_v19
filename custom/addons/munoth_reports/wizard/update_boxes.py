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

        # Decode uploaded file
        try:
            upload_file = base64.b64decode(self.upload_file)
            wb = xlrd.open_workbook(file_contents=upload_file)
        except (xlrd.biffh.XLRDError, base64.binascii.Error):
            raise ValidationError(_('Upload a valid .xls file.'))

        sheet = wb.sheet_by_index(0)

        # Get move lines sorted by ID
        move_lines = self.stock_picking_id.move_line_ids.sorted('id')

        # Check for row mismatch
        if sheet.nrows - 1 > len(move_lines):
            raise ValidationError(_('More rows in Excel than move lines.'))

        # Clear old box values in one go (only if same value needed)
        move_lines.write({'boxes': False})

        # Step: Loop and assign values
        for idx in range(1, sheet.nrows):
            raw_box_value = sheet.cell_value(idx, 1)
            try:
                boxes_value = str(raw_box_value).strip() if raw_box_value else ''
            except ValueError:
                raise ValidationError(_('Invalid number format in Excel at row %s') % (idx + 1))

            move_line = move_lines[idx - 1]
            move_line.boxes = boxes_value  # ✅ Best way to update One2many field value

            # 👇 Debug print
            print(f"[DEBUG] Row {idx + 1} → Raw: {raw_box_value}, Cleaned: {boxes_value}, Move Line ID: {move_line.id}")

        return {'type': 'ir.actions.client', 'tag': 'reload'}
