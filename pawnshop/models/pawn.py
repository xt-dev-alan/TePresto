# -*- coding: utf-8 -*-

import logging

from datetime import date, datetime, timedelta
from num2words import num2words

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)

STATES = [
    ('draft', 'Draft'), 
    ('accept', 'Accepted'), 
    ('progress', 'Progress'),
    ('arrear', 'Arrear'),
    ('close', 'Close'),
    ('expired', 'Expired'),
    
]

PICKING_TYPE = {
    'accept': 'picking_type_pawn',
    'close': 'picking_type_pawn_out',
    'expired': 'picking_type_pawn_in',
}

class PawnPawn(models.Model):  
    _name = 'pawn.pawn'
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _description = 'Pawn'

    name = fields.Char(string='Name', required=True, default=_('New') )
    approved_date = fields.Date(string='Approved')
    due_date = fields.Date(string='Due Date', readonly=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda s: s.env.user.company_id.id)
    term = fields.Selection([('weekly', 'Weekly'), ('monthly', 'Monthly')], string='Term', required=True)
    order_id = fields.Many2one('pawn.order', string='Order', readonly=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda s: s.env.user)
    
    picking_ids = fields.One2many('stock.picking', 'pawn_id', string='Picking', readonly=True)
    delivery_count = fields.Integer(string='Delivery Orders', compute='_compute_picking_ids')

    state = fields.Selection(STATES, default='draft')
    type = fields.Selection([('pawn', 'Pawn'), ('sale', 'Sale')], string='Type', default='pawn', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda s: s.env.company.currency_id )
    rate_loan = fields.Float(string="Rate Commision", )
    rate_stock = fields.Float(string="Rate Stock", )
    rate_admin = fields.Float(string="Rate Admin", )
    rate_arrear = fields.Float(string="Rate Arrear", )
    rate_loan_week = fields.Float(string="Rate Commision", )
    rate_stock_week = fields.Float(string="Rate Stock", )
    rate_admin_week = fields.Float(string="Rate Admin", )
    rate_arrear_week = fields.Float(string="Rate Arrear", )
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
    categ_id = fields.Many2one('product.category', string='Category', required=True)
    product_description = fields.Text(string="Product Description")
    product_search_ids = fields.One2many('pawn.product.search', 'pawn_id', string='Product search')
    
    @api.depends('product_search_ids.amount', 'term', 'categ_id')
    def _compute_rates(self):
        for record in self:
            try:
                average = sum( record.product_search_ids.mapped('amount') ) / len( record.product_search_ids )
                amount = average * (record.categ_id.pawn_rate / 100)
            except:
                amount = 0.0
            record.update({
                'amount': amount,
                'amount_loan': amount * ( record.rate_loan / 100.0 if record.term == 'monthly' else record.rate_loan_week / 100.0),
                'amount_stock': amount * ( record.rate_stock / 100.0 if record.term == 'monthly' else record.rate_stock_week / 100.0),
                'amount_admin': amount * ( record.rate_admin / 100.0 if record.term == 'monthly' else record.rate_admin_week / 100.0),
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

    def action_arrears(self):
        for record in self:
            if record.state == 'arrear':
                record.write( {'state': 'expired'} )
                record.create_stock_move()
            else:
                rate_arrear = record.rate_arrear_week if record.term == 'week' else record.rate_arrear 
                record.order_id.write( {'rate_arrear': rate_arrear } )
                days = 4 if record.term == 'weekly' else 8
                record.write( {'due_date': date.today() + timedelta(days=days), 'state': 'arrear'} )

    def _create_product(self):
        product = self.env['product.product']
        product_id = product.create( {  'name': self.product_name, 
                                        'default_code': self.name,
                                        'barcode': self.name,
                                        'list_price': self.amount,
                                        'type': 'product',
                                        'categ_id': self.categ_id.id
                                    } )
        return product_id

    def action_accept(self):
        for record in self:
            partner_id = record._get_partner()
            product_id = record._create_product()
            approved_date = date.today()
            if len(record.product_search_ids) < 2:
                raise ValidationError(_('Error. You must add at least two lines'))
            
            if record.type == 'pawn': 
                days = 8 if record.term == 'weekly' else 30
                due_date = approved_date + timedelta(days=days)
            else:
                due_date = approved_date
            record.write( {
                            'state': 'accept' if record.type == 'pawn' else 'close',
                            'partner_id': partner_id.id,
                            'product_id': product_id.id,
                            'approved_date': approved_date,
                            'due_date': due_date,
                            'street': partner_id.street,
                            'city': partner_id.city,
                            'phone': partner_id.phone,
                        } )
            record.create_stock_move(type=record.type)
        
    def action_close(self):
        for record in self:
            record.write( {'state': 'close'} )
            record.create_stock_move()

    def create_order(self):
        pawn_order = self.env['pawn.order']
        for record in self:
            order_id = pawn_order.create( {
                                            'partner_id': record.partner_id.id,
                                            'term': record.term, 
                                            'rate_loan': record.rate_loan,
                                            'rate_stock': record.rate_stock,
                                            'rate_admin': record.rate_admin,
                                            'amount': record.amount
                                            } )
            record.write(  {'order_id': order_id.id, 'state': 'progress'} )

    def create_stock_move(self,type=False):
        for record in self:
            if record.state in ['accept', 'close', 'expired']:
                picking_type_id = self.env.ref('pawnshop.%s'% PICKING_TYPE[record.state])
                if type == 'sale':
                    picking_type_id = self.env.ref('stock.picking_type_in')
                picking_id = record._prepare_picking( picking_type_id )
                moves = self._create_stock_moves(picking_id, record.product_id)
                moves._action_assign()


    def _prepare_picking(self, picking_type_id):
        return self.env['stock.picking'].create({
            'picking_type_id': picking_type_id.id,
            'partner_id': self.partner_id.id,
            'date': datetime.now(),
            'pawn_id': self.id,
            'origin': self.name,
            'location_dest_id': picking_type_id.default_location_dest_id.id,
            'location_id': picking_type_id.default_location_src_id.id,
            'company_id': self.env.user.company_id.id,
        }) 


    def _create_stock_moves(self, picking_id, product_id):
        """ Prepare the stock moves data. This function
        returns a recordset ready to be used.
        """
        moves = self.env['stock.move']
        if product_id.type not in ['product', 'consu']:
            return moves
        values = {
            'name': picking_id.origin,
            'product_id': product_id.id,
            'product_uom': product_id.uom_id.id,
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

    
    @api.depends('picking_ids')
    def _compute_picking_ids(self):
        for order in self:
            order.delivery_count = len(order.picking_ids)

    def action_view_delivery(self):
        '''
        This function returns an action that display existing delivery orders
        of given sales order ids. It can either be a in a list or in a form
        view, if there is only one delivery order to show.
        '''
        action = self.env.ref('stock.action_picking_tree_all').read()[0]

        pickings = self.mapped('picking_ids')
        if len(pickings) > 1:
            action['domain'] = [('id', 'in', pickings.ids)]
        elif pickings:
            form_view = [(self.env.ref('stock.view_picking_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = pickings.id
        # Prepare the context.
        action['context'] = dict(self._context, default_partner_id=self.partner_id.id, default_origin=self.name)
        return action

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
    term = fields.Selection([('weekly', 'Weekly'), ('monthly', 'Monthly')], string='Term', readonly=True)
    partner_id = fields.Many2one('res.partner', string='Partner')
    user_id = fields.Many2one('res.users', string='User', default=lambda s: s.env.user)

    company_id = fields.Many2one('res.company', string='Company', default=lambda s: s.env.company, required=True, readonly=True)

    currency_id = fields.Many2one('res.currency', string='', default=lambda s: s.env.company.currency_id)
    note = fields.Text(string='Notes')

    payment_ids = fields.One2many('pawn.payment', 'order_id', string='Payments', readonly=True)

    rate_loan = fields.Float(string="Rate Commision", readonly=True)
    rate_stock = fields.Float(string="Rate Stock", readonly=True)
    rate_admin = fields.Float(string="Rate Admin", readonly=True)
    rate_arrear = fields.Float(string="Rate Arrear", readonly=True)

    amount_loan = fields.Float(string="Amount Commision", store=True, compute="_compute_balance")
    amount_stock = fields.Float(string="Amount Stock", store=True, compute="_compute_balance")
    amount_admin = fields.Float(string="Amount Admin", store=True, compute="_compute_balance")
    amount_arrear = fields.Float(string="Amount Arrear", store=True, compute="_compute_balance")
    amount = fields.Monetary(string='Amount', readonly=True)

    interests = fields.Monetary(string='Interests', store=True, compute="_compute_balance")
    balance = fields.Monetary(string='Balance', store=True, compute="_compute_balance")

    @api.depends('amount', 'payment_ids.amount', 'rate_arrear')
    def _compute_balance(self):
        pawn = self.env['pawn.pawn']
        for record in self:
            payment_total = sum( record.payment_ids.mapped( lambda p: p.amount - p.interests ) )
            balance = record.amount - payment_total
            if not balance:
                pawn_id = pawn.search([('order_id', '=', record.id)], limit=1)
                _logger.info( pawn_id )
                pawn_id.action_close()
            amount_loan = balance * (record.rate_loan / 100.0)
            amount_stock = balance * (record.rate_stock / 100.0)
            amount_admin = balance * (record.rate_admin/ 100.0)
            amount_arrear = balance * (record.rate_arrear/ 100.0)
            record.update({
                'amount_loan': amount_loan,
                'amount_stock': amount_stock,
                'amount_admin': amount_admin,
                'amount_arrear': amount_arrear,
                'interests': amount_loan + amount_stock + amount_admin + amount_arrear,
                'balance': balance
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


class PawnPayment(models.Model):
    _name = 'pawn.payment'
    _description = 'Pawn Payment'

    move_id = fields.Many2one('account.move', string='Move')
    amount = fields.Monetary(string='Amount')
    order_id = fields.Many2one('pawn.order', string='Order')
    interests = fields.Monetary(string='Interests')
    currency_id = fields.Many2one('res.currency', string='', default=lambda s: s.env.company.currency_id)


    