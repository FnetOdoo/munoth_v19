from odoo import models, fields, api, _
from odoo.exceptions import UserError
from dateutil import relativedelta
from odoo.exceptions import ValidationError


class FirstArticleInspection(models.Model):
    _name = 'first.article.inspection'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'sequence.mixin']
    _order = 'date desc, name desc, id desc'
    _description = "First Artical"

    name = fields.Char(copy=False, readonly=True, default=lambda x: _('New'), tracking=True)
    state = fields.Selection([('draft', 'Draft'), ('request', 'Requested'), ('done', 'Done'), ('reject', 'Rejected'), ('cancel', 'Cancel')], string='Status', required=True, readonly=True,
                             copy=False, tracking=True, default='draft')
    company_id = fields.Many2one('res.company', 'Company', index=True, default=lambda self: self.env.company)
    date = fields.Date('Date', states={'done': [('readonly', True)], 'request': [('readonly', True)]}, default=fields.Date.today(), required=1)
    model_id = fields.Many2one('product.model', 'Model')
    part_number = fields.Char("Part Name")
    rev_doc_number = fields.Char("Revision Doc Number")
    rev_number = fields.Char("Revision Number")
    rev_date = fields.Date("Rev Date")
    template_id = fields.Many2one('fai.template', string="Template",states={'done': [('readonly', True)]})
    line_ids = fields.One2many('fai.line', 'inspection_id', string="Inspection")
    operation_id = fields.Many2one('manufacturing.operation', string="Operation", states={'request': [('readonly', True)], 'done': [('readonly', True)]})
    origin = fields.Char("Source Document",readonly=True)
    inspection_type = fields.Selection(
        [('process', 'Process Approval'), ('fai', 'First Article Inspection'), ('fpa', 'First Part Approval')], string="Inspection Type", required=True, states={'request': [('readonly', True)], 'done': [('readonly', True)]})
    lot_id = fields.Many2one('stock.lot', string="Serial Number")
    user_id = fields.Many2one('res.users', 'Requested By',readonly=True, default=lambda self: self.env.user)
    inspect_state = fields.Boolean(store=True)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'first.article'
                ) or _('New')
        return super().create(vals_list)

    @api.onchange('type')
    def onchange_type(self):
        company_id = self.env.user.company_id or self.env['res.company'].search([])[0]
        self.rev_doc_number = company_id.in_ins_doc_no
        self.rev_number = company_id.in_ins_rev_no
        self.rev_date = company_id.in_ins_rev_date

    @api.onchange('template_id')
    def onchange_template_id(self):
        self.line_ids = False
        lines = []
        for item in self.template_id.item_ids:
            lines.append(
                (0, 0, {
                    'name': item.name,
                    'parameter': item.parameter,
                }))
        self.line_ids = lines

    def action_request(self):
        for rec in self:
            user_ids = self.env.ref('fnet_mrp.group_mrp_quality_user').sudo().users
            process_name = 'Process Approval'
            if rec.inspection_type == 'fai':
                process_name = 'First Article Inspection'
            elif rec.inspection_type == 'fpa':
                process_name = 'First Part Approval'
            for user in user_ids:
                mail_values = {
                    'auto_delete': False,
                    'author_id': self.env.user.partner_id.id,
                    'email_from': (self.env.user.email_formatted or self.env.ref('base.user_root').email_formatted),
                    'email_to': user.login,
                    'body_html': """Dear Sir/Madam,<br/> 
                                    You have been requested to verify the %s: %s.<br/>
                                    Thanks & Regards.""" % (process_name, rec.name),
                    'subject': 'Approval request for %s: %s' % (process_name, self.name),
                }
                self.env['mail.mail'].sudo().create(mail_values).send()
            rec.write({
                'state': 'request',
            })

    def action_validate(self):
        for rec in self:
            if not self.line_ids:
                raise UserError('Kindly add Inspection Lines')
            for record in rec.line_ids:
                if not record.actual or not record.state:
                    raise ValidationError(_("Please fill all the status, Record and Remark."))
            if any(line.state == 'fail' for line in self.line_ids):
                deviation_note = self.env['deviation.note'].search([('operation_id', '=', self.operation_id.id), ('state', '=', 'done')])
                if  not deviation_note:
                    raise UserError('Inspection contains parameters that are failed. Create a deviation note to approve this quality check')
            # user_ids = self.env.ref('fnet_mrp.group_mrp_quality_user').sudo().users
            process_name = 'Process Approval'
            if rec.inspection_type == 'fai':
                process_name = 'First Article Inspection'
            elif rec.inspection_type == 'fpa':
                process_name = 'First Part Approval'
            # for user in user_ids:
            mail_values = {
                'auto_delete': False,
                'author_id': self.env.user.partner_id.id,
                'email_from': (self.env.user.email_formatted or self.env.ref('base.user_root').email_formatted),
                'email_to': rec.user_id.login,
                'body_html': """Dear Sir/Madam,<br/> 
                                Your %s request has been approved for %s.<br/>
                                Thanks & Regards.""" % (process_name, rec.name),
                'subject': 'Request approved for %s: %s' % (process_name, self.name),
            }
            self.env['mail.mail'].sudo().create(mail_values).send()
            rec.write({
                'inspect_state':True,
                'state': 'done',
            })

    def action_reject(self):
        for rec in self:
            process_name = 'Process Approval'
            if rec.inspection_type == 'fai':
                process_name = 'First Article Inspection'
            elif rec.inspection_type == 'fpa':
                process_name = 'First Part Approval'
            mail_values = {
                'auto_delete': False,
                'author_id': self.env.user.partner_id.id,
                'email_from': (self.env.user.email_formatted or self.env.ref('base.user_root').email_formatted),
                'email_to': rec.user_id.login,
                'body_html': """Dear Sir/Madam,<br/> 
                                Unfortunately your request for %s: %s have been rejected.<br/>
                                Thanks & Regards.""" % (process_name, rec.name),
                'subject': 'Approval rejected for %s: %s' % (process_name, self.name),
            }
            self.env['mail.mail'].sudo().create(mail_values).send()
            rec.write({
                'state': 'reject',
            })

    def action_cancel(self):
        for rec in self:
            rec.write({
                'state': 'cancel',
            })

    def action_reset(self):
        for rec in self:
            rec.write({
                'state': 'draft'
            })

    def action_open_deviation_note(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Create Deviation Note',
            'view_mode': 'form',
            'res_model': 'deviation.note',
            'target': 'new',
            'context': {
                'default_operation_id': self.operation_id.id,
                'default_requested_id': self.env.user.id,
                'default_origin': self.origin,
            },
        }


