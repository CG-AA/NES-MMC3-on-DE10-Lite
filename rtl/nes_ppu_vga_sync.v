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
    input   [7:0] chr_rd_data_hi,
    
    // Sprite CHR ROM read ports
    output [12:0] spr_chr_addr_lo,
    output [12:0] spr_chr_addr_hi,
    input   [7:0] spr_chr_data_lo,
    input   [7:0] spr_chr_data_hi
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
    
    // =========================================================================
    // Pipeline for Memory Latency Compensation
    // =========================================================================
    // BRAM reads are registered (1 cycle latency each):
    //   Cycle 0: NT address sent, fine_x_p1 captured
    //   Cycle 1: NT data (tile_index) available, CHR address sent, fine_x_p2 captured
    //   Cycle 2: CHR data available, use fine_x_p2 for pixel selection
    
    reg [2:0] fine_x_p1, fine_x_p2;  // Pipeline stages for fine_x
    reg [2:0] fine_y_p1;            // Pipeline stage for fine_y (used in CHR addr)
    reg [4:0] tile_x_p1, tile_y_p1; // Pipeline for quadrant calculation
    reg [7:0] vga_y_p1, vga_y_p2;   // Pipeline for Y coordinate (visibility check)
    
    always @(posedge clk) begin
        // Stage 1: Capture when NT address is sent
        fine_x_p1 <= fine_x;
        fine_y_p1 <= fine_y;
        tile_x_p1 <= tile_x;
        tile_y_p1 <= tile_y;
        vga_y_p1 <= vga_y;
        
        // Stage 2: Capture when CHR address is sent
        fine_x_p2 <= fine_x_p1;
        vga_y_p2 <= vga_y_p1;
    end
    
    // Nametable read: tile_y * 32 + tile_x (within selected nametable)
    // Full address would be: nt_select * 0x400 + tile_y * 32 + tile_x
    // But our 2KB VRAM with mirroring means we use 11 bits
    assign nt_rd_addr = {tile_y, tile_x};
    
    // Tile index from nametable (available 1 cycle after address)
    wire [7:0] tile_index = nt_rd_data;
    
    // CHR ROM reads - both bitplanes
    // Use pipelined fine_y_p1 since this is computed 1 cycle after NT addr
    wire pt_sel = ppuctrl[4];
    assign chr_rd_addr_lo = {pt_sel, tile_index, 1'b0, fine_y_p1};
    assign chr_rd_addr_hi = {pt_sel, tile_index, 1'b1, fine_y_p1};
    
    // Get pixel bits - use fine_x_p2 (2 cycles delayed to match CHR data)
    wire pixel_bit0 = chr_rd_data_lo[7 - fine_x_p2];
    wire pixel_bit1 = chr_rd_data_hi[7 - fine_x_p2];
    
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
    // Must be delayed to match attr_rd_data latency (1 cycle)
    wire quadrant_x = tile_x_p1[1];  // Use pipelined tile_x
    wire quadrant_y = tile_y_p1[1];  // Use pipelined tile_y
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
    
    // Pipeline palette_hi to match pixel data timing (need 1 more cycle)
    reg [1:0] palette_hi_p1;
    always @(posedge clk) begin
        palette_hi_p1 <= palette_hi;
    end
    
    // Palette index - use pipelined palette
    wire [3:0] bg_palette_idx = {palette_hi_p1, pixel_bit1, pixel_bit0};
    wire bg_transparent = (pixel_bit0 == 0) && (pixel_bit1 == 0);
    wire [4:0] palette_addr = bg_transparent ? 5'h00 : {1'b0, bg_palette_idx};
    
    // =========================================================================
    // Palette RAM
    // =========================================================================
    // NES palette mirroring:
    // - $3F10/$3F14/$3F18/$3F1C mirror to $3F00/$3F04/$3F08/$3F0C
    // - Palette repeats every 32 bytes ($3F00-$3F1F)
    reg [5:0] palette_ram [0:31];
    
    integer i;
    initial begin
        for (i = 0; i < 32; i = i + 1)
            palette_ram[i] = 6'h0F;
    end
    
    // Compute mirrored palette address for writes
    wire [4:0] pal_wr_addr = ppuaddr[4:0];
    // Mirror sprite backdrop colors ($3F10,$3F14,$3F18,$3F1C) to BG ($3F00,$3F04,$3F08,$3F0C)
    wire pal_is_sprite_backdrop = pal_wr_addr[4] && (pal_wr_addr[1:0] == 2'b00);
    wire [4:0] pal_wr_addr_mirrored = pal_is_sprite_backdrop ? {1'b0, pal_wr_addr[3:0]} : pal_wr_addr;
    
    always @(posedge clk) begin
        if (cpu_wr && cpu_addr == 3'h7 && ppuaddr[13:8] == 6'h3F) begin
            palette_ram[pal_wr_addr_mirrored] <= cpu_din[5:0];
        end
    end
    
    // =========================================================================
    // Output with Sprite Rendering
    // =========================================================================
    wire bg_enabled = ppumask[3];
    wire spr_enabled = ppumask[4];
    wire in_visible_p2 = (vga_y_p2 < 240);
    
    // =========================================================================
    // Simple Sprite Evaluation (Real-time, not cycle-accurate)
    // =========================================================================
    // For each pixel, scan through OAM to find matching sprites
    // This is simplified - real NES has 8-sprite limit and uses sprite evaluation
    
    // Sprite pattern table select (0 = $0000, 1 = $1000)
    wire spr_pt_sel = ppuctrl[3];
    
    // Current screen position - look ahead 1 pixel for CHR latency
    // vga_x/vga_y are the coordinates we're REQUESTING data for
    // vga_x_p2/vga_y_p2 are the coordinates we're OUTPUTTING data for
    wire [7:0] spr_x = vga_x;  // Look ahead for sprite matching
    wire [7:0] spr_y = vga_y;  // Look ahead for sprite matching
    
    // Sprite evaluation - find first matching sprite
    // Check all 64 sprites, find first one that covers this pixel
    reg [5:0] spr_found_idx;
    reg spr_found;
    reg [7:0] spr_found_tile;
    reg [7:0] spr_found_attr;
    reg [7:0] spr_found_x;
    reg [2:0] spr_row;
    
    integer s;
    always @(*) begin
        spr_found = 0;
        spr_found_idx = 0;
        spr_found_tile = 0;
        spr_found_attr = 0;
        spr_found_x = 0;
        spr_row = 0;
        
        for (s = 0; s < 64; s = s + 1) begin
            if (!spr_found) begin
                // OAM format: Y, Tile, Attr, X (4 bytes per sprite)
                // Y is actually Y-1 (sprite appears on next scanline)
                if (spr_y >= oam[s*4] + 1 && spr_y < oam[s*4] + 9) begin
                    // Sprite is on this scanline
                    if (spr_x >= oam[s*4 + 3] && spr_x < oam[s*4 + 3] + 8) begin
                        // Sprite covers this X position
                        spr_found = 1;
                        spr_found_idx = s[5:0];
                        spr_found_tile = oam[s*4 + 1];
                        spr_found_attr = oam[s*4 + 2];
                        spr_found_x = oam[s*4 + 3];
                        spr_row = spr_y - oam[s*4] - 1;
                    end
                end
            end
        end
    end
    
    // Sprite pixel calculation (combinatorial for simplicity)
    // In a real implementation, this would use CHR read ports with pipelining
    wire [2:0] spr_fine_x = spr_x - spr_found_x;
    wire [2:0] spr_fine_x_flip = spr_found_attr[6] ? (3'd7 - spr_fine_x) : spr_fine_x;
    wire [2:0] spr_row_flip = spr_found_attr[7] ? (3'd7 - spr_row) : spr_row;
    
    // Sprite CHR address (directly output to module ports)
    assign spr_chr_addr_lo = {spr_pt_sel, spr_found_tile, 1'b0, spr_row_flip};
    assign spr_chr_addr_hi = {spr_pt_sel, spr_found_tile, 1'b1, spr_row_flip};
    
    // Pipeline sprite attributes to match CHR latency
    reg spr_found_p1;
    reg [7:0] spr_found_attr_p1;
    reg [2:0] spr_fine_x_flip_p1;
    
    always @(posedge clk) begin
        spr_found_p1 <= spr_found;
        spr_found_attr_p1 <= spr_found_attr;
        spr_fine_x_flip_p1 <= spr_fine_x_flip;
    end
    
    // Sprite pixel bits from CHR ROM (bit extraction with flip) - use pipelined values
    wire spr_pixel_bit0 = spr_chr_data_lo[7 - spr_fine_x_flip_p1];
    wire spr_pixel_bit1 = spr_chr_data_hi[7 - spr_fine_x_flip_p1];
    wire [1:0] spr_palette_hi = spr_found_attr_p1[1:0];
    wire spr_transparent = (spr_pixel_bit0 == 0) && (spr_pixel_bit1 == 0);
    wire spr_behind_bg = spr_found_attr_p1[5];
    
    // Final sprite pixel
    wire spr_visible = spr_found_p1 && spr_enabled && !spr_transparent;
    wire [4:0] spr_palette_addr = {1'b1, spr_palette_hi, spr_pixel_bit1, spr_pixel_bit0};
    
    // Priority: sprite behind BG, or sprite in front
    wire use_sprite = spr_visible && (!spr_behind_bg || bg_transparent);
    wire [4:0] final_palette_addr = use_sprite ? spr_palette_addr : palette_addr;
    
    assign pixel_color = (in_visible_p2 && (bg_enabled || spr_enabled)) ? 
                         palette_ram[final_palette_addr] : palette_ram[0];

endmodule
