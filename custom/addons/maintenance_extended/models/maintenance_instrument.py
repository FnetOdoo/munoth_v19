# Copyright 2017 Camptocamp SA
# Copyright 2019-20 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
import logging
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

class MaintenanceEquipment(models.Model):

    _inherit = "maintenance.instrument"

    instrument_plan_ids = fields.One2many(
        string="Maintenance plan",
        comodel_name="maintenance.plan",
        inverse_name="calibration_plan_id",
    )
    maintenance_plan_count = fields.Integer(
        compute="_compute_maintenance_plan_count",
        store=True,
    )
    search_maintenance_plan_count = fields.Integer(
        compute="_compute_search_maintenance_plan_count",
        string="Maintenance All Plan Count",
    )
    maintenance_team_required = fields.Boolean(compute="_compute_team_required")
    notes = fields.Text()
    calibration_plan_count = fields.Integer( string="Plan Count",compute="_compute_calibration_plan_count",)
    calibration_request_count = fields.Char( string="Plan Count",compute="_compute_calibration_request_count",)
    category_id = fields.Many2one('maintenance.equipment.category',string='Category')

    def _cron_maintenance_alert(self):
        manager_group = self.env.ref('maintenance.group_equipment_manager')
        manager_users = self.env['res.users'].search([
            ('group_ids', 'in', manager_group.id),
        ])
        email_list = [u.email or u.login for u in manager_users if (u.email or u.login)]
        email_to = ','.join(email_list)

        categ_ids = self.env['maintenance.equipment.category'].search([('alert_days', '>', 0)])
        for category in categ_ids:
            alert_day = fields.Datetime.now() + relativedelta(days=category.alert_days)
            from_date = alert_day.replace(hour=0, minute=0, second=0, microsecond=0)
            to_date = alert_day.replace(hour=23, minute=59, second=59, microsecond=999999)
            request_ids = self.env['maintenance.request'].search([
                ('is_calibration', '=', True),
                ('calibration_category_id', '=', category.id),
                ('schedule_date', '>=', from_date),
                ('schedule_date', '<=', to_date),
            ])
            for request in request_ids:
                subject = 'Calibration Alert - %s' % request.name
                body = """
                          <div style="font-family: 'Lucida Grande', Ubuntu, Arial, Verdana, sans-serif; font-size: 12px; color: rgb(34, 34, 34); background-color: #FFF;">
                              <div style="height:auto; text-align: center; font-size: 30px; color: #29408c;">
                                  <strong style="border-bottom: 2px solid #29408c; padding-bottom: 1px; text-transform: uppercase;">
                                      Calibration Alert
                                  </strong>
                              </div>
                              <div style="text-align: left; font-size: 20px; margin-top: 10px; color: #29408c;">
                                  <p>Dear Maintenance Team,</p>
                                  <p>Calibration request has been scheduled for %s on %s.</p>
                                  <p>
                                      Thanks &amp; Regards,<br/>
                                      Odoo Bot.
                                  </p>
                              </div>
                          </div>
                                """ % (request.name, request.schedule_date)
                mail = self.env['mail.mail'].sudo().create({
                    'subject': subject,
                    'body_html': body,
                    'email_from': self.env.company.email or self.env.user.email,
                    'email_to': email_to,
                })
                mail.sudo().send()

    @api.depends("instrument_plan_ids")
    def _compute_calibration_plan_count(self):
        for instrument in self:
            instrument.calibration_plan_count = len(instrument.instrument_plan_ids)

    def _compute_calibration_request_count(self):
        for instrument in self:
            instrument.calibration_request_count = self.env["maintenance.request"].search_count([
                ("instrument_id", "=", instrument.id),
                ("is_calibration", "=", True),
            ])
    def get_all_instrument_plans(self):
        """Open all maintenance.plan records linked to this instrument."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Maintenance Plans",
            "res_model": "maintenance.plan",
            "view_mode": "list,form",
            "domain": [("calibration_plan_id", "=", self.id)],
            "context": {
                "default_calibration_plan_id": self.id,
                "default_is_calibration": True,
            },
        }

    def get_all_calibration_requests(self):
        """Open all maintenance.request records linked to this instrument."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "name": "Maintenance Requests",
            "res_model": "maintenance.request",
            "view_mode": "list,form",
            "domain": [("instrument_id", "=", self.id),("is_calibration", "=", True)],
            "context": {
                "default_instrument_id": self.id,
                "default_is_calibration": True,
            },
        }

    @api.depends("instrument_plan_ids")
    def _compute_maintenance_plan_count(self):
        for equipment in self:
            equipment.maintenance_plan_count = len(equipment.instrument_plan_ids)

    @api.depends("instrument_plan_ids")
    def _compute_search_maintenance_plan_count(self):
        for equipment in self:
            equipment.search_maintenance_plan_count = (
                self.env["maintenance.plan"]
                .search_count([("search_instrument_id", "=", equipment.id)])
            )

    @api.depends("instrument_plan_ids")
    def _compute_team_required(self):
        for equipment in self:
            equipment.maintenance_team_required = (
                len(
                    equipment.instrument_plan_ids.filtered(
                        lambda r: not r.maintenance_team_id
                    )
                )
                >= 1
            )

    # @api.constrains("company_id", "instrument_plan_ids")
    # def _check_company_id(self):
    #     for rec in self:
    #         if rec.company_id and not all(
    #             rec.company_id == p.company_id for p in rec.instrument_plan_ids
    #         ):
    #             raise ValidationError(
    #                 _(
    #                     "Some maintenance plan's company is incompatible with "
    #                     "the company of this equipment."
    #                 )
    #             )

    def _prepare_requests_from_plan(self, maintenance_plan, next_maintenance_date):
        if self:
            return self._prepare_request_from_plan(
                maintenance_plan, next_maintenance_date
            )
        equipments = maintenance_plan._get_maintenance_equipments()
        return [
            equipment._prepare_request_from_plan(
                maintenance_plan, next_maintenance_date
            )
            for equipment in equipments
        ]

    def _prepare_request_from_plan(self, maintenance_plan, next_maintenance_date):
        team_id = maintenance_plan.maintenance_team_id.id or self.maintenance_team_id.id
        request_model = self.env["maintenance.request"]
        if not team_id:
            team_id = request_model._get_default_team_id()

        description = self.name if self else maintenance_plan.name
        kind = maintenance_plan.maintenance_kind_id.name or _("Unspecified kind")
        name = _(
            "Calibration (%(kind)s) - %(description)s",
            kind=kind,
            description=description,
        )

        data = {
            "name": name,
            "request_date": next_maintenance_date,
            "schedule_date": next_maintenance_date,
            "calibration_category_id": self.category_id.id,
            "equipment_id": self.equipment_id.id,
            "instrument_id": self.id,
            "maintenance_type": "preventive",
            # "owner_user_id": self.owner_user_id.id or self.env.user.id,
            # "user_id": self.technician_user_id.id,
            "maintenance_team_id": team_id,
            "maintenance_kind_id": maintenance_plan.maintenance_kind_id.id,
            "maintenance_plan_id": maintenance_plan.id,
            "is_calibration": maintenance_plan.is_calibration,
            "duration": maintenance_plan.duration,
            "note": maintenance_plan.note,
            "company_id": maintenance_plan.company_id.id or self.company_id.id,
        }

        # Only set instrument_id if the field exists on both models
        if (
                "instrument_id" in maintenance_plan._fields
                and "instrument_id" in request_model._fields
        ):
            data["instrument_id"] = maintenance_plan.instrument_id.id

        if "planned_hours" in request_model._fields:
            data["planned_hours"] = maintenance_plan.duration

        return data

    def _create_new_request(self, mtn_plan):
        # Compute horizon date adding to today the planning horizon
        horizon_date = fields.Date.today() + mtn_plan.get_relativedelta(
            mtn_plan.maintenance_plan_horizon, mtn_plan.planning_step or "year"
        )
        # We check maintenance request already created and create until
        # planning horizon is met
        start_maintenance_date_plan = mtn_plan.start_maintenance_date
        furthest_maintenance_request = self.env["maintenance.request"].search(
            [
                ("maintenance_plan_id", "=", mtn_plan.id),
                ("request_date", ">=", start_maintenance_date_plan),
            ],
            order="request_date desc",
            limit=1,
        )
        if furthest_maintenance_request:
            next_maintenance_date = (
                    furthest_maintenance_request.request_date
                    + mtn_plan.get_relativedelta(
                mtn_plan.interval, mtn_plan.interval_step or "year"
            )
            )
        else:
            next_maintenance_date = mtn_plan.next_maintenance_date
        skip_notify_follower = mtn_plan.skip_notify_follower_on_requests
        # Skip assigned mail + Activity mail
        request_model = self.env["maintenance.request"].with_context(
            mail_activity_quick_update=skip_notify_follower,
            mail_auto_subscribe_no_notify=skip_notify_follower,
        )
        requests = request_model
        # Create maintenance request until we reach planning horizon
        while next_maintenance_date <= horizon_date:
            if next_maintenance_date >= fields.Date.today():
                vals = self._prepare_requests_from_plan(mtn_plan, next_maintenance_date)
                new_request = request_model.create(vals)
                requests |= new_request
            next_maintenance_date = next_maintenance_date + mtn_plan.get_relativedelta(
                mtn_plan.interval, mtn_plan.interval_step or "year"
            )
        return requests

    @api.model
    def _cron_generate_calibration_requests(self):
        """
        Generates maintenance request on the next_maintenance_date or
        today if none exists
        """
        for plan in (
            self.env["maintenance.plan"]
            .sudo()
            .search([("interval", ">", 0)])
        ):
            equipment = plan.instrument_id
            equipment._create_new_request(plan)

    @api.depends(
        "instrument_plan_ids.next_maintenance_date", "maintenance_ids.request_date"
    )
    def _compute_next_maintenance(self):
        """Redefine the function to display next_action_date in kanban view"""
        for equipment in self:
            next_plan_dates = equipment.instrument_plan_ids.mapped(
                "next_maintenance_date"
            )
            next_unplanned_dates = (
                self.env["maintenance.request"]
                .search(
                    [
                        ("instrument_id", "=", equipment.id),
                        ("maintenance_kind_id", "=", None),
                        ("request_date", ">", fields.Date.context_today(self)),
                        ("stage_id.done", "!=", True),
                        ("close_date", "=", False),
                    ]
                )
                .mapped("request_date")
            )
            if len(next_plan_dates + next_unplanned_dates) <= 0:
                equipment.next_action_date = None
            else:
                equipment.next_action_date = min(next_plan_dates + next_unplanned_dates)