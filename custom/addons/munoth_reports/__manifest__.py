{
    'name': 'munoth  Reports',
    'version': '19.0.1',
    'summary': 'Report',
    'sequence': 15,
    'description': """

    """,
    'category': '',
    'website': '',
    'images': [],
    # Migration v15→v19:
    # - account_accountant merged into account (v17+)
    # - hr_payroll_community merged into hr_payroll (v17+)
    # - sale_expected_delivery removed / merged into sale (v17+)
    'depends': ['base','sale','account','web','purchase','sales_subscription','apex_einvoice', 'hr', 'hr_payroll_community','fnet_mrp', 'stock','hr_expense', 'mrp_material_request'],
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'views/sale_order_inherit.xml',
        'reports/sales_invoice.xml',
        'reports/sales_invoice_templates.xml',
        'reports/expenses_claim_form.xml',
        'reports/grn_formate_duplicate.xml',
        'reports/injection_report.xml',
        'reports/grn_format.xml',
        'reports/packing_list.xml',
        'reports/good_inward_checklist.xml',
        'reports/gate_pass.xml',
        'reports/customer_master.xml',
        'reports/material_request.xml',
        'reports/material_request_duplicate.xml',
        'reports/quotation_order.xml',
        'reports/RFQ_report.xml',
        'reports/Tax_invoice_new.xml',
        'reports/purchase_order_report.xml',
        'reports/payslip_report.xml',
        'reports/tax_invoice.xml',
        # 'reports/degas_report.xml',
        # 'reports/voltage_report.xml',
        # 'reports/clamp_baking_report.xml',
        # 'reports/pad_printing_report.xml',
        # 'reports/capacity_test_report.xml',
        'reports/oqc_report.xml',
        'reports/process_quality_check.xml',
        'reports/engineering_change_request.xml',
        # 'reports/customer_complaint_register_report.xml',
        'wizard/process_status_report_view.xml',
        'wizard/gate_pass_boxe.xml',
        'wizard/update_boxes.xml',

    ],
    'demo': [
    ],
    'qweb': [
    ],
    'assets': {
        'web.assets_backend': [
            'munoth_reports/static/custom_css/custom_style.css',
            'munoth_reports/static/src/js/tree_view_button.js',
            # Migration v15→v19: web.assets_qweb removed in v16+
            # QWeb templates now loaded via web.assets_backend
            'munoth_reports/static/src/xml/tree_button.xml',
        ],
    },


    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'AGPL-3',
}