# pylint: disable=sql-injection
import logging
from odoo import SUPERUSER_ID, api, tools
_logger = logging.getLogger(__name__)


MODELS_TO_DELETE = (
    'ir.actions.act_window',
    'ir.actions.act_window.view',
    'ir.actions.report.xml',
    'ir.actions.todo',
    'ir.actions.url',
    'ir.actions.wizard',
    'ir.cron',
    'ir.model',
    'ir.model.access',
    'ir.model.fields',
    'ir.module.repository',
    'ir.property',
    'ir.report.custom',
    'ir.report.custom.fields',
    'ir.rule',
    'ir.sequence',
    'ir.sequence.type',
    'ir.ui.menu',
    'website.menu',
    'ir.ui.view',
    'ir.ui.view_sc',
    # 'ir.values',
    'res.groups',
    'ir.filters',
)

MODULES_TO_CLEAN = (
    'product_reserve',
    'mrp_mpps',
    'studio_customization',
    'theme_requiez',
    'email_template_multicompany',
    'argil_invoice_analysis_extension',
    'argil_account_asset_amort',
    'asti_eaccounting_mx_base',
    'l10n_mx_sat_models_datas',
    'archive_product_partner',
    'account_invoice_check_total',
    'disable_autoreserve',
    'account_reversal',
    'inputmask_widget',
    'account_invoice_currency',
    'ifrs_report',
    'account_invoice_payment_by_date_due',
    'argil_invoice_cancel',
    'invoice_prioritize',
    'l10n_mx_account_tree',
    'argil_odoo_mexico',
    'argil_account_closing',
    'l10n_mx_diot_report',
    'l10n_mx_account_tax_category',
    'landing_cost_product_average',
    'developer_mode',
    'argil_invoice_balance_analysis',
    'invoice_payment_date',
    'sale_guide_transport',
    'account_move_report',
    'account_move_line_base_tax',
    'argil_account_advance_payment',
    'controller_report_xls',
    'print_label',
    'account_multicurrency_revaluation',
    'partner_credit',
    'stock_move_entries',
    'l10n_mx_einvoice_report',
    'patch_argil_account_tax_cash_basis',
    'l10n_mx_einvoice_pac_sf',
    'account_pay_multi',
    'sale_report_payment',
    'l10n_mx_einvoice_payment',
    'sale_user_required',
    'force_assign_invisible',
    'l10n_mx_einvoice',
    'account_cfdi_audit_zipfile',
    'mrp_upload_forecast',
    'sale_date_promised',
    'argil_mx_accounting_reports_consol',
    'mrp_report',
    'l10n_mx_sat_models',
    'l10n_mx_import_info',
    'responsible_confirm_order',
    'account_period_and_fiscalyear',
    'argil_account_tax_cash_basis')


def model_to_table(model):
    """ Get a table name according to a model name

    In case the table name is set on
    an specific model manually instead the replacement, then you need to add it
    in the mapped dictionary.
    """
    model_table_map = {
        'workflow': 'wkf',
        'workflow.activity': 'wkf_activity',
        'workflow.transition': 'wkf_transition',
        'workflow.instance': 'wkf_instance',
        'workflow.workitem': 'wkf_workitem',
        'workflow.triggers': 'wkf_triggers',
        'ir.actions.client': 'ir_act_client',
        'ir.actions.actions': 'ir_actions',
        'ir.actions.report.custom': 'ir_act_report_custom',
        'ir.actions.report.xml': 'ir_act_report_xml',
        'ir.actions.act_window': 'ir_act_window',
        'ir.actions.act_window.view': 'ir_act_window_view',
        'ir.actions.url': 'ir_act_url',
        'ir.actions.act_url': 'ir_act_url',
        'ir.actions.server': 'ir_act_server',
    }
    name = model_table_map.get(model)
    if name is not None:
        return name.replace('.', '_')
    if model is not None:
        return model.replace('.', '_')
    return ''


