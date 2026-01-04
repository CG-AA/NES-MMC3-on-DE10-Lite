# NES VGA Timing Constraints

# 50 MHz input clock
create_clock -name clk50 -period 20.000 [get_ports clk50]

# Derive clocks for internal dividers
derive_clocks -period 20.000

# False paths for slow switches and buttons
set_false_path -from [get_ports {sw[*]}]
set_false_path -from [get_ports {reset_n}]
set_false_path -to [get_ports {led[*]}]
set_false_path -to [get_ports {hex0[*]}]
set_false_path -to [get_ports {hex1[*]}]
set_false_path -to [get_ports {hex2[*]}]
set_false_path -to [get_ports {hex3[*]}]
set_false_path -to [get_ports {hex4[*]}]
set_false_path -to [get_ports {hex5[*]}]
set_false_path -to [get_ports {vga_*}]
