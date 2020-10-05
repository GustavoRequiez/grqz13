# Copyright 2018 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging
from odoo import api, models
_logger = logging.getLogger(__name__)


class ProductLabelPicking(models.AbstractModel):
    _name = 'report.requiez.print_prod_label_picking'

    def decimal_format(self, num):
        return int(num)

    def op_name(self, move_id):
        move = self.env['stock.move'].search(
            [('move_dest_ids', 'in', [move_id])], limit=1)
        return move.production_id.name or ''

    def get_observation(self, move_id):
        move = self.env['stock.move'].search(
            [('move_dest_ids', 'in', [move_id])], limit=1)
        return move.production_id.sale_line_observation or ''

    def get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name(
            'requiez.print_prod_label_picking')
        docs = self.env['stock.picking'].browse(docids)

        return {
            'get_observation': self.get_observation,
            'op_name': self.op_name,
            'decimal_format': self.decimal_format,
            'doc_ids': docs.ids,
            'doc_model': report.model,
            'data': data,
            'docs': docs
        }


class ProductLabelMrp(models.AbstractModel):
    _name = 'report.requiez.print_prod_label_mrp'

    def decimal_format(self, num):
        return int(num)

    def get_data(self, mrp_id):
        query = """
        SELECT
            sp.scheduled_date,
            sot.name, rp.name,
            pp.default_code,
            pt.name,
            sol.observation,
            mp.product_qty,
            mp.name
        FROM
            mrp_production mp
        JOIN
            stock_move sm ON sm.production_id = mp.id
        JOIN
            stock_move_move_rel smd ON smd.move_orig_id = sm.id
        JOIN
            stock_move des ON des.id = smd.move_dest_id
        JOIN
            sale_order_line sol ON sol.id = des.sale_line_id
        JOIN
            sale_order so ON so.id = sol.order_id
        JOIN
            sale_order_type sot ON sot.id = so.type_id
        JOIN
            stock_picking sp ON sp.id = des.picking_id
        JOIN
            res_partner rp ON rp.id = mp.partner_id
        JOIN
            product_product pp ON pp.id = mp.product_id
        JOIN
            product_template pt ON pt.id = pp.product_tmpl_id
        WHERE
            mp.id = %s
        """
        self.env.cr.execute(query, tuple([mrp_id.id]))
        result = self.env.cr.fetchone()
        data = {}
        if result:
            data.update({'date': result[0], 'type': result[1],
                         'partner_name': result[2][:41],
                         'product_default': result[3],
                         'product_name': result[4],
                         'observation': result[5], 'qty': int(result[6]),
                         'mrp_name': result[7]})
        return data

    def _get_report_values(self, docids, data=None):
        report = self.env['ir.actions.report']._get_report_from_name(
            'requiez.print_prod_label_mrp')
        docs = self.env[report.model].browse(docids)
        return {
            'get_data': self.get_data,
            'decimal_format': self.decimal_format,
            'doc_ids': docs.ids,
            'doc_model': report.model,
            'data': data,
            'docs': docs,
        }
