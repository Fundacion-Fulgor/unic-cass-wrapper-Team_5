# Simulator setup
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Path to source directory
SRC_DIR = $(CURDIR)/../../src

# Sources
VERILOG_SOURCES += $(SRC_DIR)/debug_unit.v
VERILOG_SOURCES += $(SRC_DIR)/cdc_snapshot.v

# DUT settings
TOPLEVEL = debug_unit
MODULE   = debug_unit_tb

# Cocotb standard rules
include $(shell cocotb-config --makefiles)/Makefile.sim
