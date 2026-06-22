from odoo import api, fields, models,_
from odoo.exceptions import UserError,ValidationError

class StockMove(models.Model):
    _inherit = 'stock.move'

    mrp_material_request = fields.Many2one('mrp.material.request')

class MaterialRequestConfiguration(models.Model):
    _name = 'material.request.configuration'
    _description = 'Material Request Configuration'

    name = fields.Char( string='Configuration Name')
    department_id = fields.Many2one( 'hr.department',string='Department' )
    location_id = fields.Many2one('stock.location',string='Source Location' )
    location_dest_id = fields.Many2one('stock.location',string='Destination Location' )
    active = fields.Boolean( string='Active', default=True)
    is_sub_department = fields.Boolean()
    is_approval_line = fields.Boolean()
    user_ids = fields.Many2many('res.users')
    user_id = fields.Many2one('res.users')
    material_request_id = fields.Many2one('mrp.material.request',string='Material Request',ondelete='cascade')
    is_email_sent = fields.Boolean(string='Is Email Sent')
    approval_line_id  = fields.Many2one('material.request.configuration', domain="[('is_approval_line','=',True)]")
    is_approved = fields.Boolean()
    approved_date = fields.Datetime()

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    mrp_material_request = fields.Many2one('mrp.material.request')

class MrpMaterialRequest(models.Model):
    _name = "mrp.material.request"
    _description = 'Material Request'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _order = "id desc"

    def _po_count(self):
        for rec in self:
            rec.po_count = self.env['purchase.order'].search_count([('material_request_id', '=', self.id)])

    name = fields.Char(string='Issue No', required=True, readonly=True, default=lambda self: _('New'), copy=False)
    state = fields.Selection([('draft', 'Draft'), ('request', 'Requested'), ('manager_approve', 'Manager Approved'), ('purchase_request', 'Waiting for Purchase Approval'), ('purchase_approve', 'Purchase Manager Approved'),('purchase_reject', 'Purchase Manager Rejected'), ('confirm', 'Confirmed'), ('received', 'Purchased Material Received'), ('material_accept','Material Accepted'),('material_reject','Material Rejected'), ('cancel', 'Canceled'), ('reject', 'Rejected'),('available','Check Availability')], string="Status", default='draft', tracking=True)
    user_id = fields.Many2one('res.users', 'Requested by', tracking=True, default=lambda self: self.env.user)
    responsible_user_id = fields.Many2one('res.users', 'Responsible', tracking=True)
    type = fields.Selection([('in_ward', 'Internal'),
                             ('out_ward', 'Outward')], string="Type")
    operation_id = fields.Many2one('manufacturing.operation', string='Operation')
    section = fields.Char("Production Section")
    date = fields.Date('Requested Date', default=fields.Date.context_today)
    date_issued = fields.Date('Issued Date')
    request_line_ids = fields.One2many("mrp.material.request.line", 'request_id', string="Material Lines", copy=True)
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, default=lambda self: self.env.company.id)
    location_id = fields.Many2one(
        'stock.location', 'Source Location',
        domain="[('usage','=','internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
        help="Location where the product you want to request from.")
    temporary_location = fields.Many2one(
        'stock.location', 'Temporary Location',
        domain="[('temporary_location','=',True), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        default=lambda self: self.env['stock.location'].search([('temporary_location', '=', True)],limit=1),
        check_company=True)
    is_consumed= fields.Boolean()
    stock_location_id = fields.Many2one('stock.location')
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type', check_company=True, copy=False, default=lambda self: self.env['stock.picking.type'].search([('code', '=', 'internal')], limit=1).id)
    origin = fields.Char(
        'Source', copy=False,
        states={'confirm': [('readonly', True)], 'cancel': [('readonly', True)]},
        help="Reference of the document that generated this request.")
    reject_reason = fields.Char("Rejected Reason")
    purchase_reject_reason = fields.Char("Purchase Rejected Reason")
    reject_user_id = fields.Many2one('res.users', string="Rejected By")
    po_reject_user_id = fields.Many2one('res.users', string="Rejected By")
    picking_count = fields.Integer("Picking Cont", compute='_picking_count')
    check_product=fields.Boolean(compute='_check_product')
    po_count = fields.Integer(string="Purchase Order Count", compute='_po_count')
    picking_ids = fields.One2many('stock.picking', 'material_request_id', string="Pickings")
    check_boolean = fields.Boolean(default=True)
    purchase_boolean = fields.Boolean()
    department_id = fields.Many2one('hr.department',string='Department', compute='_compute_department_id', store=True )
    sub_department_id = fields.Many2one('material.request.configuration', string='Sub Department', ondelete='set null',  domain="[('is_sub_department','=',True), ('department_id', '=', department_id)]",)
    location_dest_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        compute='_compute_location_dest_id',
        store=True,
        readonly=False,
        domain="[('usage','=','internal'), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        check_company=True,
    )
    approval_line_ids = fields.One2many('material.request.configuration', 'material_request_id', string="Pickings")
    show_approve_button = fields.Boolean(compute='_compute_show_approve_button')
    is_product_available = fields.Boolean(copy=False)
    is_mixed_availability = fields.Boolean(copy=False)
    product_available_location = fields.Many2one('stock.location', string="Product Available Location", domain="[('stock_location', '=', True)]")
    show_remaining_transfer = fields.Boolean(compute='_compute_show_remaining_transfer')
    is_delivery_created  = fields.Boolean(copy=False)
    is_none_qty  = fields.Boolean(copy=False)
    is_transfer_complete = fields.Boolean(compute='_compute_is_transfer_complete')

    @api.depends('request_line_ids.is_transfer_complete')
    def _compute_is_transfer_complete(self):
        for rec in self:
            lines = rec.request_line_ids.filtered(lambda l: not l.display_type)
            rec.is_transfer_complete = all(lines.mapped('is_transfer_complete')) if lines else False
            
    def _compute_show_remaining_transfer(self):
        for rec in self:
            rec.show_remaining_transfer = any(line.line_state == 'received' for line in rec.request_line_ids)

    def _compute_show_approve_button(self):
        for rec in self:
            rec.show_approve_button = False

            if rec.state != 'request':
                continue

            current_line = rec.approval_line_ids.filtered(
                lambda l: not l.is_approved
            )[:1]

            if current_line and current_line.user_id == self.env.user:
                rec.show_approve_button = True


    @api.onchange('sub_department_id')
    def _onchange_populate_approval_lines(self):
        self.approval_line_ids = [(5, 0, 0)]
        if not self.sub_department_id:
            return
        config = self.sub_department_id.approval_line_id  # ✅ single record, no loop needed
        if not config:
            return
        approval_line_vals = []
        for user in config.user_ids:  # ✅ loop only users
            approval_line_vals.append((0, 0, {
                'name': user.name,
                'user_id': user.id,
                'approval_line_id': config.id,
            }))
        self.approval_line_ids = approval_line_vals

    @api.depends('sub_department_id')
    def _compute_location_dest_id(self):
        for rec in self:
            rec.location_id = rec.sub_department_id.location_id
            rec.location_dest_id = rec.sub_department_id.location_dest_id

    @api.depends('user_id')
    def _compute_department_id(self):
        employee_obj = self.env['hr.employee']
        for rec in self:
            employee = employee_obj.search(
                [('name', '=', rec.user_id.name)],
                limit=1
            )
            rec.department_id = employee.department_id


    # @api.onchange('request_line_ids.check_available')
    # def check_purchase_boolean(self):
    #     for rec in self:
    #         for record in rec.request_line_ids:
    #             if record.check_available == True:
    #                 rec.purchase_boolean =False
    #             else:
    #                 rec.purchase_boolean = True


    @api.onchange('department_id')
    def locate_location_dest(self):
        for rec in self:
            for record in rec.department_id:
                if record.dest_location_id:
                    rec.location_dest_id = record.dest_location_id
                else:
                    rec.location_dest_id = ''

    def action_purchase_reject(self):
        for rec in self:
            if not rec.purchase_reject_reason:
                raise UserError(_("Please enter the Purchase Rejected reason."))
            rec.update({'state': 'draft','po_reject_user_id': self.env.user.id })
            store_group = self.env.ref(  'mrp_material_request.group_material_request_store_user' )
            store_users = self.env['res.users'].sudo().search([('group_ids', 'in', [store_group.id]),('active', '=', True),])
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)
            for user in store_users:
                if not user.partner_id.email:
                    continue
                body_html = """
                <div style="font-family: Arial, sans-serif; margin: 0 auto;
                            border: 1px solid #c0c0c0; border-radius: 8px; overflow: hidden;">

                    <div style="background-color: #c62828; padding: 24px 32px;">
                        <h2 style="color: #ffffff; margin: 0; font-size: 20px;">
                            Purchase Request Rejected
                        </h2>
                    </div>

                    <div style="padding: 32px; background-color: #ffffff;">

                        <p style="color: #1a1a1a; font-size: 15px;">
                            Dear <strong>%s</strong>,
                        </p>

                        <p style="color: #444444; font-size: 14px; line-height: 1.6;">
                            The Purchase Team has reviewed the Material Request and
                            rejected the purchase request.
                            Please review the rejection details below.
                        </p>

                        <div style="background-color: #fdeaea;
                                    border-left: 4px solid #c62828;
                                    border-radius: 4px;
                                    padding: 16px 20px;
                                    margin: 20px 0;">

                            <table style="width:100%%; border-collapse: collapse;">

                                <tr>
                                    <td style="padding:6px 0; width:40%%;">
                                        Material Request
                                    </td>
                                    <td style="padding:6px 0;">
                                        <b>%s</b>
                                    </td>
                                </tr>

                                <tr>
                                    <td style="padding:6px 0;">
                                        Requested By
                                    </td>
                                    <td style="padding:6px 0;">
                                        <b>%s</b>
                                    </td>
                                </tr>

                                <tr>
                                    <td style="padding:6px 0;">
                                        Rejected By
                                    </td>
                                    <td style="padding:6px 0;">
                                        <b>%s</b>
                                    </td>
                                </tr>

                                <tr>
                                    <td style="padding:6px 0;">
                                        Rejected Date
                                    </td>
                                    <td style="padding:6px 0;">
                                        <b>%s</b>
                                    </td>
                                </tr>

                                <tr>
                                    <td style="padding:6px 0;">
                                        Rejection Reason
                                    </td>
                                    <td style="padding:6px 0;">
                                        <b>%s</b>
                                    </td>
                                </tr>

                            </table>

                        </div>

                        <div style="margin:24px 0;">
                            <a href="%s"
                               style="display:inline-block;
                                      background-color:#c62828;
                                      color:#ffffff;
                                      text-decoration:none;
                                      padding:10px 24px;
                                      border-radius:6px;
                                      font-weight:600;">
                                View Material Request &#8594;
                            </a>
                        </div>

                        <p style="color:#444444;font-size:14px;">
                            Thanks &amp; Regards,
                        </p>

                        <p style="color:#c62828;font-size:15px;font-weight:bold;">
                            %s
                        </p>

                    </div>

                    <div style="background-color:#c62828;
                                padding:16px 32px;
                                text-align:center;">

                        <p style="color:#ffdddd;font-size:12px;margin:0;">
                            This is an automated notification from
                            <strong style="color:#ffffff;">%s</strong>.
                        </p>

                    </div>

                </div>
                """ % (
                    user.name,
                    rec.name,
                    rec.user_id.name or '',
                    self.env.user.name,
                    fields.Date.today().strftime('%d-%m-%Y'),
                    rec.purchase_reject_reason or '',
                    base_url,
                    self.env.user.name,
                    rec.company_id.name or 'Odoo ERP'
                )

                self.env['mail.mail'].sudo().create({
                    'auto_delete': False,
                    'author_id': self.env.user.partner_id.id,
                    'email_from': (
                            rec.company_id.partner_id.email_formatted
                            or self.env.user.email_formatted
                            or self.env.ref('base.user_root').email_formatted
                    ),
                    'email_to': user.partner_id.email,
                    'subject': 'Purchase Request Rejected - %s' % rec.name,
                    'body_html': body_html,
                }).send()

    def action_view_stock_move(self):
        return {
            'res_model': 'stock.move.line',
            'type': 'ir.actions.act_window',
            'name': _("Stock Move Line"),
            'domain': [('mrp_material_request', '=', self.id)],
            'view_mode': 'list,form',
        }

    def check_available_stock(self):
        if not self.is_delivery_created:
            self.action_material_accept()
        partial_info = []
        
        for line in self.request_line_ids.filtered(lambda l: not l.display_type):
            available_qty = line.product_id.get_available_quantity(self.location_id)
            qty = line.product_uom._compute_quantity(line.quantity, line.product_id.uom_id)
            
            if qty > available_qty:
                all_available = False
                line.check_available = False
                line.line_state = 'unavailable'
                
                if available_qty > 0:
                    none_available = False
                    line.transfer_qty = available_qty
                    line.purchase_qty = qty - available_qty
                    partial_info.append(f"{line.product_id.name}: {available_qty}/{qty} available")
                else:
                    line.transfer_qty = 0
                    line.purchase_qty = qty
            else:
                none_available = False
                line.check_available = True
                line.line_state = 'available'
                line.transfer_qty = qty
                line.purchase_qty = 0
        self.is_delivery_created = True
        if not self.is_transfer_complete:
            self.action_purchase_manager_request()

    def action_partial_transfer(self):
        for rec in self:
            picking_id = self.env['stock.picking'].create({
                'picking_type_id': rec.picking_type_id.id,
                'location_id': rec.location_id.id,
                'location_dest_id': rec.location_dest_id.id,
                'company_id': rec.env.company.id,
                'material_request_id': rec.id,
                'origin': rec.name,
                'mrp_material_request': rec.id,
                'state': 'draft',
            })
            rec._send_material_sent_notification(picking_id)
            for line in rec.request_line_ids.filtered(lambda x: x.display_type == False and x.line_state == 'available'):
                self.env['stock.move'].create({
                    # 'name': line.product_id.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_uom.id,
                    'location_id': rec.location_id.id,
                    'location_dest_id': rec.location_dest_id.id,
                    'picking_id': picking_id.id,
                    'company_id': rec.company_id.id,
                    'origin': rec.name,
                    'quantity': line.quantity,
                    'mrp_material_request': rec.id,
                })
                # line.line_state = 'done'
            # picking_id.action_confirm()
            # self.state = 'purchase_request' # Wait for user to decide? Prompt says: "Create an internal transfer immediately for the available items"
            # After transfer, we keep lines editable for unavailable items.
            rec.state = 'purchase_request'

    def action_check_location_availability(self):
        if not self.product_available_location:
            raise UserError(_("Please select Product Available Location."))
        # Filter lines that were not available initially (need to check remainder)
        for line in self.request_line_ids.filtered(lambda l: l.line_state in ['unavailable', 'not_yet']):
            available_qty = line.product_id.get_available_quantity(self.product_available_location)
            # Check remaing quantity (purchase_qty) instead of total quantity
            qty_to_check = line.purchase_qty if line.purchase_qty > 0 else line.quantity
            qty = line.product_uom._compute_quantity(qty_to_check, line.product_id.uom_id)
            if qty <= available_qty:
                line.line_state = 'received'
                self.is_product_available = True
            else:
                raise UserError(_("Product %s not available in %s. Required: %s, Available: %s") % (
                    line.product_id.name, self.product_available_location.name, qty, available_qty
                ))

    def action_create_post_receipt_transfer(self):
        for rec in self:
            if not rec.product_available_location:
                raise UserError(_("Please select Product Available Location."))
            picking_id = self.env['stock.picking'].create({
                'picking_type_id': rec.picking_type_id.id,
                'location_id': rec.product_available_location.id,
                'location_dest_id': rec.location_dest_id.id,
                'company_id': rec.env.company.id,
                'material_request_id': rec.id,
                'origin': rec.name,
                'mrp_material_request': rec.id,
                'state': 'draft',
            })
            rec._send_material_sent_notification(picking_id)

            lines_to_transfer = rec.request_line_ids.filtered(lambda l: l.line_state == 'received')
            for line in lines_to_transfer:
                qty_to_transfer = line.purchase_qty if line.purchase_qty > 0 else line.quantity
                self.env['stock.move'].create({
                    'product_id': line.product_id.id,
                    # 'name': line.product_id.name,
                    'product_uom_qty': qty_to_transfer,
                    'product_uom': line.product_uom.id,
                    'location_id': rec.product_available_location.id,
                    'location_dest_id': rec.location_dest_id.id,
                    'picking_id': picking_id.id,
                    'company_id': rec.company_id.id,
                    'origin': rec.name,
                    'quantity': qty_to_transfer,
                    'mrp_material_request': rec.id,
                })
                # line.line_state = 'done'

            # If all lines are done, set MR to done
              # or move to material_accept if items are being accepted.

    def _check_product(self):
        for rec in self:
            rec.check_product = True
            for line in rec.request_line_ids:
                if line.check_available == True:
                     rec.check_product =False
                else:
                    rec.check_product = True

    def _picking_count(self):
        for rec in self:
            rec.picking_count = len(rec.picking_ids)

    def action_view_picking(self):
        self.ensure_one()
        pickings = self.picking_ids

        result = self.env["ir.actions.actions"]._for_xml_id('stock.action_picking_tree_all')

        # Remove create defaults — just VIEW, no new record context
        result['context'] = {
            'create': False,
            'delete': False,
            'duplicate': False,
        }

        if not pickings:
            # No pickings at all — return empty list view
            result['domain'] = [('id', 'in', [])]

        elif len(pickings) == 1:
            # Single picking — open form directly
            res = self.env.ref('stock.view_picking_form', False)
            form_view = [(res and res.id or False, 'form')]
            result['views'] = form_view + [
                (state, view)
                for state, view in result.get('views', [])
                if view != 'form'
            ]
            result['res_id'] = pickings.id
            result['domain'] = [('id', '=', pickings.id)]

        else:
            # Multiple pickings — open list filtered
            result['domain'] = [('id', 'in', pickings.ids)]

        return result

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if 'name' not in vals or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('mrp.material.request') or _('New')
        return super(MrpMaterialRequest, self).create(vals_list)

    @api.onchange('operation_id')
    def onchange_operation(self):
        if self.operation_id:
            self.location_dest_id = self.operation_id.location_src_id.id



    @api.onchange('picking_type_id')
    def onchange_operation(self):
        if self.picking_type_id:
            self.location_dest_id = self.picking_type_id.default_location_src_id.id

    def action_request(self):
        if not self.sub_department_id:
            raise UserError('Please Select the Sub Department')
        if not self.responsible_user_id:
            raise UserError('Please Select the Responsible')
        if not self.picking_type_id:
            raise UserError(_("Picking type not available"))
        if not self.location_id:
            raise UserError(_("Please Select the Source Location"))
        if not self.request_line_ids:
            raise UserError(_("Please enter products."))
        for rec in self.request_line_ids:
            if not rec.quantity:
                raise UserError(_("Please enter quantity."))
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (self.id, self._name)

        for rec in self:
            first_approval = rec.approval_line_ids.filtered(
                lambda l: not l.is_email_sent
            )[:1]

            if not first_approval:
                raise UserError(_("Approval line not configured."))

            manager = first_approval.user_id

            if manager.partner_id.email:
                body_html = """
                <div style="font-family: Arial, sans-serif; margin: 0 auto; 
                            border: 1px solid #c0c0c0; border-radius: 8px; overflow: hidden;">

                    <!-- Header -->
                    <div style="background-color: #2C1A47; padding: 24px 32px;">
                        <h2 style="color: #ffffff; margin: 0; font-size: 20px; letter-spacing: 0.5px;">
                            Material Request Approval
                        </h2>
                    </div>

                    <!-- Body -->
                    <div style="padding: 32px; background-color: #ffffff;">
                        <p style="color: #1a1a1a; font-size: 15px; margin-top: 0;">
                            Dear <strong>%s</strong>,
                        </p>
                        <p style="color: #444444; font-size: 14px; line-height: 1.6;">
                            A new material request has been submitted and is pending your approval.
                            Please review the details below:
                        </p>

                        <!-- Info Card -->
                        <div style="background-color: #f0ebf5; border-left: 4px solid #2C1A47; 
                                    border-radius: 4px; padding: 16px 20px; margin: 20px 0;">
                            <table style="width: 100%%; border-collapse: collapse;">
                                <tr>
                                    <td style="color: #555555; font-size: 13px; padding: 6px 0; width: 40%%;">
                                        Reference
                                    </td>
                                    <td style="color: #1a1a1a; font-size: 13px; font-weight: bold; padding: 6px 0;">
                                        %s
                                    </td>
                                </tr>
                                <tr>
                                    <td style="color: #555555; font-size: 13px; padding: 6px 0;">
                                        Requested By
                                    </td>
                                    <td style="color: #1a1a1a; font-size: 13px; font-weight: bold; padding: 6px 0;">
                                        %s
                                    </td>
                                </tr>
                                <tr>
                                    <td style="color: #555555; font-size: 13px; padding: 6px 0;">
                                        Responsible User
                                    </td>
                                    <td style="color: #1a1a1a; font-size: 13px; font-weight: bold; padding: 6px 0;">
                                        %s
                                    </td>
                                </tr>
                                <tr>
                                    <td style="color: #555555; font-size: 13px; padding: 6px 0;">
                                        Department
                                    </td>
                                    <td style="color: #1a1a1a; font-size: 13px; font-weight: bold; padding: 6px 0;">
                                        %s
                                    </td>
                                </tr>
                                <tr>
                                    <td style="color: #555555; font-size: 13px; padding: 6px 0;">
                                        Request Date
                                    </td>
                                    <td style="color: #1a1a1a; font-size: 13px; font-weight: bold; padding: 6px 0;">
                                        %s
                                    </td>
                                </tr>
                            </table>
                        </div>

                        <!-- View Form Button -->
                        <div style="margin: 24px 0 8px 0;">
                            <a href="%s"
                               style="display: inline-block; background-color: #1a6b3a; color: #ffffff;
                                      text-decoration: none; font-size: 13px; font-weight: 600;
                                      padding: 10px 24px; border-radius: 6px; letter-spacing: 0.02em;">
                                View Form &#8594;
                            </a>
                        </div>

                        <!-- Thanks & Regards -->
                        <p style="color: #444444; font-size: 14px; margin-top: 24px; margin-bottom: 4px;">
                            Thanks &amp; Regards,
                        </p>
                        <p style="color: #2C1A47; font-size: 15px; font-weight: bold; margin: 0;">
                            %s
                        </p>
                    </div>

                    <!-- Footer -->
                    <div style="background-color: #2C1A47; padding: 16px 32px; 
                                border-top: 1px solid #1a0f2e; text-align: center;">
                        <p style="color: #cccccc; font-size: 12px; margin: 0;">
                            This is an automated notification from <strong style="color: #ffffff;">%s</strong>.
                        </p>
                    </div>

                </div>
                """ % (
                    manager.name,  # Dear
                    rec.name,  # Reference
                    rec.env.user.name,  # Requested By
                    rec.responsible_user_id.name or '',  # Responsible User
                    rec.department_id.name or '',  # Department
                    rec.create_date.strftime('%d-%m-%Y') if rec.create_date else '',  # Request Date
                    base_url,  # ✅ View Form button href
                    self.env.user.name,  # Thanks & Regards
                    rec.company_id.name or 'Odoo ERP',  # Footer
                )

                mail_values = {
                    'auto_delete': False,
                    'author_id': self.env.user.partner_id.id,
                    'email_from': (
                            rec.company_id.partner_id.email_formatted
                            or self.env.user.email_formatted
                            or self.env.ref('base.user_root').email_formatted
                    ),
                    'email_to': manager.partner_id.email_formatted,
                    'body_html': body_html,
                    'subject': 'Approval Required: Material Request %s' % rec.name,
                }
                self.env['mail.mail'].sudo().create(mail_values).send()
                first_approval.write({
                    'is_email_sent': True
                })
            rec.update({'state': 'request'})

    def action_manager_approve(self):
        for rec in self:
            # Current approver line
            current_line = rec.approval_line_ids.filtered(
                lambda l: l.user_id.id == self.env.user.id
            )[:1]

            if current_line:
                current_line.write({
                    'is_approved': True,
                })

            # Find next approver
            next_line = rec.approval_line_ids.filtered(
                lambda l: not l.is_email_sent
            )[:1]

            # If next approver exists send next approval mail
            if next_line:
                manager = next_line.user_id
                next_line.write({
                    'is_email_sent': True
                })
                if manager.partner_id.email:
                    base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                    base_url += '/web#id=%d&view_type=form&model=%s' % (rec.id, rec._name)

                    body_html = """
                                  <div style="font-family: Arial, sans-serif; margin: 0 auto; 
                                              border: 1px solid #c0c0c0; border-radius: 8px; overflow: hidden;">

                                      <!-- Header -->
                                      <div style="background-color: #2C1A47; padding: 24px 32px;">
                                          <h2 style="color: #ffffff; margin: 0; font-size: 20px; letter-spacing: 0.5px;">
                                              Material Request Approval
                                          </h2>
                                      </div>

                                      <!-- Body -->
                                      <div style="padding: 32px; background-color: #ffffff;">
                                          <p style="color: #1a1a1a; font-size: 15px; margin-top: 0;">
                                              Dear <strong>%s</strong>,
                                          </p>
                                          <p style="color: #444444; font-size: 14px; line-height: 1.6;">
                                              A new material request has been submitted and is pending your approval.
                                              Please review the details below:
                                          </p>

                                          <!-- Info Card -->
                                          <div style="background-color: #f0ebf5; border-left: 4px solid #2C1A47; 
                                                      border-radius: 4px; padding: 16px 20px; margin: 20px 0;">
                                              <table style="width: 100%%; border-collapse: collapse;">
                                                  <tr>
                                                      <td style="color: #555555; font-size: 13px; padding: 6px 0; width: 40%%;">
                                                          Reference
                                                      </td>
                                                      <td style="color: #1a1a1a; font-size: 13px; font-weight: bold; padding: 6px 0;">
                                                          %s
                                                      </td>
                                                  </tr>
                                                  <tr>
                                                      <td style="color: #555555; font-size: 13px; padding: 6px 0;">
                                                          Requested By
                                                      </td>
                                                      <td style="color: #1a1a1a; font-size: 13px; font-weight: bold; padding: 6px 0;">
                                                          %s
                                                      </td>
                                                  </tr>
                                                  <tr>
                                                      <td style="color: #555555; font-size: 13px; padding: 6px 0;">
                                                          Responsible User
                                                      </td>
                                                      <td style="color: #1a1a1a; font-size: 13px; font-weight: bold; padding: 6px 0;">
                                                          %s
                                                      </td>
                                                  </tr>
                                                  <tr>
                                                      <td style="color: #555555; font-size: 13px; padding: 6px 0;">
                                                          Department
                                                      </td>
                                                      <td style="color: #1a1a1a; font-size: 13px; font-weight: bold; padding: 6px 0;">
                                                          %s
                                                      </td>
                                                  </tr>
                                                  <tr>
                                                      <td style="color: #555555; font-size: 13px; padding: 6px 0;">
                                                          Request Date
                                                      </td>
                                                      <td style="color: #1a1a1a; font-size: 13px; font-weight: bold; padding: 6px 0;">
                                                          %s
                                                      </td>
                                                  </tr>
                                              </table>
                                          </div>

                                          <!-- View Form Button -->
                                          <div style="margin: 24px 0 8px 0;">
                                              <a href="%s"
                                                 style="display: inline-block; background-color: #1a6b3a; color: #ffffff;
                                                        text-decoration: none; font-size: 13px; font-weight: 600;
                                                        padding: 10px 24px; border-radius: 6px; letter-spacing: 0.02em;">
                                                  View Form &#8594;
                                              </a>
                                          </div>

                                          <!-- Thanks & Regards -->
                                          <p style="color: #444444; font-size: 14px; margin-top: 24px; margin-bottom: 4px;">
                                              Thanks &amp; Regards,
                                          </p>
                                          <p style="color: #2C1A47; font-size: 15px; font-weight: bold; margin: 0;">
                                              %s
                                          </p>
                                      </div>

                                      <!-- Footer -->
                                      <div style="background-color: #2C1A47; padding: 16px 32px; 
                                                  border-top: 1px solid #1a0f2e; text-align: center;">
                                          <p style="color: #cccccc; font-size: 12px; margin: 0;">
                                              This is an automated notification from <strong style="color: #ffffff;">%s</strong>.
                                          </p>
                                      </div>

                                  </div>
                                  """ % (
                        manager.name,  # Dear
                        rec.name,  # Reference
                        rec.env.user.name,  # Requested By
                        rec.responsible_user_id.name or '',  # Responsible User
                        rec.department_id.name or '',  # Department
                        rec.create_date.strftime('%d-%m-%Y') if rec.create_date else '',  # Request Date
                        base_url,  # ✅ View Form button href
                        self.env.user.name,  # Thanks & Regards
                        rec.company_id.name or 'Odoo ERP',  # Footer
                    )

                    mail_values = {
                        'auto_delete': False,
                        'author_id': self.env.user.partner_id.id,
                        'email_from': (
                                rec.company_id.partner_id.email_formatted
                                or self.env.user.email_formatted
                                or self.env.ref('base.user_root').email_formatted
                        ),
                        'email_to': manager.partner_id.email_formatted,
                        'body_html': body_html,
                        'subject': 'Approval Required: Material Request %s' % rec.name,
                    }

                    self.env['mail.mail'].sudo().create(mail_values).send()

                # Wait for next approver
                return

            # ====================================================
            # NO NEXT APPROVER
            # SEND FINAL APPROVAL MAIL TO REQUESTER
            # ====================================================

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (rec.id, rec._name)
            body_html = """
               <div style="font-family: Arial, sans-serif; margin: 0 auto; 
                           border: 1px solid #c0c0c0; border-radius: 8px; overflow: hidden;">

                   <!-- Header -->
                   <div style="background-color: #1a6b3c; padding: 24px 32px;">
                       <h2 style="color: #ffffff; margin: 0; font-size: 20px; letter-spacing: 0.5px;">
                           Material Request Approved
                       </h2>
                   </div>

                   <!-- Body -->
                   <div style="padding: 32px; background-color: #ffffff;">
                       <p style="color: #1a1a1a; font-size: 15px; margin-top: 0;">
                           Dear <strong>%s</strong>,
                       </p>
                       <p style="color: #444444; font-size: 14px; line-height: 1.6;">
                           We are pleased to inform you that your material request has been 
                           <strong style="color: #1a6b3c;">approved</strong> by the manager.
                           Please find the details below:
                       </p>

                       <!-- Info Card -->
                       <div style="background-color: #edf7f1; border-left: 4px solid #1a6b3c; 
                                   border-radius: 4px; padding: 16px 20px; margin: 20px 0;">
                           <table style="width: 100%%; border-collapse: collapse;">
                               <tr>
                                   <td style="color: #555555; font-size: 13px; padding: 6px 0; width: 40%%;">
                                       Reference
                                   </td>
                                   <td style="color: #1a1a1a; font-size: 13px; font-weight: bold; padding: 6px 0;">
                                       %s
                                   </td>
                               </tr>
                               <tr>
                                   <td style="color: #555555; font-size: 13px; padding: 6px 0;">
                                       Approved By
                                   </td>
                                   <td style="color: #1a1a1a; font-size: 13px; font-weight: bold; padding: 6px 0;">
                                       %s
                                   </td>
                               </tr>
                               <tr>
                                   <td style="color: #555555; font-size: 13px; padding: 6px 0;">
                                       Approved Date
                                   </td>
                                   <td style="color: #1a1a1a; font-size: 13px; font-weight: bold; padding: 6px 0;">
                                       %s
                                   </td>
                               </tr>
                           </table>
                       </div>

                       <!-- View Form Button -->
                       <div style="margin: 24px 0 8px 0;">
                           <a href="%s"
                              style="display: inline-block; background-color: #1a6b3c; color: #ffffff;
                                     text-decoration: none; font-size: 13px; font-weight: 600;
                                     padding: 10px 24px; border-radius: 6px; letter-spacing: 0.02em;">
                               View Form &#8594;
                           </a>
                       </div>

                       <!-- Thanks & Regards -->
                       <p style="color: #444444; font-size: 14px; margin-top: 24px; margin-bottom: 4px;">
                           Thanks &amp; Regards,
                       </p>
                       <p style="color: #1a6b3c; font-size: 15px; font-weight: bold; margin: 0;">
                           %s
                       </p>
                   </div>

                   <!-- Footer -->
                   <div style="background-color: #1a6b3c; padding: 16px 32px; 
                               border-top: 1px solid #145530; text-align: center;">
                       <p style="color: #ccffdd; font-size: 12px; margin: 0;">
                           This is an automated notification from <strong style="color: #ffffff;">%s</strong>.
                       </p>
                   </div>

               </div>
                       """ % (
                rec.user_id.name or 'Sir/Madam',  # Dear
                rec.name,  # Reference
                rec.env.user.name or '',  # Approved By
                fields.Date.today().strftime('%d-%m-%Y'),  # Approved Date
                base_url,  # ✅ View Form button href
                self.env.user.name,  # Thanks & Regards
                rec.company_id.name or 'Odoo ERP',  # Footer
            )
            mail_values = {
                'auto_delete': False,
                'author_id': self.env.user.partner_id.id,
                'email_from': (
                        rec.company_id.partner_id.email_formatted
                        or self.env.user.email_formatted
                        or self.env.ref('base.user_root').email_formatted
                ),
                'email_to': rec.user_id.partner_id.email_formatted,
                'body_html': body_html,
                'subject': 'Approval Confirmation: Material Request %s' % rec.name,
            }

            self.env['mail.mail'].sudo().create(mail_values).send()

            # ====================================================
            # STORE USER MAIL
            # ====================================================
            store_group = self.env.ref(
                'mrp_material_request.group_material_request_store_user'
            )
            store_users = self.env['res.users'].sudo().search([
                ('group_ids', 'in', [store_group.id]),
                ('active', '=', True),
            ])

            for user in store_users:
                if not user.partner_id.email:
                    continue

                body_html = """

                <div style="font-family: Arial, sans-serif; margin: 0 auto;
                            border: 1px solid #c0c0c0; border-radius: 8px; overflow: hidden;">
                <!-- Header -->
                <div style="background-color: #1a6b3c; padding: 24px 32px;">
                    <h2 style="color: #ffffff; margin: 0; font-size: 20px; letter-spacing: 0.5px;">
                        Material Request Ready For Store Process
                    </h2>
                </div>

                <!-- Body -->
                <div style="padding: 32px; background-color: #ffffff;">
                    <p style="color: #1a1a1a; font-size: 15px; margin-top: 0;">
                        Dear <strong>%s</strong>,
                    </p>

                    <p style="color: #444444; font-size: 14px; line-height: 1.6;">
                        Material Request <strong>%s</strong> has completed all approval levels.
                        Kindly proceed with the store processing.
                    </p>

                    <!-- Info Card -->
                    <div style="background-color: #edf7f1; border-left: 4px solid #1a6b3c;
                                border-radius: 4px; padding: 16px 20px; margin: 20px 0;">
                        <table style="width: 100%%; border-collapse: collapse;">
                            <tr>
                                <td style="color: #555555; font-size: 13px; padding: 6px 0; width: 40%%;">
                                    Reference
                                </td>
                                <td style="color: #1a1a1a; font-size: 13px; font-weight: bold; padding: 6px 0;">
                                    %s
                                </td>
                            </tr>

                            <tr>
                                <td style="color: #555555; font-size: 13px; padding: 6px 0;">
                                    Requested By
                                </td>
                                <td style="color: #1a1a1a; font-size: 13px; font-weight: bold; padding: 6px 0;">
                                    %s
                                </td>
                            </tr>

                            <tr>
                                <td style="color: #555555; font-size: 13px; padding: 6px 0;">
                                    Approval Completed Date
                                </td>
                                <td style="color: #1a1a1a; font-size: 13px; font-weight: bold; padding: 6px 0;">
                                    %s
                                </td>
                            </tr>
                        </table>
                    </div>

                    <!-- View Form Button -->
                    <div style="margin: 24px 0 8px 0;">
                        <a href="%s"
                           style="display: inline-block; background-color: #1a6b3c; color: #ffffff;
                                  text-decoration: none; font-size: 13px; font-weight: 600;
                                  padding: 10px 24px; border-radius: 6px; letter-spacing: 0.02em;">
                            View Form &#8594;
                        </a>
                    </div>

                    <!-- Thanks -->
                    <p style="color: #444444; font-size: 14px; margin-top: 24px; margin-bottom: 4px;">
                        Thanks &amp; Regards,
                    </p>

                    <p style="color: #1a6b3c; font-size: 15px; font-weight: bold; margin: 0;">
                        %s
                    </p>
                </div>

                <!-- Footer -->
                <div style="background-color: #1a6b3c; padding: 16px 32px;
                            border-top: 1px solid #145530; text-align: center;">
                    <p style="color: #ccffdd; font-size: 12px; margin: 0;">
                        This is an automated notification from
                        <strong style="color: #ffffff;">%s</strong>.
                    </p>
                </div>
                ```

                </div>
                """ % (
                    user.name,
                    rec.name,
                    rec.name,
                    rec.user_id.name or '',
                    fields.Date.today().strftime('%d-%m-%Y'),
                    base_url,
                    self.env.user.name,
                    rec.company_id.name or 'Odoo ERP'
                )

                self.env['mail.mail'].sudo().create({
                    'auto_delete': False,
                    'author_id': self.env.user.partner_id.id,
                    'email_from': (
                            rec.company_id.partner_id.email_formatted
                            or self.env.user.email_formatted
                            or self.env.ref('base.user_root').email_formatted
                    ),
                    'email_to': user.partner_id.email_formatted,
                    'subject': 'Material Request Ready For Store Process - %s' % rec.name,
                    'body_html': body_html,
                }).send()
            rec.update({
                'state': 'manager_approve'
            })

     # if any(record.picking_type_id.sequence_code == 'INT' and record.state != 'done'
     #               for record in rec.picking_ids):
     #            rec.picking_ids.button_validate()
     #
     #        rec.action_create_delivery()


    def action_purchase_approve(self):
        for rec in self:
            rec.update({'state': 'purchase_approve'})

    def action_purchase_manager_request(self):
        for rec in self:
            # Allow manager request if it's Flow 3 (is_mixed_availability) or if nothing is available
            if rec.purchase_boolean:
                raise ValidationError(_("Check the availability first.") )
            purchase_group = self.env.ref('purchase.group_purchase_manager', raise_if_not_found=False )
            if not purchase_group:
                raise UserError(_("Purchase Manager group not found."))
            purchase_users = self.env['res.users'].sudo().search([('group_ids', 'in', [purchase_group.id]), ('active', '=', True),])
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % ( rec.id,rec._name)
            for user in purchase_users:
                if not user.partner_id.email:
                    continue
                body_html = """
                <div style="font-family: Arial, sans-serif; margin: 0 auto;
                            border: 1px solid #c0c0c0; border-radius: 8px; overflow: hidden;">
                    <div style="background-color: #2C1A47; padding: 24px 32px;">
                        <h2 style="color: #ffffff; margin: 0;">
                            Purchase Approval Required
                        </h2>
                    </div>
                    <div style="padding: 32px; background-color: #ffffff;">
                        <p>
                            Dear <strong>%s</strong>,
                        </p>
                        <p>
                            Material Request has been forwarded to the Purchase Team
                            for procurement approval. Please review the request details below.
                        </p>
                        <div style="background-color: #f0ebf5;
                                    border-left: 4px solid #2C1A47;
                                    padding: 16px 20px;
                                    margin: 20px 0;">
                            <table style="width:100%%;">
                                <tr>
                                    <td width="40%%">Reference</td>
                                    <td><b>%s</b></td>
                                </tr>
                                <tr>
                                    <td>Requested By</td>
                                    <td><b>%s</b></td>
                                </tr>
                                <tr>
                                    <td>Department</td>
                                    <td><b>%s</b></td>
                                </tr>
                                <tr>
                                    <td>Request Date</td>
                                    <td><b>%s</b></td>
                                </tr>
                            </table>
                        </div>
                        <p>
                            <a href="%s"
                               style="background:#1a6b3c;
                                      color:#ffffff;
                                      text-decoration:none;
                                      padding:10px 20px;
                                      border-radius:5px;">
                                View Form →
                            </a>
                        </p>
                        <p>Thanks &amp; Regards,</p>
                        <p>
                            <strong>%s</strong>
                        </p>
                    </div>

                    <div style="background-color:#2C1A47;
                                padding:16px;
                                text-align:center;">

                        <p style="color:#cccccc;margin:0;">
                            This is an automated notification from
                            <strong style="color:#ffffff;">%s</strong>.
                        </p>

                    </div>

                </div>
                """ % (
                    user.name,
                    rec.name,
                    rec.user_id.name or '',
                    rec.department_id.name or '',
                    fields.Date.today().strftime('%d-%m-%Y'),
                    base_url,
                    self.env.user.name,
                    rec.company_id.name or 'Odoo ERP'
                )

                self.env['mail.mail'].sudo().create({
                    'auto_delete': False,
                    'author_id': self.env.user.partner_id.id,
                    'email_from': (
                            rec.company_id.partner_id.email_formatted
                            or self.env.user.email_formatted
                            or self.env.ref('base.user_root').email_formatted
                    ),
                    'email_to': user.partner_id.email,
                    'subject': 'Purchase Approval Required - %s' % rec.name,
                    'body_html': body_html,
                }).send()
            rec.state = 'purchase_request'

    def action_material_accept(self):
        for rec in self:
            stock = self.env['stock.location'].search([('consumed_location', '=', True)], limit=1)
            picking_id = self.env['stock.picking'].create({
                'picking_type_id': rec.picking_type_id.id,
                'location_id': rec.location_id.id,
                'location_dest_id': stock.id if rec.is_consumed else rec.location_dest_id.id,
                'company_id': rec.env.company.id,
                'material_request_id': rec.id,
                'origin': rec.name,
                'mrp_material_request': rec.id,
                'state': 'draft',
            })
            # rec._send_material_sent_notification(picking_id)
            for line in rec.request_line_ids:
                self.env['stock.move'].create({
                    'description_picking': line.product_id.display_name,
                    'reference': rec.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_uom.id,
                    'location_id': rec.location_id.id,
                    'location_dest_id': stock.id if rec.is_consumed else rec.location_dest_id.id,
                    'picking_id': picking_id.id,
                    'company_id': rec.company_id.id,
                    'origin': rec.origin,
                    'mrp_material_request': rec.id,
                })

            # rec.update({'state': 'material_accept'})


    def action_material_reject(self):
        for rec in self:
            # if any(record.picking_type_id.sequence_code == 'INT' and record.state != 'done' for record in
            #        rec.picking_ids):
            #     raise ValidationError("The Material is not received from store. so kindly validate the delivery")
            # for record in rec.picking_ids.filtered(lambda x: x.picking_type_id.sequence_code == 'INT'):
            #     return {
            #         'name': _('Reverse Transfer'),
            #         'type': 'ir.actions.act_window',
            #         'view_mode': 'form',
            #         'res_model': 'stock.return.picking',
            #         'target': 'new',
            #         'context': {
            #             'default_picking_id': record.id,
            #             'default_return_value': rec.id,
            #         },
            #
            #     }
            rec.update({'state': 'material_reject'})

    def action_reject(self):
        for rec in self:
            if not rec.reject_reason:
                raise UserError(_("Please enter the rejection reason."))

            rec.update({
                'state': 'reject',
                'reject_user_id': self.env.user.id
            })

            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            base_url += '/web#id=%d&view_type=form&model=%s' % (rec.id, rec._name)

            body_html = """
            <div style="font-family: Arial, sans-serif; margin: 0 auto;
                        border: 1px solid #c0c0c0; border-radius: 8px; overflow: hidden;">

                <!-- Header -->
                <div style="background-color: #c62828; padding: 24px 32px;">
                    <h2 style="color: #ffffff; margin: 0; font-size: 20px;">
                        Material Request Rejected
                    </h2>
                </div>

                <!-- Body -->
                <div style="padding: 32px; background-color: #ffffff;">
                    <p style="color: #1a1a1a; font-size: 15px;">
                        Dear <strong>%s</strong>,
                    </p>

                    <p style="color: #444444; font-size: 14px; line-height: 1.6;">
                        We regret to inform you that your material request has been
                        <strong style="color: #c62828;">rejected</strong>.
                        Please find the details below:
                    </p>

                    <!-- Info Card -->
                    <div style="background-color: #fdeaea;
                                border-left: 4px solid #c62828;
                                border-radius: 4px;
                                padding: 16px 20px;
                                margin: 20px 0;">

                        <table style="width:100%%; border-collapse: collapse;">
                            <tr>
                                <td style="padding:6px 0;width:40%%;">Reference</td>
                                <td style="padding:6px 0;"><b>%s</b></td>
                            </tr>

                            <tr>
                                <td style="padding:6px 0;">Rejected By</td>
                                <td style="padding:6px 0;"><b>%s</b></td>
                            </tr>

                            <tr>
                                <td style="padding:6px 0;">Rejected Date</td>
                                <td style="padding:6px 0;"><b>%s</b></td>
                            </tr>

                            <tr>
                                <td style="padding:6px 0;">Rejection Reason</td>
                                <td style="padding:6px 0;"><b>%s</b></td>
                            </tr>
                        </table>

                    </div>

                    <!-- View Form Button -->
                    <div style="margin:24px 0;">
                        <a href="%s"
                           style="display:inline-block;
                                  background-color:#c62828;
                                  color:#ffffff;
                                  text-decoration:none;
                                  padding:10px 24px;
                                  border-radius:6px;
                                  font-weight:600;">
                            View Form &#8594;
                        </a>
                    </div>

                    <!-- Thanks -->
                    <p style="color:#444444;font-size:14px;">
                        Thanks &amp; Regards,
                    </p>

                    <p style="color:#c62828;font-size:15px;font-weight:bold;">
                        %s
                    </p>
                </div>

                <!-- Footer -->
                <div style="background-color:#c62828;
                            padding:16px 32px;
                            text-align:center;">
                    <p style="color:#ffdddd;font-size:12px;margin:0;">
                        This is an automated notification from
                        <strong style="color:#ffffff;">%s</strong>.
                    </p>
                </div>

            </div>
            """ % (
                rec.user_id.name or 'Sir/Madam',
                rec.name,
                self.env.user.name,
                fields.Date.today().strftime('%d-%m-%Y'),
                rec.reject_reason or '',
                base_url,
                self.env.user.name,
                rec.company_id.name or 'Odoo ERP'
            )

            mail_values = {
                'auto_delete': False,
                'author_id': self.env.user.partner_id.id,
                'email_from': (
                        rec.company_id.partner_id.email_formatted
                        or self.env.user.email_formatted
                        or self.env.ref('base.user_root').email_formatted
                ),
                'email_to': rec.user_id.partner_id.email_formatted,
                'body_html': body_html,
                'subject': 'Material Request Rejected - %s' % rec.name,
            }

            self.env['mail.mail'].sudo().create(mail_values).send()

    def action_confirm(self):
        for rec in self:
            rec.update({'state': 'confirm'})

    def action_check_available(self):
        for rec in self:
            for line in rec.request_line_ids.filtered(lambda l: l.product_id):
                stock_quant = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', rec.location_dest_id.id),
                ])
                available_quantity = sum(stock_quant.mapped('quantity'))
                # line.available_qty = available_quantity
                if available_quantity >= line.quantity:
                    line.check_available = True
                else:
                    line.check_available = False

    def action_create_delivery(self):
        for rec in self:
            picking_id = self.env['stock.picking'].create({
                'picking_type_id': rec.picking_type_id.id,
                'location_id': rec.location_id.id,
                'location_dest_id': rec.temporary_location.id,
                'company_id': rec.env.company.id,
                'material_request_id': rec.id,
                'origin': rec.name,
                'mrp_material_request': rec.id,
                'state': 'draft',

            })
            for line in rec.request_line_ids.filtered(lambda x: x.display_type==False):
                self.env['stock.move'].create({
                    'description_picking': rec.name,  # optional, for display
                    'reference': rec.name,
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.quantity,
                    'product_uom': line.product_uom.id,
                    'location_id': rec.location_id.id,
                    'location_dest_id': rec.temporary_location.id,
                    'picking_id': picking_id.id,
                    'company_id': rec.company_id.id,
                    'origin': rec.origin,
                    'quantity':line.quantity,
                    'mrp_material_request': rec.id,
                })

    def action_done(self):
        stock_pick = self.env['stock.picking'].search([("origin", '=', self.name),("state", '!=', "done")])
        if stock_pick and stock_pick.state != 'done':
            stock_pick.action_confirm()
            stock_pick.button_validate()
        for rec in self:
            pickings = self.picking_ids
            for pick in pickings:
                if pick.state not in ['done', 'cancel']:
                    raise UserError(_("Please Complete/Cancel delivery to done this request."))
            rec.update({'state': 'done'})
            rec.date_issued = fields.Date.today()

    def action_cancel(self):
        for rec in self:
            pickings = self.picking_ids
            for pick in pickings:
                if pick.state == 'done':
                    raise UserError(_("Transfer has been completed. You cannot cancel this request."))
                if pick.state not in ['cancel']:
                    raise UserError(_("Please cancel the transfer to cancel this request."))
            rec.update({'state': 'cancel'})

    def action_set_to_draft(self):
        for rec in self:
            rec.update({'state': 'draft'})

    def action_raise_po(self):
        self.state = 'purchase_approve'
        lines_to_process = self.request_line_ids.filtered(lambda l: l.line_state == 'unavailable' and not l.display_type)
        if not lines_to_process:
             lines_to_process = self.request_line_ids.filtered(lambda l: not l.display_type)
        if not lines_to_process:
            return
        # Group lines by vendor
        vendors = lines_to_process.mapped('vendor_id')
        if not vendors or any(not v for v in vendors):
            raise UserError(_("Please select vendor in all relevant request lines."))

        for vendor in vendors:
            vendor_lines = lines_to_process.filtered(lambda l: l.vendor_id == vendor)
            fpos = self.env['account.fiscal.position'].sudo()._get_fiscal_position(vendor)

            order = self.env['purchase.order'].create({
                'partner_id': vendor.id,
                'fiscal_position_id': fpos.id if fpos else False,
                'payment_term_id': vendor.property_supplier_payment_term_id.id or False,
                'company_id': self.company_id.id,
                'currency_id': self.company_id.currency_id.id,
                'origin': self.name,
                'partner_ref': self.name,
                'date_order': fields.Datetime.now(),
                'material_request_id': self.id,
            })

            for line in vendor_lines:
                seller = line.product_id.seller_ids.filtered(
                    lambda s: s.partner_id.id == vendor.id
                )

                price_unit = seller[:1].price if seller else 0.0

                qty_to_purchase = line.purchase_qty if line.purchase_qty > 0 else line.quantity
                self.env['purchase.order.line'].create({
                    'name': line.name or line.product_id.display_name,
                    'product_id': line.product_id.id,
                    'product_uom_id': line.product_uom.id,
                    'product_qty': qty_to_purchase,
                    'price_unit': price_unit,
                    'date_planned': fields.Datetime.now(),
                    'order_id': order.id,
                })
                line.line_state = 'po_created'

        # -----------------------------
        # Send Email to Store Users
        # -----------------------------
        store_group = self.env.ref(
            'mrp_material_request.group_material_request_store_user'
        )

        store_users = self.env['res.users'].sudo().search([
            ('group_ids', 'in', store_group.id),
            ('active', '=', True),
        ])

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        base_url += '/web#id=%d&view_type=form&model=%s' % (
            self.id,
            self._name
        )

        for user in store_users:
            if not user.partner_id.email:
                continue

            body_html = """
            <div style="font-family: Arial, sans-serif; margin: 0 auto;
                        border: 1px solid #c0c0c0; border-radius: 8px; overflow: hidden;">

                <div style="background-color: #1a6b3c; padding: 24px 32px;">
                    <h2 style="color: #ffffff; margin: 0; font-size: 20px;">
                        Purchase Approved - PO Created
                    </h2>
                </div>

                <div style="padding: 32px; background-color: #ffffff;">

                    <p style="font-size:15px;">
                        Dear <strong>%s</strong>,
                    </p>

                    <p style="font-size:14px; line-height:1.6;">
                        The Purchase Team has approved the Material Request and
                        Purchase Order(s) have been successfully created.
                        Kindly proceed with the next store process.
                    </p>

                    <div style="background-color:#edf7f1;
                                border-left:4px solid #1a6b3c;
                                padding:16px 20px;
                                margin:20px 0;">

                        <table style="width:100%%;">

                            <tr>
                                <td><b>Material Request</b></td>
                                <td>%s</td>
                            </tr>

                            <tr>
                                <td><b>Requested By</b></td>
                                <td>%s</td>
                            </tr>

                            <tr>
                                <td><b>Purchase Approved By</b></td>
                                <td>%s</td>
                            </tr>

                            <tr>
                                <td><b>Approval Date</b></td>
                                <td>%s</td>
                            </tr>

                        </table>

                    </div>

                    <div style="margin:24px 0;">
                        <a href="%s"
                           style="display:inline-block;
                                  background-color:#1a6b3c;
                                  color:#ffffff;
                                  text-decoration:none;
                                  padding:10px 24px;
                                  border-radius:6px;">
                            View Material Request →
                        </a>
                    </div>

                    <p>
                        Thanks & Regards,<br/>
                        <strong>%s</strong>
                    </p>

                </div>

                <div style="background-color:#1a6b3c;
                            padding:16px;
                            text-align:center;">

                    <p style="color:#ffffff;font-size:12px;margin:0;">
                        This is an automated notification from %s.
                    </p>

                </div>

            </div>
            """ % (
                user.name,
                self.name,
                self.user_id.name or '',
                self.env.user.name,
                fields.Date.today().strftime('%d-%m-%Y'),
                base_url,
                self.env.user.name,
                self.company_id.name or 'Odoo ERP'
            )

            self.env['mail.mail'].sudo().create({
                'auto_delete': False,
                'author_id': self.env.user.partner_id.id,
                'email_from': (
                        self.company_id.partner_id.email_formatted
                        or self.env.user.email_formatted
                        or self.env.ref('base.user_root').email_formatted
                ),
                'email_to': user.partner_id.email,
                'subject': 'Purchase Approved - PO Created - %s' % self.name,
                'body_html': body_html,
            }).send()

        return self.action_view_po()

    def action_view_po(self):
        return {
            'name': _('Purchase Order'),
            'type': 'ir.actions.act_window',
            'view_mode': 'list,form',
            'res_model': 'purchase.order',
            'context': {'default_material_request_id': self.id},
            'domain': [('material_request_id', '=', self.id)],
        }

    def _send_material_sent_notification(self, picking_id):
        self.ensure_one()
        if not self.user_id.partner_id.email:
            return

        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        picking_url = f"{base_url}/web#id={picking_id.id}&view_type=form&model=stock.picking"

        body_html = """
        <div style="font-family: Arial, sans-serif; margin: 0 auto; border: 1px solid #c0c0c0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #1a6b3c; padding: 24px 32px;">
                <h2 style="color: #ffffff; margin: 0; font-size: 20px;">Material Sent to You</h2>
            </div>
            <div style="padding: 32px; background-color: #ffffff;">
                <p>Dear <strong>%s</strong>,</p>
                <p>The materials requested in <strong>%s</strong> have been sent to you.</p>
                <div style="background-color: #edf7f1; border-left: 4px solid #1a6b3c; border-radius: 4px; padding: 16px 20px; margin: 20px 0;">
                    <table style="width: 100%%;">
                        <tr><td width="40%%">MR Reference</td><td><b>%s</b></td></tr>
                        <tr><td>Transfer Ref</td><td><b>%s</b></td></tr>
                    </table>
                </div>
                <div style="margin: 24px 0;">
                    <a href="%s" style="display: inline-block; background-color: #1a6b3c; color: #ffffff; text-decoration: none; padding: 10px 24px; border-radius: 6px; font-weight: 600;">
                        View Transfer
                    </a>
                </div>
            </div>
        </div>
        """ % (self.user_id.name, self.name, self.name, picking_id.name, picking_url)

        self.env['mail.mail'].sudo().create({
            'subject': f'Material Sent: {self.name} / {picking_id.name}',
            'body_html': body_html,
            'email_to': self.user_id.partner_id.email,
            'email_from': self.env.user.email_formatted or self.company_id.partner_id.email_formatted,
        }).send()

    # def action_request_purchase_and_transfer(self):
    #     self.ensure_one()
    #     # 1. Create Internal Transfer for available quantities
    #     picking_id = self.env['stock.picking'].create({
    #         'picking_type_id': self.picking_type_id.id,
    #         'location_id': self.location_id.id,
    #         'location_dest_id': self.location_dest_id.id,
    #         'company_id': self.env.company.id,
    #         'material_request_id': self.id,
    #         'origin': self.name,
    #         'mrp_material_request': self.id,
    #     })
    #
    #     has_transfer = False
    #     for line in self.request_line_ids.filtered(lambda l: not l.display_type and l.transfer_qty > 0):
    #         has_transfer = True
    #         self.env['stock.move'].create({
    #             'product_id': line.product_id.id,
    #             # 'name': line.product_id.name,
    #             'product_uom_qty': line.transfer_qty,
    #             'product_uom': line.product_uom.id,
    #             'location_id': self.location_id.id,
    #             'location_dest_id': self.location_dest_id.id,
    #             'picking_id': picking_id.id,
    #             'company_id': self.company_id.id,
    #             'origin': self.name,
    #             'quantity': line.transfer_qty,
    #             'mrp_material_request': self.id,
    #         })
    #
    #     if not has_transfer:
    #         picking_id.unlink()
    #     else:
    #         self._send_partial_sent_notification(picking_id)
    #
    #     # 2. Trigger Purchase Manager Request (sets state to purchase_request and sends emails)
    #     self.action_purchase_manager_request()
    #     # Reset flag so the button does not show again
    #     self.is_mixed_availability = False
    #     return True

    def _send_partial_sent_notification(self, picking_id):
        self.ensure_one()
        if not self.user_id.partner_id.email:
            return
        
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        picking_url = f"{base_url}/web#id={picking_id.id}&view_type=form&model=stock.picking"

        items_list_html = ""
        for line in self.request_line_ids.filtered(lambda l: not l.display_type and l.transfer_qty > 0):
            items_list_html += f"<li>{line.product_id.name}: <b>{line.transfer_qty}</b> (Stock) and <b>{line.purchase_qty}</b> (Pending Purchase)</li>"

        body_html = """
        <div style="font-family: Arial, sans-serif; margin: 0 auto; border: 1px solid #c0c0c0; border-radius: 8px; overflow: hidden;">
            <div style="background-color: #1a6b3c; padding: 24px 32px;">
                <h2 style="color: #ffffff; margin: 0; font-size: 20px;">Partial Material Fulfillment Update</h2>
            </div>
            <div style="padding: 32px; background-color: #ffffff;">
                <p>Dear <strong>%s</strong>,</p>
                <p>We are processing your material request <strong>%s</strong>. Some items are available in stock and have been transferred, while the remaining items are being purchased.</p>
                <div style="background-color: #edf7f1; border-left: 4px solid #1a6b3c; padding: 16px 20px; margin: 20px 0;">
                    <p><b>Fulfillment Status:</b></p>
                    <ul>%s</ul>
                </div>
                <div style="margin: 24px 0;">
                    <a href="%s" style="display: inline-block; background-color: #1a6b3c; color: #ffffff; text-decoration: none; padding: 10px 24px; border-radius: 6px; font-weight: 600;">
                        View Internal Transfer
                    </a>
                </div>
                <p style="font-size: 13px; color: #666666;">You will receive another notification once the purchased items are received and sent to you.</p>
            </div>
        </div>
        """ % (self.user_id.name, self.name, items_list_html, picking_url)

        self.env['mail.mail'].sudo().create({
            'subject': f'Partial Fulfillment Update: {self.name}',
            'body_html': body_html,
            'email_to': self.user_id.partner_id.email,
            'email_from': self.env.user.email_formatted or self.company_id.partner_id.email_formatted,
        }).send()

    def action_create_remaining_transfer(self):
        self.ensure_one()
        self.is_delivery_created = True
        self.action_create_post_receipt_transfer()
        return True


