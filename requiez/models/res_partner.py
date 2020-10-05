# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    credit_avaiable = fields.Monetary(
        compute='_get_credit_used'
    )
    credit_expired = fields.Boolean(
        compute='_get_credit_used',
    )
    credit_ignore = fields.Boolean(
        default=False,
    )
    credit_used = fields.Monetary(
        compute='_get_credit_used',
    )
    credit_limit = fields.Monetary()
    grace_days = fields.Integer()
    expired_ignore = fields.Boolean(
        default=False,
    )
    sale_order_ignore = fields.Boolean(
        default=False,
    )
    # pylint:disable=W8104

    def _get_credit_used(self):
        payment_term_credits_ids = (
            [payment.id
             for payment in self.env['account.payment.term'].search([])
             if payment.line_ids[-1] and payment.line_ids[-1].days >= 0])
        invoices = (self.env['account.invoice']
                    .search([
                        ('partner_id', '=', self.id),
                        ('state', '=', 'open'),
                        ('type', '=', 'out_invoice'),
                        ('payment_term_id', 'in', payment_term_credits_ids)]))
        if not self.expired_ignore:
            self.credit_expired = False
            today = fields.Date.from_string(fields.Date.today())
            for invoice in invoices:
                date_due = fields.Date.from_string(invoice.date_due)
                if date_due + timedelta(days=self.grace_days) <= today:
                    self.credit_expired = True
        self.credit_avaiable = self.credit_limit
        self.credit_used = 0
        company_currency = self.env.user.company_id.currency_id
        if not self.sale_order_ignore:
            for sale in (self.env['sale.order']
                         .search(
                             [('partner_id', '=', self.id),
                              ('state', '=', 'sale'),
                              ('invoice_status', '=', 'to invoice')])):
                self.credit_used += (
                    sale.currency_id.compute(sale.amount_total,
                                             company_currency))
        if not self.credit_ignore:
            for invoice in (invoices.filtered(lambda r:
                                              r.move_name.split('/')[0]
                                              != 'VNMSI')):
                self.credit_used += (
                    invoice.currency_id.compute(invoice.amount_total,
                                                company_currency))
        self.credit_avaiable -= self.credit_used
