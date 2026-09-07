# Simulator setup
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Path to source directory
SRC_DIR = $(CURDIR)/../../src

# Sources
VERILOG_SOURCES += $(SRC_DIR)/spi_slave_mode0.v

# DUT settings
TOPLEVEL = spi_slave_mode0
MODULE = spi_slave_mode0_tb

# Cocotb standard rules
include $(shell cocotb-config --makefiles)/Makefile.sim