def table_exists(cr, table_name):
    cr.execute("SELECT count(1) FROM information_schema.tables WHERE "
               "table_name = %s and table_schema='public'",
               [table_name])
    return cr.fetchone()[0]


def clean_views(cr):
    if table_exists(cr, 'eco_static_view'):
        cr.execute("DELETE FROM eco_static_view;")
    cr.execute("""DELETE FROM ir_ui_view
                  WHERE id NOT IN (SELECT res_id FROM ir_model_data WHERE
                  model='ir.ui.view');""")
    _logger.info('Views are being deleted: %s', cr.query)


def clean_attachments(cr):
    cr.execute("SELECT distinct(res_model) FROM ir_attachment")
    for item in cr.fetchall():
        cr.execute("""
            SELECT module,id
            FROM ir_model_data
            WHERE model='ir.model' and name = %s""",
                   (item[0],))
        for mod in cr.dictfetchall():
            cr.execute("""
                SELECT state FROM ir_module_module
                WHERE name=%s""",
                       (mod['module'],))
            res_state = cr.fetchone()
            state = res_state[0] if res_state else False
            if state not in ['installed']:
                cr.execute("""
                    DELETE FROM ir_attachment WHERE model=%s""", (item[0],))


def clean_actions(cr):
    if table_exists(cr, 'board_board_line'):
        cr.execute("""
            DELETE FROM board_board_line
            WHERE action_id in (
            SELECT id FROM ir_act_window WHERE view_id NOT IN (
            SELECT id FROM ir_ui_view))""")
    if table_exists(cr, 'share_wizard'):
        cr.execute("""
            DELETE FROM ir_act_window
            WHERE
            view_id NOT IN (
            SELECT id FROM ir_ui_view)
            and id NOT IN (
            SELECT action_id FROM share_wizard)""")
    else:
        cr.execute("""
            DELETE FROM ir_act_window
            WHERE view_id NOT IN (SELECT id FROM ir_ui_view)""")


def remove_deprecated(cr):
    for module in MODULES_TO_CLEAN:
        cr.execute("UPDATE ir_module_module "
                   "set (state, latest_version) = ('uninstalled', False)"
                   " WHERE name = '%s'" % (module))


def clean_ir_values(cr):
    cr.execute("""
        SELECT distinct(split_part(value,',',1) ) as model
        FROM ir_values iv WHERE key='action' and value is not null""")

    models = cr.dictfetchall()
    for item in models:
        sql = """
            DELETE FROM ir_values
            WHERE
            split_part(value,',',2)::int NOT IN (
            SELECT id FROM %s )
            and split_part(value,',',1)=%%s
            """ % (model_to_table(item['model']), )
        cr.execute(sql, [item['model']])
    cr.execute("""
        SELECT model FROM ir_values
        WHERE key='action' and value is null;
    """)
    items = cr.dictfetchall()
    for item in items:
        sql = """
            DELETE FROM ir_values
                WHERE model = %%s
                and value is null
                and res_id NOT IN (SELECT id FROM %s);
                """ % (model_to_table(item['model']), )
        cr.execute(sql, [item['model']])


