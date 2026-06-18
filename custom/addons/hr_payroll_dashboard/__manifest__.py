{
    'name': 'HR Payroll Dashboard',
    'version': '19.0.1.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Payroll Dashboard with KPIs, Charts and Analytics',
    'description': """
        HR Payroll Dashboard for Odoo 19
        - KPI Cards: Attendances, Leave Requests, Payslips, Contracts, Salary Rules, Salary Structures
        - Charts: Monthly Expense, Leave Analysis, Payslips, Contract Analysis, Time Off
        - Fully clickable with navigation to tree/form views
        - Responsive scrollable layout
    """,
    'author': 'Custom',
    'depends': [
        'hr',
        'hr_attendance',
        'hr_holidays',
        'hr_payroll_community',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/dashboard_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'hr_payroll_dashboard/static/src/css/dashboard.css',
            'hr_payroll_dashboard/static/src/xml/dashboard_template.xml',
            'hr_payroll_dashboard/static/src/js/dashboard.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
