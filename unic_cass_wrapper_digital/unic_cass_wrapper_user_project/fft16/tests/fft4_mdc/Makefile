# Simulator setup
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Path to source directory
SRC_DIR = $(CURDIR)/../../src

# Sources
VERILOG_SOURCES += $(SRC_DIR)/fft4_mdc.v
VERILOG_SOURCES += $(SRC_DIR)/fft4_mdc_stage1.v
VERILOG_SOURCES += $(SRC_DIR)/fft4_mdc_stage2.v
VERILOG_SOURCES += $(SRC_DIR)/btfly_2.v
VERILOG_SOURCES += $(SRC_DIR)/ds_switch.v

# DUT settings
TOPLEVEL = fft4_mdc
MODULE = fft4_mdc_tb

# Cocotb standard rules
include $(shell cocotb-config --makefiles)/Makefile.sim
