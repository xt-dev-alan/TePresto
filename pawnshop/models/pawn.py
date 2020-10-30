# -*- coding: utf-8 -*-

import logging

from datetime import date, datetime
from num2words import num2words

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)

STATES = [
    ('draft', 'draft'), 
    ('accept', 'Accepted'), 
    ('progress', 'Progress'),
    ('close', 'Close')
]

class PawnPawn(models.Model):
    _name = 'pawn.pawn'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Pawn'

    name = fields.Char(string='Name', required=True, default=_('New') )
    date = fields.Date(string='Date', default=date.today())
    approved_date = fields.Date(string='Approved')
    order_id = fields.Many2one('pawn.order', string='Order')
    user_id = fields.Many2one('res.users', string='User', default=lambda s: s.env.user)
    state = fields.Selection(STATES, default='draft')
    type = fields.Selection([('pawn', 'Pawn'), ('sale', 'Sale')], string='Type', default='pawn', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda s: s.env.company.currency_id )
    rate_loan = fields.Float(string="Rate Commision", )
    rate_stock = fields.Float(string="Rate Stock", )
    rate_admin = fields.Float(string="Rate Admin", )
    amount_loan = fields.Float(string="Rate Commision", compute="_compute_rates", store=True)
    amount_stock = fields.Float(string="Rate Stock", compute="_compute_rates", store=True)
    amount_admin = fields.Float(string="Rate Admin", compute="_compute_rates", store=True)
    amount = fields.Monetary(string='Amount', compute="_compute_rates", store=True)


    partner_name = fields.Char(string='Partner Name', required=True)
    partner_vat = fields.Char(string='Partner Vat', required=True)
    partner_id = fields.Many2one('res.partner', string='Partner', readonly=True)
    street = fields.Char()
    city = fields.Char()
    phone = fields.Char()

    product_name = fields.Char(string='Product Name', required=True)
    product_id = fields.Many2one('product.product', string='Product', readonly=True)
    product_description = fields.Text(string="Product Description")
    product_search_ids = fields.One2many('pawn.product.search', 'pawn_id', string='Product search')
    
    @api.depends('product_search_ids.amount')
    def _compute_rates(self):
        for record in self:
            try:
                amount = sum( record.product_search_ids.mapped('amount') ) / len( record.product_search_ids )
            except:
                amount = 0.0
            record.update({
                'amount': amount,
                'amount_loan': amount * ( record.rate_loan / 100.0),
                'amount_stock': amount * ( record.rate_stock / 100.0),
                'amount_admin': amount * ( record.rate_admin / 100.0),
            })

    def _get_partner(self):
        partner = self.env['res.partner']
        partner_id = partner.search( [('vat', '=', self.partner_vat)], limit=1)
        if not partner_id:
            partner_id = partner.create(  {
                                            'name': self.partner_name, 
                                            'vat': self.partner_vat,
                                            'type': 'contact'} )
        return partner_id


    def _create_product(self):
        product = self.env['product.product']
        categ_id = self.env.ref('pawnshop.categ_empeño')
        product_id = product.create( {  'name': self.product_name, 
                                        'default_code': self.name,
                                        'barcode': self.name,
                                        'list_price': self.amount,
                                        'type': 'product',
                                        'categ_id': categ_id.id
                                    } )
        return product_id

    def action_accept(self):
        for record in self:
            partner_id = record._get_partner()
            product_id = record._create_product()
            record.write( {
                            'state': 'accept',
                            'partner_id': partner_id.id,
                            'product_id': product_id.id,
                            'approved_date': date.today(),
                            'street': partner_id.street,
                            'city': partner_id.city,
                            'phone': partner_id.phone,
                        } )
        

    def create_order(self):
        pawn_order = self.env['pawn.order']
        storage = self.env.ref('pawnshop.product_costo_almacenamiento')
        admin = self.env.ref('pawnshop.product_costo_administracion')
        loan = self.env.ref('pawnshop.product_interes_prestamo')
        for record in self:
            lines = [
                (0, 0, {'name': storage.name, 'product_id': storage.id, 'price': record.amount_stock}),
                (0, 0, {'name': admin.name, 'product_id': admin.id, 'price': record.amount_admin}),
                (0, 0, {'name': loan.name, 'product_id': loan.id, 'price': record.amount_loan}),
                (0, 0, {'name': record.product_id.name, 'product_id': record.product_id.id, 'price': record.amount})                
                ]
            order_id = pawn_order.create( {'partner_id': record.partner_id.id, 'line_ids': lines} )
            record.write(  {'order_id': order_id.id, 'state': 'progress'} )



    @api.onchange('street', 'city', 'phone')
    def _onchange_partner(self):
        if not self.partner_id:
            return
        self.partner_id.street = self.street
        self.partner_id.city = self.city
        self.partner_id.phone = self.phone


    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('pawn.pawn') or _('New')
        result = super(PawnPawn, self).create(vals)
        return result


class PawnProductSearch(models.Model):
    _name = 'pawn.product.search'
    _description = 'Pawn Product Search'

    name = fields.Char(string='Name', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda s: s.env.company.currency_id )
    attachment = fields.Binary(string='Attachment')
    amount = fields.Monetary(string='Amount', required=True)
    pawn_id = fields.Many2one('pawn.pawn', string='Pawn')


