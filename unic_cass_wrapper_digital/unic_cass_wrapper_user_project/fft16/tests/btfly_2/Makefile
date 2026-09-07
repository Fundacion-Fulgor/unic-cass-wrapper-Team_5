# Simulator setup
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Path to source directory
SRC_DIR = $(CURDIR)/../../src

# Sources
VERILOG_SOURCES += $(SRC_DIR)/btfly_2.v

# DUT settings
TOPLEVEL = btfly_2
MODULE = btfly_2_tb

# Cocotb standard rules
include $(shell cocotb-config --makefiles)/Makefile.sim
