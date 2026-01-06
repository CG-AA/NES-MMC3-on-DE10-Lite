# Documentation Index

Quick reference to find what you need.

---

## Getting Started

**First time here?** Start with these:

1. **[README.md](README.md)** - Project overview, status, quick start
2. **[phase3/BUILD_GUIDE.md](phase3/BUILD_GUIDE.md)** - How to compile and run
3. **[phase3/HARDWARE.md](phase3/HARDWARE.md)** - Pin assignments, wiring

---

## By Topic

### Usage & Operation
- **Quick Start** → [README.md](README.md#quick-start)
- **Building from Source** → [phase3/BUILD_GUIDE.md](phase3/BUILD_GUIDE.md)
- **Game Switching** → [phase3/BUILD_GUIDE.md](phase3/BUILD_GUIDE.md#rom-extraction)
- **Keyboard Controls** → [phase3/BUILD_GUIDE.md](phase3/BUILD_GUIDE.md#keyboard-controller)

### Technical Details
- **Architecture Overview** → [README.md](README.md#architecture-overview-phase-3)
- **Phase 3 Summary** → [phase3/PHASE3_SUMMARY.md](phase3/PHASE3_SUMMARY.md)
- **Hardware Specs** → [phase3/HARDWARE.md](phase3/HARDWARE.md)
- **Resource Usage** → [README.md](README.md#resource-usage-phase-3)

### Debugging & Development
- **Debug Techniques** → [phase3/BUILD_GUIDE.md](phase3/BUILD_GUIDE.md#debugging-techniques)
- **Common Issues** → [phase3/BUILD_GUIDE.md](phase3/BUILD_GUIDE.md#common-issues--fixes)
- **Lessons Learned** → [LESSONS_LEARNED.md](LESSONS_LEARNED.md)

### History & Planning
- **Project Changelog** → [CHANGELOG.md](CHANGELOG.md)
- **Phase 4 Roadmap** → [phase4/PHASE4_PLAN.md](phase4/PHASE4_PLAN.md)
- **Old Documents** → [archive/](archive/)

---

## By Role

### I want to play games
1. Read [Quick Start](README.md#quick-start)
2. Follow [Build Guide](phase3/BUILD_GUIDE.md)
3. Check [Keyboard Controls](phase3/BUILD_GUIDE.md#keyboard-controller)

### I want to understand the design
1. Read [Phase 3 Summary](phase3/PHASE3_SUMMARY.md)
2. Review [Architecture](README.md#architecture-overview-phase-3)
3. Check [Hardware Specs](phase3/HARDWARE.md)

### I want to debug issues
1. Check [Common Issues](phase3/BUILD_GUIDE.md#common-issues--fixes)
2. Read [Lessons Learned](LESSONS_LEARNED.md)
3. Review [Debug Techniques](phase3/BUILD_GUIDE.md#debugging-techniques)

### I want to add features
1. Read [Phase 3 Summary](phase3/PHASE3_SUMMARY.md) - understand what exists
2. Review [Phase 4 Plan](phase4/PHASE4_PLAN.md) - see what's next
3. Check [Lessons Learned](LESSONS_LEARNED.md) - avoid past mistakes

---

## Document Descriptions

| File | Purpose | Read if... |
|------|---------|------------|
| **[README.md](README.md)** | Main index, current status | You want a quick overview |
| **[phase3/PHASE3_SUMMARY.md](phase3/PHASE3_SUMMARY.md)** | What Phase 3 built | You want to understand the system |
| **[phase3/BUILD_GUIDE.md](phase3/BUILD_GUIDE.md)** | How to build/run/debug | You want to compile or modify |
| **[phase3/HARDWARE.md](phase3/HARDWARE.md)** | Specs, pins, resources | You need hardware details |
| **[LESSONS_LEARNED.md](LESSONS_LEARNED.md)** | Debug wisdom, pitfalls | You're debugging or designing |
| **[CHANGELOG.md](CHANGELOG.md)** | Historical milestones | You want project history |
| **[phase4/PHASE4_PLAN.md](phase4/PHASE4_PLAN.md)** | Future roadmap | You want to know what's next |
| **[archive/](archive/)** | Old phase docs | You need historical context |

---

## File Organization

```
plan/
├── README.md              # Main entry point
├── INDEX.md               # This file (navigation aid)
├── CHANGELOG.md           # Historical milestones
├── LESSONS_LEARNED.md     # Technical wisdom
│
├── phase3/                # Phase 3: Standalone NES (COMPLETE)
│   ├── PHASE3_SUMMARY.md  # What was built
│   ├── BUILD_GUIDE.md     # How to build/debug
│   └── HARDWARE.md        # Hardware specifications
│
├── phase4/                # Phase 4: SDRAM + MMC3 (PLANNED)
│   └── PHASE4_PLAN.md     # Roadmap and strategy
│
└── archive/               # Old documents (historical)
    ├── 01-litex-setup.md
    ├── 02-components.md
    └── 03-memory-bridge.md
```

---

## Quick Links

### Most Frequently Needed
- [Quick Start Guide](README.md#quick-start)
- [Build Instructions](phase3/BUILD_GUIDE.md#build-process-details)
- [Pin Assignments](phase3/HARDWARE.md#pin-assignments-nes_vgaqsf)
- [Troubleshooting](phase3/BUILD_GUIDE.md#common-issues--fixes)

### Technical Reference
- [Architecture Diagram](README.md#architecture-overview-phase-3)
- [Resource Budget](phase3/HARDWARE.md#resource-budget-phase-3--phase-4)
- [Timing Constraints](phase3/HARDWARE.md#timing-constraints-nes_vgasdc)

### Development
- [Debug Techniques](phase3/BUILD_GUIDE.md#debugging-techniques)
- [Code Organization](phase3/BUILD_GUIDE.md#project-structure)
- [DMA Timing Fix](LESSONS_LEARNED.md#7-the-critical-dma-bug-root-cause-found)
- [UART Fix](LESSONS_LEARNED.md#8-uart-receiver-timing-issues)

---

*Updated: January 7, 2026 - Phase 3 Complete*
