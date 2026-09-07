# Simulator setup
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

FFT16_DIR = $(CURDIR)/../..
REPO_DIR  = $(FFT16_DIR)/../../..
# Deliberately not PDK_ROOT: that name is often already set in the environment
PDK_DIR    ?= $(REPO_DIR)/IHP-Open-PDK
STDCELL_DIR = $(PDK_DIR)/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog
IO_DIR      = $(PDK_DIR)/ihp-sg13g2/libs.ref/sg13g2_io/verilog
WRAPPER_DIR = $(REPO_DIR)/unic_cass_wrapper_digital/unic_cass_wrapper_2x2

FFT_NETLIST     ?= $(FFT16_DIR)/final/nl/fft16_project.nl.v
WRAPPER_NETLIST ?= $(WRAPPER_DIR)/final/nl/user_project_wrapper_2x2.nl.v

# fft exercises the hardened macro on its own, wrapper exercises the same design
# reached through the pad ring of the chip it is integrated in.
GLS_MODE ?= fft

SIM_BUILD           = $(CURDIR)/sim_build/$(GLS_MODE)
COCOTB_RESULTS_FILE = $(CURDIR)/results_$(GLS_MODE).xml

# The IHP cell models drive their flip-flops from delayed_* wires that only the
# specify block produces, and Icarus does not implement that, so every output
# would stay X. prepare_models.py rewrites those wires as direct aliases.
SIM_MODELS = $(SIM_BUILD)/sg13g2_stdcell_sim.v

VERILOG_SOURCES += $(STDCELL_DIR)/sg13g2_udp.v
VERILOG_SOURCES += $(SIM_MODELS)

ifeq ($(GLS_MODE),wrapper)
VERILOG_SOURCES += $(IO_DIR)/sg13g2_io.v
VERILOG_SOURCES += $(CURDIR)/gls_stubs.v
VERILOG_SOURCES += $(FFT_NETLIST)
VERILOG_SOURCES += $(WRAPPER_NETLIST)
VERILOG_SOURCES += $(CURDIR)/gls_wrapper_top.v
TOPLEVEL = gls_wrapper_top
else
VERILOG_SOURCES += $(FFT_NETLIST)
VERILOG_SOURCES += $(CURDIR)/gls_top.v
TOPLEVEL = gls_top
endif

# The bring-up testbench is reused as is; it only ever touches ports
export PYTHONPATH := $(CURDIR)/../top_fft16_bringup:$(FFT16_DIR)/model:$(PYTHONPATH)

MODULE = top_fft16_bringup_tb

.PHONY: gls gls_fft gls_wrapper

gls: gls_fft gls_wrapper

gls_fft:
	@echo "=== GLS: hardened fft16_project macro ==="
	$(MAKE) GLS_MODE=fft sim

gls_wrapper:
	@echo "=== GLS: fft16_project inside user_project_wrapper_2x2, through the pads ==="
	$(MAKE) GLS_MODE=wrapper sim

# Cocotb standard rules
include $(shell cocotb-config --makefiles)/Makefile.sim

$(SIM_MODELS): $(STDCELL_DIR)/sg13g2_stdcell.v prepare_models.py
	@mkdir -p $(dir $@)
	python3 $(CURDIR)/prepare_models.py $< $@

$(SIM_BUILD)/sim.vvp: $(SIM_MODELS)
