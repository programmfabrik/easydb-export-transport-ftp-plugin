class ExportTransportWebDAV extends ExportTransportPlugin
	getType: ->
		"easydb-export-transport-ftp:transport_webdav"

	getDisplayType: ->
		$$("export.transport.webdav.type|text")

	getDisplayIcon: ->
		ez5.loca.str_default("export.transport.webdav.type|icon")

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
			hint: true
		,
			key: "password"
			hint: true
		]
			formOpts =
				label: $$("export.transport.webdav.option."+opt.key)

			if opt.hint
				formOpts.hint = $$("export.transport.webdav.option.hint."+opt.key)

			fields.push
				type: CUI.Input
				name: opt.key
				form: formOpts
				maximize_horizontal: true

		formOpts =
			label: $$("export.transport.webdav.option.packer")

		fields.push
			type: CUI.DataFieldProxy
			name: "packer"
			form: formOpts
			element: (field) =>
				data = field.getData()

				if CUI.util.isUndef(data.packer)
					data.packer = "folder"
				select = new CUI.Select
					name: "packer"
					data: data
					options: ->
						options = []
						for k in ["folder", "zip", "tar.gz"]
							options.push
								text: $$("export.transport.packer.#{k}")
								value: k
						return options
				select.start()
				return select

		fields

	getSaveData: (data) ->
		if not data.options?.server
			throw new InvalidSaveDataException()
		loc = CUI.parseLocation(data.options.server)
		if not loc or not loc.hostname or not loc.protocol in ["http", "https"]
			throw new InvalidSaveDataException()
		return

	supportsPacker: ->
		return false

CUI.ready =>
	if ez5.version("6")
		TransportsEditor.registerPlugin(new ExportTransportWebDAV())
