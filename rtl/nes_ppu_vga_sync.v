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
    input   [7:0] spr_chr_data_hi,
    
    // DMA Debug Inputs - what DMA captured from RAM
    input   [7:0] dma_debug_byte0,
    input   [7:0] dma_debug_byte1,
    input   [7:0] dma_debug_byte2,
    input   [7:0] dma_debug_byte3,
    input   [7:0] dma_debug_page
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
    // OAM writes handled in register access block below
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
    // DEBUG: Visual OAM Diagnostic
    // =========================================================================
    // Show sprite 0's X,Y,Tile values as visual bars to verify OAM content
    // Red horizontal bar at Y=0: length = spr0_x value  
    // Green horizontal bar at Y=8: length = spr0_y value
    // Blue horizontal bar at Y=16: length = spr0_tile value
    // Cyan bar at Y=24: length = oamaddr value (shows where DMA ended)
    // Also draw a crosshair at (spr0_x, spr0_y+1) to show sprite position
    
    // Snapshot OAM during VBlank only - this avoids read/write conflicts
    reg [7:0] spr0_y_snap, spr0_tile_snap, spr0_attr_snap, spr0_x_snap;
    reg [7:0] oamaddr_snap;
    
    always @(posedge clk) begin
        // Only update snapshot at the start of vblank (scanline 241)
        if (v_count == 241 && h_count == 0) begin
            spr0_y_snap <= oam[0];
            spr0_tile_snap <= oam[1];
            spr0_attr_snap <= oam[2];
            spr0_x_snap <= oam[3];
            oamaddr_snap <= oamaddr;
        end
    end
    
    wire [7:0] spr0_y = spr0_y_snap;
    wire [7:0] spr0_tile = spr0_tile_snap;
    wire [7:0] spr0_attr = spr0_attr_snap;
    wire [7:0] spr0_x = spr0_x_snap;
    
    // =========================================================================
    // DEBUG VISUALIZATION (disabled by default, set to 1 to enable)
    // =========================================================================
    localparam DEBUG_ENABLE = 0;  // Set to 1 to show debug bars and crosshair
    
    // Debug bars at top of screen - Row 1: OAM values
    wire debug_bar_x = DEBUG_ENABLE && (vga_y < 8'd8) && (vga_x < spr0_x);
    wire debug_bar_y = DEBUG_ENABLE && (vga_y >= 8'd8) && (vga_y < 8'd16) && (vga_x < spr0_y);
    wire debug_bar_t = DEBUG_ENABLE && (vga_y >= 8'd16) && (vga_y < 8'd24) && (vga_x < spr0_tile);
    wire debug_bar_a = DEBUG_ENABLE && (vga_y >= 8'd24) && (vga_y < 8'd32) && (vga_x < oamaddr_snap);
    
    // Debug bars - Row 2: DMA-captured values (what DMA read from RAM)
    wire debug_dma_x = DEBUG_ENABLE && (vga_y >= 8'd40) && (vga_y < 8'd48) && (vga_x < dma_debug_byte3);
    wire debug_dma_y = DEBUG_ENABLE && (vga_y >= 8'd48) && (vga_y < 8'd56) && (vga_x < dma_debug_byte0);
    wire debug_dma_t = DEBUG_ENABLE && (vga_y >= 8'd56) && (vga_y < 8'd64) && (vga_x < dma_debug_byte1);
    wire debug_dma_p = DEBUG_ENABLE && (vga_y >= 8'd64) && (vga_y < 8'd72) && (vga_x < dma_debug_page);
    
    // Crosshair at sprite 0's actual position
    wire [8:0] spr0_screen_y = {1'b0, spr0_y} + 9'd1;
    wire [7:0] cross_y1 = spr0_screen_y[7:0];
    wire [7:0] cross_y2 = spr0_screen_y[7:0] + 8'd7;
    wire [7:0] cross_x1 = spr0_x;
    wire [7:0] cross_x2 = spr0_x + 8'd7;
    
    wire debug_crosshair_h = DEBUG_ENABLE && ((vga_y == cross_y1) || (vga_y == cross_y2)) && 
                             (vga_x >= cross_x1) && (vga_x <= cross_x2);
    wire debug_crosshair_v = DEBUG_ENABLE && ((vga_x == cross_x1) || (vga_x == cross_x2)) && 
                             (vga_y >= cross_y1) && (vga_y <= cross_y2);
    wire debug_crosshair = debug_crosshair_h || debug_crosshair_v;
    
    // Choose debug color - includes both OAM bars (row 1) and DMA bars (row 2)
    wire debug_oam_bars = debug_bar_x || debug_bar_y || debug_bar_t || debug_bar_a;
    wire debug_dma_bars = debug_dma_x || debug_dma_y || debug_dma_t || debug_dma_p;
    wire debug_active = debug_oam_bars || debug_dma_bars || debug_crosshair;
    
    reg [4:0] debug_palette_addr;
    always @(*) begin
        if (debug_bar_x)        debug_palette_addr = 5'h06;  // Red
        else if (debug_bar_y)   debug_palette_addr = 5'h1A;  // Green
        else if (debug_bar_t)   debug_palette_addr = 5'h12;  // Blue
        else if (debug_bar_a)   debug_palette_addr = 5'h2C;  // Cyan (for oamaddr)
        else if (debug_crosshair) debug_palette_addr = 5'h30; // White
        else                    debug_palette_addr = 5'h00;
    end
    
    // =========================================================================
    // Multi-Sprite Rendering (all 64 sprites)
    // =========================================================================
    // Sprite pattern table: ppuctrl[3] selects $0000 or $1000
    wire [12:0] spr_pattern_base = ppuctrl[3] ? 13'h1000 : 13'h0000;
    
    // Use vga_x + 1 for lookahead to compensate for 1-cycle CHR read latency
    wire [7:0] vga_x_next = vga_x + 8'd1;
    
    // Check all 64 sprites for hits (combinationally)
    // Each sprite: Y at oam[i*4], Tile at oam[i*4+1], Attr at oam[i*4+2], X at oam[i*4+3]
    wire [63:0] spr_active;
    genvar si;
    generate
        for (si = 0; si < 64; si = si + 1) begin : spr_hit
            wire [7:0] this_y = oam[si*4 + 0];
            wire [7:0] this_x = oam[si*4 + 3];
            wire [8:0] spr_top = {1'b0, this_y} + 9'd1;
            wire y_hit = (vga_y >= spr_top[7:0]) && 
                         (vga_y < (spr_top[7:0] + 8'd8)) && 
                         (spr_top < 9'd240);
            wire x_hit = (vga_x_next >= this_x) && 
                         (vga_x_next < (this_x + 8'd8));
            assign spr_active[si] = y_hit && x_hit;
        end
    endgenerate
    
    // Priority encoder: find lowest-indexed active sprite (6-bit index for 64 sprites)
    reg [5:0] winning_spr;
    reg any_spr_hit;
    integer spr_idx;
    always @(*) begin
        winning_spr = 6'd0;
        any_spr_hit = 1'b0;
        for (spr_idx = 63; spr_idx >= 0; spr_idx = spr_idx - 1) begin
            if (spr_active[spr_idx]) begin
                winning_spr = spr_idx[5:0];
                any_spr_hit = 1'b1;
            end
        end
    end
    
    // Get winning sprite's OAM data using 6-bit index
    wire [7:0] win_oam_base = {winning_spr, 2'b00};  // winning_spr * 4
    wire [7:0] win_y    = oam[win_oam_base + 0];
    wire [7:0] win_tile = oam[win_oam_base + 1];
    wire [7:0] win_attr = oam[win_oam_base + 2];
    wire [7:0] win_x    = oam[win_oam_base + 3];
    
    wire win_flip_h   = win_attr[6];
    wire win_flip_v   = win_attr[7];
    wire win_priority = win_attr[5];
    wire [1:0] win_palette = win_attr[1:0];
    
    // Calculate fine position within winning sprite (use vga_x_next to match hit detection)
    wire [8:0] win_top = {1'b0, win_y} + 9'd1;
    wire [2:0] win_fine_x_raw = vga_x_next[2:0] - win_x[2:0];
    wire [2:0] win_fine_y_raw = vga_y[2:0] - win_top[2:0];
    wire [2:0] win_fine_x = win_flip_h ? (3'd7 - win_fine_x_raw) : win_fine_x_raw;
    wire [2:0] win_fine_y = win_flip_v ? (3'd7 - win_fine_y_raw) : win_fine_y_raw;
    
    // CHR address for winning sprite tile
    assign spr_chr_addr_lo = spr_pattern_base + {win_tile, 1'b0, win_fine_y};
    assign spr_chr_addr_hi = spr_pattern_base + {win_tile, 1'b1, win_fine_y};
    
    // Pipeline sprite data (1 cycle BRAM latency)
    reg [7:0] spr_chr_lo_p1, spr_chr_hi_p1;
    reg any_spr_hit_p1;
    reg [2:0] win_fine_x_p1;
    reg [1:0] win_palette_p1;
    reg win_priority_p1;
    reg is_spr0_p1;  // Track if winning sprite is sprite 0
    
    always @(posedge clk) begin
        spr_chr_lo_p1 <= spr_chr_data_lo;
        spr_chr_hi_p1 <= spr_chr_data_hi;
        any_spr_hit_p1 <= any_spr_hit;
        win_fine_x_p1 <= win_fine_x;
        win_palette_p1 <= win_palette;
        win_priority_p1 <= win_priority;
        is_spr0_p1 <= (winning_spr == 6'd0) && any_spr_hit;
    end
    
    // Extract sprite pixel bits (bit 7 is leftmost pixel)
    wire [2:0] spr_bit_sel = 3'd7 - win_fine_x_p1;
    wire spr_pixel_lo = spr_chr_lo_p1[spr_bit_sel];
    wire spr_pixel_hi = spr_chr_hi_p1[spr_bit_sel];
    wire [1:0] spr_pixel = {spr_pixel_hi, spr_pixel_lo};
    wire spr_transparent = (spr_pixel == 2'b00);
    
    // Sprite palette address (sprite palettes are at $3F10-$3F1F)
    wire [4:0] spr_palette_addr = {1'b1, win_palette_p1, spr_pixel};
    
    // Final pixel selection with sprite priority
    wire spr_visible = any_spr_hit_p1 && !spr_transparent && spr_enabled;
    wire spr_in_front = spr_visible && !win_priority_p1;
    wire spr_behind = spr_visible && win_priority_p1;
    
    // Choose final palette address
    wire [4:0] final_palette_addr;
    assign final_palette_addr = debug_active ? debug_palette_addr :
                                (spr_in_front ? spr_palette_addr :
                                 (bg_transparent && spr_behind) ? spr_palette_addr :
                                 palette_addr);
    
    reg [5:0] debug_color;
    always @(*) begin
        // Row 1: OAM values (what PPU reads from OAM)
        if (debug_bar_x)          debug_color = 6'h16;  // Bright red/orange - OAM X
        else if (debug_bar_y)     debug_color = 6'h1A;  // Bright green - OAM Y
        else if (debug_bar_t)     debug_color = 6'h12;  // Bright blue - OAM Tile
        else if (debug_bar_a)     debug_color = 6'h2C;  // Cyan - oamaddr
        // Row 2: DMA values (what DMA read from RAM)
        else if (debug_dma_x)     debug_color = 6'h24;  // Purple - DMA X (byte3)
        else if (debug_dma_y)     debug_color = 6'h28;  // Yellow - DMA Y (byte0)
        else if (debug_dma_t)     debug_color = 6'h23;  // Magenta - DMA Tile (byte1)
        else if (debug_dma_p)     debug_color = 6'h10;  // Gray - DMA Page
        else if (debug_crosshair) debug_color = 6'h30;  // White
        else                      debug_color = 6'h00;
    end
    
    // Bypass all visibility checks for debug - use direct color
    assign pixel_color = debug_active ? debug_color : 
                         ((in_visible_p2 && (bg_enabled || spr_enabled)) ? 
                          palette_ram[final_palette_addr] : palette_ram[0]);

endmodule
