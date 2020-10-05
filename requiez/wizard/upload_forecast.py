# Copyright 2018 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import logging
import base64
from odoo import models, fields, api, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class UploadForecast(models.TransientModel):
    _name = "upload.forecast"

    name = fields.Char('File Name')
    data_file = fields.Binary('File')
    state = fields.Selection(
        [('choose', 'choose'),
         ('get', 'get')],
        default='choose')

    def confirm(self):
        # pylint: disable=C0103
        ProductProduct = self.env['product.product']
        SaleForecast = self.env['sale.forecast']
        data_file = self.data_file
        data_file_decoded = base64.b64decode(data_file)
        aux = data_file_decoded.split('\n')
        num_line = 0
        list_projects = []
        for line in aux[:-1]:
            if num_line == 0:
                line_aux = line.split(';')
                num_line += 1
                continue
            num_line += 1
            column = line.split(';')
            products = ProductProduct.search(
                [('default_code', '=', column[0])])
            if not products:
                error = 'the product does not exist! line: ' + str(num_line)
                raise UserError(_(error))
            if products.id not in list_projects:
                SaleForecast.search(
                    [('product_id.id', '=', products.id)]).unlink()
                products.write(
                    {'mps_active': True, 'apply_active': True})
                list_projects.append(products.id)
            try:
                cont = 1
                for col in column[1:]:
                    _logger.info('Running Forecast')
                    _logger.info(products.id)
                    _logger.info(line_aux[cont].strip())
                    _logger.info(col.strip())
                    SaleForecast.create(
                        {'product_id': products.id,
                         'date': line_aux[cont].strip(),
                         'forecast_qty': col.strip()})
                    cont += 1
            except BaseException:
                error = 'check the line: ' + str(num_line)
                raise UserError(_(error))
            continue
