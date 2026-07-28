from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

# File types that are allowed for upload
ALLOWED_EXTENSIONS = ('.pdf', '.doc', '.docx', '.odt', '.rtf', '.txt')


class UserManual(models.Model):
    _name = 'user.manual'
    _description = 'User Manual'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Module Name', required=True, tracking=True)
    description = fields.Text(string='Description')

    manual_file = fields.Binary(
        string='Manual File',
        required=True,
        attachment=True,
        help="Upload a PDF or document file only.",
    )
    manual_filename = fields.Char(string='File Name')

    is_pdf = fields.Boolean(
        string='Is PDF',
        compute='_compute_is_pdf',
        help="Technical field used to decide whether an inline preview "
             "can be shown.",
    )

    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('submitted', 'Submitted'),
        ],
        string='Status',
        default='draft',
        required=True,
        tracking=True,
    )

    active = fields.Boolean(default=True)

    # ------------------------------------------------------------------
    # Compute
    # ------------------------------------------------------------------
    @api.depends('manual_filename')
    def _compute_is_pdf(self):
        for rec in self:
            fname = (rec.manual_filename or '').lower()
            rec.is_pdf = fname.endswith('.pdf')

    # ------------------------------------------------------------------
    # Constraints
    # ------------------------------------------------------------------
    @api.constrains('manual_file', 'manual_filename')
    def _check_file_extension(self):
        for rec in self:
            if rec.manual_file and rec.manual_filename:
                if not rec.manual_filename.lower().endswith(ALLOWED_EXTENSIONS):
                    raise ValidationError(_(
                        "Invalid file type: %(file)s\n\n"
                        "Only PDF and document files are allowed (%(allowed)s)."
                    ) % {
                        'file': rec.manual_filename,
                        'allowed': ', '.join(ALLOWED_EXTENSIONS),
                    })

    # ------------------------------------------------------------------
    # Actions (buttons)
    # ------------------------------------------------------------------
    def action_submit(self):
        """Move the record to the 'Submitted' state. Admin only (view-level)."""
        for rec in self:
            rec.state = 'submitted'

    def action_reset_to_draft(self):
        """Move the record back to 'Draft'. Admin only (view-level)."""
        for rec in self:
            rec.state = 'draft'

    def action_view_fullscreen(self):
        """Open the uploaded document full screen in a new browser tab."""
        self.ensure_one()
        if not self.manual_file:
            raise UserError(_("Please upload a document first."))
        filename = self.manual_filename or (self.name or 'document')
        url = '/web/content/user.manual/%s/manual_file/%s?download=false' % (
            self.id, filename,
        )
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new',
        }
