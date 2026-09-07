SIM ?= icarus
TOPLEVEL_LANG ?= verilog

SRC_DIR = $(CURDIR)/../../src

# Top level
VERILOG_SOURCES += $(SRC_DIR)/top_fft16.v

# Serializers
VERILOG_SOURCES += $(SRC_DIR)/rx_serializer.v
VERILOG_SOURCES += $(SRC_DIR)/tx_serializer.v

# Debug subsystem
VERILOG_SOURCES += $(SRC_DIR)/debug_system.v
VERILOG_SOURCES += $(SRC_DIR)/debug_unit.v
VERILOG_SOURCES += $(SRC_DIR)/spi_slave_mode0.v
VERILOG_SOURCES += $(SRC_DIR)/cdc_snapshot.v

# FFT core
VERILOG_SOURCES += $(SRC_DIR)/fft16.v
VERILOG_SOURCES += $(SRC_DIR)/fft4_radix4.v
VERILOG_SOURCES += $(SRC_DIR)/fft4_mdc.v
VERILOG_SOURCES += $(SRC_DIR)/fft4_mul.v
VERILOG_SOURCES += $(SRC_DIR)/fft4_mdc_stage1.v
VERILOG_SOURCES += $(SRC_DIR)/fft4_mdc_stage2.v
VERILOG_SOURCES += $(SRC_DIR)/fft16_shift_r2.v
VERILOG_SOURCES += $(SRC_DIR)/fft16_shift_r4.v
VERILOG_SOURCES += $(SRC_DIR)/buffer_parallel2serial.v

# FFT submodules
VERILOG_SOURCES += $(SRC_DIR)/clip_round.v
VERILOG_SOURCES += $(SRC_DIR)/btfly_2.v
VERILOG_SOURCES += $(SRC_DIR)/ds_switch.v

export PYTHONPATH := $(CURDIR)/../../model:$(PYTHONPATH)

TOPLEVEL = top_fft16
MODULE   = top_fft16_tb

include $(shell cocotb-config --makefiles)/Makefile.sim
