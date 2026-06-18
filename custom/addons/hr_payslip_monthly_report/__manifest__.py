# -*- coding: utf-8 -*-
{
    'name': 'Payroll Advanced Features',
    'version': '19.0.1.0.0',
    'summary': 'Payroll Advanced Features For Odoo 19 Community.',
    'description': 'Payroll Advanced Features For Odoo 19 Community, '
                   'Payroll-Payslip Reporting, Automatic Mail During '
                   'Confirmation of Payslip, Mass Confirm Payslip.',
    'category': 'Generic Modules/Human Resources',
    'author': 'Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    # Odoo 19: hr_payroll_community renamed to 'payroll' (community edition).
    # Update this to match your actual v19 payroll module technical name.
    'depends': [
        'hr_payroll_community',
        'mail',
        'hr'
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/hr_payslip_views.xml',
        'views/res_config_settings_views.xml',
        'data/mail_template_data.xml',
        'wizard/payslip_confirm_views.xml',
        'report/hr_payslip_report_views.xml',
    ],
    'images': ['static/description/banner.jpg'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
