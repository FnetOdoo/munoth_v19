# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from datetime import datetime, date
from odoo.exceptions import UserError, ValidationError


class MaterialPurchaseRequisition(models.Model):
    _name = 'material.purchase.requisition'
    _description = 'Purchase Requisition'
    #_inherit = ['mail.thread', 'ir.needaction_mixin']
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'id desc'
    
    #@api.multi
    def unlink(self):
        for rec in self:
            if rec.state not in ('draft', 'cancel', 'reject'):
                raise UserError(_('You can not delete Purchase Requisition which is not in draft or cancelled or rejected state.'))
        return super(MaterialPurchaseRequisition, self).unlink()

    def _default_factory_manager_id(self):
        if self.env.user.has_group('material_purchase_requisitions.group_purchase_requisition_department'):
            employee = self.env['hr.employee'].sudo().search(
                [('user_id', '=', self.env.user.id)], limit=1
            )
            return employee.id
        return False

    name = fields.Char(
        string='Number',
        index=True,
        readonly=1,
    )
    state = fields.Selection([
        ('draft', 'New'),
        ('requested', 'Waiting Department Approval'),
        ('dept_manager_approved', 'Department Manager Approved'),
        ('factory_manager_approved', 'Factory Manager Approved'),
        ('po_created', 'Purchase Order Created'),
        ('partial_receive', 'Partial Material Received'),
        ('receive', 'Material Received'),
        ('done', 'Completed'),
        ('cancel', 'Cancelled'),
        ('reject', 'Rejected')],
        default='draft',
        #track_visibility='onchange',
        tracking=True
    )
    request_date = fields.Date(string='Requisition Date',default=fields.Date.context_today,required=True,)
    department_id = fields.Many2one('hr.department',string='Functional Department', required=True, copy=True,)
    employee_id = fields.Many2one('hr.employee',string='Employee', default=lambda self: self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1),
                                  required=True,copy=True,)
    dept_manager_id = fields.Many2one('hr.employee',string='Department Manager', readonly=True,  copy=False, related="employee_id.parent_id", store=True)
    factory_manager_id = fields.Many2one('hr.employee', string='Confirmed by', readonly=True, copy=False, default=lambda self: self._default_factory_manager_id(),)
    reject_manager_id = fields.Many2one( 'hr.employee',string='Department Manager Reject', readonly=True,)
    approve_employee_id = fields.Many2one('hr.employee', string='Approved by',readonly=True, copy=False,)
    reject_employee_id = fields.Many2one('hr.employee', string='Rejected by',readonly=True,copy=False,)
    company_id = fields.Many2one( 'res.company', string='Company', default=lambda self: self.env.user.company_id,required=True, copy=True,)
    location_id = fields.Many2one('stock.location', string='Source Location',
        copy=True,domain=[('stock_location', '=', True)],default=lambda self: self.env.user._get_default_warehouse_id().lot_stock_id.id,)
    requisition_line_ids = fields.One2many('material.purchase.requisition.line','requisition_id', string='Purchase Requisitions Line', copy=True,)
    date_end = fields.Date(string='Requisition Deadline', readonly=True,help='Last date for the product to be needed', copy=True,)
    date_done = fields.Date(string='Date Done',  readonly=True,  help='Date of Completion of Purchase Requisition',)
    managerapp_date = fields.Date( string='Department Approval Date',readonly=True,copy=False,)
    manareject_date = fields.Date(string='Department Manager Reject Date', readonly=True,)
    userreject_date = fields.Date( string='Rejected Date', readonly=True, copy=False,)
    userrapp_date = fields.Date(string='Approved Date',readonly=True, copy=False,)
    receive_date = fields.Date(string='Received Date', readonly=True, copy=False)
    reason = fields.Text(string='Reason for Requisitions', required=False, copy=True)
    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account', copy=True)
    dest_location_id = fields.Many2one('stock.location', string='Destination Location', required=False, copy=True)
    delivery_picking_id = fields.Many2one('stock.picking', string='Internal Picking', readonly=True, copy=False)
    # manager_id = fields.Many2one('hr.employee', string='Requisition Responsible', copy=True, related="employee_id.parent_id", store=True)
    confirm_date = fields.Date(string='Confirmed Date', readonly=True, copy=False)
    purchase_order_ids = fields.One2many('purchase.order', 'custom_requisition_id', string='Purchase Ordes')
    is_manager_login = fields.Boolean(string="Is Manager Login", compute="_compute_is_manager_login")
    custom_picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type', check_company=True, copy=False,
        default=lambda self: self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1).id)
    is_transfer_created = fields.Boolean(copy=False)
    reject_reason = fields.Text()

    @api.depends('dept_manager_id')
    def _compute_is_manager_login(self):
        current_employee = self.env.user.sudo().employee_id
        for rec in self:
            rec.is_manager_login = (
                    bool(rec.dept_manager_id) and rec.dept_manager_id == current_employee
            )

    @api.onchange('employee_id')
    def set_department(self):
        for rec in self:
            rec.department_id = rec.employee_id.sudo().department_id.id
            rec.dest_location_id = rec.employee_id.sudo().dest_location_id.id or rec.employee_id.sudo().department_id.dest_location_id.id


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.requisition.seq') or _('New')
        return super().create(vals_list)

    def requisition_confirm(self):
        for rec in self:
            if not self.location_id:
                raise UserError('Please Select the Source Location')
            if not self.dest_location_id:
                raise UserError('Please Select the Destination Location')
            if not rec.requisition_line_ids:
                raise ValidationError(_("Please create at least one requisition line before confirming."))

            for line in rec.requisition_line_ids:
                if not line.product_id:
                    raise ValidationError(_("Please select a product for all requisition lines."))
                if not line.qty or line.qty <= 0:
                    raise ValidationError(
                        _("Quantity must be greater than zero for product '%s'.") % line.product_id.display_name)
                if not line.uom:
                    raise ValidationError(
                        _("Please set a Unit of Measure for product '%s'.") % line.product_id.display_name)

            rec.confirm_date = fields.Date.today()
            rec.state = 'requested'

            # ✅ Use sudo() to bypass hr.employee public profile restriction
            employee_sudo = rec.employee_id.sudo()

            if not rec.dept_manager_id or not rec.dept_manager_id.sudo().work_email:
                continue

            from datetime import date
            today_str = date.today().strftime("%d %B %Y")

            company = rec.company_id
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (rec.id, self._name)

            body_html = """
                    <!DOCTYPE html>
                    <html lang="en">
                    <head>
                      <meta charset="UTF-8">
                      <meta name="viewport" content="width=device-width,initial-scale=1.0">
                    </head>
                    <body style="margin:0;padding:0;background-color:#E8EBF0;
                                 font-family:'Segoe UI',Helvetica,Arial,sans-serif;">

                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                             style="background-color:#E8EBF0;padding:40px 16px;">
                        <tr>
                          <td align="center">

                            <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                                   style="width:100%;background:#FFFFFF;border-radius:10px;
                                          overflow:hidden;border:1px solid #E2E8F0;">

                              <!-- Top accent bar -->
                              <tr>
                                <td style="background:#2D3E6F;height:4px;font-size:0;line-height:0;">&nbsp;</td>
                              </tr>

                              <!-- Header -->
                              <tr>
                                <td style="padding:22px 32px 18px;border-bottom:1px solid #E2E8F0;background:#dbe0f0;">
                                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                    <tr>
                                      <td style="vertical-align:middle;">
                                        <div style="font-size:11px;color:#475569;letter-spacing:0.8px;
                                                    text-transform:uppercase;margin-bottom:4px;">
                                         <b> Purchase Requisition</b>
                                        </div>
                                        <div style="font-size:15px;font-weight:600;color:#0F172A;">
                                          Approval Required
                                        </div>
                                      </td>
                                      <td style="vertical-align:middle;text-align:right;white-space:nowrap;">
                                        <span style="display:inline-block;
                                                     background:#FEF3C7;
                                                     border:1px solid #D97706;
                                                     border-radius:20px;
                                                     padding:4px 14px;
                                                     font-size:11px;font-weight:600;
                                                     color:#92400E;
                                                     letter-spacing:0.4px;">
                                          Pending Review
                                        </span>
                                      </td>
                                    </tr>
                                  </table>
                                </td>
                              </tr>

                              <!-- Greeting -->
                              <tr>
                                <td style="padding:22px 32px 0;">
                                  <p style="margin:0 0 6px;font-size:14px;color:#1E293B;">
                                    Dear <strong style="color:#0F172A;">{manager_name}</strong>,
                                  </p>
                                  <p style="margin:0;font-size:13px;color:#1E293B;line-height:1.7;">
                                    A material purchase requisition has been submitted and is awaiting
                                    your approval. Please review the details below and take the
                                    appropriate action.
                                  </p>
                                </td>
                              </tr>

                              <!-- Detail Card -->
                              <tr>
                                <td style="padding:18px 32px;">
                                  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                                         style="border:1px solid #E2E8F0;border-radius:8px;overflow:hidden;">

                                    <!-- Card header -->
                                    <tr>
                                      <td colspan="2"
                                          style="background:#dbe0f0;border-bottom:1px solid #E2E8F0;padding:9px 20px;">
                                        <span style="font-size:10px;font-weight:700;letter-spacing:1px;
                                                     text-transform:uppercase;color:#334155;">Requisition Details</span>
                                      </td>
                                    </tr>

                                    <!-- Requisition No. -->
                                    <tr>
                                      <td style="padding:12px 20px 8px;font-size:12px;color:#1E293B;
                                                 width:38%;vertical-align:top;font-weight:600;
                                                 border-bottom:1px solid #F1F5F9;">
                                        Requisition No.
                                      </td>
                                      <td style="padding:12px 20px 8px;vertical-align:top;
                                                 border-bottom:1px solid #F1F5F9;">
                                        <span style="background:#EFF6FF;border:1px solid #BFDBFE;
                                                     border-radius:5px;padding:3px 10px;
                                                     font-family:monospace;font-size:12px;color:#1D4ED8;">
                                          {rec_name}
                                        </span>
                                      </td>
                                    </tr>

                                    <!-- Requested By -->
                                    <tr>
                                      <td style="padding:11px 20px;font-size:12px;color:#1E293B;font-weight:600;
                                                 border-bottom:1px solid #F1F5F9;">
                                        Requested By
                                      </td>
                                      <td style="padding:11px 20px;font-size:13px;color:#0F172A;
                                                 border-bottom:1px solid #F1F5F9;">
                                        {employee_name}
                                      </td>
                                    </tr>

                                    <!-- Department -->
                                    <tr>
                                      <td style="padding:11px 20px;font-size:12px;color:#1E293B;font-weight:600;
                                                 border-bottom:1px solid #F1F5F9;">
                                        Department
                                      </td>
                                      <td style="padding:11px 20px;font-size:13px;color:#0F172A;
                                                 border-bottom:1px solid #F1F5F9;">
                                        {department_name}
                                      </td>
                                    </tr>

                                    <!-- Job Position -->
                                    <tr>
                                      <td style="padding:11px 20px;font-size:12px;color:#1E293B;font-weight:600;
                                                 border-bottom:1px solid #F1F5F9;">
                                        Job Position
                                      </td>
                                      <td style="padding:11px 20px;font-size:13px;color:#0F172A;
                                                 border-bottom:1px solid #F1F5F9;">
                                        {job_position}
                                      </td>
                                    </tr>

                                    <!-- Submitted On -->
                                    <tr>
                                      <td style="padding:11px 20px 13px;font-size:12px;color:#1E293B;font-weight:600;">
                                        Submitted On
                                      </td>
                                      <td style="padding:11px 20px 13px;font-size:13px;color:#0F172A;">
                                        {today_str}
                                      </td>
                                    </tr>

                                  </table>
                                </td>
                              </tr>

                              <!-- Divider -->
                              <tr>
                                <td style="padding:0 32px;">
                                  <hr style="border:none;border-top:1px solid #E2E8F0;margin:0;">
                                </td>
                              </tr>

                              <!-- CTA Button -->
                              <tr>
                                <td style="padding:18px 32px;">
                                  <a href="{base_url}"
                                     style="display:inline-block;background-color:#2D3E6F;color:#ffffff;
                                            text-decoration:none;font-size:13px;font-weight:600;
                                            padding:10px 22px;border-radius:7px;letter-spacing:0.02em;">
                                    View Requisition &#8594;
                                  </a>
                                </td>
                              </tr>

                              <!-- Closing -->
                              <tr>
                                <td style="padding:4px 32px 22px;">
                                  <p style="margin:0;font-size:13px;color:#1E293B;line-height:1.7;">
                                    Thanks &amp; regards,<br>
                                    <strong style="color:#0F172A;">{employee_name}</strong>
                                    <span style="font-weight:400;color:#64748B;">
                                      &nbsp;&bull;&nbsp; {department_name}
                                    </span>
                                  </p>
                                </td>
                              </tr>

                              <!-- Footer -->
                              <tr>
                                <td style="background:#dbe0f0;border-top:1px solid #E2E8F0;
                                           padding:12px 32px;text-align:center;">
                                  <p style="font-size:11px;color:#475569;line-height:1.7;margin:0;">
                                    You are receiving this because you are an assigned approver
                                    for this requisition.<br/>
                                    &copy; {company_name}
                                  </p>
                                </td>
                              </tr>

                              <!-- Bottom accent bar -->
                              <tr>
                                <td style="background:#2D3E6F;height:3px;font-size:0;line-height:0;">&nbsp;</td>
                              </tr>

                            </table>
                          </td>
                        </tr>
                      </table>

                    </body>
                    </html>
                    """.format(
                manager_name=rec.dept_manager_id.sudo().name or '',
                rec_name=rec.name or '',
                employee_name=employee_sudo.name or '',
                department_name=employee_sudo.department_id.name or '?',
                job_position=employee_sudo.job_id.name or '?',
                today_str=today_str,
                base_url=base_url,
                company_name=company.name or '',
            )

            mail_values = {
                'subject': f'Purchase Requisition Approval - {rec.name}',
                'email_from': employee_sudo.work_email or company.email,
                'email_to': rec.dept_manager_id.sudo().work_email,
                'body_html': body_html,
                'auto_delete': True,
            }

            self.env['mail.mail'].sudo().create(mail_values).send()

    def manager_approve(self):
        for rec in self:
            rec.managerapp_date = fields.Date.today()
            rec.dept_manager_id = self.env['hr.employee'].sudo().search(
                [('user_id', '=', self.env.uid)], limit=1
            )

            employee_sudo = rec.employee_id.sudo()
            dept_manager_sudo = rec.dept_manager_id.sudo()
            factory_manager_sudo = rec.factory_manager_id.sudo()
            company = employee_sudo.company_id or self.env.user.company_id
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (rec.id, self._name)
            today_str = fields.Date.today().strftime('%d %B %Y')

            # ============================================================
            # EMAIL 1: To Employee (Department Approved)
            # ============================================================
            employee_body = f"""
                        <!DOCTYPE html>
                        <html lang="en">
                        <head>
                          <meta charset="UTF-8">
                          <meta name="viewport" content="width=device-width,initial-scale=1.0">
                        </head>
                        <body style="margin:0;padding:0;background-color:#E8EBF0;
                                     font-family:'Segoe UI',Helvetica,Arial,sans-serif;">

                          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                                 style="background-color:#E8EBF0;padding:40px 16px;">
                            <tr>
                              <td align="center">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                                       style="width:100%;background:#FFFFFF;border-radius:10px;
                                              overflow:hidden;border:1px solid #E2E8F0;">

                                  <tr>
                                    <td style="background:#2D3E6F;height:4px;font-size:0;line-height:0;">&nbsp;</td>
                                  </tr>

                                  <tr>
                                    <td style="padding:22px 32px 18px;border-bottom:1px solid #E2E8F0;background:#F8F9FC;">
                                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                        <tr>
                                          <td style="vertical-align:middle;">
                                            <div style="font-size:11px;color:#475569;letter-spacing:0.8px;
                                                        text-transform:uppercase;margin-bottom:4px;">
                                              Purchase Requisition
                                            </div>
                                            <div style="font-size:15px;font-weight:600;color:#0F172A;">
                                              Department Approved
                                            </div>
                                          </td>
                                          <td style="vertical-align:middle;text-align:right;white-space:nowrap;">
                                            <span style="display:inline-block;
                                                         background:#F0FDF4;
                                                         border:1px solid #86EFAC;
                                                         border-radius:20px;
                                                         padding:4px 14px;
                                                         font-size:11px;font-weight:600;
                                                         color:#166534;
                                                         letter-spacing:0.4px;">
                                              Dept Approved
                                            </span>
                                          </td>
                                        </tr>
                                      </table>
                                    </td>
                                  </tr>

                                  <tr>
                                    <td style="padding:22px 32px 0;">
                                      <p style="margin:0 0 6px;font-size:14px;color:#1E293B;">
                                        Dear <strong style="color:#0F172A;">{rec.employee_id.name}</strong>,
                                      </p>
                                      <p style="margin:0;font-size:13px;color:#1E293B;line-height:1.7;">
                                        Your Purchase Requisition <strong style="color:#0F172A;">{rec.name}</strong>
                                        has been <strong style="color:#2D3E6F;">approved by the department</strong>.
                                        Please find the details below.
                                      </p>
                                    </td>
                                  </tr>

                                  <tr>
                                    <td style="padding:18px 32px;">
                                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                                             style="border:1px solid #E2E8F0;border-radius:8px;overflow:hidden;">

                                        <tr>
                                          <td colspan="2"
                                              style="background:#F8F9FC;border-bottom:1px solid #E2E8F0;padding:9px 20px;">
                                            <span style="font-size:10px;font-weight:700;letter-spacing:1px;
                                                         text-transform:uppercase;color:#334155;">Requisition Details</span>
                                          </td>
                                        </tr>

                                        <tr>
                                          <td style="padding:12px 20px 8px;font-size:12px;color:#1E293B;
                                                     width:38%;vertical-align:top;font-weight:600;
                                                     border-bottom:1px solid #F1F5F9;">Requisition No.</td>
                                          <td style="padding:12px 20px 8px;vertical-align:top;
                                                     border-bottom:1px solid #F1F5F9;">
                                            <span style="background:#EFF6FF;border:1px solid #BFDBFE;
                                                         border-radius:5px;padding:3px 10px;
                                                         font-family:monospace;font-size:12px;color:#1D4ED8;">
                                              {rec.name}
                                            </span>
                                          </td>
                                        </tr>

                                        <tr>
                                          <td style="padding:11px 20px;font-size:12px;color:#1E293B;font-weight:600;
                                                     border-bottom:1px solid #F1F5F9;">Requested By</td>
                                          <td style="padding:11px 20px;font-size:13px;color:#0F172A;
                                                     border-bottom:1px solid #F1F5F9;">{rec.employee_id.name}</td>
                                        </tr>

                                        <tr>
                                          <td style="padding:11px 20px;font-size:12px;color:#1E293B;font-weight:600;
                                                     border-bottom:1px solid #F1F5F9;">Department</td>
                                          <td style="padding:11px 20px;font-size:13px;color:#0F172A;
                                                     border-bottom:1px solid #F1F5F9;">
                                            {employee_sudo.department_id.name or '-'}
                                          </td>
                                        </tr>

                                        <tr>
                                          <td style="padding:11px 20px;font-size:12px;color:#1E293B;font-weight:600;
                                                     border-bottom:1px solid #F1F5F9;">Approved By</td>
                                          <td style="padding:11px 20px;font-size:13px;color:#0F172A;
                                                     border-bottom:1px solid #F1F5F9;">
                                            {dept_manager_sudo.name or '-'}
                                          </td>
                                        </tr>

                                        <tr>
                                          <td style="padding:11px 20px 13px;font-size:12px;color:#1E293B;font-weight:600;">
                                            Approved On</td>
                                          <td style="padding:11px 20px 13px;font-size:13px;color:#0F172A;">
                                            {today_str}
                                          </td>
                                        </tr>

                                      </table>
                                    </td>
                                  </tr>

                                  <tr>
                                    <td style="padding:0 32px;">
                                      <hr style="border:none;border-top:1px solid #E2E8F0;margin:0;">
                                    </td>
                                  </tr>

                                  <tr>
                                    <td style="padding:18px 32px;">
                                      <a href="{base_url}"
                                         style="display:inline-block;background-color:#2D3E6F;color:#ffffff;
                                                text-decoration:none;font-size:13px;font-weight:600;
                                                padding:10px 22px;border-radius:7px;letter-spacing:0.02em;">
                                        View Requisition &#8594;
                                      </a>
                                    </td>
                                  </tr>

                                  <tr>
                                    <td style="padding:4px 32px 22px;background:#F8F9FC;">
                                      <p style="margin:0;font-size:13px;color:#1E293B;line-height:1.7;">
                                        Thanks &amp; regards,<br>
                                        <strong style="color:#0F172A;">{dept_manager_sudo.name or 'Management'}</strong>
                                        <span style="font-weight:400;color:#64748B;">
                                          &nbsp;|&nbsp; {company.name}
                                        </span>
                                      </p>
                                    </td>
                                  </tr>

                                  <tr>
                                    <td style="background:#F4F6F9;border-top:1px solid #E2E8F0;
                                               padding:12px 32px;text-align:center;">
                                      <p style="font-size:11px;color:#475569;line-height:1.7;margin:0;">
                                        You are receiving this as a notification for your submitted requisition.<br/>
                                        &copy; {company.name}
                                      </p>
                                    </td>
                                  </tr>

                                  <tr>
                                    <td style="background:#2D3E6F;height:3px;font-size:0;line-height:0;">&nbsp;</td>
                                  </tr>

                                </table>
                              </td>
                            </tr>
                          </table>
                        </body>
                        </html>
                        """

            self.env['mail.mail'].sudo().create({
                'subject': f'Department Approval - Purchase Requisition - {rec.name}',
                'email_from': dept_manager_sudo.work_email,
                'email_to': employee_sudo.work_email,
                'body_html': employee_body,
                'auto_delete': True,
            }).send()

            # ============================================================
            # EMAIL 2: To Factory Manager (Pending Approval)
            # ============================================================
            factory_manager_body = f"""
                        <!DOCTYPE html>
                        <html lang="en">
                        <head>
                          <meta charset="UTF-8">
                          <meta name="viewport" content="width=device-width,initial-scale=1.0">
                        </head>
                        <body style="margin:0;padding:0;background-color:#E8EBF0;
                                     font-family:'Segoe UI',Helvetica,Arial,sans-serif;">

                          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                                 style="background-color:#E8EBF0;padding:40px 16px;">
                            <tr>
                              <td align="center">
                                <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                                       style="width:100%;background:#FFFFFF;border-radius:10px;
                                              overflow:hidden;border:1px solid #E2E8F0;">

                                  <tr>
                                    <td style="background:#B45309;height:4px;font-size:0;line-height:0;">&nbsp;</td>
                                  </tr>

                                  <tr>
                                    <td style="padding:22px 32px 18px;border-bottom:1px solid #E2E8F0;background:#F8F9FC;">
                                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                                        <tr>
                                          <td style="vertical-align:middle;">
                                            <div style="font-size:11px;color:#475569;letter-spacing:0.8px;
                                                        text-transform:uppercase;margin-bottom:4px;">
                                              Purchase Requisition
                                            </div>
                                            <div style="font-size:15px;font-weight:600;color:#0F172A;">
                                              Pending Your Approval
                                            </div>
                                          </td>
                                          <td style="vertical-align:middle;text-align:right;white-space:nowrap;">
                                            <span style="display:inline-block;
                                                         background:#FFFBEB;
                                                         border:1px solid #FDE68A;
                                                         border-radius:20px;
                                                         padding:4px 14px;
                                                         font-size:11px;font-weight:600;
                                                         color:#92400E;
                                                         letter-spacing:0.4px;">
                                              Awaiting Approval
                                            </span>
                                          </td>
                                        </tr>
                                      </table>
                                    </td>
                                  </tr>

                                  <tr>
                                    <td style="padding:22px 32px 0;">
                                      <p style="margin:0 0 6px;font-size:14px;color:#1E293B;">
                                        Dear <strong style="color:#0F172A;">{factory_manager_sudo.name}</strong>,
                                      </p>
                                      <p style="margin:0;font-size:13px;color:#1E293B;line-height:1.7;">
                                        Purchase Requisition <strong style="color:#0F172A;">{rec.name}</strong>
                                        has been <strong style="color:#2D3E6F;">approved by the department</strong>
                                        and now requires <strong style="color:#B45309;">your approval</strong> as
                                        Factory Manager. Please review the details below.
                                      </p>
                                    </td>
                                  </tr>

                                  <tr>
                                    <td style="padding:18px 32px;">
                                      <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                                             style="border:1px solid #E2E8F0;border-radius:8px;overflow:hidden;">

                                        <tr>
                                          <td colspan="2"
                                              style="background:#F8F9FC;border-bottom:1px solid #E2E8F0;padding:9px 20px;">
                                            <span style="font-size:10px;font-weight:700;letter-spacing:1px;
                                                         text-transform:uppercase;color:#334155;">Requisition Details</span>
                                          </td>
                                        </tr>

                                        <tr>
                                          <td style="padding:12px 20px 8px;font-size:12px;color:#1E293B;
                                                     width:38%;vertical-align:top;font-weight:600;
                                                     border-bottom:1px solid #F1F5F9;">Requisition No.</td>
                                          <td style="padding:12px 20px 8px;vertical-align:top;
                                                     border-bottom:1px solid #F1F5F9;">
                                            <span style="background:#EFF6FF;border:1px solid #BFDBFE;
                                                         border-radius:5px;padding:3px 10px;
                                                         font-family:monospace;font-size:12px;color:#1D4ED8;">
                                              {rec.name}
                                            </span>
                                          </td>
                                        </tr>

                                        <tr>
                                          <td style="padding:11px 20px;font-size:12px;color:#1E293B;font-weight:600;
                                                     border-bottom:1px solid #F1F5F9;">Requested By</td>
                                          <td style="padding:11px 20px;font-size:13px;color:#0F172A;
                                                     border-bottom:1px solid #F1F5F9;">{employee_sudo.name}</td>
                                        </tr>

                                        <tr>
                                          <td style="padding:11px 20px;font-size:12px;color:#1E293B;font-weight:600;
                                                     border-bottom:1px solid #F1F5F9;">Department</td>
                                          <td style="padding:11px 20px;font-size:13px;color:#0F172A;
                                                     border-bottom:1px solid #F1F5F9;">
                                            {employee_sudo.department_id.name or '-'}
                                          </td>
                                        </tr>

                                        <tr>
                                          <td style="padding:11px 20px;font-size:12px;color:#1E293B;font-weight:600;
                                                     border-bottom:1px solid #F1F5F9;">Department Approved By</td>
                                          <td style="padding:11px 20px;font-size:13px;color:#0F172A;
                                                     border-bottom:1px solid #F1F5F9;">
                                            {dept_manager_sudo.name or '-'}
                                          </td>
                                        </tr>

                                        <tr>
                                          <td style="padding:11px 20px 13px;font-size:12px;color:#1E293B;font-weight:600;">
                                            Approved On</td>
                                          <td style="padding:11px 20px 13px;font-size:13px;color:#0F172A;">
                                            {today_str}
                                          </td>
                                        </tr>

                                      </table>
                                    </td>
                                  </tr>

                                  <tr>
                                    <td style="padding:0 32px;">
                                      <hr style="border:none;border-top:1px solid #E2E8F0;margin:0;">
                                    </td>
                                  </tr>

                                  <tr>
                                    <td style="padding:18px 32px;">
                                      <a href="{base_url}"
                                         style="display:inline-block;background-color:#B45309;color:#ffffff;
                                                text-decoration:none;font-size:13px;font-weight:600;
                                                padding:10px 22px;border-radius:7px;letter-spacing:0.02em;">
                                        Review &amp; Approve &#8594;
                                      </a>
                                    </td>
                                  </tr>

                                  <tr>
                                    <td style="padding:4px 32px 22px;background:#F8F9FC;">
                                      <p style="margin:0;font-size:13px;color:#1E293B;line-height:1.7;">
                                        Thanks &amp; regards,<br>
                                        <strong style="color:#0F172A;">{dept_manager_sudo.name or 'Management'}</strong>
                                        <span style="font-weight:400;color:#64748B;">
                                          &nbsp;|&nbsp; {company.name}
                                        </span>
                                      </p>
                                    </td>
                                  </tr>

                                  <tr>
                                    <td style="background:#F4F6F9;border-top:1px solid #E2E8F0;
                                               padding:12px 32px;text-align:center;">
                                      <p style="font-size:11px;color:#475569;line-height:1.7;margin:0;">
                                        You are receiving this as the next approver for this requisition.<br/>
                                        &copy; {company.name}
                                      </p>
                                    </td>
                                  </tr>

                                  <tr>
                                    <td style="background:#B45309;height:3px;font-size:0;line-height:0;">&nbsp;</td>
                                  </tr>

                                </table>
                              </td>
                            </tr>
                          </table>
                        </body>
                        </html>
                        """

            self.env['mail.mail'].sudo().create({
                'subject': f'Approval Required - Purchase Requisition - {rec.name}',
                'email_from': dept_manager_sudo.work_email,
                'email_to': factory_manager_sudo.work_email,
                'body_html': factory_manager_body,
                'auto_delete': True,
            }).send()

            rec.state = 'dept_manager_approved'

    def requisition_reject(self):
        for rec in self:
            if not rec.reject_reason:
                raise UserError('Please enter a reason for rejection in the Other Information tab.')
            rec.state = 'reject'
            rec.reject_employee_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1)
            reject_employee_sudo = rec.reject_employee_id.sudo()
            employee_sudo = rec.employee_id.sudo()
            company = rec.company_id
            rec.userreject_date = fields.Date.today()
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (rec.id, self._name)  # fix: rec.id not self.id
            reject_body = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
              <meta charset="UTF-8">
              <meta name="viewport" content="width=device-width,initial-scale=1.0">
            </head>
            <body style="margin:0;padding:0;background-color:#E8EBF0;
                         font-family:'Segoe UI',Helvetica,Arial,sans-serif;">

              <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                     style="background-color:#E8EBF0;padding:40px 16px;">
                <tr>
                  <td align="center">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                           style="width:100%;background:#FFFFFF;border-radius:10px;
                                  overflow:hidden;border:1px solid #E2E8F0;">

                      <tr>
                        <td style="background:#DC2626;height:4px;font-size:0;line-height:0;">&nbsp;</td>
                      </tr>

                      <tr>
                        <td style="padding:22px 32px 18px;border-bottom:1px solid #E2E8F0;background:#FFF8F8;">
                          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                            <tr>
                              <td style="vertical-align:middle;">
                                <div style="font-size:11px;color:#475569;letter-spacing:0.8px;
                                            text-transform:uppercase;margin-bottom:4px;">
                                  Purchase Requisition
                                </div>
                                <div style="font-size:15px;font-weight:600;color:#0F172A;">
                                  Requisition Rejected
                                </div>
                              </td>
                              <td style="vertical-align:middle;text-align:right;white-space:nowrap;">
                                <span style="display:inline-block;
                                             background:#FEF2F2;
                                             border:1px solid #FECACA;
                                             border-radius:20px;
                                             padding:4px 14px;
                                             font-size:11px;font-weight:600;
                                             color:#991B1B;
                                             letter-spacing:0.4px;">
                                  Rejected
                                </span>
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>

                      <tr>
                        <td style="padding:22px 32px 0;">
                          <p style="margin:0 0 6px;font-size:14px;color:#1E293B;">
                            Dear <strong style="color:#0F172A;">{employee_sudo.name}</strong>,
                          </p>
                          <p style="margin:0;font-size:13px;color:#1E293B;line-height:1.7;">
                            Your Purchase Requisition <strong style="color:#0F172A;">{rec.name}</strong>
                            has been <strong style="color:#DC2626;">rejected</strong>.
                            Please review the details and reason below.
                          </p>
                        </td>
                      </tr>

                      <tr>
                        <td style="padding:18px 32px;">
                          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                                 style="border:1px solid #E2E8F0;border-radius:8px;overflow:hidden;">

                            <tr>
                              <td colspan="2"
                                  style="background:#FFF8F8;border-bottom:1px solid #E2E8F0;padding:9px 20px;">
                                <span style="font-size:10px;font-weight:700;letter-spacing:1px;
                                             text-transform:uppercase;color:#991B1B;">Requisition Details</span>
                              </td>
                            </tr>

                            <tr>
                              <td style="padding:12px 20px 8px;font-size:12px;color:#1E293B;
                                         width:38%;vertical-align:top;font-weight:600;
                                         border-bottom:1px solid #F1F5F9;">Requisition No.</td>
                              <td style="padding:12px 20px 8px;vertical-align:top;
                                         border-bottom:1px solid #F1F5F9;">
                                <span style="background:#EFF6FF;border:1px solid #BFDBFE;
                                             border-radius:5px;padding:3px 10px;
                                             font-family:monospace;font-size:12px;color:#1D4ED8;">
                                  {rec.name}
                                </span>
                              </td>
                            </tr>
                            <tr>
                              <td style="padding:11px 20px;font-size:12px;color:#1E293B;font-weight:600;
                                         border-bottom:1px solid #F1F5F9;">Rejected By</td>
                              <td style="padding:11px 20px;font-size:13px;color:#0F172A;
                                         border-bottom:1px solid #F1F5F9;">
                                {rec.reject_employee_id.name or '-'}
                              </td>
                            </tr>

                            <tr>
                              <td style="padding:11px 20px;font-size:12px;color:#1E293B;font-weight:600;
                                         border-bottom:1px solid #F1F5F9;">Rejection Date</td>
                              <td style="padding:11px 20px;font-size:13px;color:#0F172A;
                                         border-bottom:1px solid #F1F5F9;">
                                {rec.userreject_date}
                              </td>
                            </tr>

                            <tr>
                              <td style="padding:11px 20px 13px;font-size:12px;color:#1E293B;font-weight:600;
                                         vertical-align:top;">Rejection Reason</td>
                              <td style="padding:11px 20px 13px;font-size:13px;color:#991B1B;font-weight:600;">
                                {rec.reject_reason or 'No reason provided'}
                              </td>
                            </tr>

                          </table>
                        </td>
                      </tr>

                      <tr>
                        <td style="padding:0 32px;">
                          <hr style="border:none;border-top:1px solid #E2E8F0;margin:0;">
                        </td>
                      </tr>

                      <tr>
                        <td style="padding:18px 32px;">
                          <a href="{base_url}"
                             style="display:inline-block;background-color:#DC2626;color:#ffffff;
                                    text-decoration:none;font-size:13px;font-weight:600;
                                    padding:10px 22px;border-radius:7px;letter-spacing:0.02em;">
                            View Requisition &#8594;
                          </a>
                        </td>
                      </tr>

                      <tr>
                        <td style="padding:4px 32px 22px;background:#FFF8F8;">
                          <p style="margin:0;font-size:13px;color:#1E293B;line-height:1.7;">
                            Thanks &amp; regards,<br>
                            <strong style="color:#0F172A;">{rec.reject_employee_id.name or 'Management'}</strong>
                            <span style="font-weight:400;color:#64748B;">
                              
                            </span>
                          </p>
                        </td>
                      </tr>

                      <tr>
                        <td style="background:#F4F6F9;border-top:1px solid #E2E8F0;
                                   padding:12px 32px;text-align:center;">
                          <p style="font-size:11px;color:#475569;line-height:1.7;margin:0;">
                            You are receiving this because your requisition was processed.<br/>
                           
                          </p>
                        </td>
                      </tr>

                      <tr>
                        <td style="background:#DC2626;height:3px;font-size:0;line-height:0;">&nbsp;</td>
                      </tr>

                    </table>
                  </td>
                </tr>
              </table>
            </body>
            </html>
            """

            self.env['mail.mail'].sudo().create({
                'subject': f'Purchase Requisition Rejected - {rec.name}',
                'email_from': reject_employee_sudo.work_email or company.email,
                'email_to': employee_sudo.work_email,
                'body_html': reject_body,
                'auto_delete': True,
            }).send()

    def action_factory_manager_approve(self):
        for rec in self:
            rec.userrapp_date = fields.Date.today()
            rec.approve_employee_id = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.uid)], limit=1)
            rec.state = 'factory_manager_approved'

            # ✅ All employee access via sudo
            employee_sudo = rec.employee_id.sudo()
            dept_manager_sudo = rec.dept_manager_id.sudo()
            company = employee_sudo.company_id or self.env.user.company_id
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (rec.id, self._name)
            today_str = fields.Date.today().strftime('%d %B %Y')

            # ✅ Purchase group users via sudo
            purchase_group = self.env.ref(
                'material_purchase_requisitions.group_purchase_requisition_purchase',
                raise_if_not_found=False
            )
            purchase_user_emails = []
            if purchase_group:
                purchase_users = self.env['res.users'].sudo().search(
                    [('group_ids', 'in', purchase_group.id)]
                )
                for user in purchase_users:
                    emp = self.env['hr.employee'].sudo().search(
                        [('user_id', '=', user.id)], limit=1
                    )
                    if emp and emp.work_email:
                        purchase_user_emails.append(emp.work_email)
            purchase_user_email_to = ','.join(purchase_user_emails)

            # EMAIL 1: To Requester
            requester_body = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
              <meta charset="UTF-8">
              <meta name="viewport" content="width=device-width,initial-scale=1.0">
            </head>
            <body style="margin:0;padding:0;background-color:#E8EBF0;
                         font-family:'Segoe UI',Helvetica,Arial,sans-serif;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                     style="background-color:#E8EBF0;padding:40px 16px;">
                <tr>
                  <td align="center">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                           style="width:100%;background:#FFFFFF;border-radius:10px;
                                  overflow:hidden;border:1px solid #E2E8F0;">
                      <tr>
                        <td style="background:#2D3E6F;height:4px;font-size:0;line-height:0;">&nbsp;</td>
                      </tr>
                      <tr>
                        <td style="padding:22px 32px 18px;border-bottom:1px solid #E2E8F0;background:#F8F9FC;">
                          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                            <tr>
                              <td style="vertical-align:middle;">
                                <div style="font-size:11px;color:#475569;letter-spacing:0.8px;
                                            text-transform:uppercase;margin-bottom:4px;">
                                  Purchase Requisition
                                </div>
                                <div style="font-size:15px;font-weight:600;color:#0F172A;">
                                  Factory Manager Approved
                                </div>
                              </td>
                              <td style="vertical-align:middle;text-align:right;white-space:nowrap;">
                                <span style="display:inline-block;
                                             background:#DCFCE7;
                                             border:1px solid #16A34A;
                                             border-radius:20px;
                                             padding:4px 14px;
                                             font-size:11px;font-weight:600;
                                             color:#166534;
                                             letter-spacing:0.4px;">
                                  Approved
                                </span>
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding:22px 32px 26px;">
                          <p style="margin:0 0 6px;font-size:14px;color:#1E293B;">
                            Dear <strong style="color:#0F172A;">{employee_sudo.name}</strong>,
                          </p>
                          <p style="margin:0;font-size:13px;color:#1E293B;line-height:1.7;">
                            Your material purchase requisition
                            <strong style="color:#0F172A;">{rec.name}</strong>
                            has been <strong style="color:#16A34A;">approved by the Factory Manager</strong>.
                          </p>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding:4px 32px 22px;background:#F8F9FC;">
                          <p style="margin:0;font-size:13px;color:#1E293B;line-height:1.7;">
                            Thanks &amp; regards,<br>
                            <strong style="color:#0F172A;">{company.name}</strong>
                          </p>
                        </td>
                      </tr>
                      <tr>
                        <td style="background:#F4F6F9;border-top:1px solid #E2E8F0;
                                   padding:12px 32px;text-align:center;">
                          <p style="font-size:11px;color:#475569;line-height:1.7;margin:0;">
                            You are receiving this because you submitted this requisition.<br/>
                            &copy; {company.name}
                          </p>
                        </td>
                      </tr>
                      <tr>
                        <td style="background:#2D3E6F;height:3px;font-size:0;line-height:0;">&nbsp;</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </body>
            </html>
            """
            self.env['mail.mail'].sudo().create({
                'subject': f'Factory Manager Approved - Purchase Requisition - {rec.name}',
                'email_from': employee_sudo.work_email or company.email,
                'email_to': employee_sudo.work_email,
                'body_html': requester_body,
                'auto_delete': True,
            }).send()

            # EMAIL 2: To Purchase User
            purchase_user_body = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
              <meta charset="UTF-8">
              <meta name="viewport" content="width=device-width,initial-scale=1.0">
            </head>
            <body style="margin:0;padding:0;background-color:#E8EBF0;
                         font-family:'Segoe UI',Helvetica,Arial,sans-serif;">
              <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                     style="background-color:#E8EBF0;padding:40px 16px;">
                <tr>
                  <td align="center">
                    <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                           style="width:100%;background:#FFFFFF;border-radius:10px;
                                  overflow:hidden;border:1px solid #E2E8F0;">
                      <tr>
                        <td style="background:#2D3E6F;height:4px;font-size:0;line-height:0;">&nbsp;</td>
                      </tr>
                      <tr>
                        <td style="padding:22px 32px 18px;border-bottom:1px solid #E2E8F0;background:#F8F9FC;">
                          <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
                            <tr>
                              <td style="vertical-align:middle;">
                                <div style="font-size:11px;color:#475569;letter-spacing:0.8px;
                                            text-transform:uppercase;margin-bottom:4px;">
                                  Purchase Requisition
                                </div>
                                <div style="font-size:15px;font-weight:600;color:#0F172A;">
                                  Purchase Order Required
                                </div>
                              </td>
                              <td style="vertical-align:middle;text-align:right;white-space:nowrap;">
                                <span style="display:inline-block;
                                             background:#FEF3C7;
                                             border:1px solid #D97706;
                                             border-radius:20px;
                                             padding:4px 14px;
                                             font-size:11px;font-weight:600;
                                             color:#92400E;
                                             letter-spacing:0.4px;">
                                  Pending PO
                                </span>
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding:22px 32px 0;">
                          <p style="margin:0 0 6px;font-size:14px;color:#1E293B;">
                            Dear <strong style="color:#0F172A;">Purchase Team</strong>,
                          </p>
                          <p style="margin:0;font-size:13px;color:#1E293B;line-height:1.7;">
                            A material purchase requisition submitted by
                            <strong style="color:#0F172A;">{employee_sudo.name}</strong>
                            has been approved by the Factory Manager. Please
                            <strong style="color:#1D4ED8;">create a Purchase Order</strong>
                            for this requisition. Please review the details below.
                          </p>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding:18px 32px;">
                          <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
                                 style="border:1px solid #E2E8F0;border-radius:8px;overflow:hidden;">
                            <tr>
                              <td colspan="2"
                                  style="background:#F8F9FC;border-bottom:1px solid #E2E8F0;padding:9px 20px;">
                                <span style="font-size:10px;font-weight:700;letter-spacing:1px;
                                             text-transform:uppercase;color:#334155;">Requisition Details</span>
                              </td>
                            </tr>
                            <tr>
                              <td style="padding:12px 20px 8px;font-size:12px;color:#1E293B;
                                         width:38%;vertical-align:top;font-weight:600;
                                         border-bottom:1px solid #F1F5F9;">Requisition No.</td>
                              <td style="padding:12px 20px 8px;vertical-align:top;
                                         border-bottom:1px solid #F1F5F9;">
                                <span style="background:#EFF6FF;border:1px solid #BFDBFE;
                                             border-radius:5px;padding:3px 10px;
                                             font-family:monospace;font-size:12px;color:#1D4ED8;">
                                  {rec.name}
                                </span>
                              </td>
                            </tr>
                            <tr>
                              <td style="padding:11px 20px;font-size:12px;color:#1E293B;font-weight:600;
                                         border-bottom:1px solid #F1F5F9;">Requested By</td>
                              <td style="padding:11px 20px;font-size:13px;color:#0F172A;
                                         border-bottom:1px solid #F1F5F9;">{employee_sudo.name}</td>
                            </tr>
                            <tr>
                              <td style="padding:11px 20px;font-size:12px;color:#1E293B;font-weight:600;
                                         border-bottom:1px solid #F1F5F9;">Department</td>
                              <td style="padding:11px 20px;font-size:13px;color:#0F172A;
                                         border-bottom:1px solid #F1F5F9;">
                                {employee_sudo.department_id.name or '?'}
                              </td>
                            </tr>
                            <tr>
                              <td style="padding:11px 20px;font-size:12px;color:#1E293B;font-weight:600;
                                         border-bottom:1px solid #F1F5F9;">Job Position</td>
                              <td style="padding:11px 20px;font-size:13px;color:#0F172A;
                                         border-bottom:1px solid #F1F5F9;">
                                {employee_sudo.job_id.name or '?'}
                              </td>
                            </tr>
                            <tr>
                              <td style="padding:11px 20px;font-size:12px;color:#1E293B;font-weight:600;
                                         border-bottom:1px solid #F1F5F9;">Dept. Approved By</td>
                              <td style="padding:11px 20px;font-size:13px;color:#0F172A;
                                         border-bottom:1px solid #F1F5F9;">
                                {dept_manager_sudo.name or '?'}
                              </td>
                            </tr>
                            <tr>
                              <td style="padding:11px 20px 13px;font-size:12px;color:#1E293B;font-weight:600;">
                                Submitted On</td>
                              <td style="padding:11px 20px 13px;font-size:13px;color:#0F172A;">
                                {today_str}
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding:0 32px;">
                          <hr style="border:none;border-top:1px solid #E2E8F0;margin:0;">
                        </td>
                      </tr>
                      <tr>
                        <td style="padding:18px 32px;">
                          <a href="{base_url}"
                             style="display:inline-block;background-color:#2D3E6F;color:#ffffff;
                                    text-decoration:none;font-size:13px;font-weight:600;
                                    padding:10px 22px;border-radius:7px;letter-spacing:0.02em;">
                            Create Purchase Order &#8594;
                          </a>
                        </td>
                      </tr>
                      <tr>
                        <td style="padding:4px 32px 22px;background:#F8F9FC;">
                          <p style="margin:0;font-size:13px;color:#1E293B;line-height:1.7;">
                            Thanks &amp; regards,<br>
                            <strong style="color:#0F172A;">{employee_sudo.name}</strong>
                            <span style="font-weight:400;color:#64748B;">
                              &nbsp;&bull;&nbsp; {employee_sudo.department_id.name or company.name}
                            </span>
                          </p>
                        </td>
                      </tr>
                      <tr>
                        <td style="background:#F4F6F9;border-top:1px solid #E2E8F0;
                                   padding:12px 32px;text-align:center;">
                          <p style="font-size:11px;color:#475569;line-height:1.7;margin:0;">
                            You are receiving this because you are an assigned approver
                            for this requisition.<br/>
                            &copy; {company.name}
                          </p>
                        </td>
                      </tr>
                      <tr>
                        <td style="background:#2D3E6F;height:3px;font-size:0;line-height:0;">&nbsp;</td>
                      </tr>
                    </table>
                  </td>
                </tr>
              </table>
            </body>
            </html>
            """
            self.env['mail.mail'].sudo().create({
                'subject': f'Factory Manager Approved - Please Create PO - {rec.name}',
                'email_from': employee_sudo.work_email or company.email,
                'email_to': purchase_user_email_to,
                'body_html': purchase_user_body,
                'auto_delete': True,
            }).send()

    #@api.multi
    def reset_draft(self):
        for rec in self:
            rec.state = 'draft'

    @api.model
    def _prepare_pick_vals(self, line=False, stock_id=False):
        pick_vals = {
            'product_id': line.product_id.id,
            'product_uom_qty': line.qty,
            'packaging_uom_id': line.uom.id,  # ← was 'product_uom'
            'location_id': self.location_id.id,
            'location_dest_id': self.dest_location_id.id,
            'description_picking': line.product_id.name,
            'picking_type_id': self.custom_picking_type_id.id,
            'picking_id': stock_id.id,
            'custom_requisition_line_id': line.id,
            'company_id': line.requisition_id.company_id.id,
        }
        return pick_vals

    @api.model
    def _prepare_po_line(self, line=False, purchase_order=False):
        seller = line.product_id._select_seller(
            partner_id=self._context.get('partner_id'),
            quantity=line.qty,
            date=purchase_order.date_order and purchase_order.date_order.date(),
            uom_id=line.uom
        )

        # Build analytic distribution if analytic account is set
        analytic_distribution = {}
        if self.analytic_account_id:
            analytic_distribution = {str(self.analytic_account_id.id): 100}

        po_line_vals = {
            'product_id': line.product_id.id,
            'name': line.product_id.name,
            'product_qty': line.qty,
            'product_uom_id': line.uom.id,
            'date_planned': fields.Date.today(),
            'price_unit': seller.price or line.product_id.standard_price or 0.0,
            'order_id': purchase_order.id,
            'analytic_distribution': analytic_distribution,  # ← replaces account_analytic_id
            'custom_requisition_line_id': line.id,
        }
        return po_line_vals

    # def _prepare_pick_vals(self, line=False, stock_id=False):
    #     pick_vals = {
    #         'product_id': line.product_id.id,
    #         'product_uom_qty': line.qty,
    #         'product_uom': line.uom.id,
    #         'name': line.product_id.name,
    #         'location_id': self.location_id.id,
    #         'location_dest_id': self.dest_location_id.id,
    #         'picking_id': stock_id.id,
    #         'picking_type_id': self.custom_picking_type_id.id,
    #         'custom_requisition_line_id': line.id,
    #         'company_id': line.requisition_id.company_id.id,
    #     }
    #     return pick_vals

    def create_transfer(self):
        stock_obj = self.env['stock.picking']
        move_obj = self.env['stock.move']
        for rec in self:
            if not rec.requisition_line_ids:
                raise UserError(_('Please create some requisition lines.'))
            if not rec.location_id.id:
                raise UserError(_('Select Source location under the picking details.'))
            if not rec.custom_picking_type_id.id:
                raise UserError(_('Select Picking Type under the picking details.'))
            if not rec.dest_location_id:
                raise UserError(_('Select Destination location under the picking details.'))
            self.is_transfer_created = True
            picking_vals = {
                'partner_id': rec.employee_id.sudo().address_id.id,
                'location_id': rec.location_id.id,
                'location_dest_id': rec.dest_location_id.id,
                'picking_type_id': rec.custom_picking_type_id.id,
                'note': rec.reason,
                'custom_requisition_id': rec.id,
                'origin': rec.name,
                'company_id': rec.company_id.id,
            }
            stock_id = stock_obj.sudo().create(picking_vals)
            rec.write({'delivery_picking_id': stock_id.id})

            for line in rec.requisition_line_ids:
                pick_vals = rec._prepare_pick_vals(line, stock_id)
                move_obj.sudo().create(pick_vals)
        return True
            # rec.state = 'po_created'

    def create_po(self):
        purchase_obj = self.env['purchase.order']
        purchase_line_obj = self.env['purchase.order.line']

        for rec in self:
            if not rec.requisition_line_ids:
                raise UserError(_('Please create some requisition lines.'))

            po_dict = {}
            for line in rec.requisition_line_ids:
                if line.requisition_type == 'purchase':
                    if not line.partner_id:
                        raise UserError(
                            _('Please enter at least one vendor on Requisition Lines for Requisition Action Purchase'))

                    for partner in line.partner_id:
                        if partner not in po_dict:
                            po_vals = {
                                'partner_id': partner.id,
                                'currency_id': rec.env.user.company_id.currency_id.id,
                                'date_order': fields.Date.today(),
                                'company_id': rec.company_id.id,
                                'custom_requisition_id': rec.id,
                                'origin': rec.name,
                            }
                            purchase_order = purchase_obj.create(po_vals)
                            po_dict.update({partner: purchase_order})
                        else:
                            purchase_order = po_dict.get(partner)

                        po_line_vals = rec.with_context(partner_id=partner)._prepare_po_line(line, purchase_order)
                        purchase_line_obj.sudo().create(po_line_vals)
            self.create_transfer()
            rec.state = 'po_created'
    
    #@api.multi
    def action_received(self):
        for rec in self:
            rec.receive_date = fields.Date.today()
            rec.state = 'receive'
    
    #@api.multi
    def action_cancel(self):
        for rec in self:
            rec.state = 'cancel'

    # @api.multi
    def show_picking(self):
        for rec in self:
            res = self.env.ref('stock.action_picking_tree_all')
            res = res.sudo().read()[0]
            res['domain'] = str([('custom_requisition_id', '=', rec.id)])
            res['context'] = {'create': False}
        return res

    # @api.multi
    def action_show_po(self):
        for rec in self:
            purchase_action = self.env.ref('purchase.purchase_rfq')
            purchase_action = purchase_action.sudo().read()[0]
            purchase_action['domain'] = str([('custom_requisition_id', '=', rec.id)])
            purchase_action['context'] = {'create': False}
        return purchase_action
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
