# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name' : 'Voucher',
    'summary': 'Voucher Entry',
    'sequence': 40,
    'author': 'Dhaksha Biztechnovations / S&V',
    'description': """
Accounting Voucher & Receipts
=============================
The specific and easy-to-use Invoicing system in Odoo allows you to keep track of your accounting, even when you are not an accountant. It provides an easy way to follow up on your suppliers and customers. 

You could use this simplified accounting in case you work with an (external) account to keep your books, and you still want to keep track of payments. 

The Invoicing system includes receipts and vouchers (an easy way to keep track of sales and purchases). It also offers you an easy method of registering payments, without having to encode complete abstracts of account.

This module manages:

* Voucher Entry
* Voucher Receipt/Payment for Cash and Bank


    """,
    'category': 'Accounting',
    'website': '',
    'depends': ['base', 'account','purchase'],
    'data': [
        'security/account_voucher_security.xml',
        'security/ir.model.access.csv',
        'views/account_voucher_view.xml',
        'views/account_journal_view.xml',
        'views/account_move_view.xml',
            ],
    'demo': [],
    'qweb': [],
    'installable': True,
    'application': False,
    'auto_install': False,
}

