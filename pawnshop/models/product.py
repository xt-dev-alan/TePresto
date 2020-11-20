# -*- coding: utf-8 -*-

from odoo import _, api, fields, models

class ProductCategory(models.Model):
    _inherit = 'product.category'

    pawn_rate = fields.Float('Pawn Rate')