# Copyright 2017-2021 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

{
    "name": "Mrp Request",
    "summary": "Internal Mrp request",
    "version": "19.0.1.5.0",
    "website": "https://www.futurenet.in",
    "author": "Futurenet",
    "category": "Stock",
    "depends": ['stock', 'fnet_mrp', 'hr', 'material_purchase_requisitions','customers_vendors_configuration'],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/data.xml",
        "views/mrp_request.xml",
        "views/stock_picking.xml",
        "views/product_plan.xml",
        "views/mrp_material_request_views.xml",
        # "views/production_material_request.xml",
        "views/purchase_views.xml",
        "wizard/return_stock.xml",

    ],
    "installable": True,
    'license': 'LGPL-3',
}