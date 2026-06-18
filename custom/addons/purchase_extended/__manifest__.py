{
    "name": "Purchase Extended",
    "summary": "Internal Purchase Extended",
    "version": "19.0.1",
    "website": "https://www.futurenet.in",
    "author": "Futurenet",
    "category": "Stock",
    "depends": ['stock', 'purchase', 'purchase_requisition','sale','crm','account'],
    "data": [
        "security/ir.model.access.csv",
        "data/cron.xml",
        "data/sequence.xml",
        "views/purchase_views.xml",
        "views/purchase_agreement_views.xml",
    ],
    "installable": True,
    "sequence": 0,
    'license': 'LGPL-3',
}