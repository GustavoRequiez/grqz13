# Copyright 2018 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from datetime import datetime
import logging
from odoo import api, fields, models
_logger = logging.getLogger(__name__)


class SaleCommission(models.TransientModel):
    _name = "sale.commission"

    # @api.multi
    def calculate(self):
        sale_commission_det_obj = self.env['sale.commission.detail']
        sale_commission_brand_obj = self.env['sale.commission.brand']
        sale_commi_settings_obj = self.env['sale.commission.setting']
        association_obj = self.env['account.association']

        sale_commission_settings = sale_commi_settings_obj.search([], limit=1)
        commission_sett = sale_commission_settings.commission / 100
        settings_day = sale_commission_settings.day
        sale_commission_det_obj.search([]).unlink()

        date_start = self.date_start
        date_stop = self.date_end
        user_id = self.user_id.id
        # In the `account.association` model, payments to invoices and
        # their reconciliation date are stored.
        # We take the associations that are within the range of dates
        # and the user_id of the invoice selected in the wizard.
        association_ids = association_obj.search([
            ('date', '>=', date_start), ('date', '<=', date_stop),
            ('move_id.user_id.id', '=', user_id),
            ('move_id.type', '=', 'out_invoice'),
            ('move_id.state', 'in', ['open', 'paid']),
            ('aml_state', '=', 'posted'),
            # Filter out Credit Notes
            '|', ('aml_invoice_type', '=', False),
            ('aml_invoice_type', '!=', 'out_refund')],
            order='move_id'
        ).filtered(lambda a: a.payment_amount != 0.0)

        for assoc in association_ids:
            invoice = assoc.move_id

            # We look for the brand commission for this seller.
            commission_brand = 0
            if invoice.brand:
                sale_commission_brand = sale_commission_brand_obj.search([
                    ('user_id', '=', invoice.user_id.id),
                    ('brand_id', '=', invoice.brand)], limit=1)
                commission_brand = sale_commission_brand.commission / 100

            # We take the reconciliation date of the payment and
            # the due date of the invoice for the calculation of commission
            # and penalization (if exists a penalization).
            payment_date = assoc.move_line_id.date
            date_due = invoice.invoice_date_due

            def fnc(date):
                return datetime.strptime(date, '%Y-%m-%d')

            # If the payment was made after the due date of the invoice,
            # and is after the grace days configured in
            # `sale.commission.setting` then a penalization must be made to
            # the amount of the commission. Next, the calculation
            days_of_difference = (payment_date - date_due).days
            days_of_interest = days_of_difference if \
                days_of_difference > settings_day else 0

            amount = assoc.payment_amount
            penalization = ((
                amount * commission_sett) / 30) * days_of_interest
            amount_before_penalization = amount * commission_brand
            commission = (amount_before_penalization - penalization) if \
                amount_before_penalization > 0 else 0
            sale_commission_det_obj.create({
                'account_payment_amount': amount,
                'sale_commission_id': self.id,
                'account_move_id': invoice.id,
                'day_difference': days_of_difference,
                'day_int': days_of_interest,
                'penalization': penalization,
                'commission_brand': commission_brand,
                'before_penalization': amount_before_penalization,
                'commission': commission,
                'brand_id': sale_commission_brand and
                sale_commission_brand.brand_id.id,
                'account_payment_date': payment_date})

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'sale.commission',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }

    user_id = fields.Many2one('res.users', 'Salesman')
    date_start = fields.Date('Start Date', required=True)
    date_end = fields.Date('End Date', required=True)
    sale_commission_detail_ids = fields.One2many('sale.commission.detail',
                                                 'sale_commission_id',
                                                 'Details')
    commission_tax = fields.Float('Commission with tax',
                                  compute='_compute_commission',
                                  readonly=True)
    commission = fields.Float(compute='_compute_commission',
                              readonly=True)

    # @api.multi
    def print_commission(self):
        report = self.env['ir.actions.report']._get_report_from_name(
            'sale_commission.sale_commission_report_template')
        return report.report_action(self)

    # @api.multi
    def _compute_commission(self):
        self.commission_tax = sum([sale_commission_detail.commission
                                   for sale_commission_detail in
                                   self.sale_commission_detail_ids
                                   ])
        self.commission = self.commission_tax / 1.16


class SaleCommissionDetail(models.TransientModel):
    _name = "sale.commission.detail"

    # @api.multi
    def compute_currency_id(self):
        for record in self:
            record.currency_id = self.env.user.company_id.currency_id

    sale_commission_id = fields.Many2one('sale.commission', 'Commission')
    account_move_id = fields.Many2one('account.move', 'Invoice',
                                      readonly=True)
    account_invoice_number = fields.Char(related='account_move_id.name',
                                         string='Number', readonly=True)
    account_invoice_date = fields.Date(related='account_move_id.invoice_date_due',
                                       string='Invoice date', readonly=True)
    partner_id = fields.Many2one(related='account_move_id.partner_id',
                                 string='Customer', readonly=True)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  compute='compute_currency_id',
                                  readonly=True)
    account_payment_id = fields.Many2one('account.payment', 'Payment',
                                         readonly=True)
    account_payment_date = fields.Date(string='Payment date', readonly=True)
    account_payment_amount = fields.Monetary(string='Amount',
                                             currency_field="currency_id",
                                             readonly=True)
    day_difference = fields.Integer('Days of difference')
    day_int = fields.Integer('Days of interest')
    penalization = fields.Monetary('Penalty amount',
                                   currency_field="currency_id")
    before_penalization = fields.Monetary('Amount before penalty',
                                          currency_field="currency_id")
    commission = fields.Monetary(currency_field="currency_id")
    commission_brand = fields.Float(digits=(2, 4))
    brand_id = fields.Many2one('product.brand', string='Brand')
