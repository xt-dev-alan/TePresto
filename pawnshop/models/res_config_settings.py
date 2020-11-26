# -*- coding: utf-8 -*-


from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    default_rate_loan = fields.Float(string="Rate Loan", default_model="pawn.pawn")
    default_rate_stock = fields.Float(string="Rate Stock", default_model="pawn.pawn")
    default_rate_admin = fields.Float(string="Rate Admin", default_model="pawn.pawn")
    default_rate_arrear = fields.Float(string="Rate Arrear", default_model="pawn.pawn")
    
    default_rate_loan_week = fields.Float(string="Rate Loan", default_model="pawn.pawn")
    default_rate_stock_week = fields.Float(string="Rate Stock", default_model="pawn.pawn")
    default_rate_admin_week = fields.Float(string="Rate Admin", default_model="pawn.pawn")
    default_rate_arrear_week = fields.Float(string="Rate Arrear", default_model="pawn.pawn")

    default_picking_type_id = fields.Many2one('stock.picking.type', string='Picking Type', default_model="pawn.order")

    

    
