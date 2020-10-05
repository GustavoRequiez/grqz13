# Copyright 2018 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging
from odoo import api, models, fields

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = 'stock.picking'

    box = fields.Integer('Boxes', default=1, help="Boxes number.")

    stock_move_ids = fields.One2many(
        'stock.move', 'picking_id', 'Stock Moves')

    account_moves = fields.One2many('account.move', 'stock_move_id',
                                    'Jornal Entry', compute='_compute_get_account_moves')

    def _compute_get_account_moves(self):
        account_move_ids = []
        for move in self.stock_move_ids:
            account_move_ids.append(move.id)
        related_recordset = self.env["account.move"].search(
            [('stock_move_id', 'in', account_move_ids)])
        self.account_moves = related_recordset

    def _add_delivery_cost_to_so(self):
        """Creates the delivery line within the sale order only when the
        carrier price is different from zero."""
        self.ensure_one()
        if not self.carrier_price:
            return None
        return super(StockPicking, self)._add_delivery_cost_to_so()


class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    def _get_orderpoint_domain(self, company_id=False):
        domain = super(ProcurementGroup, self)._get_orderpoint_domain(
            company_id=company_id)
        domain += [('mps', '=', False)]
        return domain


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    mps = fields.Boolean('MPS')
