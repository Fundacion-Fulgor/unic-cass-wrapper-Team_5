# Clock - 50 MHz
create_clock -name clk_master -period 10.0000 [get_ports {io_clock_PAD}]

# Clock SPI - 10 MHz (100 ns)
create_clock -name clk_spi -period 100.0000 [get_ports {ui_PAD[2]}]

set_clock_groups -asynchronous \
    -group [get_clocks {clk_master}] \
    -group [get_clocks {clk_spi}]
