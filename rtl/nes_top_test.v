// NES Top Level - Phase 2 Minimal Test
// T65 CPU + BRAM only (no PPU yet)
// For testing CPU execution on DE10-Lite
//
// DEBUG MODES:
//   SW[9] = 0: Normal speed (~1.78 MHz CPU)
//   SW[9] = 1: Ultra-slow (1 Hz CPU) for visual debugging

module nes_top_test (
    input         clk50,          // 50 MHz input clock
    input         reset_n,        // Active low reset (directly from button KEY[0])
    input   [9:0] sw,             // Slide switches for debug modes
    
    // LED output for debug
    output  [9:0] led,
    
    // 7-segment displays for debug
    output  [7:0] hex0,
    output  [7:0] hex1,
    output  [7:0] hex2,
    output  [7:0] hex3
);

    // =========================================================================
    // Clock Generation
    // =========================================================================
    // NES master clock: 21.477272 MHz (NTSC)
    // CPU clock: 21.477272 / 12 = 1.789773 MHz
    // PPU clock: 21.477272 / 4  = 5.369318 MHz
    //
    // For testing, we'll run slower - use 50MHz with dividers
    // Normal mode: CPU enable every 28 clocks = ~1.78 MHz
    // Slow mode (SW[9]=1): CPU enable every 50M clocks = 1 Hz
    
    reg [4:0] clk_div;
    reg [25:0] slow_div;
    
    wire slow_mode = sw[9];
    wire cpu_ce_fast = (clk_div == 5'd27);
    wire cpu_ce_slow = (slow_div == 26'd49_999_999);  // 1 Hz
    wire cpu_ce = slow_mode ? cpu_ce_slow : cpu_ce_fast;
    
    always @(posedge clk50) begin
        if (!reset_n) begin
            clk_div <= 0;
            slow_div <= 0;
        end else begin
            // Fast divider
            if (clk_div == 5'd27)
                clk_div <= 0;
            else
                clk_div <= clk_div + 1'b1;
            
            // Slow divider (1 Hz)
            if (slow_div == 26'd49_999_999)
                slow_div <= 0;
            else
                slow_div <= slow_div + 1'b1;
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
    // T65 CPU Instance
    // =========================================================================
    wire [23:0] cpu_addr;
    wire  [7:0] cpu_dout;
    wire  [7:0] cpu_din;
    wire        cpu_rw_n;  // 1 = read, 0 = write
    wire        cpu_sync;
    
    T65 cpu (
        .Mode       (2'b00),        // 6502 mode
        .BCD_en     (1'b0),         // NES 2A03 has no BCD
        
        .Res_n      (reset_sync),
        .Enable     (cpu_ce),
        .Clk        (clk50),
        .Rdy        (1'b1),
        .Abort_n    (1'b1),
        .IRQ_n      (1'b1),         // No IRQ for now
        .NMI_n      (1'b1),         // No NMI for now
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
    // $0000-$07FF: 2KB Internal RAM (mirrored to $1FFF)
    // $2000-$3FFF: PPU registers (not implemented yet)
    // $4000-$401F: APU/IO registers (not implemented yet)
    // $8000-$FFFF: PRG-ROM (32KB BRAM)
    
    wire [15:0] addr16 = cpu_addr[15:0];
    
    // RAM: 2KB at $0000-$07FF
    wire ram_sel = (addr16[15:13] == 3'b000);  // $0000-$1FFF
    wire [10:0] ram_addr = addr16[10:0];       // 2KB
    wire [7:0] ram_rdata;
    wire ram_we = ram_sel && !cpu_rw_n && cpu_ce;
    
    // PRG-ROM: 32KB at $8000-$FFFF
    wire prg_sel = addr16[15];                 // $8000-$FFFF
    wire [14:0] prg_addr = addr16[14:0];       // 32KB
    wire [7:0] prg_rdata;
    
    // LED register: $00FF (for debug output)
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
    // IMPORTANT: T65 requires DI to reflect DO during writes!
    // See T65.vhd comments: "route the DO signal back to the DI signal while R_W_n='0'"
    assign cpu_din = !cpu_rw_n ? cpu_dout :  // During writes, echo back write data
                     prg_sel   ? prg_rdata :
                     ram_sel   ? ram_rdata :
                     8'hFF;  // Open bus

    // =========================================================================
    // RAM Instance (2KB)
    // =========================================================================
    reg [7:0] ram [0:2047];
    
    always @(posedge clk50) begin
        if (ram_we)
            ram[ram_addr] <= cpu_dout;
    end
    
    // Combinational read - data available same cycle as address
    // Required for 6502 which expects immediate data
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
        .we     (1'b0),     // ROM is read-only
        .rdata  (prg_rdata)
    );

    // =========================================================================
    // LED Output
    // =========================================================================
    assign led[7:0] = led_reg;
    assign led[8] = cpu_sync;     // Show when CPU is fetching opcode
    assign led[9] = reset_sync;   // Show reset state

    // =========================================================================
    // 7-Segment Display - Show CPU Address (latched on valid cycles only)
    // =========================================================================
    // Latch address only when CPU clock enable is active
    // This helps distinguish "stuck" vs "running wild" CPU
    reg [15:0] addr_latched;
    always @(posedge clk50) begin
        if (!reset_sync)
            addr_latched <= 16'h0000;
        else if (cpu_ce)
            addr_latched <= addr16;
    end
    
    hex_display h0 (.value(addr_latched[3:0]),   .segments(hex0));
    hex_display h1 (.value(addr_latched[7:4]),   .segments(hex1));
    hex_display h2 (.value(addr_latched[11:8]),  .segments(hex2));
    hex_display h3 (.value(addr_latched[15:12]), .segments(hex3));

endmodule

// Simple 7-segment hex display driver
module hex_display (
    input  [3:0] value,
    output [7:0] segments  // Active low: {DP, G, F, E, D, C, B, A}
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
    
    assign segments = {1'b1, seg};  // DP off

endmodule
