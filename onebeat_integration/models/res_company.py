# -*- coding: utf-8 -*-
from odoo import _, api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    ftp_host = fields.Char(
        string='Host',
    )
    ftp_port = fields.Integer(
        string='Port',
        default=21
    )
    ftp_user = fields.Char(
        string='User',
    )
    ftp_passwd = fields.Char(
        string='Password',
    )
