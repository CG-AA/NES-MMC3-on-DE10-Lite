// NES Address Decoder
// Decodes CPU address to chip selects for memory and I/O
//
// Note on $4017: This address is shared between APU (write) and Controller (read)
// - Write to $4017: APU frame counter mode
// - Read from $4017: Controller 2 data

module nes_addr_decode (
    input  wire [15:0] addr,
    input  wire        rd,
    input  wire        wr,
    
    // Chip selects (active high)
    output wire        ram_cs,       // $0000-$1FFF (2KB mirrored)
    output wire        ppu_cs,       // $2000-$3FFF (8 regs mirrored)
    output wire        apu_cs,       // $4000-$4013, $4015, $4017 (write only)
    output wire        oam_dma_cs,   // $4014 (write only)
    output wire        ctrl_cs,      // $4016 (R/W), $4017 (read only)
    output wire        prg_ram_cs,   // $6000-$7FFF
    output wire        prg_rom_cs,   // $8000-$FFFF (read)
    output wire        mapper_cs,    // $8000-$FFFF (write) - mapper registers
    
    // Decoded register addresses
    output wire [2:0]  ppu_reg,      // PPU register 0-7
    output wire [4:0]  apu_reg       // APU register 0-31
);

    // Internal RAM: $0000-$1FFF (2KB at $0000-$07FF, mirrored 4x)
    assign ram_cs = (addr < 16'h2000);
    
    // PPU Registers: $2000-$3FFF (8 registers mirrored every 8 bytes)
    assign ppu_cs = (addr >= 16'h2000) && (addr < 16'h4000);
    assign ppu_reg = addr[2:0];  // Only bottom 3 bits matter
    
    // APU/IO: $4000-$4017
    wire apu_io_range = (addr >= 16'h4000) && (addr < 16'h4018);
    
    // OAM DMA: $4014 (write only)
    assign oam_dma_cs = (addr == 16'h4014) && wr;
    
    // Controller: $4016 (read/write), $4017 (read only - write goes to APU)
    // $4016 write: strobe latch
    // $4016 read: P1 controller data
    // $4017 read: P2 controller data
    // $4017 write: APU frame counter (handled by apu_cs)
    assign ctrl_cs = (addr == 16'h4016) || ((addr == 16'h4017) && rd);
    
    // APU: $4000-$4013, $4015, $4017 (write only)
    // Note: $4017 write goes to APU, $4017 read goes to controller
    assign apu_cs = (apu_io_range && ~oam_dma_cs && (addr != 16'h4016) && 
                    ((addr != 16'h4017) || wr));
    assign apu_reg = addr[4:0];
    
    // PRG-RAM: $6000-$7FFF (8KB, battery-backed for some mappers)
    assign prg_ram_cs = (addr >= 16'h6000) && (addr < 16'h8000);
    
    // PRG-ROM: $8000-$FFFF (32KB, bank-switched) - active for reads
    assign prg_rom_cs = (addr >= 16'h8000) && rd;
    
    // Mapper registers: $8000-$FFFF (active for writes)
    // MMC3 uses:
    //   $8000-$9FFF: Bank select / Bank data
    //   $A000-$BFFF: Mirroring / PRG-RAM protect  
    //   $C000-$DFFF: IRQ latch / IRQ reload
    //   $E000-$FFFF: IRQ disable / IRQ enable
    assign mapper_cs = (addr >= 16'h8000) && wr;

endmodule
