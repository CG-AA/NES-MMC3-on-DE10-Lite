// NES Top Level - Phase 2 with VGA
// T65 CPU + PPU + BRAM + VGA output
//
// DEBUG MODES:
//   SW[9] = 0: Normal speed (~1.78 MHz CPU)
//   SW[9] = 1: Ultra-slow (1 Hz CPU) for visual debugging
//   SW[8] = 0: Show PPU output on VGA
//   SW[8] = 1: Show VGA test pattern (palette display)

module nes_top (
    input         clk50,          // 50 MHz input clock
    input         reset_n,        // Active low reset (KEY[0])
    input   [9:0] sw,             // Slide switches
    
    // LED output for debug
    output  [9:0] led,
    
    // 7-segment displays for debug
    output  [7:0] hex0,
    output  [7:0] hex1,
    output  [7:0] hex2,
    output  [7:0] hex3,
    output  [7:0] hex4,
    output  [7:0] hex5,
    
    // VGA output (4-bit DAC)
    output  [3:0] vga_r,
    output  [3:0] vga_g,
    output  [3:0] vga_b,
    output        vga_hs,
    output        vga_vs
);

    // =========================================================================
    // Clock Generation
    // =========================================================================
    // VGA pixel clock: 25 MHz (50 MHz / 2)
    // CPU clock: ~1.78 MHz (50 MHz / 28)
    // PPU clock: ~5.37 MHz (50 MHz / ~9.3)
    
    reg clk25;  // 25 MHz pixel clock
    always @(posedge clk50) begin
        if (!reset_n)
            clk25 <= 0;
        else
            clk25 <= ~clk25;
    end
    
    // CPU clock divider
    reg [4:0] clk_div;
    reg [25:0] slow_div;
    
    wire slow_mode = sw[9];
    wire cpu_ce_fast = (clk_div == 5'd27);
    wire cpu_ce_slow = (slow_div == 26'd49_999_999);
    wire cpu_ce = slow_mode ? cpu_ce_slow : cpu_ce_fast;
    
    // PPU runs at ~5.37 MHz (50 MHz / 9.3) - use /9 for simplicity
    // PPU is 3x faster than CPU
    reg [3:0] ppu_div;
    wire ppu_ce = (ppu_div == 4'd8);
    
    always @(posedge clk50) begin
        if (!reset_n) begin
            clk_div <= 0;
            slow_div <= 0;
            ppu_div <= 0;
        end else begin
            if (clk_div == 5'd27)
                clk_div <= 0;
            else
                clk_div <= clk_div + 1'b1;
            
            if (slow_div == 26'd49_999_999)
                slow_div <= 0;
            else
                slow_div <= slow_div + 1'b1;
                
            if (ppu_div == 4'd8)
                ppu_div <= 0;
            else
                ppu_div <= ppu_div + 1'b1;
        end
    end

    // =========================================================================
    // Reset Synchronization
    // =========================================================================
    reg [3:0] reset_sr;
    wire reset_sync = reset_sr[3];
    
    always @(posedge clk50) begin
        reset_sr <= {reset_sr[2:0], reset_n};
    end

    // =========================================================================
    // VGA Timing Generator
    // =========================================================================
    wire        vga_active;
    wire        vga_hblank, vga_vblank;
    wire [9:0]  pixel_x, pixel_y;
    
    vga_timing vga_tim (
        .clk        (clk25),
        .reset      (~reset_sync),
        .hsync      (vga_hs),
        .vsync      (vga_vs),
        .hblank     (vga_hblank),
        .vblank     (vga_vblank),
        .active     (vga_active),
        .pixel_x    (pixel_x),
        .pixel_y    (pixel_y)
    );

    // =========================================================================
    // Test Pattern Generator (color bars + NES palette test)
    // =========================================================================
    // NES resolution: 256x240
    // VGA resolution: 640x480
    // Scale: 2x (256*2=512 fits in 640, 240*2=480 exact fit)
    
    wire [7:0] nes_x = pixel_x[8:1];  // Divide by 2 for 2x scaling
    wire [7:0] nes_y = pixel_y[9:1];  // Divide by 2 for 2x scaling
    
    // Border detection (NES visible area is 256x240, centered in 640x480)
    // Horizontal: (640-512)/2 = 64 pixels border on each side
    wire nes_active = (pixel_x >= 64) && (pixel_x < 576) &&
                      (pixel_y < 480);
    
    // Test pattern: show NES palette (8x8 grid of colors)
    // Top half: palette colors
    // Bottom half: gradient test
    wire [5:0] test_palette_index;
    wire in_palette_area = (nes_y < 128);
    
    // Palette grid: 16 columns x 4 rows
    wire [3:0] pal_col = nes_x[7:4];   // 0-15
    wire [1:0] pal_row = nes_y[6:5];   // 0-3
    assign test_palette_index = in_palette_area ? {pal_row, pal_col} : 
                           {2'b00, nes_x[7:4]};  // Gradient in bottom half
    
    // NES Palette lookup for test pattern
    wire [3:0] test_r, test_g, test_b;
    nes_palette test_palette (
        .color_index(test_palette_index),
        .r(test_r),
        .g(test_g),
        .b(test_b)
    );
    
    // =========================================================================
    // PPU Instance
    // =========================================================================
    wire [13:0] ppu_vram_addr;
    wire  [7:0] ppu_vram_din;
    wire  [7:0] ppu_vram_dout;
    wire        ppu_vram_rd;
    wire        ppu_vram_wr;
    wire  [5:0] ppu_pixel_color;
    wire  [8:0] ppu_scanline;
    wire  [8:0] ppu_cycle;
    wire        ppu_vblank;
    wire        ppu_nmi_n;
    
    wire ppu_cpu_rd = ppu_sel && cpu_rw_n && cpu_ce;
    wire ppu_cpu_wr = ppu_sel && !cpu_rw_n && cpu_ce;
    
    nes_ppu_simple ppu_inst (
        .clk        (clk50),
        .reset      (~reset_sync),
        .ppu_ce     (ppu_ce),
        
        .cpu_addr   (ppu_reg),
        .cpu_din    (cpu_dout),
        .cpu_dout   (ppu_rdata),
        .cpu_rd     (ppu_cpu_rd),
        .cpu_wr     (ppu_cpu_wr),
        
        .nmi_n      (ppu_nmi_n),
        
        .vram_addr  (ppu_vram_addr),
        .vram_din   (ppu_vram_din),
        .vram_dout  (ppu_vram_dout),
        .vram_rd    (ppu_vram_rd),
        .vram_wr    (ppu_vram_wr),
        
        .pixel_color(ppu_pixel_color),
        .scanline   (ppu_scanline),
        .cycle      (ppu_cycle),
        .vblank     (ppu_vblank)
    );
    
    // =========================================================================
    // PPU VRAM (CHR + Nametable mux)
    // =========================================================================
    // VRAM Address Decode:
    //   $0000-$1FFF: CHR ROM (8KB)
    //   $2000-$2FFF: Nametables (4KB, mirrored based on cart)
    //   $3000-$3EFF: Mirror of $2000-$2EFF
    //   $3F00-$3F1F: Palette (internal to PPU)
    
    wire chr_sel  = (ppu_vram_addr[13] == 1'b0);  // $0000-$1FFF
    wire nt_sel   = (ppu_vram_addr[13] == 1'b1) && (ppu_vram_addr[12:8] < 5'h1F); // $2000-$3EFF
    
    // CHR BRAM (8KB)
    wire [7:0] chr_rdata;
    nes_chr_bram #(
        .INIT_FILE("ppu_test_chr.hex")
    ) chr_rom (
        .clk    (clk50),
        .addr   (ppu_vram_addr[12:0]),
        .wdata  (ppu_vram_dout),
        .we     (1'b0),  // CHR-ROM is read-only
        .rdata  (chr_rdata)
    );
    
    // Nametable VRAM (2KB, with mirroring)
    wire [7:0] nt_rdata;
    nes_vram #(
        .MIRROR_V(1)  // Vertical mirroring for horizontal scrolling games
    ) nametable (
        .clk    (clk50),
        .addr   (ppu_vram_addr[10:0]),  // 2KB
        .wdata  (ppu_vram_dout),
        .we     (nt_sel && ppu_vram_wr),
        .rdata  (nt_rdata)
    );
    
    // VRAM read mux
    assign ppu_vram_din = chr_sel ? chr_rdata : nt_rdata;
    
    // =========================================================================
    // PPU to VGA Conversion
    // =========================================================================
    // PPU outputs 256x240 @ ~60Hz
    // VGA is 640x480 @ 60Hz
    // We use 2x scaling
    
    // Frame buffer: We need to buffer PPU output since PPU and VGA run at different rates
    // Simple approach: Use current PPU cycle to determine color for current VGA pixel
    // This may cause artifacts but works for initial testing
    
    // Map VGA coordinates to PPU coordinates
    wire [7:0] ppu_x = (pixel_x >= 64 && pixel_x < 576) ? (pixel_x - 64) >> 1 : 8'd0;
    wire [7:0] ppu_y = pixel_y >> 1;
    
    // PPU palette lookup
    wire [3:0] ppu_r, ppu_g, ppu_b;
    nes_palette ppu_palette (
        .color_index(ppu_pixel_color),
        .r(ppu_r),
        .g(ppu_g),
        .b(ppu_b)
    );
    
    // Select between test pattern and PPU output
    wire use_test_pattern = sw[8];
    
    // VGA output
    assign vga_r = vga_active ? (nes_active ? (use_test_pattern ? test_r : ppu_r) : 4'h0) : 4'h0;
    assign vga_g = vga_active ? (nes_active ? (use_test_pattern ? test_g : ppu_g) : 4'h0) : 4'h0;
    assign vga_b = vga_active ? (nes_active ? (use_test_pattern ? test_b : ppu_b) : 4'h0) : 4'h0;

    // =========================================================================
    // T65 CPU Instance
    // =========================================================================
    wire [23:0] cpu_addr;
    wire  [7:0] cpu_dout;
    wire  [7:0] cpu_din;
    wire        cpu_rw_n;
    wire        cpu_sync;
    
    // NMI from PPU (declared later with PPU instance)
    
    T65 cpu (
        .Mode       (2'b00),
        .BCD_en     (1'b0),
        
        .Res_n      (reset_sync),
        .Enable     (cpu_ce),
        .Clk        (clk50),
        .Rdy        (1'b1),
        .Abort_n    (1'b1),
        .IRQ_n      (1'b1),
        .NMI_n      (ppu_nmi_n),
        .SO_n       (1'b1),
        
        .R_W_n      (cpu_rw_n),
        .Sync       (cpu_sync),
        .EF         (),
        .MF         (),
        .XF         (),
        .ML_n       (),
        .VP_n       (),
        .VDA        (),
        .VPA        (),
        .A          (cpu_addr),
        .DI         (cpu_din),
        .DO         (cpu_dout),
        .Regs       (),
        .DEBUG      (),
        .NMI_ack    ()
    );

    // =========================================================================
    // Memory Map
    // =========================================================================
    wire [15:0] addr16 = cpu_addr[15:0];
    
    // RAM: 2KB at $0000-$07FF (mirrored to $1FFF)
    wire ram_sel = (addr16[15:13] == 3'b000);
    wire [10:0] ram_addr = addr16[10:0];
    wire [7:0] ram_rdata;
    wire ram_we = ram_sel && !cpu_rw_n && cpu_ce;
    
    // PPU registers: $2000-$3FFF (mirrored every 8 bytes)
    wire ppu_sel = (addr16[15:13] == 3'b001);
    wire [2:0] ppu_reg = addr16[2:0];
    wire [7:0] ppu_rdata;  // Connected to PPU instance
    
    // PRG-ROM: 32KB at $8000-$FFFF
    wire prg_sel = addr16[15];
    wire [14:0] prg_addr = addr16[14:0];
    wire [7:0] prg_rdata;
    
    // LED register: $00FF
    reg [7:0] led_reg;
    wire led_sel = (addr16 == 16'h00FF);
    
    always @(posedge clk50) begin
        if (!reset_sync)
            led_reg <= 8'h00;
        else if (led_sel && !cpu_rw_n && cpu_ce)
            led_reg <= cpu_dout;
    end

    // =========================================================================
    // Data Bus Mux
    // =========================================================================
    assign cpu_din = !cpu_rw_n ? cpu_dout :
                     prg_sel   ? prg_rdata :
                     ppu_sel   ? ppu_rdata :
                     ram_sel   ? ram_rdata :
                     8'hFF;

    // =========================================================================
    // RAM Instance (2KB)
    // =========================================================================
    reg [7:0] ram [0:2047];
    
    always @(posedge clk50) begin
        if (ram_we)
            ram[ram_addr] <= cpu_dout;
    end
    
    assign ram_rdata = ram[ram_addr];

    // =========================================================================
    // PRG-ROM Instance (32KB)
    // =========================================================================
    nes_prg_bram #(
        .INIT_FILE("test_rom.hex")
    ) prg_rom (
        .clk    (clk50),
        .addr   (prg_addr),
        .wdata  (8'h00),
        .we     (1'b0),
        .rdata  (prg_rdata)
    );

    // =========================================================================
    // LED Output
    // =========================================================================
    assign led[7:0] = led_reg;
    assign led[8] = cpu_sync;
    assign led[9] = reset_sync;

    // =========================================================================
    // 7-Segment Displays
    // =========================================================================
    reg [15:0] addr_latched;
    always @(posedge clk50) begin
        if (!reset_sync)
            addr_latched <= 16'h0000;
        else if (cpu_ce)
            addr_latched <= addr16;
    end
    
    // HEX0-3: CPU address
    hex_display hd0 (.value(addr_latched[3:0]),   .segments(hex0));
    hex_display hd1 (.value(addr_latched[7:4]),   .segments(hex1));
    hex_display hd2 (.value(addr_latched[11:8]),  .segments(hex2));
    hex_display hd3 (.value(addr_latched[15:12]), .segments(hex3));
    
    // HEX4-5: PPU scanline (for debug)
    hex_display hd4 (.value(ppu_scanline[3:0]), .segments(hex4));
    hex_display hd5 (.value(ppu_scanline[7:4]), .segments(hex5));

endmodule

// Simple 7-segment hex display driver
module hex_display (
    input  [3:0] value,
    output [7:0] segments
);
    reg [6:0] seg;
    
    always @(*) begin
        case (value)
            4'h0: seg = 7'b1000000;
            4'h1: seg = 7'b1111001;
            4'h2: seg = 7'b0100100;
            4'h3: seg = 7'b0110000;
            4'h4: seg = 7'b0011001;
            4'h5: seg = 7'b0010010;
            4'h6: seg = 7'b0000010;
            4'h7: seg = 7'b1111000;
            4'h8: seg = 7'b0000000;
            4'h9: seg = 7'b0010000;
            4'hA: seg = 7'b0001000;
            4'hB: seg = 7'b0000011;
            4'hC: seg = 7'b1000110;
            4'hD: seg = 7'b0100001;
            4'hE: seg = 7'b0000110;
            4'hF: seg = 7'b0001110;
        endcase
    end
    
    assign segments = {1'b1, seg};
endmodule
