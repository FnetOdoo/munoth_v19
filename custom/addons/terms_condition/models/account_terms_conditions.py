# -*- coding: utf-8 -*-
"""
Migration Notes — account_terms_conditions.py (v13/v15 → v19)
===============================================================

1.  @api.onchange that creates records (anti-pattern fixed)
    ────────────────────────────────────────────────────────
    In v15 the onchange directly called self.env[...].create() on a related
    model. In v19 this causes issues because onchange runs in a pseudo-
    transaction and self.id may be a NewId (not yet committed).

    Fix: build the One2many commands list and assign to the field instead
    of calling .create() directly. Odoo will write them on save.

2.  No other model-level changes required — all models are custom (_name)
    or inherit account.move which still exists in v19.
"""

from odoo import api, fields, models


class TermsConditions(models.Model):
    _name = 'account.terms'
    _description = 'Account Terms'

    name = fields.Char()
    company_id = fields.Many2one(
        'res.company',
        required=True,
        default=lambda self: self.env.company,
    )
    terms_conditions_ids = fields.One2many(
        'account.terms.conditions',
        'terms_conditions_id',
        string='Terms & Conditions',
    )


class SaleTermsConditions(models.Model):
    _name = 'account.terms.conditions'
    _description = 'Account Terms and Condition'
    _rec_name = 'value'

    value = fields.Char()
    terms_conditions_id = fields.Many2one('account.terms')


class AccountMoveTermsConditions(models.Model):
    _name = 'account.move.terms.conditions'
    _description = 'Account Move Terms and Conditions'

    name = fields.Char()
    value = fields.Char()
    invoice_id = fields.Many2one('account.move')
    terms_conditions_id = fields.Many2one('account.terms')
    terms_conditions_value_ids = fields.Many2one(
        'account.terms.conditions',
        string='Terms & Conditions',
    )


class AccountTermsConditionsTemplate(models.Model):
    _name = 'account.terms.template'
    _description = 'Account Terms Template'

    name = fields.Char()
    terms_conditions_ids = fields.Many2many(
        'account.terms',
        copy=False,
        string='Template',
    )


class AccountMoveDescriptionDetails(models.Model):
    _name = 'account.move.description.details'
    _description = 'Account Move Description Details'

    name = fields.Char()
    value = fields.Char()
    invoice_id = fields.Many2one('account.move')


class AccountMove(models.Model):
    _inherit = 'account.move'

    terms_conditions_template_id = fields.Many2one(
        'account.terms.template',
        copy=False,
    )
    terms_conditions_ids = fields.One2many(
        'account.move.terms.conditions',
        'invoice_id',
    )
    description_detail_ids = fields.One2many(
        'account.move.description.details',
        'invoice_id',
    )
    note_inside_description = fields.Html(string='Note Inside Description')
    project_description = fields.Text(string='Description')

    @api.onchange('terms_conditions_template_id')
    def terms_conditions_onchange(self):
        """
        Populate terms_conditions_ids from the selected template.

        v15 issue: called self.env['account.move.terms.conditions'].create()
        directly inside onchange — unsafe when self.id is a NewId.

        v19 fix: build (0, 0, vals) command list and assign to the One2many
        field. Odoo writes the lines on record save, not during onchange.
        """
        # Clear existing lines
        self.terms_conditions_ids = [(5, 0, 0)]

        if self.terms_conditions_template_id:
            lines = []
            for terms in self.terms_conditions_template_id.terms_conditions_ids:
                lines.append((0, 0, {
                    'terms_conditions_id': terms.id,
                }))
            self.terms_conditions_ids = lines
