# -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta

from odoo import SUPERUSER_ID, api


_logger = logging.getLogger(__name__)


def set_payment_move_line(env, date_from, date_to):
    """Search for the account.move.line that holds the invoice payment amount
    and set it into the move_line_id field of the account.association. This is
    being done because the payment_id fields is now being deprecated on the
    model account.association, so this migration is to keep track of the old
    data without losing its association.
    """
    assoc_obj = env['account.association']

    _logger.info('Extracting payment lines from %s to %s', date_from, date_to)
    lines = env['account.move'].search([
        ('state', 'in', ['open', 'paid']),
        ('date_invoice', '>=', date_from),
        ('date_invoice', '<=', date_to)]).filtered(
            lambda i: i.payment_move_line_ids).mapped(
                lambda i: (i.id, [
                    (l.id, l.create_date)
                    for l in i.payment_move_line_ids]))

    _logger.info('Creating payment associations for %s invoices', len(lines))
    for inv, amls in lines:
        assoc_obj.search([('move_id', '=', inv)]).unlink()
        for aml in amls:
            assoc_obj.create({
                'move_id': inv,
                'move_line_id': aml[0],
                'date': aml[1],
            })


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    date_from = datetime(2017, 1, 1)  # Date of the first invoice in db
    while date_from <= datetime.today():
        date_to = date_from + timedelta(days=30)
        set_payment_move_line(env, date_from, date_to)
        date_from = date_to
