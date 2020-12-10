# -*- coding: utf-8 -*-
import logging
from datetime import date, timedelta

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
            'amount_arrear': order_id.amount_arrear,
            'residual_amount': order_id.balance + order_id.interests,
            'interests': order_id.interests,
        })
        return res

    amount = fields.Monetary(string='Amount')
    amount_loan = fields.Float(string="Amount Commision", readonly=True)
    amount_stock = fields.Float(string="Amount Stock", readonly=True)
    amount_admin = fields.Float(string="Amount Admin", readonly=True)
    amount_arrear = fields.Float(string="Amount Arrear", readonly=True)
    interests = fields.Monetary(string='Interests', readonly=True)
    residual_amount = fields.Monetary(string="Residual Amount", readonly=True)
    currency_id = fields.Many2one('res.currency', string='', default=lambda s: s.env.company.currency_id)

    def create_payment(self):
        order_id = self.env['pawn.order'].browse( self.env.context.get('active_id') )
        account_move = self.env['account.move']
        pawn_payment = self.env['pawn.payment']
        pawn = self.env['pawn.pawn']
        storage = self.env.ref('pawnshop.product_costo_almacenamiento')
        admin = self.env.ref('pawnshop.product_costo_administracion')
        loan = self.env.ref('pawnshop.product_interes_prestamo')
        arrear = self.env.ref('pawnshop.product_interes_mora')
        msg = ''

        if self.amount < self.interests:
            raise UserError(_('the payment must be made greater than or equal to the interest'))
        
        lines = [
            (0, 0, {'name': storage.name, 'product_id': storage.id, 'price_unit': self.amount_stock}),
            (0, 0, {'name': admin.name, 'product_id': admin.id, 'price_unit': self.amount_admin}),
            (0, 0, {'name': loan.name, 'product_id': loan.id, 'price_unit': self.amount_loan}),
        ]

        if self.amount_arrear:
            lines.append(
                (0, 0, {'name': arrear.name, 'product_id': arrear.id, 'price_unit': self.amount_arrear}),
            )

        if self.amount > self.interests:
            if self.amount > self.residual_amount:
                raise UserError(_('you cannot create a payment greater than the residual amount'))
            msg = 'Se abonaron %s %s al CAPITAL'%(self.amount - self.interests, self.currency_id.symbol)
            pawn_id = pawn.search( [('order_id', '=', order_id.id)] )
            days = 8 if pawn_id.term == 'weekly' else 30
            order_id.write( {'rate_arrear': 0.0} )
            pawn_id.write( {'due_date': date.today() + timedelta(days=days), 'state': 'progress'} )
        
        move_id = account_move.create( {
            'partner_id': order_id.partner_id.id,
            'invoice_line_ids': lines,
            'invoice_date': date.today(),
            'invoice_origin': order_id.name,
            'type': 'in_invoice',
            'narration': msg
        } )
        move_id.post()
        pawn_payment.create({
            'move_id': move_id.id,
            'amount': self.amount,
            'order_id': order_id.id,
            'interests': self.interests
        })

