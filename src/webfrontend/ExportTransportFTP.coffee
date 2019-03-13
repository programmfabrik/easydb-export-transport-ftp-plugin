class ExportTransportFTP extends ExportTransportPlugin
	getType: ->
		"ftp"

	getDisplayType: ->
		$$("export.transport.ftp.type|text")

	getDisplayIcon: ->
		ez5.loca.str_default("export.transport.ftp.type|icon")

	isAllowed: ->
		true

	getOptionsDisplay: (data) ->
		if data.options.server
			[ data.options.server ]
		else
			return

	getOptions: ->
		fields = []

		for opt in [
			key: "server"
			hint: true
		,
			key: "directory"
			hint: true
		,
			key: "login"
		,
			key: "password"
		]
			formOpts =
				label: $$("export.transport.ftp.option."+opt.key)

			if opt.hint
				formOpts.hint = $$("export.transport.ftp.option.hint."+opt.key)

			fields.push
				type: CUI.Input
				name: opt.key
				form: formOpts
				maximize_horizontal: true

		fields

	getSaveData: (data) ->
		if not data.options?.server
			throw new InvalidSaveDataException()
		loc = CUI.parseLocation(data.options.server)
		if not loc or not loc.hostname or not loc.protocol in ["ftp", "ftps", "sftp"]
			throw new InvalidSaveDataException()
		return

CUI.ready =>
	TransportsEditor.registerPlugin(new ExportTransportFTP())
