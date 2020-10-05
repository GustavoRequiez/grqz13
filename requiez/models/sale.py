# Copyright 2018 Vauxoo
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from datetime import timedelta
from odoo import fields, models, api, exceptions, _
_logger = logging.getLogger(__name__)


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    user_id = fields.Many2one(default=None, required=True)
    client_order_ref = fields.Char(required=True, copy=True)
    date_promised = fields.Datetime()

    # @api.multi
    @api.onchange('partner_id')
    def onchange_partner_id(self):
        """If the partner does not have a salesman this field should be filled
        out manually
        """
        res = super(SaleOrder, self).onchange_partner_id()
        values = {
            'user_id': self.partner_id.user_id.id
        }
        self.update(values)
        return res

    # @api.multi
    def action_confirm(self):
        payment_term_credits = (
            [payment
             for payment in (self.env['account.payment.term'].search([]))
             if payment.line_ids[-1] and payment.line_ids[-1].days >= 0])
        for order in self.filtered(lambda r: r.payment_term_id
                                   in payment_term_credits):
            if (not order.partner_id.expired_ignore
                    and order.partner_id.credit_expired):
                raise exceptions.Warning(
                    _("AT THE MOMENT, IT'S NOT AUTHORIZE A CREDIT SALE. "
                      "THE CLIENT HAS EXPIRED BALANCE "
                      "ON PREVIOUS INVOICES!. "
                      "FOR MORE INFORMATION CHECK INVOICING!"))
            company_currency = self.env.user.company_id.currency_id
            total = order.currency_id.compute(order.amount_total,
                                              company_currency)
            credit_used = order.partner_id.credit_used
            if not order.partner_id.credit_ignore and (
                    (credit_used + total) > order.partner_id.credit_limit):
                raise exceptions.Warning(
                    _("THE CLIENT DOESN'T HAVE ENOUGH "
                      "CREDIT FOR THE SALE!, "
                      "FOR MORE INFORMATION CHECK INVOICING!"))
        super(SaleOrder, self).action_confirm()

    # @api.multi
    @api.onchange('expected_date')
    def onchange_partner_shipping_id(self):
        # self.date_promised = self.commitment_date
        self.date_promised = self.expected_date
        self.commitment_date = self.expected_date
        return {}


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # @api.multi
    def _prepare_procurement_values(self, group_id=False):
        vals = super(SaleOrderLine, self)._prepare_procurement_values(group_id)
        vals['date_planned'] = self.order_id.date_promised
        return vals
