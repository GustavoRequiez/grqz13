odoo.define('l10n_mx_edi_vendor_bills', function (require) {
"use strict";

var basicFields = require('web.basic_fields');
var FieldRegistry = require('web.field_registry');
var FieldChar = basicFields.FieldChar;

var _t = require('web.translation')._t;

var attachXmlsWizard = FieldChar.extend({
    template: 'attach_xmls_template',

    events: {
        // events drag and drop on the div handler
        'dragenter #dragandrophandler': function(e){
            e.stopPropagation();
            e.preventDefault();
        },
        'dragover #dragandrophandler': function(e){
            e.stopPropagation();
            e.preventDefault();
            $(e.currentTarget).removeClass('dnd_out').addClass('dnd_inside');
        },
        'drop #dragandrophandler': function(e){
            e.preventDefault();
            this.handleFileUpload(e.originalEvent.dataTransfer.files);
        },
        // Opens dialog box to attach files
        'click #dragandrophandler': function(){
            this.$el.find("#files").val("");
            this.$el.find("#files").click();
        },
        'change #files': function(e){
            if(e.currentTarget.files.length > 0){
                this.handleFileUpload(e.currentTarget.files);
            }
        },
        // Removes the file with a click over the respective file content in page
        'click #filescontent .xml_cont_hover': function(e){
            delete this.files[e.currentTarget.attributes.title.value];
            $(e.currentTarget).animate({'opacity': '0'}, 500, function(){
                $(this).remove();
            });
        },
        // Executes the respective actions for each case in the exceptions after press button save
        'click #alertscontent .dnd-alert-button': function(e){
            var type = e.currentTarget.attributes.tag.value;
            var alertnode = e.currentTarget.parentElement.parentElement;
            var filekey = alertnode.attributes.tag.value;
            var self = this;
            if(type === 'remove'){
                this.removeWrongAlerts($(alertnode), filekey, true);
            }else if(type === 'supplier'){
                self._rpc({
                    model: 'attach.xmls.wizard',
                    method: 'create_partner',
                    args: [this.alerts_in_queue.alertHTML[filekey].xml64, filekey],
                    context: self.getParent().state.context,
                }).then(function () {
                    self.sendErrorToServer(self.alerts_in_queue.alertHTML[filekey].xml64, filekey, 'check_xml');
                });
            }else if(type === 'tryagain'){
                this.sendErrorToServer(this.alerts_in_queue.alertHTML[filekey].xml64, filekey, 'check_xml');
            } else if (type === 'forcesave') {
                self.getParent().state.context = _.extend(self.getParent().state.context, {'force_save': true});
                self.sendErrorToServer(self.alerts_in_queue.alertHTML[filekey].xml64, filekey, 'check_xml');
            }
        },
        'click #dndfooter button#save': function(e){
            e.preventDefault();
            this.$el.find('.alert-warning.dnd-alert').remove();
            if(Object.keys(this.files).length <= 0){
                this.do_warn(_t('There is no files selected'));
            }else if(Object.keys(this.files).length > 1 && this.getParent().state.context.active_ids){
                this.do_warn(_t('You cannot attach more than one xml to an invoice'));
            }else{
                this.$el.find("#dragandrophandler").hide();
                this.$el.find('#dndfooter button#save').attr('disabled', true);
                this.$el.find("#filescontent").find('.xml_cont').removeClass('xml_cont_hover');
                this.readFiles(this.files);
            }
        },
        // Closes the wizard view
        'click #dndfooter button#close': function(e){
            e.preventDefault();
            this.do_action({'type': 'ir.actions.act_window_close'});
        },
        // Shows you the invoices created in a treeview
        'click #dndfooter button#show': function(e){
            e.preventDefault();
            if(this.invoice_ids.length > 0){
                var domain = [['id', 'in', this.invoice_ids]];
                return this.do_action({
                    name: _t('Supplier Invoices'),
                    view_type: 'list',
                    view_mode: 'list,form',
                    res_model: 'account.move',
                    type: 'ir.actions.act_window',
                    views: [[false, 'list'], [false, 'form']],
                    targe: 'current',
                    domain: domain,
                });
            }
        },
    },
    start: function(){
        this.files = {};
        this.uploading_files = false;
        this.invoice_ids = [];

        var handler = this.$el.find("#dragandrophandler");
        // events drag and drop inside the page
        $(document).on('dragenter', function (e) {
            e.stopPropagation();
            e.preventDefault();
            handler.removeClass('dnd_inside dnd_normal').addClass('dnd_out');
        });
        $(document).on('dragover', function (e) {
            // allows to execute the drop event
            e.stopPropagation();
            e.preventDefault();
        });
        $(document).on('drop', function (e) {
            e.stopPropagation();
            e.preventDefault();
            handler.removeClass('dnd_out dnd_inside').addClass('dnd_normal');
        });
        $(document).on('dragleave', function (e) {
            e.stopPropagation();
            e.preventDefault();
            if(!e.originalEvent.clientX && !e.originalEvent.clientY){
                handler.removeClass('dnd_out dnd_inside').addClass('dnd_normal');
            }
        });
    },
    handleFileUpload: function(files){
        /* Creates the file element in the DOM and shows alerts wheter the extension
        file is not the correct one or the file is already uploaded */
        var self = this;
        if(self.uploading_files){
            self.do_warn(_t('There are files uploading'));
        }else{
            self.uploading_files = true;
            var files_used = [];
            var wrong_files = [];
            $.each(files, function(i, file){
                if(file.type !== 'text/xml'){
                    wrong_files.push(file.name);
                }else if(Object.prototype.hasOwnProperty.call(self.files, file.name)){
                    files_used.push(file.name);
                }else{
                    self.files[file.name] = file;
                    var newelement = $('<div class="xml_cont xml_cont_hover" title="'+file.name+'">' +
                        '<img class="xml_img" height="100%" align="left" hspace="5"/>' +
                        '<p>'+file.name+'</p><div class="remove_xml">&times;</div>' +
                        '</div>').css('opacity', '0');
                    self.$el.find("#filescontent").append(newelement);
                    newelement.animate({'opacity': '1'}, 500);
                }
            });
            var alert_message = '';
            if(wrong_files.length > 0){
                alert_message += _t('<strong>Info!</strong> You only can upload XML files.<br>') +
                    wrong_files.join(" <b style='font-size:15px;font-wight:900;'>&#8226;</b> ");
            }
            if(files_used.length > 0){
                if(alert_message !== ''){
                    alert_message += '<br>';
                }
                alert_message += _t('<strong>Info!</strong> Some files are already loaded.<br>') +
                    files_used.join(" <b style='font-size:15px;font-wight:900;'>&#8226;</b> ");
            }
            if(alert_message !== ''){
                self.$el.find("#alertscontent").html('<div class="alert alert-warning dnd-alert">' +
                    '<a href="#" class="close" data-dismiss="alert" aria-label="close">&times;</a>' + alert_message +
                    '</div>');
            }
            self.uploading_files = false;
        }
    },
    readFiles: function(files){
        /* Convert the file object uploaded to a base64 string */
        var self = this;
        var readfiles = {};
        $.each(files, function(key, file){
            var fr = new FileReader();
            fr.onload = function(){
                readfiles[key] = fr.result;
                if(Object.keys(files).length === Object.keys(readfiles).length){
                    self.sendFileToServer(readfiles);
                }
            };
            fr.readAsDataURL(file);
        });
    },
    getFields: function(){
        var self = this;
        var fields = {};
        $.each(self.getParent().state.data, function(field, value){
            if (!value || field === 'omit_cfdi_related'){
                fields[field] = value;
            } else if (value.data.constructor === Array) {
                var valueList = [];
                $.each(value.data, function(index, val){
                    valueList.push(val.data.id);
                });
                fields[field] = valueList;
            } else {
                fields[field] = value.data.id;
            }
        });
        return fields;
    },
    sendFileToServer: function(files){
        /* Sends each base64 file string to the back-end server to create the invoices */
        var self = this;
        var options = self.getFields();
        var ctx = self.getParent().state.context;
        ctx.account_id = options.account_id;
        ctx.journal_id = options.journal_id;
        ctx.omit_cfdi_related = options.omit_cfdi_related;
        self._rpc({
            model: 'attach.xmls.wizard',
            method: 'check_xml',
            args: [files],
            context: ctx,
        }).then(function (result) {
            var wrongfiles = result.wrongfiles;
            var invoices = result.invoices;
            $.each(invoices, function(key, data){
                self.invoice_ids.push(data.invoice_id);
                self.createdCorrectly(key);
            });
            if(Object.keys(wrongfiles).length > 0){
                self.handleFileWrong(wrongfiles);
            }
            if(Object.keys(wrongfiles).length === 0 || self.alerts_in_queue.total === 0){
                self.correctFinalRegistry();
            }
        });
    },
    createdCorrectly: function(key){
        /* Colors the files content in the DOM when the invoice is created with that XML */
        var self = this;
        var alert = self.$el.find('#filescontent div[title="'+key+'"]');
        alert.addClass('xml_correct');
        alert.find('div.remove_xml').html('&#10004;');
    },
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
                self.do_warn(_t('XML removed, the TipoDeComprobante is not I or E.'));
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
    prepareWrongAlert: function(key, data){
        /* Prepares the buttons and message the invoice alert exception will contain */
        var self = this;
        var errors = '';
        var buttons = '';
        var able_buttons = [];
        var alerttype = '';
        if('error' in data){
            errors += self.wrongMsgServer(data, able_buttons);
            alerttype = 'danger';
        }else{
            errors += self.wrongMsgXml(data, able_buttons);
            alerttype = 'info';
        }
        if(able_buttons.includes('remove')){
            buttons += _t('<button class="dnd-alert-button" tag="remove">Remove XML</button>');
        }else if(able_buttons.includes('supplier') && !able_buttons.includes('remove')){
            buttons += _t('<button class="dnd-alert-button" tag="remove">Remove XML</button>') +
                _t('<button class="dnd-alert-button" tag="supplier">Create Supplier</button>');
        }else if(able_buttons.includes('tryagain')){
            buttons += _t('<button class="dnd-alert-button" tag="remove">Remove XML</button>') +
                _t('<button class="dnd-alert-button" tag="tryagain">Try again</button>');
        }else if(able_buttons.includes('invoice_not_found')){
             buttons += _t('<button class="dnd-alert-button" tag="remove">Remove XML</button>') +
                 _t('<button class="dnd-alert-button" tag="forcesave">Force Save</button>');
        }
        return {'errors': errors, 'buttons': buttons, 'alerttype': alerttype};
    },
    wrongMsgServer: function(data, able_buttons){
        /* Prepares the message to the server error */
        var typemsg = {'CheckXML': _t('Error checking XML data.'), 'CreatePartner': _t('Error creating supplier.'), 'CreateInvoice': _t('Error creating invoice.')};
        var errors = '<div><span level="2">'+ data.error[0] +'</span> <span level="1">'+ data.error[1] +'</span>.<br>'+ typemsg[data.where] +'</div>';
        able_buttons.push('tryagain');
        return errors;
    },
    wrongMsgXml: function(file, able_buttons){
        /* Prepares the message to the xml errors */
        var self = this;
        var errors = '';
        var map_error = {
            signed: _t('<div><span level="1">UUID</span> not found in the XML.</div>'),
            version: _t('<div><span level="1">Unable to generate invoices from an XML with version 3.2.</span>You can create the invoice manually and then attach the xml.</div>'),
            cancel: _t('<div><span level="1">The XML state</span> is CANCELED in the SAT system.</div>'),
            nothing: _t('<div><strong>Info!</strong> XML data could not be read correctly.</div>'),
            no_xml_related_uuid: _t('<div><span level="1">The DocumentType is "E" and The XML UUID / and the node CfdiRelacionados</span> were not found in the XML.</div>'),
        };
        $.each(file, function(ikey, val){
            if(ikey !== 'supplier' && ikey !== 'xml64' && ikey !== 'invoice_not_found' && !able_buttons.includes('remove')){
                able_buttons.push('remove');
            }
            if(ikey === 'supplier'){
                errors += _t('<div><span level="1">The XML Supplier</span> was not found: <span level="2">') + val + '</span>.</div>';
                able_buttons.push('supplier');
            }else if(ikey === 'rfc'){
                errors += _t('<div><span level="1">The XML Receptor RFC</span> does not match with <span level="1">your Company RFC</span>: ') +
                    _t('XML Receptor RFC: <span level="2">') + val[0] + _t(', </span> Your Company RFC: <span level="2">') + val[1] + '</span></div>';
            }else if(ikey === 'currency'){
                errors += _t('<div><span level="1">The XML Currency</span> <span level="2">') + val + _t('</span> was not found or is disabled.</div>');
            }else if(ikey === 'taxes'){
                errors += _t('<div><span level="1">Some taxes</span> do not exist: <span level="2">') + val.join(', ') + '</span>.</div>';
            }else if(ikey === 'taxes_wn_accounts'){
                errors += _t('<div><span level="1">Some taxes</span> do not have account asigned: <span level="2">') + val.join(', ') + '</span>.</div>';
            }else if(ikey === 'folio'){
                errors += _t('<div><span level="1">The XML Folio</span> does not match with <span level="1">Supplier Invoice Number</span>: ') +
                    _t('XML Folio: <span level="2">') + val[0] + _t(', </span> Supplier invoice number: <span level="2">') + val[1] + '</span></div>';
            }else if(ikey === 'rfc_supplier'){
                errors += _t('<div><span level="1">The XML Emitter RFC</span> does not match with <span level="1">Customer RFC</span>: ') +
                    _t('XML Emitter RFC: <span level="2">') + val[0] + _t(', </span> Customer RFC: <span level="2">') + val[1] + '</span></div>';
            }else if(ikey === 'amount'){
                errors += _t('<div><span level="1">The XML amount total</span> does not match with <span level="1">Invoice total</span>: ') +
                    _t('XML amount total: <span level="2">') + val[0] + _t(', </span> Invoice Total: <span level="2">') + val[1] + '</span></div>';
            }else if(ikey === 'uuid_duplicate'){
                errors += _t('<div><span level="1">The XML UUID</span> belong to other invoice. <span level="1">UUID: </span>') + val +'</div>';
            }else if(ikey === 'reference'){
                errors += _t('<div><span level="1">The invoice reference</span> belong to other invoice of same partner. <span level="1">Partner: </span>') + val[0] + _t('<span level="1"> Reference: </span>') + val[1] +'</div>';
            }else if(ikey === 'invoice_not_found'){
                errors += _t('<div><span level="1">The DocumentType is "E" and The XML UUID</span> is not related to any invoice. <span level="1">UUID: </span>') + val +'</div>';
                $.when(self.getSession().user_has_group('l10n_mx_edi_vendor_bills.allow_force_invoice_generation')).then( function (has_group) {
                     if (has_group) {
                         able_buttons.push('invoice_not_found');
                     }else{
                         able_buttons.push('remove');
                     }
                });
            }else if(Object.prototype.hasOwnProperty.call(map_error, ikey)){
                errors += map_error[ikey];
            }
        });
        return errors;
    },
    sendErrorToServer: function(xml64, key, function_def){
        /* Sends again the base64 file string to the server to tries to create the invoice, or
        sends the partner data to create him if does not exist */
        var self = this;
        var xml_file = {};
        xml_file[key] = xml64;
        var options = self.getFields();
        var ctx = self.getParent().state.context;
        ctx.account_id = options.account_id;
        self._rpc({
            model: 'attach.xmls.wizard',
            method: function_def,
            args: [xml_file],
            context: ctx,
        }).then(function (data) {
            var wrongfiles = data.wrongfiles;
            var invoices = data.invoices;
            $.each(invoices, function(rkey, result){
                var alertobj = self.$el.find('#alertscontent div[tag="'+rkey+'"].alert.dnd-alert');
                self.invoice_ids.push(result.invoice_id);
                self.createdCorrectly(rkey);
                self.removeWrongAlerts(alertobj, rkey, false);
                });
            $.each(wrongfiles, function(rkey, result){
                var alert_parts = self.prepareWrongAlert(rkey, result);
                var alertobj = self.$el.find('#alertscontent div[tag="'+rkey+'"].alert.dnd-alert');
                var footer = alertobj.find('div:last-child span:not(.index-alert)');
                alertobj.removeClass('alert-danger alert-info').addClass('alert-'+alert_parts.alerttype);
                alertobj.html(alert_parts.errors + '<div>' + alert_parts.buttons + '</div>');
                alertobj.find('div:last-child').append(footer);
            });
        });
    },
    removeWrongAlerts: function(alertobj, filekey, removefile){
        /* Removes the current error alert to continue with the others */
        var self = this;
        alertobj.slideUp(500, function(){
            delete self.alerts_in_queue.alertHTML[filekey];
            if(removefile){
                delete self.files[filekey];
                self.$el.find('#filescontent div[title="'+filekey+'"]').animate({'opacity': '0'}, 500, function(){
                    $.when($(this).remove()).done(function(){
                        self.continueAlert(alertobj);
                    });
                });
            }else{
                self.continueAlert(alertobj);
            }
        });
    },
    continueAlert: function(alertobj){
        /* After the error alert is removed, execute the next actions
        (Next error alert, Restarts to attach more files, or Shows the final success alert) */
        var self = this;
        $.when(alertobj.remove()).done(function(){
            if(Object.keys(self.alerts_in_queue.alertHTML).length > 0){
                self.nextWrongAlert();
            }else if(Object.keys(self.files).length === 0){
                self.restart();
            }else{
                self.correctFinalRegistry();
            }
        });
    },
    nextWrongAlert: function(){
        /* Shows the next error alert */
        var self = this;
        var keys = Object.keys(self.alerts_in_queue.alertHTML);
        var alert = self.alerts_in_queue.alertHTML[keys[0]].alert.hide();
        alert.find('div:last-child .index-alert').html(self.alerts_in_queue.total - (keys.length - 1));
        self.$el.find("#alertscontent").html(alert);
        alert.slideDown(500);
    },
    restart: function(){
        /* Restarts all the variables and restores all the DOM element to attach more new files */
        this.files = {};
        this.invoice_ids = [];
        this.uploading_files = false;
        this.alerts_in_queue = {};
        this.$el.find("#dragandrophandler").show();
        this.$el.find("#filescontent").html('');
        this.$el.find("#files").val('');
        this.$el.find('#dndfooter button#save').attr('disabled', false);
        this.$el.find('#alertscontent div.alert').remove();
        this.$el.find('#dndfooter button#show').hide();
    },
    correctFinalRegistry: function(){
        /* Shows the final success alert and the button to see the invoices created */
        var self = this;
        var alert = $('<div class="alert alert-success dnd-alert"><strong>' + _t('Congratulations') + '!</strong> ' +
            _t('Your invoices were created correctly') + '.</div>').hide();
        self.$el.find("#alertscontent").html(alert);
        alert.slideDown(500, function(){
            self.$el.find('#dndfooter button#show').show();
        });
    },
});

FieldRegistry.add('attach_xmls_wizard_widget', attachXmlsWizard);
return {attachXmlsWizard: attachXmlsWizard};
});
