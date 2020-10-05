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


class ProcessMeasurement(models.TransientModel):
    _name = 'process.measurement'
    _description = 'Process Measurement'

    name = fields.Char('Name', compute='_compute_get_name')
    csv_file = fields.Binary(attachment=True,
                             copy=False,
                             readonly=True)

    # # @api.multi
    def _compute_get_name(self):
        today = datetime.now().strftime('%d-%m-%Y')
        mname = "Order: %s.csv" % today
        self.name = mname

    # # @api.multi
    def get_csv_file(self):
        mrp_production_ids = self.env['mrp.production'].browse(
            self._context.get('active_ids'))
        order_list = []
        for order in mrp_production_ids:
            p1 = ''
            p2 = ''
            p3 = ''
            p4 = ''
            obs = ''
            if order.sale_line_observation:
                obs = order.sale_line_observation
                if 'ARMAD' in order.sale_line_observation:
                    p4 = 'Si'
            for route in order.product_id.route_ids:
                if route.name == 'TAPIZADO':
                    p1 = 'Si'
                elif route.name == 'COSTURA':
                    p2 = 'Si'
                elif route.name == 'MASSIMO':
                    p2 = 'Si'
                data = (
                    order.name.rstrip('\n'),
                    order.product_id.barcode.rstrip('\n'),
                    order.product_id.name.rstrip('\n'),
                    obs,
                    order.product_qty,
                    order.partner_id.name.rstrip('\n'),
                    order.date_planned_start,
                    order.sale_type_id.rstrip('\n'),
                    p1,
                    p2,
                    p3,
                    p4)
            order_list.append(data)

        handle, fn = tempfile.mkstemp(suffix='.csv')
        with os.fdopen(handle, "w", encoding='utf-8', errors='surrogateescape', newline='') as f:
            writer = csv.writer(
                f, delimiter=';', quoting=csv.QUOTE_MINIMAL)  # , quotechar='|'
            writer.writerow(['OP', 'PRODUCTO', 'NOMBRE', 'OBSERVACIONES', 'CANTIDAD', 'CLIENTE',
                             'VIGENTE DESDE', 'PRIORIDAD', 'TAPIZADO', 'COSTURA', 'EMPACADO', 'ARMADO'])
            try:
                writer.writerows(order_list)
            except Exception as e:
                msj = 'Error in writing row: %s' % e
                raise exceptions.Warning(msj)
            f.close()
            url = 'file://' + fn.replace(os.path.sep, '/')
            file = open(fn, "rb")
            out = file.read()
            file.close()
            self.csv_file = base64.b64encode(out)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'process.measurement',
            'view_mode': 'form',
            'view_type': 'form',
            'res_id': self.id,
            'views': [(False, 'form')],
            'target': 'new',
        }