def module_delete(cr, module_name):
    _logger.info('deleting module %s', module_name)

    cr.execute("SELECT res_id, model "
               "FROM ir_model_data "
               "WHERE module=%s and model in %s order by res_id desc",
               (module_name, MODELS_TO_DELETE))
    data_to_delete = cr.fetchall()
    for rec in data_to_delete:
        table = model_to_table(rec[1])

        cr.execute("SELECT count(*) "
                   "FROM ir_model_data "
                   "WHERE model = %s and res_id = %s", [rec[1], rec[0]])
        count1 = cr.dictfetchone()['count']
        if count1 > 1:
            continue

        try:
            # ir_ui_view
            if table == 'ir_ui_view':
                cr.execute('SELECT model '
                           'FROM ir_ui_view WHERE id = %s', (rec[0],))
                t_name = cr.fetchone()
                table_name = model_to_table(t_name[0])
                cr.execute("SELECT viewname "
                           "FROM pg_catalog.pg_views "
                           "WHERE viewname = %s", [table_name])
                if cr.fetchall():
                    cr.execute('drop view ' + table_name + ' CASCADE')
                cr.execute('DELETE FROM ir_model_constraint '
                           'WHERE model=%s', (rec[0],))
                cr.execute('DELETE FROM ' + table + ' WHERE inherit_id=%s',
                           (rec[0],))
                cr.execute('SELECT * FROM ' + table + ' WHERE id=%s',
                           (rec[0],))
                view_exists = cr.fetchone()
                if bool(view_exists):
                    cr.execute('DELETE FROM ' + table + ' WHERE id=%s',
                               (rec[0],))

            # ir_act_window:
            if table == 'ir_act_window' and table_exists(cr, 'board_board_line'):  # noqa
                cr.execute('SELECT count(1) FROM board_board_line '
                           'WHERE action_id = %s', (rec[0],))
                count = cr.fetchone()[0]
                if not count:  # yes, there is a bug here. The line is not
                    # correctly indented, but fixing the bug creates some
                    # problems after.
                    cr.execute('DELETE FROM ' + table + ' WHERE id=%s',
                               (rec[0],))
            elif table == 'ir_model':
                if table_exists(cr, 'ir_model_constraint'):
                    cr.execute('DELETE FROM ir_model_constraint '
                               'WHERE model=%s', (rec[0],))
                if table_exists(cr, 'ir_model_relation'):
                    cr.execute('DELETE FROM ir_model_relation '
                               'WHERE model=%s', (rec[0],))
                cr.execute('DELETE FROM ' + table + ' WHERE id=%s', (rec[0],))
            else:
                cr.execute('DELETE FROM ' + table + ' WHERE id=%s', (rec[0],))

            # also DELETE dependencies:
            cr.execute('DELETE FROM ir_module_module_dependency '
                       'WHERE module_id = %s', (rec[0],))
        except BaseException as ex:
            msg = ("Module delete error\n"
                   "Model: %s, id: %s\n"
                   "Query: %s\n"
                   "Error: %s\n"
                   "On Module: %s\n"
                   "" % (rec[1], rec[0], cr.query, ex.pgerror, module_name))
            _logger.info(msg)
        else:
            _logger.info('Query on Else is %s', cr.query)

    cr.execute("DELETE FROM ir_model_data WHERE module=%s", (module_name,))
    cr.execute('UPDATE ir_module_module set state=%s WHERE name=%s',
               ('uninstalled', module_name))


def remove_uncertified_data(cr):
    cr.execute("ALTER TABLE ir_ui_menu "
               "drop CONSTRAINT ir_ui_menu_parent_id_fkey")
    cr.execute("ALTER TABLE ir_ui_view "
               "drop CONSTRAINT ir_ui_view_inherit_id_fkey")
    cr.execute("""
        ALTER TABLE ir_ui_menu
        ADD CONSTRAINT ir_ui_menu_parent_id_fkey FOREIGN KEY (parent_id)
        REFERENCES ir_ui_menu(id) ON DELETE CASCADE
        """)
    for module in MODULES_TO_CLEAN:
        module_delete(cr, module)


def group_custom_menus(cr):
    cr.execute("""
        SELECT id FROM ir_ui_menu
        WHERE name = 'Custom' and parent_id is null""")
    menu_id = cr.fetchone()
    menu_id = menu_id[0] if menu_id else False
    if not menu_id:
        cr.execute("""
            INSERT INTO ir_ui_menu(
                name,parent_id,sequence
            ) values(
                'Custom',null,100)
            returning id""")
        menu_id = cr.fetchone()[0]

    cr.execute("""
        UPDATE ir_ui_menu im
        SET parent_id = %s
        WHERE id NOT IN (SELECT res_id
                       FROM ir_model_data
                       WHERE model='ir.ui.menu')
            AND id != %s""", [menu_id, menu_id])

    if MODULES_TO_CLEAN:
        cr.execute("""
            UPDATE ir_ui_menu im
            SET parent_id = %s
            WHERE id in (SELECT res_id
                       FROM ir_model_data
                       WHERE model='ir.ui.menu' and module in %s)
            AND id != %s
            """, [menu_id, tuple(MODULES_TO_CLEAN), menu_id])


