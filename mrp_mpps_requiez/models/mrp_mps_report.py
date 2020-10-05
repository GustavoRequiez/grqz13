# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime
from dateutil import relativedelta
import babel.dates
import pytz

from odoo import api, fields, models, _
from odoo.tools.misc import DEFAULT_SERVER_DATETIME_FORMAT


NUMBER_OF_COLS = 12

#
# TODO: This object should be removed, use a controller instead of an object to generate the report
#


class MrpMpsReport(models.TransientModel):
    _name = 'mrp.mps.report'
    _description = 'MPS Report'

    def _default_manufacturing_period(self):
        return self.env.user.company_id.manufacturing_period

    company_id = fields.Many2one('res.company', string="Company",
                                 default=lambda self: self.env['res.company']._company_default_get('mrp.mps.report'), required=True)
    period = fields.Selection([('month', 'Monthly'), ('week', 'Weekly'), (
        'day', 'Daily')], default=_default_manufacturing_period, string="Period")
    # TODO: this object should not be used as wizard and as report
    product_id = fields.Many2one('product.product', string='Product')

    # @api.multi
    def add_product_mps(self):
        MrpBomLine = self.env['mrp.bom.line']
        for mps in self:
            mps.product_id.write({
                'mps_active': True,
                'apply_active': self.env['mrp.bom']._bom_find(product=mps.product_id, company_id=mps.company_id.id) and True or False})
            # If you add a difference account
            boms = MrpBomLine.search(
                [('product_id', '=', mps.product_id.id)]).mapped('bom_id')
            for bom in boms:
                products = (bom.product_id or (
                    bom.product_tmpl_id.product_variant_ids)).filtered(lambda x: x.mps_active)
                if products:
                    products.apply_active = True
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    @api.model
    def get_indirect(self, product, date=False, date_to=False):
        domain = [('product_id', '=', product.id)]
        data = self.env['sale.forecast.indirect'].search(domain)
        result = {product.id: {}}
        for d in data:
            result.setdefault(d.product_id.id, {})
            result[d.product_id.id].setdefault(d.date, 0.0)
            result[d.product_id.id][d.date] += d.quantity
        return result

    @api.model
    def _set_indirect(self, product, data):
        self.env['sale.forecast.indirect'].search(
            [('product_origin_id', '=', product.id)]).unlink()
        BoM = self.env['mrp.bom']
        #products_to_calculate = [(product, datas),]

        products_to_calculate = {product: []}
        for inner_data in data:
            products_to_calculate[product].append({'lead': 0.0,
                                                   'qty': inner_data['to_supply'],
                                                   'date': fields.Date.from_string(inner_data['date']),
                                                   })
        original_product = product
        while products_to_calculate:
            (product, product_lines) = products_to_calculate.popitem()
            # TODO: how is it possible not to find a BoM here?
            bom = BoM._bom_find(product=product)
            if not bom:
                break
            # TODO: Take into account security days on company level
            product_qty = bom.product_uom_id._compute_quantity(
                bom.product_qty, product.uom_id)
            explored_boms, explored_lines = bom.explode(
                product, 1.0 / product_qty)
            for bom_line, line_data in explored_lines:

                # If the product is in the report, add it to the objects of the report immediately,
                # else search further and add to products_to_calculate if you find something
                if bom_line.product_id.mps_active:
                    for supply_line in product_lines:
                        lead = product.produce_delay + supply_line['lead']
                        qty = bom_line.product_uom_id._compute_quantity(
                            line_data['qty'], bom_line.product_id.uom_id)
                        self.env['sale.forecast.indirect'].create({
                            'product_origin_id': original_product.id,
                            'product_id': bom_line.product_id.id,
                            'quantity': qty * supply_line['qty'],
                            'date': supply_line['date'] - relativedelta.relativedelta(days=product.produce_delay)
                            # The date the product is needed (don't calculate its own lead time)
                        })
                    if BoM._bom_find(product=bom_line.product_id):
                        bom_line.product_id.apply_active = True
                else:
                    # If there is a child BoM, add them to the dictionary
                    bom = BoM._bom_find(product=bom_line.product_id)
                    if bom:
                        products_to_calculate.setdefault(
                            bom_line.product_id, [])
                        qty = bom_line.product_uom_id._compute_quantity(
                            line_data['qty'], bom_line.product_id.uom_id)
                        for supply_line in product_lines:
                            lead = supply_line['lead'] + \
                                bom_line.product_id.produce_delay
                            products_to_calculate[bom_line.product_id].append({
                                'lead': lead,
                                'qty': qty * supply_line['qty'],
                                'date': supply_line['date'] - relativedelta.relativedelta(days=product.produce_delay),
                            })
        return True

    @api.model
    def update_indirect(self, product):
        forcast = self.search([])[0]
        if isinstance(product, int):
            product = self.env['product.product'].browse(product)
        product.apply_active = False
        datas = forcast.get_data(product)
        self._set_indirect(product, datas)
        return True

    # @api.multi
    def get_data(self, product):
        result = []
        forecasted = product.mps_forecasted
        date = fields.Date.today()
        local_tz = pytz.timezone(self.env.context.get('tz') or 'UTC')
        indirect = self.get_indirect(product)[product.id]
        display = _('To Receive / To Supply / Produce')
        buy_type = self.env.ref(
            'purchase_stock.route_warehouse0_buy', raise_if_not_found=False)
        mo_type = self.env.ref(
            'mrp.route_warehouse0_manufacture', raise_if_not_found=False)
        lead_time = 0
        if buy_type and buy_type.id in product.route_ids.ids:
            lead_time = (
                product.seller_ids and product.seller_ids[0].delay or 0) + self.env.user.company_id.po_lead
        if mo_type and mo_type.id in product.route_ids.ids:
            lead_time = product.produce_delay + self.env.user.company_id.manufacturing_lead
        leadtime = date + relativedelta.relativedelta(days=int(lead_time))
        # Take first day of month or week
        if self.period == 'month':
            date = datetime.date(date.year, date.month, 1)
        elif self.period == 'week':
            date = date - relativedelta.relativedelta(days=date.weekday())

        if date < fields.Date.today():
            initial = product.with_context(
                to_date=date.strftime('%Y-%m-%d')).qty_available
        else:
            initial = product.qty_available
        # Compute others cells
        for p in range(NUMBER_OF_COLS):
            if self.period == 'month':
                date_to = date + relativedelta.relativedelta(months=1)
                name = date.strftime('%b')
                name = babel.dates.format_date(
                    format="MMM YY", date=date, locale=self._context.get('lang') or 'en_US')
            elif self.period == 'week':
                date_to = date + relativedelta.relativedelta(days=7)
                name = _('Week %s') % babel.dates.format_datetime(
                    date, format="w",
                    locale=self._context.get('lang') or 'en_US'
                )
            else:
                date_to = date + relativedelta.relativedelta(days=1)
                name = babel.dates.format_date(
                    format="MMM d", date=date, locale=self._context.get('lang') or 'en_US')
            forecasts = self.env['sale.forecast'].search([
                ('date', '>=', date.strftime('%Y-%m-%d')),
                ('date', '<', date_to.strftime('%Y-%m-%d')),
                ('product_id', '=', product.id),
            ])
            state = 'draft'
            mode = 'auto'
            proc_dec = False
            for f in forecasts:
                if f.mode == 'manual':
                    mode = 'manual'
                if f.state == 'done':
                    state = 'done'
                    proc_dec = True
            demand = sum(forecasts.filtered(
                lambda x: x.mode == 'auto').mapped('forecast_qty'))
            indirect_total = 0.0
            for day, qty in indirect.items():
                if (day >= date) and (day < date_to):
                    indirect_total += qty
            to_supply = product.mps_forecasted - initial + demand + indirect_total
            to_supply = max(to_supply, product.mps_min_supply)
            if product.mps_max_supply > 0:
                to_supply = min(product.mps_max_supply, to_supply)
            # Need to compute auto and manual separately as forecasts are still important
            if mode == 'manual':
                to_supply = sum(forecasts.filtered(
                    lambda x: x.mode == 'manual').mapped('to_supply'))
            if proc_dec:
                wh = self.env['stock.warehouse'].search([], limit=1)
                loc = wh.lot_stock_id
                purchase_lines = self.env['purchase.order.line'].search([('order_id.picking_type_id.default_location_dest_id', 'child_of', loc.id),
                                                                         ('product_id',
                                                                          '=', product.id),
                                                                         ('state', 'in', ('draft',
                                                                                          'sent', 'to approve')),
                                                                         ('date_planned', '>=', date.strftime(
                                                                             '%Y-%m-%d')),
                                                                         ('date_planned', '<', date_to.strftime('%Y-%m-%d'))])
                move_lines = self.env['stock.move'].search([('location_dest_id', 'child_of', loc.id),
                                                            ('product_id',
                                                             '=', product.id),
                                                            ('state', 'not in', [
                                                             'done', 'cancel', 'draft']),
                                                            ('location_id.usage',
                                                             '!=', 'internal'),
                                                            ('date_expected', '>=', date.strftime(
                                                                '%Y-%m-%d')),
                                                            ('date_expected', '<', date_to.strftime('%Y-%m-%d'))])
                to_supply = sum([x.product_uom._compute_quantity(x.product_qty, x.product_id.uom_id)
                                 for x in purchase_lines]) + sum([x.product_qty for x in move_lines])
            forecasted = to_supply - demand + initial - indirect_total
            result.append({
                'period': name,
                'date': date.strftime('%Y-%m-%d'),
                'date_to': date_to.strftime('%Y-%m-%d'),
                'initial': initial,
                'demand': demand,
                'mode': mode,
                'state': state,
                'indirect': indirect_total,
                'to_supply': to_supply,
                'forecasted': forecasted,
                'route_type': display,
                'procurement_enable': True if not proc_dec and leadtime >= date else False,
                'procurement_done': proc_dec,
                'lead_time': leadtime.strftime('%Y-%m-%d'),
            })
            initial = forecasted
            date = date_to
        return result

    @api.model
    def get_html(self, domain=[]):
        res = self.search([], limit=1)
        if not res:
            res = self.create({})
        domain.append(['mps_active', '=', True])
        rcontext = {
            'products': [(x, res.get_data(x)) for x in self.env['product.product'].search(domain, limit=20)],
            'nb_periods': NUMBER_OF_COLS,
            'company': self.env.user.company_id,
            'format_float': self.env['ir.qweb.field.float'].value_to_html,
        }
        result = {
            'html': self.env.ref('mrp_mps.report_inventory').render(rcontext),
            'report_context': {'nb_periods': NUMBER_OF_COLS, 'period': res.period},
        }
        return result
