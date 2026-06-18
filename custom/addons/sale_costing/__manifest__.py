# -*- coding: utf-8 -*-
{
    'name': "Sale Costing",
    'summary': """This module helps to calculate sale price from the purchase agreement.""",
    'author': "Futurenet Technologies",
    'website': "http://www.futurenet.in",
    'category': 'Sales',
    'version': '19.0.1',
    'depends': ['product', 'purchase_requisition', 'sale', 'fnet_mrp'],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'data/datas.xml',
        'views/configuration_views.xml',
        'views/sale_costing_views.xml',
        'views/purchase_views.xml',
        'views/sale_views.xml',
    ],
    'license': 'LGPL-3',
}
