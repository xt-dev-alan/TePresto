# -*- coding: utf-8 -*-

import logging

from odoo import _, api, fields, models
_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    dpi = fields.Char(string="DPI")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if  not vals.get('ref'):
                vals['ref'] = self.env['ir.sequence'].next_by_code('pawn.partner')
        return super(ResPartner, self).create(vals_list)
    