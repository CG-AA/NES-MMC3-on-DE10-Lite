# Timing constraints for NES test on DE10-Lite

# 50 MHz input clock
create_clock -name clk50 -period 20.000 [get_ports clk50]

# Derive PLL clocks (if any)
derive_pll_clocks

# Derive clock uncertainty
derive_clock_uncertainty
