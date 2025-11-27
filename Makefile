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
	src/server/fylr-export-transport-ftp.py \
	src/server/fylr-export-transport-webdav.py \
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
	python3 src/server/ftp_test.py

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


# ----------------------------
# fylr only

BUILD_DIR=build
ZIP_NAME=$(PLUGIN_PATH).zip

zip: build
	(rm $(BUILD_DIR)/$(ZIP_NAME) || true)
	mkdir -p $(PLUGIN_PATH)/src
	mkdir -p $(PLUGIN_PATH)/webfrontend/l10n
	cp $(JS) $(PLUGIN_PATH)/webfrontend
	cp -r src/server $(PLUGIN_PATH)/src/server
	cp $(L10N_FILES) $(PLUGIN_PATH)/webfrontend/l10n
	cp $(WEB)/l10n/*.json $(PLUGIN_PATH)/webfrontend/l10n
	cp manifest.yml $(PLUGIN_PATH)
	cp build-info.json $(PLUGIN_PATH)
	zip $(BUILD_DIR)/$(ZIP_NAME) -r $(PLUGIN_PATH)/
	rm -rf $(PLUGIN_PATH)
