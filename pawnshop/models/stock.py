# -*- coding: utf-8 -*-

from odoo import _, api, fields, models

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    pawn_id = fields.Many2one('pawn.pawn')