class FaiLine(models.Model):
    _name = 'fai.line'

    inspection_id = fields.Many2one('first.article.inspection', string="Inspection")
    name = fields.Char('Parameter', required=True)
    parameter = fields.Char("Specification")
    actual = fields.Char("Actual")
    state = fields.Selection([('pass', 'Pass'), ('fail', 'Fail')], string="Status")
    remark = fields.Char('Remarks')


class FaiTemplate(models.Model):
    _name = 'fai.template'
    _description = 'Inspection Template'

    name = fields.Char("Name", required=True)
    item_ids = fields.One2many('fai.template.item', 'template_id', string="Inspection Items")


class FaiTemplateItem(models.Model):
    _name = 'fai.template.item'
    _description = 'Inspection Items'

    template_id = fields.Many2one('fai.template', string="Template")
    name = fields.Char('Parameter', required=True)
    parameter = fields.Char("Specification", required=True)


# class CellDrying(models.Model):
#     _inherit = 'cell.drying'
#
#     def _get_pa_count(self):
#         for rec in self:
#             rec.pa_count = self.env['first.article.inspection'].search_count(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'process')])
#
#     pa_count = fields.Integer('Inspection Count', compute='_get_pa_count')
#
#     def action_open_process_approval(self):
#         pa_ids = self.env['first.article.inspection'].search([('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'process')])
#         return {
#             'res_model': 'first.article.inspection',
#             'type': 'ir.actions.act_window',
#             'name': _("Process Approval"),
#             'domain': [('id', 'in', pa_ids.ids)],
#             'view_mode': 'list,form',
#             'context': {'default_inspection_type': 'process',
#                         'default_operation_id': self.operation_id.id,
#                         'default_origin': self.name,
#                         'default_model_id': self.product_model_id.id
#                         }
#         }
#
#     def action_request_process_approval(self):
#         pa_id_requested = self.env['first.article.inspection'].search([('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'process'),('state', 'in', ['draft', 'request'])])
#         if pa_id_requested:
#             raise UserError(_("First article inspection is already requested."))
#         pa_id = self.env['first.article.inspection'].search([('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('state', '=', 'done'), ('inspection_type', '=', 'process')])
#         if pa_id:
#             raise UserError(_("First article inspection already done."))
#         inspection_id = self.env['first.article.inspection'].create({
#             'inspection_type': 'process',
#             'date': fields.Date.today(),
#             'operation_id': self.operation_id.id,
#             'origin': self.name,
#             'user_id': self.env.user.id,
#             'model_id': self.product_model_id.id,
#         })
#         inspection_id.action_request()
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'message': _("Process has been created."),
#                 'type': 'success',
#                 'sticky': False,
#                 'next': {
#                     'type': 'ir.actions.act_window_close'
#                 },
#             }
#         }
#
#     def action_start(self):
#         for rec in self:
#             pa_id = self.env['first.article.inspection'].search([('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('inspection_type', '=', 'process'), ('state', '=', 'done')])
#             if not pa_id:
#                 pass
#                 # raise UserError("Kindly do process Approval before starting production")
#         return super(CellDrying, self).action_start()