def delete_obsolete_objects_from_data(cr):
    cr.execute("""
        DELETE FROM ir_model_data
        WHERE res_id
        NOT IN (SELECT id FROM ir_model) and model = 'ir.model';
        """)
    cr.execute(
        """UPDATE
               res_partner
           SET
               vat = regexp_replace(vat, '^MX*', '')
           WHERE
              vat ilike 'MX%'""")
    cr.execute(
        """DELETE FROM
               ir_filters
           WHERE
              model_id = 'account.account' AND
              context ilike '%group_by%parent_id%'
        """)


def handle_attachment_linked_to_unknown_models(cr):
    cr.execute("""
        UPDATE ir_attachment
        SET res_model = NULL
        WHERE res_model NOT IN (SELECT model FROM ir_model);
    """)


def remove_custom_reports(cr):
    cr.execute("""
        UPDATE ir_act_report_xml
        SET report_rml_content_data = null;
    """)


def remove_custom_views_without_data(cr):
    # DELETE views without ir_model_data
    cr.execute("""
        DELETE FROM ir_ui_view
        WHERE id NOT IN
              (SELECT res_id FROM ir_model_data WHERE model='ir.ui.view');
        """)


def remove_custom_workflows(cr):
    cr.execute("""
        DELETE FROM wkf
        WHERE id NOT IN
            (SELECT res_id FROM ir_model_data WHERE model like 'workflow');
    """)


def remove_customized_reports(cr):
    cr.execute("""
        UPDATE ir_act_report_xml set report_rml_content_data=null
        WHERE report_rml_content_data is not null;
        """)
    cr.execute("""
        DELETE FROM ir_values
        WHERE split_part(value,',',1)='ir.actions.report.xml'
        AND cast(split_part(value,',',2) as int)
            in (SELECT id FROM ir_act_report_xml WHERE report_type='aeroo');
    """)


def clean_custom_menu(cr):
    """ Deleting everything as Custom fixed in the migration process.

    We will use 100% of menus FROM our modules. All custom menus will come
    FROM there.
    """
    cr.execute("""
    DELETE FROM ir_ui_menu
    WHERE parent_id IN
        (SELECT id FROM ir_ui_menu WHERE name ILIKE 'Custom')
    OR id IN
        (SELECT id FROM ir_ui_menu WHERE name ILIKE 'Custom');
    """)


def clean_orphans_views(cr):
    """ Deleting everything as Custom Views in the migration process.

    We will use 100% of views FROM our modules. All custom views will come
    FROM there.
    Due to the fact that we refactor the modules dependencies then some views
    will stay orphan it is better if we simply clean up everything before the
    update.
    """
    cr.execute("""
    DELETE FROM ir_ui_view
    WHERE id IN
        (SELECT res_id
         FROM ir_model_data
         WHERE module='abastotal' and model='ir.ui.view');
    """)


