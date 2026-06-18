# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import _
from odoo.exceptions import UserError

_logger = logging.getLogger("odoo.addons.maintenance_plan")


def post_init_hook(env):

    _logger.info("Migrating existing preventive maintenance from v15")

    # Check if the legacy 'period' column still exists in the DB
    env.cr.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'maintenance_equipment' 
        AND column_name = 'period'
    """)
    if not env.cr.fetchone():
        _logger.info(
            "Legacy 'period' column not found in maintenance_equipment. "
            "Migration already done or not applicable. Skipping."
        )
        return

    env.cr.execute("""
        SELECT id, period, maintenance_duration, next_action_date
        FROM maintenance_equipment
        WHERE period IS NOT NULL AND period != 0
    """)
    rows = env.cr.dictfetchall()

    if not rows:
        _logger.info("No legacy data found to migrate. Skipping.")
        return

    maintenance_kind = env["maintenance.kind"].create(
        {"name": "Install", "active": True}
    )

    for row in rows:
        equipment = env["maintenance.equipment"].browse(row["id"])

        request = equipment.maintenance_ids.filtered(
            lambda r: r.maintenance_type == "preventive"
            and not r.stage_id.done
            and r.request_date == row["next_action_date"]
        )

        if len(request) > 1:
            raise UserError(
                _(
                    "You have multiple preventive maintenance requests on "
                    "equipment %(name)s next action date (%(date)s). Please leave only "
                    "one preventive request on the date of equipment's next "
                    "action to install the module.",
                    name=equipment.name,
                    date=row["next_action_date"],
                )
            )
        elif len(request) == 1:
            request.write({"maintenance_kind_id": maintenance_kind.id})

        env["maintenance.plan"].create(
            {
                "equipment_id": equipment.id,
                "maintenance_kind_id": maintenance_kind.id,
                "duration": row["maintenance_duration"] or 0,
                "interval": row["period"],
            }
        )

    _logger.info("Migration complete: %d equipment records processed.", len(rows))