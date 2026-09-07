# Simulator setup
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Path to source directory
SRC_DIR = $(CURDIR)/../../src

# Sources
VERILOG_SOURCES += $(SRC_DIR)/buffer_parallel2serial.v

# DUT settings
TOPLEVEL = buffer_parallel2serial
MODULE   = buffer_parallel2serial_tb

# Cocotb standard rules
include $(shell cocotb-config --makefiles)/Makefile.sim
