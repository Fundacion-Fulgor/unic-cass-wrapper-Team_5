# Simulator setup
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Path to source directory
SRC_DIR = $(CURDIR)/../../src

# Sources
VERILOG_SOURCES += $(SRC_DIR)/cdc_snapshot.v

# DUT settings
TOPLEVEL = cdc_snapshot
MODULE = cdc_snapshot_tb

# Cocotb standard rules
include $(shell cocotb-config --makefiles)/Makefile.sim