# class CellInjection(models.Model):
#     _inherit = 'cell.injection'
#
#
#
#     def _get_pa_count(self):
#         for rec in self:
#             rec.pa_count = self.env['first.article.inspection'].search_count(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'process')])
#
#     def _get_fai_count(self):
#         for rec in self:
#             rec.fai_count = self.env['first.article.inspection'].search_count(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'fai')])
#
#     pa_count = fields.Integer('Inspection Count', compute='_get_pa_count')
#     fai_count = fields.Integer('Inspection Count', compute='_get_fai_count')
#
#     def action_open_process_approval(self):
#         pa_ids = self.env['first.article.inspection'].search([('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'process')])
#         return {
#             'res_model': 'first.article.inspection',
#             'type': 'ir.actions.act_window',
#             'name': _("Process Approval"),
#             'domain': [('id', 'in', pa_ids.ids)],
#             'view_mode': 'list,form',
#             'context': {'default_inspection_type': 'process',
#                         'default_operation_id': self.operation_id.id,
#                         'default_origin': self.name,
#                         'default_model_id': self.product_model_id.id
#                         }
#         }
#
#     def action_request_process_approval(self):
#         pa_id_requested = self.env['first.article.inspection'].search([('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'process'),('state', 'in', ['draft', 'request'])])
#         if pa_id_requested:
#             raise UserError(_("Process Approval is already requested."))
#         pa_id = self.env['first.article.inspection'].search([('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('state', '=', 'done'), ('inspection_type', '=', 'process')])
#         if pa_id:
#             raise UserError(_("Process Approval already done."))
#         inspection_id = self.env['first.article.inspection'].create({
#             'inspection_type': 'process',
#             'date': fields.Date.today(),
#             'operation_id': self.operation_id.id,
#             'origin': self.name,
#             'user_id': self.env.user.id,
#             'model_id': self.product_model_id.id,
#         })
#         inspection_id.action_request()
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'message': _("Process has been created."),
#                 'type': 'success',
#                 'sticky': False,
#                 'next': {
#                     'type': 'ir.actions.act_window_close'
#                 },
#             }
#         }
#
#     def action_open_inspection(self):
#         fai_ids = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id),('inspection_type', '=', 'fai')])
#         return {
#             'res_model': 'first.article.inspection',
#             'type': 'ir.actions.act_window',
#             'name': _("First Article Inspection"),
#             'domain': [('id', 'in', fai_ids.ids)],
#             'view_mode': 'list,form',
#             'context': {'default_inspection_type': 'fai',
#                         'default_operation_id': self.operation_id.id,
#                         'default_origin': self.name,
#                         'default_model_id': self.product_model_id.id
#                         }
#         }
#
#     def action_request_inspection(self):
#         ins_id_requested = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'fai'),
#              ('state', 'in', ['draft', 'request'])])
#         if ins_id_requested:
#             raise UserError(_("First article inspection is already requested."))
#         ins_id = self.env['first.article.inspection'].search([('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('state', '=', 'done'), ('inspection_type', '=', 'fai')])
#         if ins_id:
#             raise UserError(_("First article inspection already done."))
#         inspection_id = self.env['first.article.inspection'].create({
#             'inspection_type': 'fai',
#             'date': fields.Date.today(),
#             'operation_id': self.operation_id.id,
#             'origin': self.name,
#             'user_id': self.env.user.id,
#             'model_id': self.product_model_id.id,
#         })
#         inspection_id.action_request()
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'message': _("First article inspection has been created."),
#                 'type': 'success',
#                 'sticky': False,
#                 'next': {
#                     'type': 'ir.actions.act_window_close'
#                 },
#             }
#         }
#
#     def action_start(self):
#         for rec in self:
#             pa_id = self.env['first.article.inspection'].search([('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('inspection_type', '=', 'process'), ('state', '=', 'done')])
#             if not pa_id:
#                 pass
#                 # raise UserError("Kindly do process Approval before starting production")
#             fai_id = self.env['first.article.inspection'].search([('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('inspection_type', '=', 'fai'), ('state', '=', 'done')])
#             if not fai_id:
#                 pass
#                 # raise UserError("Kindly do First Article Inspection before starting production")
#         return super(CellInjection, self).action_start()

    # def action_done_production(self):
    #     for rec in self:
    #         fai_id = self.env['first.article.inspection'].search(
    #             [('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('state', '=', 'done')])
    #         dn_id = self.env['deviation.note'].search(
    #             [('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('state', '=', 'done')])
    #         if not fai_id and not dn_id:
    #             raise UserError(
    #                 _("First article inspection or Deviation Note is not yet finished. Please contact the inspection personnel to complete it."))
    #     return super(CellInjection, self).action_done_production()


