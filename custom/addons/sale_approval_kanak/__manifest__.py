# -*- coding: utf-8 -*-
{
    "name": "Sale Approval Rules",
    "summary": "Sale Order Approval Rules",
    "description": "Sale Approval Rules",
    "version": "19.0.1.0.0",
    "category": "Sales",
    "license": "OPL-1",
    "author": "Kanak Infosystems LLP.",
    "website": "https://www.kanakinfosystems.com",

    "depends": [
        "hr",
        "sale"
    ],

    "data": [
        "security/ir.model.access.csv",
        # "data/mail_template.xml",
        "views/approval_config.xml",
        "views/sale_order_config.xml",
        "views/sale_view.xml",
        "wizard/custom_warning_view.xml"
    ],
    "assets": {
        "web.assets_backend": [],
    },
    "installable": True,
    "application": False,
    "sequence": 1,
}