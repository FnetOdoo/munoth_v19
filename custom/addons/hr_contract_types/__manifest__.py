# -*- coding: utf-8 -*-

{
    'name': 'Odoo19 Employee Contract Types',
    'version': '19.0.1.1.0',
    'category': 'Generic Modules/Human Resources',
    'summary': """
        Contract type on employees (migrated from hr.contract to hr.employee for Odoo 19)
    """,
    'description': """Odoo19 Employee Contract Types, Employee Contracts, Odoo 19.
    Migrated from Odoo 15: hr.contract removed in Odoo 19, type_id field moved to hr.employee.""",
    'author': 'Odoo SA,Cybrosys Techno Solutions',
    'company': 'Cybrosys Techno Solutions',
    'maintainer': 'Cybrosys Techno Solutions',
    'website': 'https://www.cybrosys.com',
    # hr_contract dependency removed — hr.contract model no longer exists in Odoo 19
    'depends': ['hr'],
    'data': [
        'security/ir.model.access.csv',
        'views/contract_view.xml',
        'data/hr_contract_type_data.xml',
    ],
    'installable': True,
    'images': ['static/description/banner.png'],
    'auto_install': False,
    'application': False,
    'license': 'AGPL-3',
}
