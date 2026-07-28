{
    'name': 'User Manual',
    'version': '19.0.1.0.0',
    'category': 'Tools',
    'summary': 'Upload, manage and view user manuals (PDF / Document)',
    'description': """
User Manual
===========
Upload user manuals (PDF or document files only) and view them in full screen.

Features
--------
* Upload only PDF / document files (.pdf, .doc, .docx, .odt, .rtf, .txt)
* View any uploaded manual in full screen (opens in a new browser tab)
* Two access levels:
    - User  -> read only (granted to every internal user by default)
    - Administrator -> read / write / create / delete
* Submit / Reset to Draft workflow buttons, visible only to Administrators
""",
    'author': 'Custom',
    'website': '',
    'depends': ['base', 'web', 'mail'],
    'data': [
        'security/user_manual_groups.xml',
        'security/ir.model.access.csv',
        'views/user_manual_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'LGPL-3',
}
