# Simulator setup
SIM ?= icarus
TOPLEVEL_LANG ?= verilog

# Path to source directory
SRC_DIR = $(CURDIR)/../../src

# Sources
VERILOG_SOURCES += $(SRC_DIR)/clip_round.v
VERILOG_SOURCES += $(CURDIR)/clip_round_cfg.v

# DUT settings
TOPLEVEL = clip_round_cfg
MODULE = clip_round_tb

# Cocotb standard rules
include $(shell cocotb-config --makefiles)/Makefile.sim
