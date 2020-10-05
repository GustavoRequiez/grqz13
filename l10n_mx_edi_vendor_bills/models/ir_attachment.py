# Copyright 2018, Jarsa Sistemas, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import logging
import json

from lxml import objectify
from odoo import api, models

_logger = logging.getLogger(__name__)


class IrAttachment(models.Model):
    _inherit = 'ir.attachment'

    @api.model
    def create(self, values):
        if 'datas' in values and self._validate_xml(values['datas']):
            description = self._create_description(values['datas'])
            values.update(description)
        return super().create(values)

    def write(self, values):
        no_mx_rec = self
        for rec in self:
            datas = values['datas'] if 'datas' in values else rec.datas
            if (('description' in values or 'datas' in values) and
                    self._validate_xml(datas)):
                description = self._create_description(datas)
                rec_values = values.copy()
                rec_values.update(description)
                super(IrAttachment, rec).write(rec_values)
                no_mx_rec -= rec
            elif ('datas' in values and rec.mimetype == 'application/xml' and
                    not self._validate_xml(datas)):
                rec_values = values.copy()
                rec_values.update({
                    'description': False,
                    'mimetype': self._compute_mimetype({'datas': datas})
                })
                super(IrAttachment, rec).write(rec_values)
                no_mx_rec -= rec
        return super(IrAttachment, no_mx_rec).write(values)

    @api.model
    def _validate_xml(self, datas):
        if not datas:
            return False
        data_file = base64.b64decode(datas)
        try:
            objectify.fromstring(data_file)
        except (SyntaxError, ValueError):
            return False
        return True

    @api.model
    def _create_description(self, datas):
        """Process XML file to get description.
        Args:
            datas (binary): attachment in base64.
        Returns:
            dict: procesed description dict or empty dict.
        """
        xml_str = base64.b64decode(datas)
        try:
            xml_obj = objectify.fromstring(xml_str)
        except (SyntaxError, ValueError) as err:
            _logger.error(str(err))
            return {}
        if (xml_obj.get('Version') != '3.3' or
                xml_obj.get('TipoDeComprobante') != 'I'):
            return {}
        partner = self.env['res.partner'].search([
            ('vat', '=ilike', xml_obj.Emisor.get('Rfc'))], limit=1)
        if not partner:
            wizard_attachment = self.env['attach.xmls.wizard']
            wizard_attachment.create_partner(datas, '')
        return {
            'description': json.dumps(
                self._prepare_description_attachment(xml_obj),
                ensure_ascii=False),
            'mimetype': 'application/xml',
        }

    @api.model
    def _prepare_description_attachment(self, xml):
        # TODO: Check if we can avoid use enterprise.
        cfdi = self.env['account.move'].l10n_mx_edi_get_tfd_etree(xml)
        data = {
            'date': xml.get('Fecha', ' ').replace('T', ' '),
            'number': xml.get('Folio', ''),
            'name': xml.Emisor.get('Nombre', ' '),
            'emitter_vat': xml.Emisor.get('Rfc', ' '),
            'subtotal': float(xml.get('SubTotal', '0.0')),
            'tax': 0.0,
            'tax_retention': 0.0,
            'currency': xml.get('Moneda', ''),
            'total': float(xml.get('Total')),
            'uuid': cfdi.get('UUID') if cfdi is not None else ' ',
        }
        if hasattr(xml, 'Impuestos'):
            data.update({
                'tax': float(xml.Impuestos.get(
                    'TotalImpuestosTrasladados', '0.0')),
                'tax_retention': float(xml.Impuestos.get(
                    'TotalImpuestosRetenidos', '0.0')),
            })
        return data
