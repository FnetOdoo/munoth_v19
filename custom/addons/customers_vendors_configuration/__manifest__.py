# -*- coding: utf-8 -*-
{
    'name': "Customers Vendors Configuration",
    'summary': """Configure the customer and vendors.""",
    'description': """Includes all the requirement in Dome Project.""",
    'author': "Futurenet Technologies",
    'website': "http://www.futurenet.in",
    'category': 'All',
    'version': '19.0.1',
    'depends': ['base', 'sale_management', 'crm', 'purchase', 'account', 'product', 'purchase_requisition'],
    'data': [
        'views/views.xml',
    ],

    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}
