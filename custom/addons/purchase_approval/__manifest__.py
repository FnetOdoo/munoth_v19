{
    "name": "Purchase Approval Rules",
    "summary": "Purchase Approval Rules",
    'images': ['static/description/banner.jpg'],
    "description": "Purchase Approval Rules",
    'summary': 'Purchase Order Approval Rules',
    "version": "19.0.1.1",
    "category": "Purchase",
    "author": "Futurenet Technologies India Pvt Ltd.",
    "website": "https://www.futurenet.in",
    "depends": ["hr", "purchase", 'purchase_extended',  'sales_team'],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/mail_template.xml",
        "views/approval_config.xml",
        "views/purchase_order_config.xml",
        "views/purchase_view.xml",
        "wizard/custom_warning_view.xml"
    ],
    'sequence': 1,
    "installable": True,
    'license': 'LGPL-3',
}
