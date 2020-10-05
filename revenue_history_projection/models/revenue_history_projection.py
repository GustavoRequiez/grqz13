# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).


from datetime import date, datetime, timedelta
import logging
from odoo import api, fields, models, exceptions

_logger = logging.getLogger(__name__)


class RevenueHistoryProjection(models.TransientModel):
    _name = 'revenue.history.projection'
    _description = 'Revenue history projection'

    projection_line_ids = fields.One2many(
        'revenue.history.projection.line', 'Projection_id', 'Details', store=True)

    type_report = fields.Selection([
        ('income', 'Income'),
        ('expenses', 'Expenses')
    ], string='Select a report type', default='income')

    @api.depends('projection_line_ids')
    def get_revenue_history_projection(self):
        week_colums = (1, 2, 3, 4, 5, 6, 7, 8)
        today = datetime.now().strftime('%Y/%m/%d')
        dt = datetime.strptime(today, '%Y/%m/%d')
        start = dt - timedelta(days=dt.weekday())
        year = start.strftime('%Y')
        account_invoice_obj = self.env['account.move']
        total_gral = 0.0
        projection_line_obj = self.env['revenue.history.projection.line']
        projection_line_obj.search([]).unlink()

        # validation report_type
        invoice_type = ()
        if self.type_report == "income":
            invoice_type = ('type', 'in', ('out_invoice', 'out_refund'))
        else:
            invoice_type = ('type', 'in', ('in_invoice', 'in_refund'))
        # validation report_type
        for w in week_colums:
            end = start + timedelta(days=6)
            week = start.isocalendar()[1]
            if w == 1:
                invoice_ids = account_invoice_obj.search(
                    [('state', '=', 'open'), ('date_due', '>=', today), ('date_due', '<=', end), invoice_type])
                date_range_from_week = '%s - %s' % (datetime.now().strftime('%d/%m/%Y'),
                                                    end.strftime('%d/%m/%Y'))
            elif w == 8:
                invoice_ids = account_invoice_obj.search(
                    [('state', '=', 'open'), ('date_due', '>=', start), invoice_type])
                date_range_from_week = ' Del %s en delante ' % start.strftime(
                    '%d/%m/%Y')
            else:
                invoice_ids = account_invoice_obj.search(
                    [('state', '=', 'open'), ('date_due', '>=', start), ('date_due', '<=', end), invoice_type])
                date_range_from_week = '%s - %s' % (
                    start.strftime('%d/%m/%Y'), end.strftime('%d/%m/%Y'))
            total = 0.0

            for i in invoice_ids:
                invoice_residual = 0.00
                if i.currency_id.name != 'MXN':
                    account_move_id = self.env['account.move'].search(
                        [('name', '=', str(i.number))])
                    for am in account_move_id.line_ids:
                        if am.debit > 0.00:
                            exchange_rate = am.debit / am.amount_currency
                            invoice_residual = i.residual * exchange_rate
                            break
                else:
                    invoice_residual = i.residual

                if i.type == 'out_refund':
                    invoice_residual = invoice_residual * -1

                projection_line_obj.create({
                    'Projection_id': self.id,
                    'week_number': week,
                    'date_range': date_range_from_week,
                    'invoice_number': i.number,
                    'partner_name': i.partner_id.name,
                    'date_due': i.date_due,
                    'residual': invoice_residual})

            start = start + timedelta(days=7)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'revenue.history.projection.line',
            'view_mode': 'pivot',
            'view_type': 'pivot',
            'res_id': self.id,
            'views': [(False, 'pivot')],
            'target': 'new',
        }


class RevenueHistoryProjectionLine(models.TransientModel):
    _name = 'revenue.history.projection.line'
    _description = 'Revenue history projection Lines'

    Projection_id = fields.Many2one(
        'revenue.history.projection', 'Projection')
    week_number = fields.Integer('Week number')
    date_range = fields.Char('Week range')
    invoice_number = fields.Char('Invoice')
    partner_name = fields.Char('Partner')
    date_due = fields.Date('Date due')
    residual = fields.Float('Residual', digit=(8, 2))
