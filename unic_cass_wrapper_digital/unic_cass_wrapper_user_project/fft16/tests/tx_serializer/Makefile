# Simulator setup
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Path to source directory
SRC_DIR = $(CURDIR)/../../src

# Sources
VERILOG_SOURCES += $(SRC_DIR)/tx_serializer.v

# DUT settings
TOPLEVEL = tx_serializer
MODULE = tx_serializer_tb

# Cocotb standard rules
include $(shell cocotb-config --makefiles)/Makefile.sim