# class CellClampBaking(models.Model):
#     _inherit = 'cell.clamp.baking'
#
#     def _get_pa_count(self):
#         for rec in self:
#             rec.pa_count = self.env['first.article.inspection'].search_count(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'process')])
#
#     def _get_fai_count(self):
#         for rec in self:
#             rec.fai_count = self.env['first.article.inspection'].search_count(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'fai')])
#
#     pa_count = fields.Integer('Inspection Count', compute='_get_pa_count')
#     fai_count = fields.Integer('Inspection Count', compute='_get_fai_count')
#
#     def action_open_process_approval(self):
#         pa_ids = self.env['first.article.inspection'].search([('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'process')])
#         return {
#             'res_model': 'first.article.inspection',
#             'type': 'ir.actions.act_window',
#             'name': _("Process Approval"),
#             'domain': [('id', 'in', pa_ids.ids)],
#             'view_mode': 'list,form',
#             'context': {'default_inspection_type': 'process',
#                         'default_operation_id': self.operation_id.id,
#                         'default_origin': self.name,
#                         'default_model_id': self.product_model_id.id
#                         }
#         }
#
#     def action_request_process_approval(self):
#         pa_id_requested = self.env['first.article.inspection'].search([('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'process'),('state', 'in', ['draft', 'request'])])
#         if pa_id_requested:
#             raise UserError(_("Process Approval is already requested."))
#         pa_id = self.env['first.article.inspection'].search([('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('state', '=', 'done'), ('inspection_type', '=', 'process')])
#         if pa_id:
#             raise UserError(_("Process Approval already done."))
#         inspection_id = self.env['first.article.inspection'].create({
#             'inspection_type': 'process',
#             'date': fields.Date.today(),
#             'operation_id': self.operation_id.id,
#             'origin': self.name,
#             'user_id': self.env.user.id,
#             'model_id': self.product_model_id.id,
#         })
#         inspection_id.action_request()
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'message': _("Process has been created."),
#                 'type': 'success',
#                 'sticky': False,
#                 'next': {
#                     'type': 'ir.actions.act_window_close'
#                 },
#             }
#         }
#
#     def action_open_inspection(self):
#         fai_ids = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id),('inspection_type', '=', 'fai')])
#         return {
#             'res_model': 'first.article.inspection',
#             'type': 'ir.actions.act_window',
#             'name': _("First Article Inspection"),
#             'domain': [('id', 'in', fai_ids.ids)],
#             'view_mode': 'list,form',
#             'context': {'default_inspection_type': 'fai',
#                         'default_operation_id': self.operation_id.id,
#                         'default_origin': self.name,
#                         'default_model_id': self.product_model_id.id
#                         }
#         }
#
#     def action_request_inspection(self):
#         ins_id_requested = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'fai'),
#              ('state', 'in', ['draft', 'request'])])
#         if ins_id_requested:
#             raise UserError(_("First article inspection is already requested."))
#         ins_id = self.env['first.article.inspection'].search([('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('state', '=', 'done'), ('inspection_type', '=', 'fai')])
#         if ins_id:
#             raise UserError(_("First article inspection already done."))
#         inspection_id = self.env['first.article.inspection'].create({
#             'inspection_type': 'fai',
#             'date': fields.Date.today(),
#             'operation_id': self.operation_id.id,
#             'origin': self.name,
#             'user_id': self.env.user.id,
#             'model_id': self.product_model_id.id,
#         })
#         inspection_id.action_request()
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'message': _("First article inspection has been created."),
#                 'type': 'success',
#                 'sticky': False,
#                 'next': {
#                     'type': 'ir.actions.act_window_close'
#                 },
#             }
#         }
#
#     def action_start(self):
#         for rec in self:
#             pa_id = self.env['first.article.inspection'].search([('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('inspection_type', '=', 'process'), ('state', '=', 'done')])
#             if not pa_id:
#                 pass
#                 # raise UserError("Kindly do process Approval before starting production")
#             fai_id = self.env['first.article.inspection'].search([('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('inspection_type', '=', 'fai'), ('state', '=', 'done')])
#             if not fai_id:
#                 pass
#                 # raise UserError("Kindly do First Article Inspection before starting production")
#         return super(CellClampBaking, self).action_start()


    # def action_done_production(self):
    #     for rec in self:
    #         fai_id = self.env['first.article.inspection'].search(
    #             [('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('state', '=', 'done')])
    #         dn_id = self.env['deviation.note'].search(
    #             [('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('state', '=', 'done')])
    #         if not fai_id and not dn_id:
    #             raise UserError(
    #                 _("First article inspection or Deviation Note is not yet finished. Please contact the inspection personnel to complete it."))
    #     return super(CellClampBaking, self).action_done_production()


# class DegasCell(models.Model):
#     _inherit = 'degas.cell'
#
#     def _get_pa_count(self):
#         for rec in self:
#             rec.pa_count = self.env['first.article.inspection'].search_count(
#                 [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id),
#                  ('inspection_type', '=', 'process')])
#
#     def _get_fai_count(self):
#         for rec in self:
#             rec.fai_count = self.env['first.article.inspection'].search_count(
#                 [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id),
#                  ('inspection_type', '=', 'fai')])
#
#     pa_count = fields.Integer('Inspection Count', compute='_get_pa_count')
#     fai_count = fields.Integer('Inspection Count', compute='_get_fai_count')
#
#     def action_open_process_approval(self):
#         pa_ids = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'process')])
#         return {
#             'res_model': 'first.article.inspection',
#             'type': 'ir.actions.act_window',
#             'name': _("Process Approval"),
#             'domain': [('id', 'in', pa_ids.ids)],
#             'view_mode': 'list,form',
#             'context': {'default_inspection_type': 'process',
#                         'default_operation_id': self.operation_id.id,
#                         'default_origin': self.name,
#                         'default_model_id': self.product_model_id.id
#                         }
#         }
#
#     def action_request_process_approval(self):
#         pa_id_requested = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'process'),
#              ('state', 'in', ['draft', 'request'])])
#         if pa_id_requested:
#             raise UserError(_("Process Approval is already requested."))
#         pa_id = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('state', '=', 'done'), ('inspection_type', '=', 'process')])
#         if pa_id:
#             raise UserError(_("Process Approval already done."))
#         inspection_id = self.env['first.article.inspection'].create({
#             'inspection_type': 'process',
#             'date': fields.Date.today(),
#             'operation_id': self.operation_id.id,
#             'origin': self.name,
#             'user_id': self.env.user.id,
#             'model_id': self.product_model_id.id,
#         })
#         inspection_id.action_request()
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'message': _("Process has been created."),
#                 'type': 'success',
#                 'sticky': False,
#                 'next': {
#                     'type': 'ir.actions.act_window_close'
#                 },
#             }
#         }
#
#     def action_open_inspection(self):
#         fai_ids = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id),('inspection_type', '=', 'fai')])
#         return {
#             'res_model': 'first.article.inspection',
#             'type': 'ir.actions.act_window',
#             'name': _("First Article Inspection"),
#             'domain': [('id', 'in', fai_ids.ids)],
#             'view_mode': 'list,form',
#             'context': {'default_inspection_type': 'fai',
#                         'default_operation_id': self.operation_id.id,
#                         'default_origin': self.name,
#                         'default_model_id': self.product_model_id.id
#                         }
#         }
#
#     def action_request_inspection(self):
#         ins_id_requested = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'fai'),
#              ('state', 'in', ['draft', 'request'])])
#         if ins_id_requested:
#             raise UserError(_("First article inspection is already requested."))
#         ins_id = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('state', '=', 'done'), ('inspection_type', '=', 'fai')])
#         if ins_id:
#             raise UserError(_("First article inspection already done."))
#         inspection_id = self.env['first.article.inspection'].create({
#             'inspection_type': 'fai',
#             'date': fields.Date.today(),
#             'operation_id': self.operation_id.id,
#             'origin': self.name,
#             'user_id': self.env.user.id,
#             'model_id': self.product_model_id.id,
#         })
#         inspection_id.action_request()
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'message': _("First article inspection has been created."),
#                 'type': 'success',
#                 'sticky': False,
#                 'next': {
#                     'type': 'ir.actions.act_window_close'
#                 },
#             }
#         }
#
#     def action_start(self):
#         for rec in self:
#             pa_id = self.env['first.article.inspection'].search(
#                 [('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id),
#                  ('inspection_type', '=', 'process'), ('state', '=', 'done')])
#             if not pa_id:
#                 pass
#                 # raise UserError("Kindly do process Approval before starting production")
#             fai_id = self.env['first.article.inspection'].search(
#                 [('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('inspection_type', '=', 'fai'),
#                  ('state', '=', 'done')])
#             if not fai_id:
#                 pass
# #                 raise UserError("Kindly do First Article Inspection before starting production")
#         return super(DegasCell, self).action_start()

    # def action_done_production(self):
    #     for rec in self:
    #         fai_id = self.env['first.article.inspection'].search(
    #             [('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('state', '=', 'done')])
    #         dn_id = self.env['deviation.note'].search(
    #             [('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('state', '=', 'done')])
    #         if not fai_id and not dn_id:
    #             raise UserError(
    #                 _("First article inspection or Deviation Note is not yet finished. Please contact the inspection personnel to complete it."))
    #     return super(DegasCell, self).action_done_production()


