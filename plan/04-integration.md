# Phase 4: MMC3 Support

**Goal:** Run Super Mario Bros 3 and other MMC3 games.

## Success Criteria

- [ ] MMC3 mapper ported and integrated
- [ ] PRG bank switching works
- [ ] CHR bank switching works  
- [ ] Scanline counter IRQ works
- [ ] SMB3 boots to title screen
- [ ] SMB3 is playable (scrolling works)

## Strategy

MMC3 is the most common NES mapper. Once it works, ~70% of NES games are playable.

## Steps

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
