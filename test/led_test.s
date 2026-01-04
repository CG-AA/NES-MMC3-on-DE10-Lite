; Simple NES test ROM - LED Blinker
; This runs on bare 6502, no PPU needed
; Writes to $FF (mapped to LED output)

.segment "HEADER"
    ; No iNES header for raw test

.segment "CODE"

reset:
    sei             ; Disable interrupts
    cld             ; Clear decimal mode
    ldx #$FF
    txs             ; Initialize stack

    lda #$00        ; Start with LED off
    sta $00         ; Store counter in zero page

loop:
    ; Increment counter
    inc $00
    
    ; Write counter to LED port ($FF)
    lda $00
    sta $FF
    
    ; Delay loop
    ldx #$00
delay_outer:
    ldy #$00
delay_inner:
    dey
    bne delay_inner
    dex
    bne delay_outer
    
    ; Loop forever
    jmp loop

nmi:
irq:
    rti

.segment "VECTORS"
    .word nmi       ; NMI vector
    .word reset     ; Reset vector  
    .word irq       ; IRQ vector
