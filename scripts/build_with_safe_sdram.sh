#!/bin/bash
# Build and load LiteX SoC with SAFE SDRAM timings

set -e

echo "========================================================================"
echo "Building LiteX SoC with IS42S16320_SAFE (relaxed SDRAM timings)"
echo "========================================================================"
echo ""
echo "Changes from default:"
echo "  - tRP:  40ns → 80ns (doubled precharge time)"
echo "  - tRCD: 40ns → 80ns (doubled row-to-column delay)"
echo "  - tWR:  40ns → 80ns (doubled write recovery time)"
echo "  - tRFC: 140ns → 200ns (increased refresh cycle time)"
echo ""
echo "This should reduce write collisions with refresh cycles."
echo ""

# Build
echo "Building..."
python3 terasic_de10lite_custom.py \
    --build \
    --cpu-type=vexriscv \
    --uart-baudrate=115200

echo ""
echo "Build complete!"
echo ""
echo "To load to FPGA:"
echo "  python3 terasic_de10lite_custom.py --load"
echo ""
echo "To test synchronous upload:"
echo "  python3 test_sync_upload.py"
echo ""