def clean_specific_views(cr):
    """The theme_bairn was writing this views without inheritance which
    make that the original views were modified and avoid a proper cleanup
    through the ir_model_data technique that's why we are writing directly
    into the element the original view and the we will set a proper inheritance
    in the app.
    """
    # TODO: Dear future me I am really sorry!
    force_original = '''<?xml version="1.0"?>
    <data inherit_id="website.layout" name="Footer Copyright">
        <xpath expr="//div[contains(@id, 'footer')]" position="inside">
            <div class="container mt16 mb8">
                <div class="pull-right" t-ignore="true" t-if="not editable">
                </div>
                <div class="pull-left text-muted"
                     itemscope="itemscope"
                     itemtype="http://schema.org/Organization">
                     Copyright &amp;copy; <span t-field="res_company.name"
                     itemprop="name">Company name</span>
                </div>
            </div>
        </xpath>
    </data>
    '''

    cr.execute("""
    UPDATE ir_ui_view
    SET active=true, arch_db=%s
    WHERE id in
        (SELECT res_id
         FROM ir_model_data
         WHERE name ='layout_footer_copyright' and module='website');
    """, (force_original,))

    add_to_cart = """<?xml version="1.0"?>
    <xpath expr="//div[@class='product_price']" position="inside">
    <input name="product_id" t-att-value="product.product_variant_ids[0].id"
    type="hidden"/>
    <t t-if="len(product.product_variant_ids) == 1">
      <a class="btn btn-default btn-xs a-submit"><span
      class="fa fa-shopping-cart"/></a>
    </t>
    <t t-if="len(product.product_variant_ids) &gt; 1">
      <a class="btn btn-default btn-xs"
      t-att-href="keep('/shop/product/%s' % slug(product),
page=(pager['page']['num'] if pager['page']['num']>1 else None))">
      <span class="fa fa-shopping-cart"/></a>
    </t>
  </xpath>
    """

    cr.execute("""
    UPDATE ir_ui_view
    SET active=true, arch_db=%s
    WHERE id in
        (SELECT res_id
         FROM ir_model_data
         WHERE name ='products_add_to_cart' and module='website_sale');
    """, (add_to_cart,))

# Part of Odoo. See LICENSE file for full copyright and licensing details.


def remove_module_record(cr):
    """Removing Warnings generated when the database was migrated
    """
    with api.Environment.manage():
        env = api.Environment(cr, SUPERUSER_ID, {})
        ids = []
        for i in env['ir.model'].search([]):
            try:
                env[i.model]
            except BaseException:
                ids.append(i.id)
        if ids:
            env.cr.execute(
                '''DELETE FROM
                       ir_model
                   WHERE
                       id in %s''', (tuple(ids),))


def set_product_uom(cr):
    cr.execute(
        """UPDATE stock_move_line as sml
        SET product_uom_id=t.uom_id
        FROM product_product AS p
        INNER JOIN product_template AS t ON t.id=p.product_tmpl_id
        WHERE sml.product_uom_id IS NULL AND p.id=sml.product_id;""")


def remove_country_format(cr):
    country_mx_format = "%(street)s\n%(street2)s\n%(city)s %(state_code)s %(zip)s\n%(country_name)s"  # noqa
    cr.execute(
        """UPDATE res_country
        SET address_format=%s
        WHERE code='MX'""", (country_mx_format,))


def update_res_partner_bank_index(cr):
    cr.execute(
        """UPDATE res_partner_bank AS b1
        SET sanitized_acc_number = b1.sanitized_acc_number || '-' || b1.id
        FROM res_partner_bank AS b2
        WHERE b1.sanitized_acc_number = b2.sanitized_acc_number
        AND b1.id>b2.id;""")


def set_client_order_ref(cr):
    env = api.Environment(cr, SUPERUSER_ID, {})
    sale_ids = env["sale.order"].search([
        ("client_order_ref", "=", False)
    ])
    sale_ids.write({"client_order_ref": "  "})
    env.user.company_id.write(
        {'chart_template_id': env.ref('requiez.mx_coa').id})


def pre_init_hook(cr):
    remove_deprecated(cr)
    remove_uncertified_data(cr)
    clean_actions(cr)
    clean_views(cr)
    clean_attachments(cr)
    group_custom_menus(cr)
    delete_obsolete_objects_from_data(cr)
    handle_attachment_linked_to_unknown_models(cr)
    remove_custom_views_without_data(cr)
    clean_custom_menu(cr)
    clean_orphans_views(cr)
    clean_specific_views(cr)
    remove_module_record(cr)
    set_product_uom(cr)
    remove_country_format(cr)
    update_res_partner_bank_index(cr)
    _logger.info('Importing Chart')
    tools.convert_file(
        cr, 'requiez',
        'data/chart_template.xml', {}, 'init',
        True, 'data', False)
    set_client_order_ref(cr)
