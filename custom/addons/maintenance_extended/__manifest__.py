{
    'name': 'Maintenance Extended',
    'author': 'Futurenet Technologies India Pvt Ltd',
    'website': 'https://futurenet.in/',
    'category': 'Maintenance',
    'license': 'LGPL-3',
    'version': '19.0.0',
    'depends': ['maintenance', 'hr', 'stock', 'maintenance_plan', 'sales_subscription','base_maintenance'],
    'data': [
        'security/ir.model.access.csv',
        'datas/sequence.xml',
        'datas/crons.xml',
        'views/views.xml',
        'views/engineering_change_request.xml',
        'views/work_order_view.xml',
        'views/material_request.xml',
    ],
    'installable': True,
}
