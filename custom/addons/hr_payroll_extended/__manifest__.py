# -*- coding: utf-8 -*-
{
    'name': "Payroll Extended",

    'summary': """
        Extended payroll fields for Indian payroll — allowances, deductions,
        PF/ESI/TDS, NEFT statement, and Excel batch report.""",

    'description': """
        Migrated from v15 to v19.
        - hr.contract fields migrated to hr.employee (contract model removed in v17+)
        - Salary structure fields stored on employee record
        - Excel payslip batch report
        - NEFT bank statement export
        - Auto contract-expiry cron replaced with hr.plan / employee contract logic
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",
    'category': 'Payroll',
    'version': '19.0.1',

    # hr_payroll_community no longer exists in v17+; use standard hr_payroll.
    # hr_contract is NOT listed — the model does not exist in v19 community.
    # If your v19 build is Enterprise, add 'payroll' instead of 'hr_payroll'.
    'depends': ['base', 'hr', 'hr_payroll_community'],

    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'data/cron.xml',
    ],

    'license': 'LGPL-3',
}
