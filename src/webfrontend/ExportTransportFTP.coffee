class ExportTransportFTP extends ExportTransportPlugin
	getType: ->
		if ez5.version("6")
			"easydb-export-transport-ftp-plugin:transport_ftp"
		else
			return "ftp"

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

		formOpts =
			label: $$("export.transport.ftp.option.packer")

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
		if not loc or not loc.hostname or not loc.protocol in ["ftp", "ftps", "sftp"]
			throw new InvalidSaveDataException()
		if not data.uuid? or data.uuid is ''
			data.uuid = ez5.generateUUID()
		return

	supportsPacker: ->
		return false

CUI.ready =>
	TransportsEditor.registerPlugin(new ExportTransportFTP())
