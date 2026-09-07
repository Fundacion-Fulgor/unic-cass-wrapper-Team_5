SIM ?= icarus
TOPLEVEL_LANG ?= verilog

SRC_DIR = $(CURDIR)/../../src

VERILOG_SOURCES += $(CURDIR)/buffer_tx.v
VERILOG_SOURCES += $(SRC_DIR)/buffer_parallel2serial.v
VERILOG_SOURCES += $(SRC_DIR)/tx_serializer.v

TOPLEVEL = buffer_tx
MODULE   = buffer_tx_tb

include $(shell cocotb-config --makefiles)/Makefile.sim
