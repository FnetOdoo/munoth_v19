# -*- coding: utf-8 -*-

{
    'name': 'Purchase Requisition',
    'version': '19.0.1.0.0',
    'price': 79.0,
    'currency': 'EUR',
    'license': 'OPL-1',
    'summary': 'Allow employees to create and manage purchase requisitions',
    'description': """
        Employee Purchase Requisition Management
        
        This module allows employees or users to create purchase requisitions for materials/products.
        
        Key Features:
        - Employees can create purchase requisitions with multiple items
        - Approval workflow (Department Head & Requisition Manager)
        - Email notifications for approvals
        - Option to fulfill requisitions via:
            * Internal Picking (Warehouse)
            * Purchase Orders (Vendors)
        - Automatic stock/internal transfer handling
        - Integration with Purchase, Inventory, and HR modules
        
        Use Cases:
        - Inventory replenishment
        - Internal material requests
        - Department-level purchase control
        - Warehouse and procurement workflows
    """,
    'author': 'Probuse Consulting Service Pvt. Ltd.',
    'website': 'http://www.probuse.com',
    'support': 'contact@probuse.com',
    'category': 'Inventory/Purchase',
    'depends': [
        'stock',
        'hr',
        'purchase',
    ],
    'data': [
        'security/security.xml',
        'security/multi_company_security.xml',
        'security/ir.model.access.csv',
        'data/purchase_requisition_sequence.xml',
        # 'data/employee_purchase_approval_template.xml',
        # 'data/confirm_template_material_purchase.xml',
        'report/purchase_requisition_report.xml',
        'views/purchase_requisition_view.xml',
        'views/hr_employee_view.xml',
        'views/hr_department_view.xml',
        'views/stock_picking_view.xml',
    ],
    'images': ['static/description/img1.jpeg'],
    'installable': True,
    'application': False,
    'auto_install': False,
}