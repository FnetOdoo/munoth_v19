{
    'name': 'Manufacturing',
    'version': '19.0.1.0.0',
    'website': 'https://www.erp.futurenet.in',
    'category': 'Manufacturing/Manufacturing',
    'sequence': 1,
    'summary': 'Manufacturing Orders',
    'depends': [
        'base',
        'product',
        'stock',
        'web',
        'mail',
        'sale',
        'sale_stock',
        # 'purchase_extended',  # ensure this exists in v19
        # 'board',  # uncomment only if confirmed available
    ],
    'description': "Manufacturing process of the Battery, Cells",

    'data': [
        'security/mrp_security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequences.xml',

        'views/config.xml',
        'views/stock_qty.xml',
        'views/operation.xml',
        'views/machine.xml',
        'views/product_model.xml',
        'views/production_plan.xml',
        'views/production_estimation.xml',

        # 'views/cathode_slitting.xml',
        # 'views/anode_slitting.xml',

        'wizard/input_import_views.xml',
        'wizard/scrap.xml',
        'wizard/product_tray.xml',
        'wizard/mttr_mtbf_report.xml',
        'wizard/availability_report.xml',

        # 'views/anode_drying.xml',
        # 'views/cathode_drying.xml',
        # 'views/diaphragm_drying.xml',
        # 'views/anode_electrode.xml',
        # 'views/cathode_electrode.xml',
        # 'views/winding.xml',
        # 'views/hot_press.xml',
        # 'views/assembly.xml',
        # 'views/cell_drying.xml',
        # 'views/injection.xml',
        # 'views/high_temperature_cell.xml',
        # 'views/clamp_baking_formation.xml',
        # 'views/aged_formation_cell.xml',
        # 'views/degas.xml',
        # 'views/double_side_folding.xml',
        # 'views/pad_printing.xml',
        # 'views/capacity_test.xml',
        # 'views/voltage_test.xml',
        # 'views/package.xml',

        'views/quality_check_views.xml',
        'views/stock_views.xml',
        'views/first_article_inspection.xml',
        'views/inspection_report_receiving.xml',
        'views/outgoing_quality_control_inspection.xml',
        'views/powerbank_views.xml',

        # 'views/quality_check_injection.xml',

        'views/monthly_plan_views.xml',
        'views/process_quality_check.xml',
        'views/customer_complaint_register.xml',
        # 'views/qr_code_printing.xml',
        'views/res_config_settings.xml',
        'views/production_process_views.xml',
        'views/manufacturing_bom_views.xml',
        'views/sale_order_views.xml',
        'views/menuitems.xml',

    ],

    'assets': {
        'web.assets_backend': [
            'fnet_mrp/static/src/js/dynamic_process_menu.js',
            'fnet_mrp/static/src/xml/dynamic_process_menu.xml',
            'fnet_mrp/static/src/css/dynamic_process_menu.css',
        ],
    },

    'application': True,
    'license': 'LGPL-3',
}