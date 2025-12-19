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
	manifest.master.yml

COFFEE_FILES = 	src/webfrontend/ExportTransportFTP.coffee \
				src/webfrontend/ExportTransportWebDAV.coffee


all: build build_fylr

include easydb-library/tools/base-plugins.make

build: code $(L10N) buildinfojson

code: $(JS)

clean: clean-base clean_fylr

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

FYLR_BUILD_DIR=build_fylr

clean_fylr:
	rm -rf $(FYLR_BUILD_DIR)

build_fylr: code buildinfojson
	mkdir -p             $(FYLR_BUILD_DIR)/$(PLUGIN_PATH)/l10n
	cp -r build/*        $(FYLR_BUILD_DIR)/$(PLUGIN_PATH)
	cp -f $(L10N_FILES)  $(FYLR_BUILD_DIR)/$(PLUGIN_PATH)/l10n
	cp -r src/server     $(FYLR_BUILD_DIR)/$(PLUGIN_PATH)
	cp manifest_fylr.yml $(FYLR_BUILD_DIR)/$(PLUGIN_PATH)/manifest.yml
	cp build-info.json   $(FYLR_BUILD_DIR)/$(PLUGIN_PATH)
# delete unnecessary files from a previous easdyb5 build process
	rm -rf               $(FYLR_BUILD_DIR)/$(PLUGIN_PATH)/webfrontend/l10n

zip: build_fylr
	cd $(FYLR_BUILD_DIR) && zip $(PLUGIN_PATH).zip -r $(PLUGIN_PATH)
