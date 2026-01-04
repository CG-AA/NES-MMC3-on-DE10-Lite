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
    // Direct Rendering
    // =========================================================================
    
    // Tile coordinates from VGA position
    wire [4:0] tile_x = vga_x[7:3];  // 0-31
    wire [4:0] tile_y = vga_y[7:3];  // 0-29  
    wire [2:0] fine_x = vga_x[2:0];  // 0-7
    wire [2:0] fine_y = vga_y[2:0];  // 0-7
    
    // Nametable read: tile_y * 32 + tile_x
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
    
    // Attribute table read would require another port
    // For now use palette 0
    wire [1:0] palette_hi = 2'b00;
    
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
