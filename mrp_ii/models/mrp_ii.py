# -*- coding: utf-8 -*-
###############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2017 Humanytek (<www.humanytek.com>).
#    Rubén Bravo <rubenred18@gmail.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
###############################################################################

from odoo import api, fields, models
import logging
_logger = logging.getLogger(__name__)


class MrpIi(models.TransientModel):
    _name = "mrp.ii"

    # # @api.multi
    def calculate(self):
        bill_material_ii_obj = self.env['bill.material.ii']
        bill_material_ii_sale_obj = self.env['bill.material.ii.sale']
        bill_material_ii_purchase_obj = self.env['bill.material.ii.purchase']
        product_compromise_obj = self.env['product.compromise']
        stock_move_obj = self.env['stock.move']
        bill_material_ii_obj.search([]).unlink()
        for line in self.bom_id.bom_line_ids:
            bill_id = bill_material_ii_obj.create({
                'product_id': line.product_id.id,
                'mrp_ii_id': self.id,
                'qty_product': self.qty_product * line.product_qty})
            # REVISAR SI AQUI SE PUEDE BUSCAR POR UBICACION,
            # AUN NO SE SI SEA ORIGEN O DESTINO
            stock_moves = stock_move_obj.search([
                ('product_id', '=', line.product_id.id),
                ('state', 'in', ['assigned', 'confirmed',
                                 'partially_available']),
                ('raw_material_production_id', '!=', False), '|',
                ('location_id', '=', self.location_id.id),
                ('location_dest_id', '=', self.location_id.id)])
            for move in stock_moves:
                bill_material_ii_sale_obj.create({
                    'bill_material_ii_id': bill_id.id, 'move_id': move.id})
                product_compromises = product_compromise_obj.search([
                    ('product_id', '=', line.product_id.id),
                    ('state', '=', 'assigned'),
                    ('stock_move_out_id', '=', move.id)])
                for product_compromise in product_compromises:
                    bill_material_ii_purchase_obj.create({
                        'bill_material_ii_id': bill_id.id, 'move_id': move.id,
                        'move_in_id': product_compromise.stock_move_in_id.id})

        return {'type': 'ir.actions.act_window', 'res_model': 'mrp.ii',
                'view_mode': 'form',
                'view_type': 'form',
                'res_id': self.id,
                'views': [(False, 'form')],
                'target': 'new'}

    @api.model
    def _get_default_location_id(self):
        stock_location_obj = self.env['stock.location']
        stock_location = stock_location_obj.search(
            [('default_location', '=', True),
             ('company_id', '=', self.env.user.company_id.id)], limit=1)
        return stock_location.id

    # # @api.multi
    @api.onchange('product_id')
    def onchange_product_id(self):
        mrp_bom_obj = self.env['mrp.bom']
        for record in self:
            mrp_bom = mrp_bom_obj.search([
                ('product_tmpl_id', '=', record.product_id.id)], limit=1)
            record.bom_id = mrp_bom.id

    product_id = fields.Many2one('product.template', 'Product', required=True)
    qty_product = fields.Float('Quantity', required=True, default=1)
    bill_material_ii_ids = fields.One2many('bill.material.ii', 'mrp_ii_id',
                                           'BoM')
    location_id = fields.Many2one('stock.location', 'Location', required=True,
                                  default=_get_default_location_id)
    bom_id = fields.Many2one('mrp.bom', 'BOM', required=True)


