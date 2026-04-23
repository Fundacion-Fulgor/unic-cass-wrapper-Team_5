set_false_path -from [get_ports {ui_PAD2CORE[0]}]
create_clock -name pll_control_clock -period 6.666 [get_pins *ringosc.ibufp01/Y]