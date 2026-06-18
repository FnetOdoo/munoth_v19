# -*- coding: utf-8 -*-
{
    'name': "Sale Expected Delivery",
    'summary': """This module used to calculate the delivery date of the battary""",
    'description': """This module used to calculate the delivery date of the battary.""",
    'author': "Futurenet Technologies India Pvt Ltd",
    'website': "http://www.futurenet.in",
    'category': 'Sales',
    'version': '19.0.1',
    'depends': ['sale', 'fnet_mrp'],
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/sale_views.xml',
        'data/data.xml',
    ],
    'license': 'LGPL-3',
}