# class PadPrinting(models.Model):
#     _inherit = 'pad.printing'
#
#     def _get_pa_count(self):
#         for rec in self:
#             rec.pa_count = self.env['first.article.inspection'].search_count(
#                 [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id),
#                  ('inspection_type', '=', 'process')])
#
#     def _get_fai_count(self):
#         for rec in self:
#             rec.fai_count = self.env['first.article.inspection'].search_count(
#                 [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id),
#                  ('inspection_type', '=', 'fai')])
#
#     pa_count = fields.Integer('Inspection Count', compute='_get_pa_count')
#     fai_count = fields.Integer('Inspection Count', compute='_get_fai_count')
#
#     def action_open_process_approval(self):
#         pa_ids = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'process')])
#         return {
#             'res_model': 'first.article.inspection',
#             'type': 'ir.actions.act_window',
#             'name': _("Process Approval"),
#             'domain': [('id', 'in', pa_ids.ids)],
#             'view_mode': 'list,form',
#             'context': {'default_inspection_type': 'process',
#                         'default_operation_id': self.operation_id.id,
#                         'default_origin': self.name,
#                         'default_model_id': self.product_model_id.id
#                         }
#         }
#
#     def action_request_process_approval(self):
#         pa_id_requested = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'process'),
#              ('state', 'in', ['draft', 'request'])])
#         if pa_id_requested:
#             raise UserError(_("Process Approval is already requested."))
#         pa_id = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('state', '=', 'done'), ('inspection_type', '=', 'process')])
#         if pa_id:
#             raise UserError(_("Process Approval already done."))
#         inspection_id = self.env['first.article.inspection'].create({
#             'inspection_type': 'process',
#             'date': fields.Date.today(),
#             'operation_id': self.operation_id.id,
#             'origin': self.name,
#             'user_id': self.env.user.id,
#             'model_id': self.product_model_id.id,
#         })
#         inspection_id.action_request()
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'message': _("Process has been created."),
#                 'type': 'success',
#                 'sticky': False,
#                 'next': {
#                     'type': 'ir.actions.act_window_close'
#                 },
#             }
#         }
#
#     def action_open_inspection(self):
#         fai_ids = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id),('inspection_type', '=', 'fai')])
#         return {
#             'res_model': 'first.article.inspection',
#             'type': 'ir.actions.act_window',
#             'name': _("First Article Inspection"),
#             'domain': [('id', 'in', fai_ids.ids)],
#             'view_mode': 'list,form',
#             'context': {'default_inspection_type': 'fai',
#                         'default_operation_id': self.operation_id.id,
#                         'default_origin': self.name,
#                         'default_model_id': self.product_model_id.id
#                         }
#         }
#
#     def action_request_inspection(self):
#         ins_id_requested = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'fai'),
#              ('state', 'in', ['draft', 'request'])])
#         if ins_id_requested:
#             raise UserError(_("First article inspection is already requested."))
#         ins_id = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('state', '=', 'done'), ('inspection_type', '=', 'fai')])
#         if ins_id:
#             raise UserError(_("First article inspection already done."))
#         inspection_id = self.env['first.article.inspection'].create({
#             'inspection_type': 'fai',
#             'date': fields.Date.today(),
#             'operation_id': self.operation_id.id,
#             'origin': self.name,
#             'user_id': self.env.user.id,
#             'model_id': self.product_model_id.id,
#         })
#         inspection_id.action_request()
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'message': _("First article inspection has been created."),
#                 'type': 'success',
#                 'sticky': False,
#                 'next': {
#                     'type': 'ir.actions.act_window_close'
#                 },
#             }
#         }
#
#     def action_start(self):
#         for rec in self:
#             pa_id = self.env['first.article.inspection'].search(
#                 [('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id),
#                  ('inspection_type', '=', 'process'), ('state', '=', 'done')])
#             if not pa_id:
#                 pass
#                 # raise UserError("Kindly do process Approval before starting production")
#             fai_id = self.env['first.article.inspection'].search(
#                 [('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('inspection_type', '=', 'fai'),
#                  ('state', '=', 'done')])
#             if not fai_id:
#                 pass
# #                 raise UserError("Kindly do First Article Inspection before starting production")
#         return super(PadPrinting, self).action_start()


