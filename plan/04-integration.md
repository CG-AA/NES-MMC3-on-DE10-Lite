# Phase 4: MMC3 Support

**Goal:** Run Super Mario Bros 3 and other MMC3 games.

**Status:** ⏳ NOT STARTED

**Prerequisites:** 
- Phase 3 complete ✅
- SDRAM bulk uploads working ❌ (need Etherbone or custom loader)

---

## Why SDRAM is Required

MMC3 games are too large for BRAM:

| Game | PRG | CHR | Total | Fits in BRAM? |
|------|-----|-----|-------|---------------|
| Super Mario Bros 3 | 256KB | 128KB | 384KB | ❌ No (BRAM = 100KB free) |
| Mega Man 3 | 256KB | 128KB | 384KB | ❌ No |
| Kirby's Adventure | 512KB | 256KB | 768KB | ❌ No |

**Solution:** Fix SDRAM bulk uploads before proceeding. Options:
1. **Etherbone** - Ethernet-based (~1MB/s vs 11KB/s UART)
2. **Custom binary loader** - Skip text-based BIOS commands
3. **SD Card** - Load ROM from FAT filesystem

---

## Success Criteria

- [ ] SDRAM bulk upload reliable (32KB+)
- [ ] Wishbone bridge for NES → SDRAM access
- [ ] MMC3 mapper ported and integrated
- [ ] PRG bank switching works
- [ ] CHR bank switching works  
- [ ] Scanline counter IRQ works
- [ ] SMB3 boots to title screen
- [ ] SMB3 is playable (scrolling works)

## Strategy

MMC3 is the most common NES mapper. Once it works, ~70% of NES games are playable.

## Steps

### 0. Fix SDRAM Uploads (Prerequisite)

Choose one:
- **Etherbone:** Rebuild LiteX with `--with-etherbone`, use `litex_server` + `litex_cli`
- **Custom loader:** Binary protocol over UART, skip text commands
- **SD Card:** Add SPI master, FAT filesystem

### 1. Get MMC3 from MiSTer

```bash
git clone https://github.com/MiSTer-devel/NES_MiSTer.git
# Extract mapper 4 (MMC3) from rtl/mappers/
```

### 2. Port to Our Interface

Adapt MMC3 module to use our signals:
- `mapper_cs` from address decoder
- PRG bank outputs to bridge
- CHR bank outputs to CHR cache
- Scanline counter IRQ to CPU

### 3. Add CHR Bank Switching

Expand CHR BRAM to 32KB (or use cache if game needs more):
- 8 × 1KB banks for MMC3
- Bank select from mapper

### 4. Add PRG Bank Switching

- Fixed bank ($C000-$FFFF) stays in BRAM
- Switchable bank ($8000-$BFFF) uses mapper offset into SDRAM

### 5. Test with SMB3

Super Mario Bros 3:
- PRG-ROM: 256KB (needs SDRAM)
- CHR-ROM: 128KB (needs cache or large BRAM)
- Uses scanline IRQ for status bar

## What NOT To Do

- Don't implement other mappers yet
- Don't optimize CHR cache
- Don't add audio

## Files to Create/Modify

| File | Purpose |
|:-----|:--------|
| `rtl/nes_mapper_mmc3.v` | MMC3 mapper |
| Modify `nes_top.v` | Wire mapper |
| Modify bridge | Bank offset calculation |

## After This

Project is "done" when SMB3 is playable. Further improvements optional:
- More mappers
- Audio output
- Controller input from GPIO
