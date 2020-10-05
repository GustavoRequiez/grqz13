# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

from datetime import date, datetime, timedelta
import logging
import csv
import codecs
import base64
import tempfile
import os
from odoo import models, fields, api, exceptions, _
from odoo.exceptions import UserError
import xlrd

_logger = logging.getLogger(__name__)


class UploadCarrierTracking(models.TransientModel):
    _name = 'upload.carrier.tracking'
    _description = 'Mass reference load of tracking guides'

    name = fields.Char('File Name', default='status.csv')
    data_file = fields.Binary('File')
    csv_file = fields.Binary(attachment=True,
                             copy=False,
                             readonly=True)

    getted = fields.Boolean('Getted', default=False)

    # @api.multi
    def confirm(self):
        # function to send email with information of tracking to partner
        def send_tracking_ref(picking_id):
            stockpickingid = self.env['stock.picking'].search(
                [('id', '=', picking_id)])

            attach_name = stockpickingid.name.replace('/', '_')
            attachment_id = self.env['ir.attachment'].search([
                ('res_id', '=', stockpickingid.id),
                ('res_model', '=', 'stock.picking'),
                '|', ('name', '=', attach_name + '.pdf'), ('name', '=', stockpickingid.name + '.pdf')])
            if not attachment_id:
                data, data_format = self.env.ref(
                    'stock.action_report_delivery').render([stockpickingid.id])
                att_id = self.env['ir.attachment'].create({
                    'name': attach_name + '.pdf',
                    'type': 'binary',
                    'datas': base64.encodestring(data),
                    'datas_fname': attach_name + '.pdf',
                    'res_model': 'stock.picking',
                    'res_id': stockpickingid.id,
                    'mimetype': 'application/x-pdf'
                })
            else:
                att_id = attachment_id[0]

            # # create mail to send
            mail_pool = self.env['mail.mail']
            msj_subject = 'Guía GRUPO REQUIEZ, S.A DE C.V Orden de Envío (%s)' % attach_name
            msj_body = 'Estimado ' + stockpickingid.partner_id.name + '<br></br>'
            msj_body += 'Nos complace informarle que su pedido ha sido enviado.<br></br>'
            msj_body += 'Su identificador: ' + \
                stockpickingid.carrier_tracking_ref + '<br></br>'
            msj_body += 'Consulte el albarán adjunto para más detalles.<br></br>'
            msj_body += 'Gracias!!!!'

            values = {}
            values.update({'subject': msj_subject})
            values.update({'email_to': stockpickingid.partner_id.email})
            values.update({'body_html': msj_body})
            values.update({'body': msj_body})
            values.update({'attachment_ids': [(4, att_id.id)]})
            values.update({'res_id': stockpickingid.id})
            values.update({'model': 'stock.picking'})
            values.update({'mail_server_id': 2})
            values.update({'state': 'sent'})
            msg_id = mail_pool.create(values)
            if msg_id:
                # mail_pool.send([msg_id])
                template_id = self.env.ref(
                    'delivery.mail_template_data_delivery_confirmation').id
                self.env['mail.template'].browse(template_id).send_mail(
                    stockpickingid.id, force_send=True)

        # Decode data
        data = base64.b64decode(self.data_file)
        # Save file
        file_name = '/tmp/%s' % self.name
        with open(file_name, 'wb') as file:
            file.write(data)
        try:
            xl_workbook = xlrd.open_workbook(file.name)
        except:
            raise exceptions.Warning(
                'The only file extensions allowed are xls and xlsx')
        sheet_names = xl_workbook.sheet_names()
        xl_sheet = xl_workbook.sheet_by_name(sheet_names[0])
        # Number of columns
        num_cols = xl_sheet.ncols
        # Extract headers from xls file
        headers = []
        count = 0
        for col_idx in range(0, num_cols):
            cell_obj = xl_sheet.cell(6, col_idx)
            headers.append(cell_obj.value)
            if cell_obj.value in ('REFERENCIA', 'OBSERVACION 1', 'F.DOC', 'TALON'):
                count += 1
        if count == 4:
            # Read xls file and build array of dictionary
            import_data = []
            for row_idx in range(7, (xl_sheet.nrows - 1)):    # Iterate through rows
                row_dict = {}
                for col_idx in range(0, num_cols):  # Iterate through columns
                    # Get cell object by row, col
                    cell_obj = xl_sheet.cell(row_idx, col_idx)
                    row_dict[headers[col_idx]] = cell_obj.value
                import_data.append(row_dict)
            # Browse result and update the tracking reference on stock.picking model.
            data_list = []
            for row in import_data:
                tracking_ref_status = ''
                if row['REFERENCIA'] != 'CANCELADO':
                    StockPicking_id = self.env['stock.picking'].search(
                        [('origin', '=', row['OBSERVACION 1'])])
                    if StockPicking_id:
                        if len(StockPicking_id) == 1:
                            tracking_ref = 'EMBARCADO EL %s CON NO. GUIA %s' % (
                                row['F.DOC'], row['TALON'])
                            StockPicking_id.write(
                                {'carrier_tracking_ref': tracking_ref})
                            tracking_ref_status = 'OK'
                            send_tracking_ref(StockPicking_id.id)
                        else:
                            tracking_ref_status = 'Se encontraron multiples vales de entrega'
                    else:
                        tracking_ref_status = 'No encontrado'
                else:
                    tracking_ref_status = 'CANCELADO'
                data = (
                    row['TALON'],
                    row['OBSERVACION 1'],
                    tracking_ref_status)
                data_list.append(data)
            handle, fn = tempfile.mkstemp(suffix='.csv')
            with os.fdopen(handle, "w", encoding='utf-8', errors='surrogateescape', newline='') as f:
                writer = csv.writer(
                    f, delimiter=';', quoting=csv.QUOTE_MINIMAL)
                writer.writerow(['GUIA', 'REFERENCIA', 'STATUS'])
                try:
                    writer.writerows(data_list)
                except Exception as e:
                    msj = 'Error in writing row: %s' % e
                    raise exceptions.Warning(msj)
                f.close()
                url = 'file://' + fn.replace(os.path.sep, '/')
                status_file = open(fn, "rb")
                out = status_file.read()
                status_file.close()
                self.csv_file = base64.b64encode(out)
            if self.csv_file:
                self.getted = True
                return {
                    'type': 'ir.actions.act_window',
                    'res_model': 'upload.carrier.tracking',
                    'view_mode': 'form',
                    'view_type': 'form',
                    'res_id': self.id,
                    'views': [(False, 'form')],
                    'target': 'new',
                }
        else:
            raise exceptions.Warning(
                'The selected file does not have the necessary information.\n \t"REFERENCIA"\n \t"OBSERVACION 1"\n \t"F.DOC"\n \t"TALON"')
