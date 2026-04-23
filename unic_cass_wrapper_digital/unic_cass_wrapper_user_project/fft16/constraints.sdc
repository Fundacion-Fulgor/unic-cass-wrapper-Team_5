# Clock - 50 MHz
create_clock -name clk_i -period 20 [get_ports {clk_i}]

# Clock SPI - 10 MHz (100 ns)
create_clock -name spi_clk -period 100 [get_ports {ui_PAD2CORE[2]}]

set_clock_groups -asynchronous \
    -group [get_clocks {clk_i}] \
    -group [get_clocks {spi_clk}]