# Copyright 2018 Vauxoo (https://www.vauxoo.com) <info@vauxoo.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).
import logging

_logger = logging.getLogger(__name__)


def update_partner_data(cr):
    cr.execute("""
        UPDATE res_partner AS p
        SET street_name = p.street || ' ' || p.street2,
            street_number = p.l10n_mx_street3,
            street_number2 = p.l10n_mx_street4,
            zip = (SELECT code FROM res_country_zip_sat_code
                   WHERE id = p.zip_sat_id),
            l10n_mx_edi_colony = (SELECT name FROM res_colonia_zip_sat_code
                                  WHERE id = p.colonia_sat_id),
            city_id = (SELECT id FROM res_city
                       WHERE l10n_mx_edi_code = (
                          SELECT code
                          FROM res_country_township_sat_code
                          WHERE id = p.township_sat_id)
                       AND state_id = p.state_id
                       AND country_id = p.country_id),
            l10n_mx_edi_locality = (SELECT name
                                    FROM res_country_locality_sat_code
                                    WHERE id = p.locality_sat_id),
            vat = p.num_reg_trib,
            comment = p.l10n_mx_street_reference;
    """)


def migrate(cr, version):
    if not version:
        return
    update_partner_data(cr)
