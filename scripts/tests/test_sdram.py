#!/usr/bin/env python3
"""
Test SDRAM with different clock phases
"""

from migen import *
from migen.genlib.resetsync import AsyncResetSynchronizer

from litex.gen import *
from litex.build.io import DDROutput

from litex_boards.platforms import terasic_de10lite

from litex.soc.cores.clock import Max10PLL
from litex.soc.integration.soc import SoCRegion
from litex.soc.integration.soc_core import *
from litex.soc.integration.builder import *
from litex.soc.cores.led import LedChaser

from litedram.modules import IS42S16320
from litedram.phy import GENSDRPHY, HalfRateGENSDRPHY

# CRG with adjustable phase
class _CRG(LiteXModule):
    def __init__(self, platform, sys_clk_freq, sdram_phase=270):
        self.rst       = Signal()
        self.cd_sys    = ClockDomain()
        self.cd_sys_ps = ClockDomain()

        # Clk / Rst
        clk50 = platform.request("clk50")

        # PLL
        self.pll = pll = Max10PLL(speedgrade="-7")
        self.comb += pll.reset.eq(self.rst)
        pll.register_clkin(clk50, 50e6)
        pll.create_clkout(self.cd_sys,    sys_clk_freq)
        pll.create_clkout(self.cd_sys_ps, sys_clk_freq, phase=sdram_phase)

        # SDRAM clock
        self.specials += DDROutput(1, 0, platform.request("sdram_clock"), ClockSignal("sys_ps"))

class TestSoC(SoCCore):
    def __init__(self, sys_clk_freq=50e6, sdram_phase=270, **kwargs):
        platform = terasic_de10lite.Platform()

        # CRG
        self.crg = _CRG(platform, sys_clk_freq, sdram_phase)

        # SoCCore
        SoCCore.__init__(self, platform, sys_clk_freq, 
                         ident=f"Test SoC phase={sdram_phase}", **kwargs)

        # SDRAM
        if not self.integrated_main_ram_size:
            self.sdrphy = GENSDRPHY(platform.request("sdram"), sys_clk_freq)
            self.add_sdram("sdram",
                phy           = self.sdrphy,
                module        = IS42S16320(sys_clk_freq, "1:1"),
                l2_cache_size = kwargs.get("l2_size", 8192)
            )

        # LEDs
        self.leds = LedChaser(
            pads         = platform.request_all("user_led"),
            sys_clk_freq = sys_clk_freq)

def main():
    import sys
    phase = int(sys.argv[1]) if len(sys.argv) > 1 else 90
    print(f"Building with SDRAM clock phase = {phase}°")
    
    soc = TestSoC(sys_clk_freq=50e6, sdram_phase=phase)
    builder = Builder(soc, output_dir=f"build/test_phase{phase}")
    builder.build()
    print(f"\nBuild complete. SOF at build/test_phase{phase}/gateware/test_sdram.sof")

if __name__ == "__main__":
    main()
