odoo.define('l10n_mx_edi_customer_bills', function (require) {
    "use strict";

    var core = require('web.core');
    var _t = core._t;
    var vendor_bills = require('l10n_mx_edi_vendor_bills');

    vendor_bills.attachXmlsWizard.include({
        events: _.extend({}, vendor_bills.attachXmlsWizard.prototype.events, {
            'click #dndfooter button#show': function(e){
                e.preventDefault();
                if(this.invoice_ids.length > 0){
                    var domain = [['id', 'in', this.invoice_ids]];
                    var name = this.getParent().state.context.l10n_mx_edi_invoice_type === 'out' ? 'Customer Invoices': 'Supplier Invoices';
                    return this.do_action({
                        name: _t(name),
                        view_type: 'list',
                        view_mode: 'list,form',
                        res_model: 'account.move',
                        type: 'ir.actions.act_window',
                        views: [[false, 'list'], [false, 'form']],
                        targe: 'current',
                        domain: domain,
                        context: this.getParent().state.context,
                    });

                }

            },

        }),
        handleFileWrong: function(wrongfiles){
            /* Saves the exceptions occurred in the invoices creation */
            this.alerts_in_queue = {'alertHTML': {}, total: Object.keys(wrongfiles).length};
            var self = this;
            $.each(wrongfiles, function(key, file){
                if('cfdi_type' in file){
                    if(Object.keys(self.files).length === 0){
                        self.restart();
                    }
                    self.alerts_in_queue.total -= 1;
                    self.$el.find('#filescontent div[title="'+key+'"]').remove();
                    var message = self.getParent().state.context.l10n_mx_edi_invoice_type === 'out' ? _t('XML removed, the TipoDeComprobante is not I.'): _t('XML removed, the TipoDeComprobante is not I or E.');
                    self.do_warn(message);
                }else{
                    var alert_parts = self.prepareWrongAlert(key, file);

                    var alertelement = $('<div tag="'+ key +'" class="alert alert-'+ alert_parts.alerttype +' dnd-alert">' +
                        alert_parts.errors + '<div>' + alert_parts.buttons + _t('<span>Wrong File: <span class="index-alert"></span>') + '/' + self.alerts_in_queue.total +
                        '<b style="font-size:15px;font-wight:900;">&#8226;</b> ' + key + '</span></div></div>');
                    self.alerts_in_queue.alertHTML[key] = {'alert': alertelement, 'xml64': file.xml64};
                }
                if(self.alerts_in_queue.total > 0 && self.alerts_in_queue.total === Object.keys(self.alerts_in_queue.alertHTML).length){
                    self.nextWrongAlert();
                }
            });
        },
        wrongMsgXml: function(file, able_buttons){
            var errors = this._super.apply(this, arguments);
            $.each(file, function(ikey, val){
                if(ikey === 'rfc_cust'){
                    errors += _t('<div><span level="1">The XML Emitter RFC</span> does not match with <span level="1">your Company RFC</span>: ') +
                        _t('XML Emitter RFC: <span level="2">') + val[0] + _t(', </span> Your Company RFC: <span level="2">') + val[1] + '</span></div>';
                    if(!able_buttons.includes('remove')){
                        able_buttons.push('remove');
                    }
                }
            });
            return errors;
        }
    });
});