class MrpMaterialRequestLine(models.Model):
    _name = 'mrp.material.request.line'
    _description = 'Request Line'

    request_id = fields.Many2one("mrp.material.request", string="Material Request")
    sequence = fields.Integer(
        'Sequence', default=1,
        help="Gives the sequence order when displaying.")
    product_id = fields.Many2one('product.product', 'Product', check_company=True)
    name = fields.Char("Specification", required=True)
    model_make = fields.Char("Model/Make")
    product_uom = fields.Many2one('uom.uom', string='Unit of Measure',
                                  )
    quantity = fields.Float("Quantity")
    purpose = fields.Char("Purpose")
    remark = fields.Char("Remarks")
    check_available=fields.Boolean()
    line_state = fields.Selection([('draft', 'Draft'), ('available', 'Available'), ('unavailable', 'Unavailable'), ('po_created', 'PO Created'), ('received', 'Received'), ('not_yet', 'Not Yet'), ('done', 'Done')], string="Status", default='draft')
    state = fields.Selection(related='request_id.state', store=True)
    company_id = fields.Many2one('res.company', related='request_id.company_id', string='Company', store=True, readonly=True)
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], default=False, help="Technical field for UX purpose.")
    vendor_id = fields.Many2one('res.partner', string="Vendor", domain=[('is_vendor', '=', True)])
    transfer_qty = fields.Float("Transfer Quantity", digits='Product Unit of Measure')
    purchase_qty = fields.Float("Purchase Quantity", digits='Product Unit of Measure')
    is_transfer_complete = fields.Boolean(compute='compute_is_transfer_complete')

    def compute_is_transfer_complete(self):
        for rec in self:
            if rec.transfer_qty == rec.quantity:
                rec.is_transfer_complete = True
            else:
                rec.is_transfer_complete = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            request_id = vals.get('request_id')
            if request_id:
                request = self.env['mrp.material.request'].browse(request_id)
                if request.state != 'draft':
                    raise UserError(_("You can only add lines when the request is in Draft state!"))
        return super(MrpMaterialRequestLine, self).create(vals_list)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if not self.product_id:
            return
        self.product_uom = self.product_id.uom_id
        self.name = self.product_id.get_product_multiline_description_sale()

    def unlink(self):
        for rec in self:
            if rec.request_id and rec.request_id.state not in ['draft', 'cancel']:
                raise UserError(_("Invalid Action!"))
        super(MrpMaterialRequestLine, self).unlink()

