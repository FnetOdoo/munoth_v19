# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Assets Management',
    'description': """
Assets management
=================
Manage assets owned by a company or a person.
Keeps track of depreciations, and creates corresponding journal entries.

    """,
    'category': 'Accounting/Accounting',
    'sequence': 32,
    'version': '19.0.1',
    'depends': ['account_reports','account'],
    'data': [
        'security/account_asset_security.xml',
        'security/ir.model.access.csv',
        'wizard/asset_modify_views.xml',
        'wizard/asset_pause_views.xml',
        'wizard/asset_sell_views.xml',
        'views/account_account_views.xml',
        'views/account_asset_views.xml',
        'views/account_deferred_revenue.xml',
        'views/account_deferred_expense.xml',
        'views/account_move_views.xml',
        'report/account_assets_report_views.xml',
    ],
    'demo': [
        'demo/account_deferred_revenue_demo.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            'account_asset/static/src/**/*',
        ],
        'web.assets_backend_xml': [
            'account_asset/static/src/xml/account_asset_reversed_widget.xml',
        ],
    }
}