# class CapacityTest(models.Model):
#     _inherit = 'capacity.test'
#
#     def _get_pa_count(self):
#         for rec in self:
#             rec.pa_count = self.env['first.article.inspection'].search_count(
#                 [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id),
#                  ('inspection_type', '=', 'process')])
#
#     def _get_fai_count(self):
#         for rec in self:
#             rec.fai_count = self.env['first.article.inspection'].search_count(
#                 [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id),
#                  ('inspection_type', '=', 'fai')])
#
#     pa_count = fields.Integer('Inspection Count', compute='_get_pa_count')
#     fai_count = fields.Integer('Inspection Count', compute='_get_fai_count')
#
#     def action_open_process_approval(self):
#         pa_ids = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'process')])
#         return {
#             'res_model': 'first.article.inspection',
#             'type': 'ir.actions.act_window',
#             'name': _("Process Approval"),
#             'domain': [('id', 'in', pa_ids.ids)],
#             'view_mode': 'list,form',
#             'context': {'default_inspection_type': 'process',
#                         'default_operation_id': self.operation_id.id,
#                         'default_origin': self.name,
#                         'default_model_id': self.product_model_id.id
#                         }
#         }
#
#     def action_request_process_approval(self):
#         pa_id_requested = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'process'),
#              ('state', 'in', ['draft', 'request'])])
#         if pa_id_requested:
#             raise UserError(_("Process Approval is already requested."))
#         pa_id = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('state', '=', 'done'), ('inspection_type', '=', 'process')])
#         if pa_id:
#             raise UserError(_("Process Approval already done."))
#         inspection_id = self.env['first.article.inspection'].create({
#             'inspection_type': 'process',
#             'date': fields.Date.today(),
#             'operation_id': self.operation_id.id,
#             'origin': self.name,
#             'user_id': self.env.user.id,
#             'model_id': self.product_model_id.id,
#         })
#         inspection_id.action_request()
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'message': _("Process has been created."),
#                 'type': 'success',
#                 'sticky': False,
#                 'next': {
#                     'type': 'ir.actions.act_window_close'
#                 },
#             }
#         }
#
#     def action_open_inspection(self):
#         fai_ids = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id),('inspection_type', '=', 'fai')])
#         return {
#             'res_model': 'first.article.inspection',
#             'type': 'ir.actions.act_window',
#             'name': _("First Article Inspection"),
#             'domain': [('id', 'in', fai_ids.ids)],
#             'view_mode': 'list,form',
#             'context': {'default_inspection_type': 'fai',
#                         'default_operation_id': self.operation_id.id,
#                         'default_origin': self.name,
#                         'default_model_id': self.product_model_id.id
#                         }
#         }
#
#     def action_request_inspection(self):
#         ins_id_requested = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'fai'),
#              ('state', 'in', ['draft', 'request'])])
#         if ins_id_requested:
#             raise UserError(_("First article inspection is already requested."))
#         ins_id = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('state', '=', 'done'), ('inspection_type', '=', 'fai')])
#         if ins_id:
#             raise UserError(_("First article inspection already done."))
#         inspection_id = self.env['first.article.inspection'].create({
#             'inspection_type': 'fai',
#             'date': fields.Date.today(),
#             'operation_id': self.operation_id.id,
#             'origin': self.name,
#             'user_id': self.env.user.id,
#             'model_id': self.product_model_id.id,
#         })
#         inspection_id.action_request()
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'message': _("First article inspection has been created."),
#                 'type': 'success',
#                 'sticky': False,
#                 'next': {
#                     'type': 'ir.actions.act_window_close'
#                 },
#             }
#         }
#
#     def action_start(self):
#         for rec in self:
#             pa_id = self.env['first.article.inspection'].search(
#                 [('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id),
#                  ('inspection_type', '=', 'process'), ('state', '=', 'done')])
#             if not pa_id:
#                 pass
#                 # raise UserError("Kindly do process Approval before starting production")
#             fai_id = self.env['first.article.inspection'].search(
#                 [('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('inspection_type', '=', 'fai'),
#                  ('state', '=', 'done')])
#             if not fai_id:
#                 pass
# #                 raise UserError("Kindly do First Article Inspection before starting production")
#         return super(CapacityTest, self).action_start()


    # def action_done_production(self):
    #     for rec in self:
    #         fai_id = self.env['first.article.inspection'].search(
    #             [('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('state', '=', 'done')])
    #         print("\n---", rec.name, "--rec.name--\n")
    #         print("\n---", rec.operation_id.type, "--rec.operation_id.type--\n")
    #
    #         dn_id = self.env['deviation.note'].search(
    #             [('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('state', '=', 'done')])
    #         print("\n---", dn_id, "--dn_id--\n")
    #         if not fai_id and not dn_id:
    #             raise UserError(
    #                 _("First article inspection or Deviation Note is not yet finished. Please contact the inspection personnel to complete it."))
    #     return super(CapacityTest, self).action_done_production()