class BillMaterialIi(models.TransientModel):
    _name = "bill.material.ii"

    mrp_ii_id = fields.Many2one('mrp.ii', 'MRP II')
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    qty_product = fields.Float('Quantity', readonly=True)
    bill_material_ii_sale_ids = fields.One2many('bill.material.ii.sale',
                                                'bill_material_ii_id',
                                                'BoM-Sale', readonly=True)
    bill_material_ii_purchase_ids = fields.One2many(
        'bill.material.ii.purchase', 'bill_material_ii_id', 'BoM-Purchase',
        readonly=True)
    product_qty_product = fields.Float('Total Product',
                                       compute='_compute_product_qty_product',
                                       readonly=True)
    product_incoming_qty = fields.Float(
        'Total Incoming Product',
        compute='_compute_product_incoming_qty', readonly=True)

    total_compromise_product = fields.Float(
        compute='_compute_total_compromise_product', readonly=True)

    total_reserved_product = fields.Float(
        compute='_compute_total_reserved_product', readonly=True)

    dis_product_in = fields.Float(
        'Availability Incoming Product', compute='_compute_dis_product_in',
        readonly=True)

    dis_product = fields.Float(
        'Availability Product', compute='_compute_dis_product', readonly=True)

    # # @api.multi
    def _compute_total_compromise_product(self):
        stock_move_obj = self.env['stock.move']
        product_compromise_obj = self.env['product.compromise']

        for record in self:
            stock_moves = stock_move_obj.search([
                ('product_id.id', '=', record.product_id.id),
                ('picking_type_id.code', '=', 'incoming'),
                ('state', 'not in', ['cancel', 'done']),
                ('location_dest_id', '=', record.mrp_ii_id.location_id.id)])

            commited_products = product_compromise_obj.search([
                ('product_id', '=', record.product_id.id),
                ('state', '=', 'assigned'),
                ('stock_move_in_id', 'in', stock_moves.ids)])

            record.total_compromise_product = sum([
                product.qty_compromise for product in commited_products])

    # @api.multi
    def _compute_total_reserved_product(self):
        stock_move_obj = self.env['stock.move']
        for record in self:
            stock_moves = stock_move_obj.search(
                [('product_id.id', '=', record.product_id.id),
                 ('state', 'in', [
                     'assigned', 'confirmed', 'partially_available']),
                 ('location_id', '=', record.mrp_ii_id.location_id.id)])

            record.total_reserved_product = sum([move.reserved_availability
                                                 for move in stock_moves])

    # @api.multi
    def _compute_product_qty_product(self):
        quant_obj = self.env['stock.quant']
        for record in self:
            quant_data = quant_obj.read_group([
                ('product_id', '=', record.product_id.id),
                ('location_id', 'child_of', record.mrp_ii_id.location_id.id)],
                ['product_id', 'quantity'], ['product_id'])
            if quant_data:
                record.product_qty_product = quant_data[0].get('quantity', 0.0)

    # @api.multi
    def _compute_product_incoming_qty(self):
        stock_move_obj = self.env['stock.move']
        for record in self:
            stock_move_data = stock_move_obj.read_group([
                ('product_id.id', '=', record.product_id.id),
                ('picking_type_id.code', '=', 'incoming'),
                ('state', 'not in', ['cancel', 'done']),
                ('location_dest_id', '=', record.mrp_ii_id.location_id.id)],
                ['product_id', 'product_uom_qty'], ['product_id'])
            if stock_move_data:
                record.product_incoming_qty = stock_move_data[0].get(
                    'product_uom_qty', 0.0)

    # @api.multi
    def _compute_dis_product_in(self):
        for record in self:
            record.dis_product_in = record.product_incoming_qty - \
                record.total_compromise_product

    # @api.multi
    def _compute_dis_product(self):
        for record in self:
            record.dis_product = record.product_qty_product - \
                record.total_reserved_product


class BillMaterialIiSale(models.TransientModel):
    _name = "bill.material.ii.sale"

    bill_material_ii_id = fields.Many2one('bill.material.ii', 'MRP II')
    move_id = fields.Many2one('stock.move', 'Move', required=True)
    product_qty = fields.Float(related='move_id.product_uom_qty',
                               string='Quantity', readonly=True, store=False)
    product_reserved_qty = fields.Float(related='move_id.reserved_availability',
                                        string='Quantity Reserved',
                                        readonly=True, store=False)
    sale_id = fields.Many2one(
        related='move_id.raw_material_production_id.sale_id',
        string='Sale Order', readonly=True, store=False)
    partner_id = fields.Many2one(
        related='move_id.raw_material_production_id.partner_id',
        string='Customer', readonly=True, store=False)


class BillMaterialIiPurchase(models.TransientModel):
    _name = "bill.material.ii.purchase"

    bill_material_ii_id = fields.Many2one('bill.material.ii', 'MRP II')
    move_id = fields.Many2one('stock.move', 'Move', required=True)
    move_in_id = fields.Many2one('stock.move', 'Move In', required=True)

    product_qty = fields.Float(related='move_id.product_uom_qty',
                               string='Quantity', readonly=True, store=False)
    sale_id = fields.Many2one(
        related='move_id.raw_material_production_id.sale_id',
        string='Sale Order', readonly=True, store=False)
    partner_id = fields.Many2one(
        related='move_id.raw_material_production_id.partner_id',
        string='Customer', readonly=True, store=False)
    compromise_product = fields.Float(compute='_compute_compromise_product',
                                      readonly=True)
    picking_purchase_order = fields.Char(
        related='move_in_id.picking_id.origin', string='Purchase Order',
        readonly=True, store=False)

    # @api.multi
    def _compute_compromise_product(self):
        product_compromise_obj = self.env['product.compromise']
        for record in self:
            commited_products = product_compromise_obj.search([
                ('product_id.id', '=', record.move_in_id.product_id.id),
                ('state', '=', 'assigned'),
                ('stock_move_in_id', '=', record.move_in_id.id),
                ('stock_move_out_id', '=', record.move_id.id)])
            record.compromise_product = sum([product.qty_compromise
                                             for product in commited_products])
