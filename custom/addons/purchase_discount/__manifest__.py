{
    "name": "Purchase order lines with discounts",
    "version": "19.0.2.0.1",
    "category": "Purchase Management",
    "depends": [
        "purchase",
        "purchase_stock",
        # "mrp",
    ],
    "data": [
        "views/purchase_discount_view.xml",
        "views/report_purchaseorder.xml",
        # "views/product_supplierinfo_view.xml",
        "views/res_partner_view.xml",
        "views/res_config_view.xml",
    ],
    "license": "AGPL-3",
    "installable": True,
    "images": ["images/purchase_discount.png"],
}