class PawnOrder(models.Model):

    _name = 'pawn.order'
    _description = 'Pawn order'

    name = fields.Char(string='Name', required=True, readonly=True)
    date = fields.Date(string='Date', required=True, default=date.today())
    date_due = fields.Date(string='Date', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    user_id = fields.Many2one('res.users', string='User', default=lambda s: s.env.user)

    company_id = fields.Many2one('res.company', string='Company', default=lambda s: s.env.company, required=True, readonly=True)
    picking_type_id = fields.Many2one('stock.picking.type', string='Picking Type', required=True, readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Picking', readonly=True)

    move_id = fields.Many2one('account.move', string='Invoice')
    currency_id = fields.Many2one('res.currency', string='', default=lambda s: s.env.company.currency_id)
    note = fields.Text(string='Notes')

    line_ids = fields.One2many('pawn.order.line', 'order_id', string='Lines')

    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')


    def create_invoice(self):
        account_move = self.env['account.move']
        for record in self:
            lines = []
            picking_id = record._prepare_picking()
            moves = self._create_stock_moves(picking_id, record.line_ids)
            moves._action_assign()

            for l in record.line_ids:
                lines.append( (0, 0, {
                    'name': l.name, 
                    'product_id': l.product_id.id,
                    'tax_ids': [(6, 0, l.taxes_id.ids)],
                    'price_unit': l.price,
                    'quantity': 1.0
                }) )

            move_id = account_move.create( {
                'partner_id': record.partner_id.id,
                'invoice_line_ids': lines,
                'invoice_date': record.date,
                'invoice_origin': record.name,
                'type': 'in_invoice',
            } )
            record.write( {'picking_id': picking_id.id, 'move_id': move_id.id} )



    def _prepare_picking(self):
        return self.env['stock.picking'].create({
            'picking_type_id': self.picking_type_id.id,
            'partner_id': self.partner_id.id,
            'date': datetime.now(),
            'origin': self.name,
            'location_dest_id': self.picking_type_id.default_location_dest_id.id,
            'location_id': self.picking_type_id.default_location_src_id.id,
            'company_id': self.company_id.id,
        }) 
		 


    def _create_stock_moves(self, picking_id, lines):
        """ Prepare the stock moves data for one order line. 
        This function returns a recordset ready to be used.
        """
        moves = self.env['stock.move']
        for line in lines:
            if line.product_id.type not in ['product', 'consu']:
                continue
            values = {
                'name': picking_id.origin,
                'product_id': line.product_id.id,
                'product_uom': line.product_id.uom_id.id,
                'date': picking_id.date,
                'date_expected': picking_id.date,
                'location_id': picking_id.picking_type_id.default_location_src_id.id,
                'location_dest_id': picking_id.picking_type_id.default_location_dest_id.id,
                'product_uom_qty': 1.0,
                'picking_id': picking_id.id,
                'partner_id': picking_id.partner_id.id,
                'state': 'draft',
                'company_id': picking_id.company_id.id,
                'picking_type_id': picking_id.picking_type_id.id,
                'origin': picking_id.name,
                'route_ids': picking_id.picking_type_id.warehouse_id and [(6, 0, [x.id for x in picking_id.picking_type_id.warehouse_id.route_ids])] or [],
                'warehouse_id': picking_id.picking_type_id.warehouse_id.id,
                }
            moves |= moves.create(values)
        return moves._action_confirm()

    @api.depends('line_ids.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = 0.0
            for line in order.line_ids:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
            order.update({
                'amount_untaxed': amount_untaxed,
                'amount_tax': amount_tax,
                'amount_total': amount_untaxed + amount_tax,
            })


    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('pawn.order') or _('New')
        result = super(PawnOrder, self).create(vals)
        return result


    def action_view_invoice(self):
        '''
        This function returns an action that display existing vendor bills of given purchase order ids.
        When only one found, show the vendor bill immediately.
        '''
        action = self.env.ref('account.action_move_in_invoice_type')
        result = action.read()[0]
        res = self.env.ref('account.view_move_form', False)
        form_view = [(res and res.id or False, 'form')]
        result['views'] = form_view
        result['res_id'] = self.move_id.id or False
        return result

class PawnOrderLine(models.Model):

    _name = 'pawn.order.line'
    _description = 'Pawn order line'


    name = fields.Char(string='Description', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    taxes_id = fields.Many2many('account.tax', string='Taxes')
    price = fields.Monetary(string='Price', required=True)
    order_id = fields.Many2one('pawn.order', string='Order')
    currency_id = fields.Many2one('res.currency', string='', default=lambda s: s.env.company.currency_id)

    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', readonly=True, store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Total Tax', readonly=True, store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', readonly=True, store=True)

    @api.depends('price', 'taxes_id')
    def _compute_amount(self):
        """
        Compute the amounts of the pawn order line.
        """
        for line in self:
            taxes = line.taxes_id.compute_all(line.price, line.currency_id, 1.0, product=line.product_id, partner=line.order_id.partner_id)
            line.update({
                'price_tax': sum(t.get('amount', 0.0) for t in taxes.get('taxes', [])),
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })





    

    