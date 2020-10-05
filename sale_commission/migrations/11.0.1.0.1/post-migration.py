# -*- coding: utf-8 -*-

import logging
from openerp import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def delete_canceled_associations(cr):
    """This method removes associations of payments or canceled invoices."""

    env = api.Environment(cr, SUPERUSER_ID, {})
    assoc_obj = env['account.association']
    canceled_associations = assoc_obj.search([
        '|', ('payment_id.state', '=', 'cancelled'),
        ('move_id.state', '=', 'cancel')])
    canceled_associations.unlink()


def delete_duplicate_associations(cr):
    """This method removes all associations that have been duplicated by the
    cancellation and validation of the same payment. There should only be one
    association per date, payment and invoice."""

    _logger.info('Create a backup table with duplicate data.')
    cr.execute("""
               SELECT date, move_id, payment_id INTO backup_table
               FROM account_association
               GROUP BY date, move_id, payment_id HAVING COUNT(*) > 1;
               """)
    _logger.info('Delete duplicate data from the account_association table')
    cr.execute("""
               DELETE FROM account_association WHERE id IN (
               SELECT a.id FROM account_association a JOIN backup_table b ON (
               a.date = b.date AND a.move_id = b.move_id AND
               a.payment_id = b.payment_id) ORDER BY a.move_id);
               """)
    _logger.info('Take the records from the backup table and insert them into '
                 'the account.association table')
    cr.execute("""
               INSERT INTO account_association (id, date,
               move_id, payment_id)
               SELECT
               nextval('account_association_id_seq'::regclass), date,
               move_id,
               payment_id FROM backup_table;
               """)
    _logger.info('Drop backup table')
    cr.execute("""
               DROP TABLE backup_table;
               """)


def migrate(cr, version):
    if not version:
        return
    delete_canceled_associations(cr)
    delete_duplicate_associations(cr)
