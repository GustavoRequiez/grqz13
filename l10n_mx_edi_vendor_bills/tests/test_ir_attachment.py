# Copyright 2018, Jarsa Sistemas, S.A. de C.V.
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

import base64
import json
import os
from unittest.mock import patch

from lxml import objectify
from odoo.tests.common import TransactionCase
from odoo.tools import misc, mute_logger


class TestIrAttachment(TransactionCase):

    def setUp(self):
        super().setUp()
        self.attachment = self.env['ir.attachment']
        self.mexico = self.env.ref('base.mx')
        self.list_xml = {
            '56D16DE2-5503-4116-A972-6BD29E8D648A.xml': {
                'tax': 5.9,
                'tax_retention': 0.0,
                'total': 79.65,
                'name': 'ENERGIA Y SERVICIOS COORDINADOS SA DE CV',
                'date': '2018-03-01 18:24:30',
                'subtotal': 73.75,
                'currency': 'MXN',
                'emitter_vat': 'ESC1412031E8',
                'number': '17266881',
                'uuid': '56d16de2-5503-4116-a972-6bd29e8d648a',
            },
            '999D6FB8-A77D-4BF3-B687-658C5B433438.xml': {
                'subtotal': 155.59,
                'emitter_vat': 'DME021218T82',
                'number': '045948',
                'date': '2018-04-03 02:24:56',
                'name': 'DTS MEXICO S DE RL DE CV',
                'currency': 'MXN',
                'tax': 24.89,
                'tax_retention': 0.0,
                'total': 180.48,
                'uuid': '999D6FB8-A77D-4BF3-B687-658C5B433438',
            },
        }

    def open_attachment_base64(self, name_file):
        xml_file = misc.file_open(os.path.join(
            'l10n_mx_edi_vendor_bills', 'tests', name_file))
        return base64.b64encode(bytes(xml_file.read(), 'utf-8'))

    def create_attachments(self):
        attachments = self.attachment
        for xml_file in self.list_xml:
            xml = self.open_attachment_base64(xml_file)
            attachments |= self.attachment.create({
                'name': xml_file,
                'datas': xml,
            })
        return attachments

    def validate_description(self, attachments):
        for attachment in attachments:
            description_dict = json.loads(attachment.description)
            for key, value in description_dict.items():
                self.assertEqual(value, self.list_xml[attachment.name][key])

    def test_01_create_attachments(self):
        for attach in self.create_attachments():
            description_dict = json.loads(attach.description)
            for key, value in description_dict.items():
                self.assertEqual(value, self.list_xml[attach.name][key])
        partner = self.env['res.partner'].search([
            ('vat', '=', 'DME021218T82'),
            ('country_id', '=', self.mexico.id)])
        self.assertTrue(partner, 'Error in partner creation.')

    def test_02_write_attachments(self):
        attachments = self.create_attachments()
        attachments.write({'description': False})
        self.validate_description(attachments)
        attachments.write({'datas': False})
        for attachment in attachments:
            self.assertFalse(attachment.description)

    @mute_logger('odoo.addons.l10n_mx_edi_vendor_bills.models.ir_attachment')
    @patch.object(objectify, 'fromstring', side_effect=ValueError('Error'))
    def test_03_exception_xml(self, mock_fromstring):
        self.create_attachments()
        self.assertTrue(mock_fromstring.called)

    def test_04_xml_version(self):
        file_name = '56D16DE2-5503-4116-A972-6BD29E8D648A.xml'
        xml_file = misc.file_open(os.path.join(
            'l10n_mx_edi_vendor_bills', 'tests', file_name))
        xml = xml_file.read().replace('Version="3.3"', 'vesion="3.2"')
        xml_b64 = base64.b64encode(bytes(xml, 'utf-8'))
        attachment = self.attachment.create({
            'name': file_name,
            'datas': xml_b64,
        })
        self.assertFalse(attachment.description)

    def test_05_change_file_type(self):
        attachment = self.env.ref('l10n_mx_edi_vendor_bills.attachment_pdf')
        old_datas = attachment.datas
        self.assertFalse(attachment.description)
        file_name = '56D16DE2-5503-4116-A972-6BD29E8D648A.xml'
        xml_file = misc.file_open(os.path.join(
            'l10n_mx_edi_vendor_bills', 'tests', file_name))
        xml_b64 = base64.b64encode(bytes(xml_file.read(), 'utf-8'))
        attachment.write({
            'name': file_name,
            'datas': xml_b64,
        })
        self.validate_description(attachment)
        attachment.write({
            'datas': old_datas,
        })
        self.assertFalse(attachment.description)
