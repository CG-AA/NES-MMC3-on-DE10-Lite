// Minimal NES PPU for Phase 2 Testing - Direct Rendering Version
// 
// This PPU uses separate read ports for nametable and CHR ROM
// to avoid timing issues with multiplexed reads.

module nes_ppu_vga_sync (
    input         clk,            // System clock (50 MHz)
    input         reset,
    
    input         ppu_ce,         // PPU clock enable
    
    // CPU Interface
    input   [2:0] cpu_addr,
    input   [7:0] cpu_din,
    output  [7:0] cpu_dout,
    input         cpu_rd,
    input         cpu_wr,
    
    output reg    nmi_n,
    
    // VRAM interface - for CPU access
    output [13:0] vram_addr,
    input   [7:0] vram_din,
    output  [7:0] vram_dout,
    output        vram_rd,
    output        vram_wr,
    
    // Video output
    output  [5:0] pixel_color,
    output  [8:0] scanline,
    output  [8:0] cycle,
    output        vblank,
    
    // VGA coordinates for rendering
    input   [7:0] vga_x,
    input   [7:0] vga_y,
    
    // Direct nametable read port
    output [10:0] nt_rd_addr,
    input   [7:0] nt_rd_data,
    
    // Attribute table read port (same memory, different address)
    output [10:0] attr_rd_addr,
    input   [7:0] attr_rd_data,
    
    // Direct CHR ROM read ports (need 2 for both bitplanes)
    output [12:0] chr_rd_addr_lo,
    input   [7:0] chr_rd_data_lo,
    output [12:0] chr_rd_addr_hi,
    input   [7:0] chr_rd_data_hi
);

    // =========================================================================
    // PPU Registers
    // =========================================================================
    reg [7:0] ppuctrl;
    reg [7:0] ppumask;
    reg [7:0] ppustatus;
    reg [7:0] oamaddr;
    reg [15:0] ppuaddr;
    
    // =========================================================================
    // OAM (Object Attribute Memory) - 256 bytes for 64 sprites
    // =========================================================================
    // Each sprite: 4 bytes (Y, Tile, Attr, X)
    // Note: Sprite rendering not yet implemented, but OAM needed for DMA
    reg [7:0] oam [0:255];
    reg [15:0] ppuaddr_t;
    reg [7:0] ppuscroll_x;
    reg [7:0] ppuscroll_y;
    reg addr_latch;
    reg [7:0] read_buffer;
    
    // =========================================================================
    // PPU Timing (for vblank/NMI)
    // =========================================================================
    reg [8:0] h_count;
    reg [8:0] v_count;
    
    always @(posedge clk) begin
        if (reset) begin
            h_count <= 0;
            v_count <= 0;
        end else if (ppu_ce) begin
            if (h_count == 340) begin
                h_count <= 0;
                v_count <= (v_count == 261) ? 9'd0 : v_count + 1'b1;
            end else begin
                h_count <= h_count + 1'b1;
            end
        end
    end
    
    assign scanline = v_count;
    assign cycle = h_count;
    assign vblank = (v_count >= 241) && (v_count <= 260);
    
    // =========================================================================
    // Register Access
    // =========================================================================
    reg [7:0] cpu_dout_reg;
    assign cpu_dout = cpu_dout_reg;
    
    always @(posedge clk) begin
        if (reset) begin
            ppuctrl <= 8'h00;
            ppumask <= 8'h00;
            ppustatus <= 8'h00;
            oamaddr <= 8'h00;
            ppuaddr <= 16'h0000;
            ppuaddr_t <= 16'h0000;
            ppuscroll_x <= 8'h00;
            ppuscroll_y <= 8'h00;
            addr_latch <= 1'b0;
            read_buffer <= 8'h00;
        end else begin
            if (ppu_ce) begin
                if (v_count == 241 && h_count == 1)
                    ppustatus[7] <= 1'b1;
                else if (v_count == 261 && h_count == 1)
                    ppustatus[7] <= 1'b0;
            end
            
            if (cpu_rd) begin
                case (cpu_addr)
                    3'h2: begin
                        ppustatus[7] <= 1'b0;
                        addr_latch <= 1'b0;
                    end
                    3'h4: begin
                        // OAMDATA read - no increment on read
                    end
                    3'h7: begin
                        read_buffer <= vram_din;
                        ppuaddr <= ppuaddr + (ppuctrl[2] ? 16'd32 : 16'd1);
                    end
                endcase
            end
            
            if (cpu_wr) begin
                case (cpu_addr)
                    3'h0: ppuctrl <= cpu_din;
                    3'h1: ppumask <= cpu_din;
                    3'h3: oamaddr <= cpu_din;
                    3'h4: begin
                        // OAMDATA write - write to OAM and increment address
                        oam[oamaddr] <= cpu_din;
                        oamaddr <= oamaddr + 8'd1;
                    end
                    3'h5: begin
                        if (!addr_latch) begin
                            ppuscroll_x <= cpu_din;
                            addr_latch <= 1'b1;
                        end else begin
                            ppuscroll_y <= cpu_din;
                            addr_latch <= 1'b0;
                        end
                    end
                    3'h6: begin
                        if (!addr_latch) begin
                            ppuaddr_t[13:8] <= cpu_din[5:0];
                            ppuaddr_t[15:14] <= 2'b00;
                            addr_latch <= 1'b1;
                        end else begin
                            ppuaddr_t[7:0] <= cpu_din;
                            ppuaddr <= {2'b00, ppuaddr_t[13:8], cpu_din};
                            addr_latch <= 1'b0;
                        end
                    end
                    3'h7: ppuaddr <= ppuaddr + (ppuctrl[2] ? 16'd32 : 16'd1);
                endcase
            end
        end
    end
    
    always @(posedge clk) begin
        if (reset)
            nmi_n <= 1'b1;
        else
            nmi_n <= ~(ppustatus[7] && ppuctrl[7]);
    end
    
    always @(*) begin
        case (cpu_addr)
            3'h2: cpu_dout_reg = ppustatus;
            3'h4: cpu_dout_reg = oam[oamaddr];  // OAMDATA read
            3'h7: cpu_dout_reg = read_buffer;
            default: cpu_dout_reg = 8'h00;
        endcase
    end
    
    // CPU VRAM interface
    assign vram_addr = ppuaddr[13:0];
    assign vram_dout = cpu_din;
    assign vram_rd = cpu_rd && (cpu_addr == 3'h7);
    assign vram_wr = cpu_wr && (cpu_addr == 3'h7) && (ppuaddr[13:8] != 6'h3F);
    
    // =========================================================================
    // Direct Rendering with Scrolling
    // =========================================================================
    
    // Apply scroll offset to VGA coordinates
    wire [8:0] scroll_x = {1'b0, vga_x} + {1'b0, ppuscroll_x};
    wire [8:0] scroll_y = {1'b0, vga_y} + {1'b0, ppuscroll_y};
    
    // Handle nametable switching for horizontal scrolling (bit 8 selects nametable)
    wire nt_sel_h = scroll_x[8];  // Which nametable horizontally (0 or 1)
    wire nt_sel_v = scroll_y[8];  // Which nametable vertically (0 or 1)
    // Combined nametable select (ppuctrl bits 0-1 set base, scroll wraps)
    wire [1:0] nt_select = ppuctrl[1:0] ^ {nt_sel_v, nt_sel_h};
    
    // Tile coordinates from scrolled position
    wire [4:0] tile_x = scroll_x[7:3];  // 0-31
    wire [4:0] tile_y = scroll_y[7:3];  // 0-29  
    wire [2:0] fine_x = scroll_x[2:0];  // 0-7
    wire [2:0] fine_y = scroll_y[2:0];  // 0-7
    
    // Nametable read: tile_y * 32 + tile_x (within selected nametable)
    // Full address would be: nt_select * 0x400 + tile_y * 32 + tile_x
    // But our 2KB VRAM with mirroring means we use 11 bits
    assign nt_rd_addr = {tile_y, tile_x};
    
    // Tile index from nametable
    wire [7:0] tile_index = nt_rd_data;
    
    // CHR ROM reads - both bitplanes
    // Pattern address: (pt_select << 12) | (tile << 4) | plane_bit << 3 | fine_y
    wire pt_sel = ppuctrl[4];
    assign chr_rd_addr_lo = {pt_sel, tile_index, 1'b0, fine_y};
    assign chr_rd_addr_hi = {pt_sel, tile_index, 1'b1, fine_y};
    
    // Get pixel bits
    wire pixel_bit0 = chr_rd_data_lo[7 - fine_x];
    wire pixel_bit1 = chr_rd_data_hi[7 - fine_x];
    
    // =========================================================================
    // Attribute Table Lookup
    // =========================================================================
    // Attribute table is at offset $3C0 within each nametable (960-1023)
    // Each byte covers a 4x4 tile (32x32 pixel) area
    // Bits: [7:6]=BR, [5:4]=BL, [3:2]=TR, [1:0]=TL (each 2x2 tile quadrant)
    //
    // Attribute address = $23C0 + (tile_y / 4) * 8 + (tile_x / 4)
    //                   = $3C0 + (tile_y[4:2]) * 8 + tile_x[4:2]
    
    wire [2:0] attr_x = tile_x[4:2];  // 0-7 (which attribute byte horizontally)
    wire [2:0] attr_y = tile_y[4:2];  // 0-7 (which attribute byte vertically)
    
    // Output attribute address for external VRAM lookup
    // Address within nametable: $3C0 + attr_y * 8 + attr_x
    assign attr_rd_addr = 11'h3C0 + {5'b0, attr_y, attr_x};
    
    // Quadrant within the 4x4 tile area (which 2x2 sub-block)
    wire quadrant_x = tile_x[1];  // 0=left, 1=right
    wire quadrant_y = tile_y[1];  // 0=top, 1=bottom
    wire [1:0] quadrant = {quadrant_y, quadrant_x};
    
    // Extract palette bits from attribute byte based on quadrant
    // quadrant 00 (TL) = bits [1:0], 01 (TR) = bits [3:2]
    // quadrant 10 (BL) = bits [5:4], 11 (BR) = bits [7:6]
    reg [1:0] palette_hi;
    always @(*) begin
        case (quadrant)
            2'b00: palette_hi = attr_rd_data[1:0];  // Top-left
            2'b01: palette_hi = attr_rd_data[3:2];  // Top-right
            2'b10: palette_hi = attr_rd_data[5:4];  // Bottom-left
            2'b11: palette_hi = attr_rd_data[7:6];  // Bottom-right
        endcase
    end
    
    // Palette index
    wire [3:0] bg_palette_idx = {palette_hi, pixel_bit1, pixel_bit0};
    wire bg_transparent = (pixel_bit0 == 0) && (pixel_bit1 == 0);
    wire [4:0] palette_addr = bg_transparent ? 5'h00 : {1'b0, bg_palette_idx};
    
    // =========================================================================
    // Palette RAM
    // =========================================================================
    reg [5:0] palette_ram [0:31];
    
    integer i;
    initial begin
        for (i = 0; i < 32; i = i + 1)
            palette_ram[i] = 6'h0F;
    end
    
    always @(posedge clk) begin
        if (cpu_wr && cpu_addr == 3'h7 && ppuaddr[13:8] == 6'h3F) begin
            palette_ram[ppuaddr[4:0]] <= cpu_din[5:0];
            if (ppuaddr[4] && !ppuaddr[1] && !ppuaddr[0])
                palette_ram[{1'b0, ppuaddr[3:2], 2'b00}] <= cpu_din[5:0];
        end
    end
    
    // =========================================================================
    // Output
    // =========================================================================
    wire bg_enabled = ppumask[3];
    wire in_visible = (vga_y < 240);
    
    assign pixel_color = (in_visible && bg_enabled) ? palette_ram[palette_addr] : palette_ram[0];

endmodule
