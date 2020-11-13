# -*- coding: utf-8 -*-
import logging
from datetime import date

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class PawnCreatePayment(models.TransientModel):
    _name = 'pawn.create.payment'
    _description = 'Pawn Create Payment'

    @api.model
    def default_get(self, values):
        res=super(PawnCreatePayment, self).default_get(values)
        order_id = self.env['pawn.order'].browse(
            self.env.context.get('active_id')
        )
        res.update({
            'amount_loan': order_id.amount_loan,
            'amount_stock': order_id.amount_stock,
            'amount_admin': order_id.amount_admin,
            'interests': order_id.interests,
        })
        return res

    amount = fields.Monetary(string='Amount')
    amount_loan = fields.Float(string="Amount Commision", readonly=True)
    amount_stock = fields.Float(string="Amount Stock", readonly=True)
    amount_admin = fields.Float(string="Amount Admin", readonly=True)
    interests = fields.Monetary(string='Interests', readonly=True)
    currency_id = fields.Many2one('res.currency', string='', default=lambda s: s.env.company.currency_id)

    def create_payment(self):
        order_id = self.env['pawn.order'].browse( self.env.context.get('active_id') )
        account_move = self.env['account.move']
        pawn_payment = self.env['pawn.payment']
        storage = self.env.ref('pawnshop.product_costo_almacenamiento')
        admin = self.env.ref('pawnshop.product_costo_administracion')
        loan = self.env.ref('pawnshop.product_interes_prestamo')

        if self.amount < self.interests:
            raise UserError(_('the payment must be made greater than or equal to the interest'))
        
        lines = [
            (0, 0, {'name': storage.name, 'product_id': storage.id, 'price_unit': self.amount_stock}),
            (0, 0, {'name': admin.name, 'product_id': admin.id, 'price_unit': self.amount_admin}),
            (0, 0, {'name': loan.name, 'product_id': loan.id, 'price_unit': self.amount_loan}),
        ]

        if self.amount > self.interests:
            lines.append(
                (0, 0, {'name': 'CAPITAL', 'price_unit': self.amount - self.interests}),
            )

        move_id = account_move.create( {
            'partner_id': order_id.partner_id.id,
            'invoice_line_ids': lines,
            'invoice_date': date.today(),
            'invoice_origin': order_id.name,
            'type': 'in_invoice',
        } )
        move_id.post()
        pawn_payment.create({
            'move_id': move_id.id,
            'amount': self.amount,
            'order_id': order_id.id,
            'interests': self.interests
        })
