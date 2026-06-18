# -*- coding: utf-8 -*-

from odoo import models, fields, api


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def _get_journal(self):
        ttype = self._context.get('journal_type')
        if ttype:
            journal = self.env['account.journal'].search(
                [('name', '=', ttype)], limit=1
            )
            if journal:
                return journal

        # Odoo 19 safe fallback
        return self.env['account.journal'].search([
            ('type', '=', 'general'),
            ('company_id', '=', self.env.company.id)
        ], limit=1)

    journal_id = fields.Many2one(
        'account.journal',
        string='Journal',
        required=True,
        readonly=True,
        states={'draft': [('readonly', False)]},
        domain="[('company_id', '=', company_id)]",
        default=_get_journal,
    )


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def _select_action_to_open(self):
        res = super(AccountJournal, self)._select_action_to_open()
        if self.type == 'cash':
            return 'action_move_journal_line'
        elif self.type == 'bank':
            return 'action_move_journal_line'
        return res