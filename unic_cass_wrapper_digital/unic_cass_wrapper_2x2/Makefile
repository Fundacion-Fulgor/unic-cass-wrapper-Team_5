TOP = unic_cass_wrapper_2x2
TOP_DESIGN = user_project_wrapper_2x2
TAG ?= unic_cass_wrapper_2x2_run
HOME_DIR = ../../
PROJECT_DIR = $(HOME_DIR)/unic_cass_wrapper_digital
LIBRELANE_DIR ?= $(HOME_DIR)/librelane
PDK_ROOT = $(HOME_DIR)/IHP-Open-PDK
PDK=ihp-sg13g2

CONFIG_FILE = $(PROJECT_DIR)/$(TOP)/config.json

.PHONY: all
all: librelane drc

librelane: final/gds/$(TOP).gds
.PHONY: librelane

final/gds/$(TOP).gds:
	# Run librelane to generate the layout
	nix-shell --pure $(LIBRELANE_DIR) --run "PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) librelane --run-tag $(TAG) --overwrite --manual-pdk $(CONFIG_FILE)"

	# copy final results to top directory
	rm -rf $(PROJECT_DIR)/$(TOP)/final
	cp -r $(PROJECT_DIR)/$(TOP)/runs/$(TAG)/final $(PROJECT_DIR)/$(TOP)

.PHONY: view_results
view_results: 
	# View the results in KLayout
	nix-shell --pure $(LIBRELANE_DIR) --run "PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) librelane --last-run --manual-pdk $(CONFIG_FILE) --flow OpenInOpenROAD"

.PHONY: view_klayout
view_klayout:
	# View the generated GDS in KLayout
	nix-shell --pure $(LIBRELANE_DIR) --run "PDK_ROOT=$(PDK_ROOT) PDK=$(PDK) librelane --last-run --manual-pdk $(CONFIG_FILE) --flow OpenInKlayout"

.PHONY: drc
drc: 
	# Run DRC on the generated GDS
	python $(PDK_ROOT)/$(PDK)/libs.tech/klayout/tech/drc/run_drc.py --path final/gds/$(TOP_DESIGN).gds --run_dir final/drc --no_density --disable_extra_rules --no_recommended
