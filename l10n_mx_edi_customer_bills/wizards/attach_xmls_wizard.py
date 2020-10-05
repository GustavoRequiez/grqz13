import base64

from lxml import etree, objectify

from odoo import _, api, models
from odoo.tools.float_utils import float_is_zero
from odoo.exceptions import UserError


class AttachXmlsWizard(models.TransientModel):
    _inherit = 'attach.xmls.wizard'

    def get_impuestos(self, xml):
        if self._context.get('l10n_mx_edi_invoice_type') != 'out':
            return super().get_impuestos(xml=xml)
        if not hasattr(xml, 'Impuestos'):
            return {}
        taxes_list = {'wrong_taxes': [], 'taxes_ids': {}, 'withno_account': []}
        taxes = []
        tax_tag_obj = self.env['account.account.tag']
        tax_obj = self.env['account.tax']
        for index, rec in enumerate(xml.Conceptos.Concepto):
            if not hasattr(rec, 'Impuestos'):
                continue
            taxes_list['taxes_ids'][index] = []
            taxes_xml = rec.Impuestos
            if hasattr(taxes_xml, 'Traslados'):
                taxes = self.collect_taxes(taxes_xml.Traslados.Traslado)
            if hasattr(taxes_xml, 'Retenciones'):
                taxes += self.collect_taxes(taxes_xml.Retenciones.Retencion)

            for tax in taxes:
                tax_tag_id = tax_tag_obj.search(
                    [('name', 'ilike', tax['tax'])])
                domain = [('type_tax_use', '=', 'sale'),
                          ('amount', '=', tax['rate'])]

                name = '%s(%s%%)' % (tax['tax'], tax['rate'])

                taxes_get = tax_obj.search(domain)
                tax_get = False
                for tax_id in taxes_get:
                    if not set(tax_id.invoice_repartition_line_ids.tag_ids.ids).isdisjoint(tax_tag_id.ids):  # noqa
                        tax_get = tax_id
                        break

                if not tax_tag_id or not tax_get:
                    taxes_list['wrong_taxes'].append(name)
                    continue
                # TODO review if this validation of account in taxes is correct
                tax_account = tax_get.invoice_repartition_line_ids.filtered(
                    lambda rec: rec.repartition_type == 'tax')

                if not tax_account:
                    taxes_list['withno_account'].append(
                        name if name else tax['tax'])
                else:
                    tax['id'] = tax_get.id
                    tax['account'] = tax_account.id
                    tax['name'] = name if name else tax['tax']
                    taxes_list['taxes_ids'][index].append(tax)
        return taxes_list

    @api.model
    def check_xml(self, files, account_id=False):
        """Validate that attributes in the XML before create invoice
        or attach XML in it.
        If the invoice is not found in the system, will be created and
        validated using the same 'Serie-Folio' that in the CFDI.
        :param files: dictionary of CFDIs in b64
        :type files: dict
        :param account_id: The account by default that must be used in the
            lines of the invoice if this is created
        :type account_id: int
        :return: the Result of the CFDI validation
        :rtype: dict
        """
        if self._context.get('l10n_mx_edi_invoice_type') != 'out':
            return super().check_xml(files, account_id=account_id)
        if not isinstance(files, dict):
            raise UserError(_("Something went wrong. The parameter for XML "
                              "files must be a dictionary."))
        wrongfiles = {}
        invoices = {}
        account_id = self._context.get('account_id', False)
        outgoing_docs = {}
        for key, xml64 in files.items():
            try:
                if isinstance(xml64, bytes):
                    xml64 = xml64.decode()
                xml_str = base64.b64decode(xml64.replace(
                    'data:text/xml;base64,', ''))
                # Fix the CFDIs emitted by the SAT
                xml_str = xml_str.replace(
                    b'xmlns:schemaLocation', b'xsi:schemaLocation')
                xml = objectify.fromstring(xml_str)
            except (AttributeError, SyntaxError) as exce:
                wrongfiles.update({key: {
                    'xml64': xml64, 'where': 'CheckXML',
                    'error': [exce.__class__.__name__, str(exce)]}})
                continue
            xml = self._l10n_mx_edi_convert_cfdi32_to_cfdi33(xml)
            if xml.get('TipoDeComprobante', False) == 'E':
                outgoing_docs.update({key: {'xml': xml, 'xml64': xml64}})
                continue
            if xml.get('TipoDeComprobante', False) != 'I':
                wrongfiles.update({key: {'cfdi_type': True, 'xml64': xml64}})
                continue
            # Check the incoming documents
            validated_documents = self.validate_documents(key, xml, account_id)
            wrongfiles.update(validated_documents.get('wrongfiles'))
            if wrongfiles.get(key, False) and \
                    wrongfiles[key].get('xml64', False):
                wrongfiles[key]['xml64'] = xml64
            invoices.update(validated_documents.get('invoices'))
        # Check the outgoing documents
        for key, value in outgoing_docs.items():
            xml64 = value.get('xml64')
            xml = value.get('xml')
            xml = self._l10n_mx_edi_convert_cfdi32_to_cfdi33(xml)
            validated_documents = self.validate_documents(
                key, xml, account_id)
            wrongfiles.update(validated_documents.get('wrongfiles'))
            if wrongfiles.get(key, False) and \
                    wrongfiles[key].get('xml64', False):
                wrongfiles[key]['xml64'] = xml64
            invoices.update(validated_documents.get('invoices'))
        return {'wrongfiles': wrongfiles, 'invoices': invoices}

    # pylint: disable=unused-variable
    def validate_documents(self, key, xml, account_id):
        """ Validate the incoming or outcoming document before create or
        attach the xml to invoice
        :param key: Name of the document that is being validated
        :type key: str
        :param xml: xml file with the datas of purchase
        :type xml: etree
        :param account_id: The account by default that must be used in the
            lines of the invoice if this is created
        :type account_id: int
        :return: Result of the validation of the CFDI and the invoices created.
        :rtype: dict
        """
        if self._context.get('l10n_mx_edi_invoice_type') != 'out':
            return super().validate_documents(
                key=key, xml=xml, account_id=account_id)
        wrongfiles = {}
        invoices = {}
        inv_obj = self.env['account.move']
        partner_obj = self.env['res.partner']
        currency_obj = self.env['res.currency']
        inv = inv_obj
        inv_id = False
        xml_str = etree.tostring(xml, pretty_print=True, encoding='UTF-8')
        version = xml.get('Version', xml.get('version'))
        xml_vat_emitter, xml_vat_receiver, xml_amount, xml_currency,\
            version, xml_name_supplier, xml_type_of_document, xml_uuid,\
            xml_folio, xml_taxes = self._get_xml_data(xml)
        domain = ['&', ('vat', '=', xml_vat_receiver)] if (
            xml_vat_receiver not in ['XEXX010101000', 'XAXX010101000']
        ) else ['&', ('name', '=ilike', xml_name_supplier)]
        domain.extend(['|', ('company_id', '=', False),
                       ('company_id', '=', self.env.company.id)])
        exist_supplier = partner_obj.search(
            domain, limit=1).commercial_partner_id
        exist_reference = xml_folio and inv_obj.search(
            [('invoice_origin', '=ilike', xml_folio),
             ('partner_id', '=', exist_supplier.id)], limit=1)
        tag_folio = (self.env.ref(
            'l10n_mx_edi_customer_bills.tag_customer_avoid_duplicate_folio') in
            self.env.company.partner_id.category_id)
        if exist_reference and (
                not exist_reference.l10n_mx_edi_cfdi_uuid or
                exist_reference.l10n_mx_edi_cfdi_uuid == xml_uuid):
            inv = exist_reference
            inv_id = inv.id
            exist_reference = False
            inv.l10n_mx_edi_update_sat_status()
        elif (tag_folio and exist_reference and
                exist_reference.l10n_mx_edi_cfdi_uuid and
                exist_reference.l10n_mx_edi_cfdi_uuid != xml_uuid):
            exist_reference = False
        xml_status = inv.l10n_mx_edi_sat_status
        inv_vat_emitter = (
            self.env.company.vat or '').upper()
        inv_vat_receiver = (
            inv and inv.commercial_partner_id.vat or '').upper()
        inv_amount = inv.amount_total
        inv_folio = inv.invoice_origin
        domain = [('l10n_mx_edi_cfdi_name', '!=', False),
                  ('type', '=', 'out_invoice'),
                  ('id', '!=', inv_id)]
        if exist_supplier:
            domain += [('partner_id', 'child_of', exist_supplier.id)]
        uuid_dupli = xml_uuid in inv_obj.search(domain).mapped(
            'l10n_mx_edi_cfdi_uuid')
        mxns = ['mxp', 'mxn', 'pesos', 'peso mexicano', 'pesos mexicanos']
        xml_currency = 'MXN' if xml_currency.lower(
        ) in mxns else xml_currency

        exist_currency = currency_obj.search(
            [('name', '=', xml_currency)], limit=1)

        errors = [
            (not xml_uuid, {'signed': True}),
            (xml_status == 'cancelled', {'cancel': True}),
            ((xml_uuid and uuid_dupli), {'uuid_duplicate': xml_uuid}),
            ((inv_id and inv_vat_receiver and inv_vat_receiver != xml_vat_receiver),  # noqa
                {'supplier': (xml_vat_receiver, inv_vat_receiver)}),
            ((not inv_id and exist_reference),
                {'reference': (xml_name_supplier, xml_folio)}),
            (version != '3.3', {'version': True}),
            ((not inv_id and not exist_supplier),
                {'supplier': xml_name_supplier}),
            ((not inv_id and xml_currency and not exist_currency),
                {'currency': xml_currency}),
            ((not inv_id and xml_taxes.get('wrong_taxes', False)),
                {'taxes': xml_taxes.get('wrong_taxes', False)}),
            ((not inv_id and xml_taxes.get('withno_account', False)),
                {'taxes_wn_accounts': xml_taxes.get(
                    'withno_account', False)}),
            ((inv_id and inv_folio != xml_folio),
                {'folio': (xml_folio, inv_folio)}),
            ((inv_vat_emitter != xml_vat_emitter), {
                'rfc_cust': (xml_vat_emitter, inv_vat_emitter)}),
            ((inv_id and not float_is_zero(float(inv_amount)-float(
                xml_amount), precision_digits=0)), {
                    'amount': (xml_amount, inv_amount)})
        ]
        msg = {}
        for error in errors:
            if error[0]:
                msg.update(error[1])
        if msg:
            msg.update({'xml64': True})
            wrongfiles.update({key: msg})
            return {'wrongfiles': wrongfiles, 'invoices': invoices}

        if not inv_id:
            invoice_status = self.create_invoice(
                xml, exist_supplier, exist_currency,
                xml_taxes.get('taxes_ids', {}), account_id)

            if invoice_status['key'] is False:
                del invoice_status['key']
                invoice_status.update({'xml64': True})
                wrongfiles.update({key: invoice_status})
                return {'wrongfiles': wrongfiles, 'invoices': invoices}

            del invoice_status['key']
            invoices.update({key: invoice_status})
            return {'wrongfiles': wrongfiles, 'invoices': invoices}
        if inv_id and inv.state == 'draft':
            inv.write(self.prepare_invoice_data(xml))
            self._assign_cfdi_related(xml, inv)

        inv.l10n_mx_edi_cfdi = xml_str.decode('UTF-8')
        inv.generate_xml_attachment()
        if tag_folio:
            inv.invoice_payment_ref = '%s|%s' % (
                xml_folio, xml_uuid.split('-')[0])
        inv.action_post()
        inv.l10n_mx_edi_update_sat_status()
        invoices.update({key: {'invoice_id': inv.id}})
        return {'wrongfiles': wrongfiles,
                'invoices': invoices}

    def _assign_cfdi_related(self, xml, invoice):
        """If the document is 'E', assign the CFDI Origin in the invoice and
        relate the invoices"""
        if xml.get('TipoDeComprobante', False) != 'E' or not (
                hasattr(xml, 'CfdiRelacionados') and
                xml.CfdiRelacionados.CfdiRelacionado.get('UUID')):
            return False
        xml_related_uuid = xml.CfdiRelacionados.CfdiRelacionado.get('UUID')
        invoice._set_cfdi_origin('01', [xml_related_uuid])
        related_invoices = invoice.search([
            ('partner_id', '=', invoice.partner_id.id),
            ('type', '=', 'in_invoice')])
        related_invoices = related_invoices.filtered(
            lambda inv: inv.l10n_mx_edi_cfdi_uuid == xml_related_uuid)
        if related_invoices:
            related_invoices.reversal_move_id |= invoice
        return True

    @api.model
    def _get_xml_data(self, xml):
        """Return data from XML"""
        res = super(AttachXmlsWizard, self)._get_xml_data(xml)
        if self._context.get('l10n_mx_edi_invoice_type') != 'out':
            return res
        res = list(res)
        res[5] = xml.Receptor.get('Nombre', '')
        res[8] = xml.get('Folio', '')
        return tuple(res)

    def _prepare_invoice_lines_data(self, xml, account_id, taxes):
        """Prepare dict for invoice line creation.
        This allows inherit and write new values in the lines, because the CFDI
        is signed and cannot be cancelled.
        :return: the lines to be created in the invoice
        :rtype: list
        """
        sat_code_obj = self.env['l10n_mx_edi.product.sat.code']
        uom_obj = uom_obj = self.env['uom.uom']
        invoice_line_ids = []
        msg = (_('Some products are not found in the system, and the account '
                 'that is used like default is not configured in the journal, '
                 'please set default account in the journal '
                 '%s to create the invoice.'))
        invoice_line_ids = []
        for index, rec in enumerate(xml.Conceptos.Concepto):
            name = rec.get('Descripcion', '')
            no_id = rec.get('NoIdentificacion', name)
            product_code = rec.get('ClaveProdServ', '')
            uom = rec.get('Unidad', '')
            uom_code = rec.get('ClaveUnidad', '')
            qty = rec.get('Cantidad', '')
            price = rec.get('ValorUnitario', '')
            amount = float(rec.get('Importe', '0.0'))
            product_id = self._get_product_line([
                '|', ('default_code', '=ilike', no_id),
                ('name', '=ilike', name)])
            account_line_id = (
                product_id.property_account_income_id.id or
                product_id.categ_id.property_account_income_categ_id.id or
                account_id)

            if not account_line_id:
                return {
                    'key': False, 'where': 'CreateInvoice',
                    'error': [
                        _('Account to set in the lines not found.<br/>'), msg]}

            discount = 0.0
            if rec.get('Descuento') and amount:
                discount = (float(rec.get('Descuento', '0.0')) / amount) * 100

            domain_uom = [('name', '=ilike', uom)]
            line_taxes = [tax['id'] for tax in taxes.get(index, [])]
            code_sat = sat_code_obj.search([('code', '=', uom_code)], limit=1)
            domain_uom = [('l10n_mx_edi_code_sat_id', '=', code_sat.id)]
            uom_id = uom_obj.with_context(
                lang='es_MX').search(domain_uom, limit=1)

            if product_code in self._get_fuel_codes():
                tax = taxes.get(index)[0] if taxes.get(index, []) else {}
                qty = 1.0
                price = tax.get('amount') / (tax.get('rate') / 100)
                invoice_line_ids.append((0, 0, {
                    'account_id': account_line_id,
                    'name': _('FUEL - IEPS'),
                    'quantity': qty,
                    'product_uom_id': uom_id.id,
                    'price_unit': float(rec.get('Importe', 0)) - price,
                }))
            invoice_line_ids.append((0, 0, {
                'product_id': product_id.id,
                'account_id': account_line_id,
                'name': name,
                'quantity': float(qty),
                'product_uom_id': uom_id.id,
                'tax_ids': [(6, 0, line_taxes)],
                'price_unit': float(price),
                'discount': discount,
            }))
        return invoice_line_ids

    def prepare_invoice_data(self, xml):
        """Prepare dict for invoice creation.
        This allows inherit and write new values in the lines, because the CFDI
        is signed and cannot be cancelled.
        :return: the common data to create the invoice
        :rtype: dict
        """
        acc_pay_term = self.env['account.payment.term']
        payment_term = xml.get('MetodoPago') or False
        payment_condition = xml.get('CondicionesDePago') or False
        xml_folio = xml.get('Folio', '')
        company = self.env.company
        if payment_term and payment_condition:
            acc_pay_term = acc_pay_term.search([
                ('name', '=', payment_condition)], limit=1)
        if payment_term and payment_term == 'PPD' and not acc_pay_term:
            term = 'l10n_mx_edi_customer_bills.aux_account_payment_term_ppd'
            acc_pay_term = (self.env.ref('%s_%s' % (term, company.id), False)
                            or self.env.ref(term))
            if acc_pay_term.sudo().company_id != company:
                pay_term_values = acc_pay_term.sudo().copy_data({
                    'company_id': company.id})
                load_values = [{
                    'xml_id': '%s_%s' % (term, company.id),
                    'noupdate': True,
                    'values': pay_term_values[0]}]
                acc_pay_term = self.env['account.payment.term']._load_records(
                    load_values)

        tag_folio = (self.env.ref(
            'l10n_mx_edi_customer_bills.tag_customer_avoid_duplicate_folio') in
            company.partner_id.category_id)
        date_inv = xml.get('Fecha', '').split('T')
        payment_method_id = self.env['l10n_mx_edi.payment.method'].search(
            [('code', '=', xml.get('FormaPago', '99'))], limit=1)
        xml_tfd = self.env['account.move'].l10n_mx_edi_get_tfd_etree(xml)
        uuid = False if xml_tfd is None else xml_tfd.get('UUID', '')
        return {
            'invoice_payment_term_id': acc_pay_term.id,
            'invoice_origin': '%s|%s' % (
                xml_folio, uuid.split('-')[0]) if tag_folio else xml_folio,
            'invoice_payment_ref': '%s|%s' % (
                self.get_xml_folio(xml), uuid.split('-')[0]),
            'l10n_mx_edi_payment_method_id': payment_method_id.id,
            'l10n_mx_edi_usage': xml.Receptor.get('UsoCFDI', 'P01'),
            'invoice_date': date_inv[0],
            'l10n_mx_edi_time_invoice': date_inv[1],
            'name': '%s%s%s' % (
                xml.get('Serie', ''), xml_folio,
                '|' + uuid.split('-')[0] if tag_folio else ''),
        }

    def create_invoice(
            self, xml, supplier, currency_id, taxes, account_id=False):
        """ Create supplier invoice from xml file
        :param xml: xml file with the invoice data
        :type xml: etree
        :param supplier: customer partner
        :type supplier: res.partner
        :param currency_id: payment currency of the invoice
        :type currency_id: res.currency
        :param taxes: Datas of taxes
        :type taxes: list
        :param account_id: The account by default that must be used in the
            lines, if this is defined will to use this.
        :type account_id: int
        :return: the Result of the invoice creation
        :rtype: dict
        """
        if self._context.get('l10n_mx_edi_invoice_type') != 'out':
            return super().create_invoice(
                xml, supplier, currency_id, taxes, account_id=account_id)
        inv_obj = self.env['account.move']
        line_obj = self.env['account.move.line']
        xml_type_doc = xml.get('TipoDeComprobante', False)
        type_invoice = 'out_invoice' if xml_type_doc == 'I' else 'out_refund'
        journal = self._context.get('journal_id', False)
        journal = self.env['account.journal'].browse(
            journal) if journal else inv_obj.with_context(
                type=type_invoice)._get_default_journal()
        account_id = account_id or line_obj.with_context({
            'journal_id': journal.id,
            'type': type_invoice})._default_account()
        invoice_line_ids = self._prepare_invoice_lines_data(
            xml, account_id, taxes)
        if isinstance(invoice_line_ids, dict):
            return invoice_line_ids
        xml_str = etree.tostring(xml, pretty_print=True, encoding='UTF-8')
        invoice_data = self.prepare_invoice_data(xml)
        invoice_data.update({
            'partner_id': supplier.id,
            'currency_id': (
                currency_id.id or self.env.company.currency_id.id),
            'invoice_line_ids': invoice_line_ids,
            'type': type_invoice,
            'journal_id': journal.id,
        })
        invoice_id = inv_obj.create(invoice_data)

        local_taxes = self.get_local_taxes(xml).get('taxes', [])
        if local_taxes:
            invoice_id.write({
                'tax_line_ids': local_taxes,
            })
        if xml.get('version') == '3.2':
            # Global tax used for each line since that a manual tax line
            # won't have base amount assigned.
            tax_path = '//cfdi:Impuestos/cfdi:Traslados/cfdi:Traslado'
            tax_obj = self.env['account.tax']
            for global_tax in xml.xpath(tax_path, namespaces=xml.nsmap):
                tax_name = global_tax.attrib.get('impuesto')
                tax_percent = float(global_tax.attrib.get('tasa'))
                tax_domain = [
                    ('type_tax_use', '=', 'sale'),
                    ('company_id', '=', self.env.company.id),
                    ('amount_type', '=', 'percent'),
                    ('amount', '=', tax_percent),
                    ('tag_ids.name', '=', tax_name),
                ]
                tax = tax_obj.search(tax_domain, limit=1)
                if not tax:
                    return {
                        'key': False,
                        'taxes': ['%s(%s%%)' % (tax_name, tax_percent)],
                    }

                invoice_id.invoice_line_ids.write({
                    'invoice_line_tax_ids': [(4, tax.id)]})

            # Global discount used for each line
            # Decimal rounding wrong values could be imported will fix manually
            discount_amount = float(xml.attrib.get('Descuento', 0))
            sub_total_amount = float(xml.attrib.get('subTotal', 0))
            if discount_amount and sub_total_amount:
                percent = discount_amount * 100 / sub_total_amount
                invoice_id.invoice_line_ids.write({'discount': percent})
        invoice_id.l10n_mx_edi_cfdi = xml_str.decode('UTF-8')
        invoice_id.generate_xml_attachment()
        self._assign_cfdi_related(xml, invoice_id)
        total_xml = float(xml.get('Total', xml.get('total')))
        if invoice_id.amount_total != total_xml:
            invoice_id.create_adjustment_line(total_xml)
        invoice_id.action_post()
        invoice_id.l10n_mx_edi_update_sat_status()
        return {'key': True, 'invoice_id': invoice_id.id}

    @api.model
    def create_partner(self, xml64, key):
        """ It creates the supplier dictionary, getting data from the XML
        Receives an xml decode to read and returns a dictionary with data """
        # Default Mexico because only in Mexico are emitted CFDIs
        if self._context.get('l10n_mx_edi_invoice_type') != 'out':
            return super().create_partner(xml64, key)
        try:
            if isinstance(xml64, bytes):
                xml64 = xml64.decode()
            xml_str = base64.b64decode(xml64.replace(
                'data:text/xml;base64,', ''))
            # Fix the CFDIs emitted by the SAT
            xml_str = xml_str.replace(
                b'xmlns:schemaLocation', b'xsi:schemaLocation')
            xml = objectify.fromstring(xml_str)
        except BaseException as exce:
            return {
                key: False, 'xml64': xml64, 'where': 'CreatePartner',
                'error': [exce.__class__.__name__, str(exce)]}

        xml = self._l10n_mx_edi_convert_cfdi32_to_cfdi33(xml)
        rfc_receiver = xml.Receptor.get('Rfc', False)
        name = xml.Receptor.get('Nombre', rfc_receiver)

        # check if the partner exist from a previos invoice creation
        domain = [('vat', '=', rfc_receiver)] if rfc_receiver not in [
            'XEXX010101000', 'XAXX010101000'] else [('name', '=', name)]
        domain.extend(['|', ('company_id', '=', False),
                       ('company_id', '=', self.env.company.id)])
        partner = self.env['res.partner'].search(domain, limit=1)
        if partner:
            return partner

        partner = self.env['res.partner'].sudo().create({
            'name': name,
            'company_type': 'company',
            'vat': rfc_receiver,
            'country_id': self.env.ref('base.mx').id,
            'company_id': self.env.company.id,
        })
        msg = _('This partner was created when invoice %s%s was added from '
                'a XML file. Please verify that the datas of partner are '
                'correct.') % (xml.get('Serie', ''), xml.get('Folio', ''))
        partner.message_post(subject=_('Info'), body=msg)
        return partner
