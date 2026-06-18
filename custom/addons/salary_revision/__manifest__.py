# -*- coding: utf-8 -*-
{
    'name': "Salary Revision",

    'summary': """
        Employee salary history and revision management (Odoo 19)""",

    'description': """
        Migrated from v15 to v19.
        - hr.contract removed in v19 → all salary fields now on hr.employee
        - salary.history.line linked to hr.employee (not hr.contract)
        - salary.revision wizard reads/writes hr.employee fields
        - Salary History tab shown on employee form
        - Salary Revision button on employee form
    """,

    'author': "Futurenet Technologies India Pvt Ltd/P.Padmajothi",
    'website': "http://www.futurenet.in",
    'installable': True,
    'application': True,
    'auto_install': False,

    'category': 'Human Resource',
    'version': '19.0.1',

    # hr_contract and hr_payroll_community removed — not available in v19
    'depends': ['base', 'hr', 'hr_payroll_community'],

    'data': [
        'security/ir.model.access.csv',
        'wizard/salary_revision.xml',
        'views/views.xml',
    ],

    'demo': [
        'demo/demo.xml',
    ],

    'license': 'LGPL-3',
}
