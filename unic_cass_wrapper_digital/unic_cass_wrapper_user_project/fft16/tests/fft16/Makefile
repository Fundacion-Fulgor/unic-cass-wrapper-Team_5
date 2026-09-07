# Simulator setup
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Path to source directory
SRC_DIR = $(CURDIR)/../../src

# Sources
VERILOG_SOURCES += $(SRC_DIR)/fft16.v

VERILOG_SOURCES += $(SRC_DIR)/clip_round.v
VERILOG_SOURCES += $(SRC_DIR)/btfly_2.v
VERILOG_SOURCES += $(SRC_DIR)/ds_switch.v
VERILOG_SOURCES += $(SRC_DIR)/buffer_parallel2serial.v

VERILOG_SOURCES += $(SRC_DIR)/fft4_radix4.v
VERILOG_SOURCES += $(SRC_DIR)/fft4_mul.v
VERILOG_SOURCES += $(SRC_DIR)/fft4_mdc.v
VERILOG_SOURCES += $(SRC_DIR)/fft4_mdc_stage1.v
VERILOG_SOURCES += $(SRC_DIR)/fft4_mdc_stage2.v
VERILOG_SOURCES += $(SRC_DIR)/fft16_shift_r2.v
VERILOG_SOURCES += $(SRC_DIR)/fft16_shift_r4.v


# DUT settings
export PYTHONPATH := $(CURDIR)/../../model:$(PYTHONPATH)

TOPLEVEL = fft16
MODULE = fft16_tb

# Cocotb standard rules
include $(shell cocotb-config --makefiles)/Makefile.sim
