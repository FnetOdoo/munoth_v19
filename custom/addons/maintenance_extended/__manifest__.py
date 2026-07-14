{
    'name': 'Maintenance Extended',
    'author': 'Futurenet Technologies India Pvt Ltd',
    'website': 'https://futurenet.in/',
    'category': 'Maintenance',
    'license': 'LGPL-3',
    'version': '19.0.0',
    'depends': ['maintenance', 'hr', 'stock', 'maintenance_plan', 'sales_subscription','base_maintenance'],
'assets': {
    'web.assets_backend': [
        'maintenance_extended/static/src/js/maintenance_dashboard.js',
        'maintenance_extended/static/src/xml/maintenance_dashboard.xml',
        'maintenance_extended/static/src/scss/maintenance_dashboard.scss',
    ],
},
    'data': [
        'security/ir.model.access.csv',
        'datas/sequence.xml',
        'datas/crons.xml',
        'views/views.xml',
        'views/engineering_change_request.xml',
        'views/work_order_view.xml',
        'views/material_request.xml',
        'views/maintenance_report_wizard_views.xml',
    ],
    'installable': True,
}
