# -*- coding: utf-8 -*-

{
    'name': 'Pawn Shop',
    'version': '1.0.1',
    'author': 'Xetechs GT',
    'website': 'https://xetechs.com',
    'license': 'LGPL-3',
    'depends': [
        'sale_management',
        'stock',
        'account',
        'point_of_sale'
        
    ],
    'data': [
        'data/ir_cron_data.xml',
        'data/product_data.xml',
        'data/ir_sequence_data.xml',
        'data/stock_data.xml',
        'security/ir.model.access.csv',
        'wizard/pawn_create_payment.xml',
        'views/pawn_views.xml',
        'views/product_views.xml',
        'views/contract_template.xml',
        'views/ir_actions_report.xml',
        'views/res_config_settings_views.xml',
    ]
}