# -*- encoding: utf-8 -*-
{
    "name": "Terms & Conditions",
    "version": "19.0.1",
    "author": "Futurenet Pvt.Ltd.",
    "website": "http://www.futurenet.in",
    "sequence": 0,
    "depends": ["sale", "base", "account", "purchase", "product"],
    "category": "All",
    "license": "LGPL-3",
    "description": """Terms & Conditions""",
    "data": [
        "security/ir.model.access.csv",
        "security/security.xml",
        "views/account_terms_condition.xml",
    ],
    "auto_install": False,
    "installable": True,
    "application": False,
}