# class VoltageTest(models.Model):
#     _inherit = 'voltage.test'
#
#     def _get_pa_count(self):
#         for rec in self:
#             rec.pa_count = self.env['first.article.inspection'].search_count(
#                 [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id),
#                  ('inspection_type', '=', 'process')])
#
#     def _get_fai_count(self):
#         for rec in self:
#             rec.fai_count = self.env['first.article.inspection'].search_count(
#                 [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id),
#                  ('inspection_type', '=', 'fai')])
#
#     pa_count = fields.Integer('Inspection Count', compute='_get_pa_count')
#     fai_count = fields.Integer('Inspection Count', compute='_get_fai_count')
#
#     def action_open_process_approval(self):
#         pa_ids = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'process')])
#         return {
#             'res_model': 'first.article.inspection',
#             'type': 'ir.actions.act_window',
#             'name': _("Process Approval"),
#             'domain': [('id', 'in', pa_ids.ids)],
#             'view_mode': 'list,form',
#             'context': {'default_inspection_type': 'process',
#                         'default_operation_id': self.operation_id.id,
#                         'default_origin': self.name,
#                         'default_model_id': self.product_model_id.id
#                         }
#         }
#
#     def action_request_process_approval(self):
#         pa_id_requested = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'process'),
#              ('state', 'in', ['draft', 'request'])])
#         if pa_id_requested:
#             raise UserError(_("Process Approval is already requested."))
#         pa_id = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('state', '=', 'done'), ('inspection_type', '=', 'process')])
#         if pa_id:
#             raise UserError(_("Process Approval is already done."))
#         inspection_id = self.env['first.article.inspection'].create({
#             'inspection_type': 'process',
#             'date': fields.Date.today(),
#             'operation_id': self.operation_id.id,
#             'origin': self.name,
#             'user_id': self.env.user.id,
#             'model_id': self.product_model_id.id,
#         })
#         inspection_id.action_request()
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'message': _("Process has been created."),
#                 'type': 'success',
#                 'sticky': False,
#                 'next': {
#                     'type': 'ir.actions.act_window_close'
#                 },
#             }
#         }
#
#     def action_open_inspection(self):
#         fai_ids = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id),('inspection_type', '=', 'fai')])
#         return {
#             'res_model': 'first.article.inspection',
#             'type': 'ir.actions.act_window',
#             'name': _("First Article Inspection"),
#             'domain': [('id', 'in', fai_ids.ids)],
#             'view_mode': 'list,form',
#             'context': {'default_inspection_type': 'fai',
#                         'default_operation_id': self.operation_id.id,
#                         'default_origin': self.name,
#                         'default_model_id': self.product_model_id.id
#                         }
#         }
#
#     def action_request_inspection(self):
#         ins_id_requested = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('inspection_type', '=', 'fai'),
#              ('state', 'in', ['draft', 'request'])])
#         if ins_id_requested:
#             raise UserError(_("First article inspection is already requested."))
#         ins_id = self.env['first.article.inspection'].search(
#             [('origin', '=', self.name), ('operation_id', '=', self.operation_id.id), ('state', '=', 'done'), ('inspection_type', '=', 'fai')])
#         if ins_id:
#             raise UserError(_("First article inspection already done."))
#         inspection_id = self.env['first.article.inspection'].create({
#             'inspection_type': 'fai',
#             'date': fields.Date.today(),
#             'operation_id': self.operation_id.id,
#             'origin': self.name,
#             'user_id': self.env.user.id,
#             'model_id': self.product_model_id.id,
#         })
#         inspection_id.action_request()
#         return {
#             'type': 'ir.actions.client',
#             'tag': 'display_notification',
#             'params': {
#                 'message': _("First article inspection has been created."),
#                 'type': 'success',
#                 'sticky': False,
#                 'next': {
#                     'type': 'ir.actions.act_window_close'
#                 },
#             }
#         }
#
#     def action_start(self):
#         for rec in self:
#             pa_id = self.env['first.article.inspection'].search(
#                 [('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id),
#                  ('inspection_type', '=', 'process'), ('state', '=', 'done')])
#             if not pa_id:
#                 pass
#                 # raise UserError("Kindly do process Approval before starting production")
#             fai_id = self.env['first.article.inspection'].search(
#                 [('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('inspection_type', '=', 'fai'),
#                  ('state', '=', 'done')])
#             if not fai_id:
#                 pass
# #                 raise UserError("Kindly do First Article Inspection before starting production")
#         return super(VoltageTest, self).action_start()

    # def action_done_production(self):
    #     for rec in self:
    #         fai_id = self.env['first.article.inspection'].search(
    #             [('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('state', '=', 'done')])
    #         dn_id = self.env['deviation.note'].search(
    #             [('origin', '=', rec.name), ('operation_id', '=', rec.operation_id.id), ('state', '=', 'done')])
    #         if not fai_id and not dn_id:
    #             raise UserError(
    #                 _("First article inspection or Deviation Note is not yet finished. Please contact the inspection personnel to complete it."))
    #     return super(VoltageTest, self).action_done_production()


