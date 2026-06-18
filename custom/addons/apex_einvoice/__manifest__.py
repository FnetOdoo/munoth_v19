# -*- coding: utf-8 -*-
{
    'name': "E-Invoice",
    'summary': """
        This module integrate government invoicing site with odoo via the third party api provider called cygnet api provider.""",
    'description': """
        This module integrate government invoicing site with odoo via the third party api provider called cygnet api provider.
    """,
    'author': "Futurenet Technologies India Pvt Ltd",
    'website': "http://www.futurenet.in",
    'category': 'Accounting',
    'version': '11.0.1',
    'depends': ['base', 'account', 'l10n_in', 'web', 'account_accountant'],
    'data': [
        'security/ir.model.access.csv',
        'views/layouts.xml',
        'wizards/cancel_irn_views.xml',
        'views/configuration_views.xml',
        'views/res_company_views.xml',
        'views/views.xml',
        'views/invoice_views.xml',
        'views/report_views.xml',
    ],
    'license': 'AGPL-3',
}