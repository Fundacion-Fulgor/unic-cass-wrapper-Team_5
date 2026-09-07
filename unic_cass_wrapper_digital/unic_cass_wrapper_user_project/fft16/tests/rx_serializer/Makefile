# Simulator setup
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Path to source directory
SRC_DIR = $(CURDIR)/../../src

# Sources
VERILOG_SOURCES += $(SRC_DIR)/rx_serializer.v

# DUT settings
TOPLEVEL = rx_serializer
MODULE = rx_serializer_tb

# Cocotb standard rules
include $(shell cocotb-config --makefiles)/Makefile.sim
