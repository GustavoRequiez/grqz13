# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).


from datetime import date, datetime, timedelta
import logging
import csv
import codecs
import base64
import tempfile
import os
from odoo import api, fields, models, exceptions, _

_logger = logging.getLogger(__name__)


class ValueMerchandiseSent(models.TransientModel):
    _name = 'value.merchandise.sent'
    _description = 'Value of merchandise sent'

    name = fields.Char('Name', default='Merchandise Value.csv')

    csv_file = fields.Binary(attachment=True,
                             copy=False,
                             readonly=True)

    getted = fields.Boolean('Getted', default=False)

    # @api.multi
    def get_csv_file(self):

        def get_merchandise_value(ids):
            total_value = 0
            for line in ids:
                sale_order_line_id = sale_order_line_obj.search(
                    [('id', '=', line.sale_line_id.id)])
                price_unit = sale_order_line_id.price_unit
                discount = sale_order_line_id.discount
                if discount > 0.0:
                    sub_total = line.quantity_done * price_unit
                    value = sub_total - (sub_total * (discount / 100))
                    total_value += value
                else:
                    total_value += line.quantity_done * price_unit
            return total_value

        sale_order_line_obj = self.env["sale.order.line"]
        stock_picking_ids = self.env['stock.picking'].browse(
            self._context.get('active_ids'))
        data_list = []
        for picking in stock_picking_ids:
            merchandise_value = get_merchandise_value(picking.move_lines)
            tracking_ref = ''
            pname = ''
            if picking.carrier_tracking_ref:
                tracking_ref = picking.carrier_tracking_ref
            if picking.partner_id.parent_name:
                pname = picking.partner_id.parent_name
            else:
                pname = picking.partner_id.name
            data = (
                picking.origin,
                picking.name,
                pname,
                picking.carrier_id.name,
                merchandise_value,
                tracking_ref)
            data_list.append(data)

        handle, fn = tempfile.mkstemp(suffix='.csv')
        with os.fdopen(handle, "w", encoding='utf-8', errors='surrogateescape', newline='') as f:
            writer = csv.writer(
                f, delimiter=';', quoting=csv.QUOTE_MINIMAL)  # , quotechar='|'
            writer.writerow(['PEDIDO', 'VALE DE ENTRAGA',
                             'CLIENTE', 'TRANSPORTE', 'VALOR', 'GUIA', ])
            try:
                writer.writerows(data_list)
            except Exception as e:
                msj = 'Error in writing row: %s' % e
                raise exceptions.Warning(msj)
            f.close()
            url = 'file://' + fn.replace(os.path.sep, '/')
            file = open(fn, "rb")
            out = file.read()
            file.close()
            self.csv_file = base64.b64encode(out)

        if self.csv_file:
            self.getted = True

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'value.merchandise.sent',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
