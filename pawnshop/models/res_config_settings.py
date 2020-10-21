# -*- coding: utf-8 -*-


from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_rate_loan = fields.Float(string="Rate Loan", default_model="pawn.pawn")
    default_rate_stock = fields.Float(string="Rate Stock", default_model="pawn.pawn")
    default_rate_admin = fields.Float(string="Rate Admin", default_model="pawn.pawn")

    

    