class DeviationNote(models.Model):
    _name = 'deviation.note'

    name = fields.Char('Deviation No',  default='New', required=True)
    state = fields.Selection(
        [('draft', 'Draft'), ('request', 'Requested'), ('request2', 'Requested'), ('done', 'Done'), ('reject', 'Rejected'), ('cancel', 'Cancel')],
        string='Status', required=True, readonly=True,
        copy=False, tracking=True, default='draft')
    doc_no = fields.Char('Doc No')
    rev = fields.Char('Rev')
    operation_id = fields.Many2one('manufacturing.operation', string="Operation")
    part = fields.Char('Part Name')
    shift = fields.Char('Shift')
    qty = fields.Integer('Qty')
    part_no = fields.Char('Part No')
    deviation_end = fields.Selection([
        ('supplier', 'Supplier'),
        ('house', 'In-house')
    ], string='Deviation End')
    # requested_by = fields.Char(string="Requested By")
    requested_id = fields.Many2one('res.users', string="Requested By", readonly=True)
    description = fields.Text('Deviation Requested Details')
    from_date = fields.Date('Approval Period')
    to_date = fields.Date('To date')
    date = fields.Date('Date')
    remarks = fields.Char('Remarks (if any)')
    first_approve = fields.Char('First Approved By')
    second_approve = fields.Char('Second Approved By')
    user_id = fields.Many2one('res.users', string='User')
    origin = fields.Char("Source Document")

    @api.model
    def default_get(self, fields):
        defaults = super(DeviationNote, self).default_get(fields)
        company_id = self.env.user.company_id or self.env['res.company'].search([])[0]
        defaults['rev'] = company_id.dn_rev_no
        defaults['doc_no'] = company_id.dn_doc_no
        defaults['date'] = company_id.dn_rev_date
        return defaults

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'deviation.note'
                ) or _('New')
        return super().create(vals_list)


    def action_request(self):
        for rec in self:
            user_ids = self.env.ref('fnet_mrp.group_mrp_quality_manager').sudo().user_ids
            process_name = 'Deviation Note'

            for user in user_ids:
                mail_values = {
                    'auto_delete': False,
                    'author_id': self.env.user.partner_id.id,
                    'email_from': (self.env.user.email_formatted or self.env.ref('base.user_root').email_formatted),
                    'email_to': user.login,
                    'body_html': """Dear Sir/Madam,<br/> 
                                    You have been requested to verify the %s: %s.<br/>
                                    Thanks & Regards.""" % (process_name, rec.name),
                    'subject': 'Approval request for %s: %s' % (process_name, self.name),
                }
                self.env['mail.mail'].sudo().create(mail_values).send()
            rec.write({
                'state': 'request',
            })

    def action_validate(self):
        for rec in self:
            user_ids = self.env.ref('fnet_mrp.group_manufacturing_manager').sudo().user_ids
            process_name = 'Deviation Note'
            for user in user_ids:
                mail_values = {
                    'auto_delete': False,
                    'author_id': self.env.user.partner_id.id,
                    'email_from': (self.env.user.email_formatted or self.env.ref('base.user_root').email_formatted),
                    'email_to': user.login,
                    'body_html': """Dear Sir/Madam,<br/> 
                                    You have been requested to verify the %s: %s.<br/>
                                    Thanks & Regards.""" % (process_name, rec.name),
                    'subject': 'Approval request for %s: %s' % (process_name, self.name),
                }
                self.env['mail.mail'].sudo().create(mail_values).send()
            rec.write({
                'state': 'request2', 'first_approve': self.env.user.name
            })

    def action_validate2(self):
        for rec in self:
            process_name = 'Deviation Note'

            mail_values = {
                'auto_delete': False,
                'author_id': self.env.user.partner_id.id,
                'email_from': (self.env.user.email_formatted or self.env.ref('base.user_root').email_formatted),
                'email_to': rec.user_id.login,
                'body_html': """Dear Sir/Madam,<br/> 
                                Your %s request has been approved for %s.<br/>
                                Thanks & Regards.""" % (process_name, rec.name),
                'subject': 'Request approved for %s: %s' % (process_name, self.name),
            }
            self.env['mail.mail'].sudo().create(mail_values).send()
            rec.write({
                'state': 'done', 'second_approve': self.env.user.name
            })

    def action_reject(self):
        for rec in self:
            process_name = 'Deviation Note'
            mail_values = {
                'auto_delete': False,
                'author_id': self.env.user.partner_id.id,
                'email_from': (self.env.user.email_formatted or self.env.ref('base.user_root').email_formatted),
                'email_to': rec.user_id.login,
                'body_html': """Dear Sir/Madam,<br/> 
                                Unfortunately your request for %s: %s have been rejected.<br/>
                                Thanks & Regards.""" % (process_name, rec.name),
                'subject': 'Approval rejected for %s: %s' % (process_name, rec.name),
            }
            self.env['mail.mail'].sudo().create(mail_values).send()
            rec.write({
                'state': 'reject',
            })

    def action_cancel(self):
        for rec in self:
            rec.write({
                'state': 'cancel',
            })

    def action_reset(self):
        for rec in self:
            rec.write({
                'state': 'draft'
            })
