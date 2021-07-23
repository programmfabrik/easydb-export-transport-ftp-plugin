PLUGIN_NAME = easydb-export-transport-ftp
PLUGIN_PATH = easydb-export-transport-ftp-plugin

L10N_FILES = l10n/$(PLUGIN_NAME).csv
L10N_GOOGLE_KEY = 1Z3UPJ6XqLBp-P8SUf-ewq4osNJ3iZWKJB83tc6Wrfn0
L10N_GOOGLE_GID = 1868686590

INSTALL_FILES = \
	$(WEB)/l10n/cultures.json \
	$(WEB)/l10n/de-DE.json \
	$(WEB)/l10n/en-US.json \
	$(WEB)/l10n/es-ES.json \
	$(WEB)/l10n/it-IT.json \
	$(JS) \
	src/server/$(PLUGIN_NAME).py \
	manifest.yml

COFFEE_FILES = 	src/webfrontend/ExportTransportFTP.coffee \
				src/webfrontend/ExportTransportWebDAV.coffee


all: build

include easydb-library/tools/base-plugins.make

build: code $(L10N) buildinfojson

code: $(JS)

clean: clean-base

wipe: wipe-base

test:
	python2 src/server/test.py

# all:

# INSTALL_FILES = \
# 	ftp.py \
# 	plugin.json

# install-server: ${INSTALL_FILES}
# 	[ ! -z "${INSTALL_PREFIX}" ]
# 	for f in ${INSTALL_FILES}; do \
# 		mkdir -p ${INSTALL_PREFIX}/server/base/plugins/transport/ftp/`dirname $$f`; \
# 		cp $$f ${INSTALL_PREFIX}/server/base/plugins/transport/ftp/$$f; \
# 	done

