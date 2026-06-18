# -*- encoding: utf-8 -*-
{
    "name": "Battery Cell API",
    "version": "19.0.1.0.0",
    "summary": "API to log battery cell data via JSON",
    "author": "",
    "website": "",
    "category": "Custom",
    "license": "LGPL-3",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "views/battery_cell_log_view.xml",
        "views/res_partner_views.xml",
    ],
    "assets": {},
    "installable": True,
    "application": False,
    "auto_install": False,
}