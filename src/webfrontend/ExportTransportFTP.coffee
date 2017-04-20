class ExportTransportFTP extends ExportTransportPlugin
	getType: ->
		"ftp"

	getDisplayType: ->
		$$("export.transport.ftp.name")

	getOptions: ->
		fields = []

		for opt in [
			"server"
			"directory"
			"login"
			"password"
		]
			fields.push
				type: Input
				name: opt
				form: label: $$("export.transport.ftp.option."+opt)
				undo_and_changed_support: false

		fields

CUI.ready =>
	TransportsEditor.registerPlugin(new ExportTransportFTP())
