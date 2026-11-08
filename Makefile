# NetHack 3.4.3 for the Commodore 64 - build entry point.
#
#   make            EasyFlash cartridge  -> build/nethack-ef.crt   (primary target)
#   make prg        plain C64 program    -> build/nethack.prg      (quick iteration)
#   make run        build the cart and launch VICE with a 512KB REU
#   make run-prg    same for the .prg
#   make test       headless self-tests in VICE (AUTOTEST builds, debug cartridge)
#   make repros     re-run the Oscar64 compatibility repros (tests/oscar64-repros)
#   make upstream   fetch + verify NetHack 3.4.3 into upstream/nethack-3.4.3
#   make port-tree  derive port/ from upstream (ANSI + Oscar64 normalisation)
#   make memmap     summarise the last build's memory map
#   make clean
#
# Tools are found on PATH; override e.g.  make OSCAR64=~/src/oscar64/bin/oscar64

OSCAR64  ?= oscar64
VICE     ?= x64sc
PYTHON   ?= python3
REUSIZE  ?= 512
# EasyFlash hardware sub-type written into the .crt header:
#   0 = standard EasyFlash (default)
#   1 = "REU-aware" EasyFlash on Ultimate-family hardware ($DF00-$DF1F left
#       to the REU).  See docs/HARDWARE.md before relying on it.
CRT_SUBTYPE ?= 0

BUILD    := build
GEN      := $(BUILD)/gen
SRCS     := src/main.c src/hal/sys.c src/hal/screen80.c
HDRS     := $(wildcard src/*.h src/hal/*.h) $(GEN)/font4x8.h

# -Os: code density matters more than speed for this project (see docs/ARCHITECTURE.md)
# -g : source-level debug info, .lbl labels for VICE, annotated .asm
OSCFLAGS ?= -Os -g
OSC      := $(OSCAR64) $(OSCFLAGS) -i=src -i=$(GEN)

CRT      := $(BUILD)/nethack-ef.crt
PRG      := $(BUILD)/nethack.prg

.PHONY: all ef prg run run-prg test repros font upstream port-tree memmap clean help

all: ef

help:
	@sed -n '2,15p' Makefile

ef: $(CRT)
prg: $(PRG)

$(GEN)/font4x8.h: tools/mkfont4x8.py
	@mkdir -p $(GEN)
	$(PYTHON) tools/mkfont4x8.py $@

font: $(GEN)/font4x8.h

# -tf=crt : EasyFlash image; bank 0 is copied to RAM at boot (oscar64 "main" region)
# the header name/sub-type are then set by tools/crtinfo.py (CRT format 1.1)
$(CRT): $(SRCS) $(HDRS)
	@mkdir -p $(BUILD)
	$(OSC) -tf=crt -o=$@ $(SRCS)
	@$(PYTHON) tools/crtinfo.py $@ --name "NETHACK-C64" --subtype $(CRT_SUBTYPE)

$(PRG): $(SRCS) $(HDRS)
	@mkdir -p $(BUILD)
	$(OSC) -o=$@ $(SRCS)

# ---- self-test builds ----------------------------------------------------
$(BUILD)/test-ef.crt: $(SRCS) $(HDRS)
	@mkdir -p $(BUILD)
	$(OSC) -dAUTOTEST -tf=crt -o=$@ $(SRCS)

$(BUILD)/test.prg: $(SRCS) $(HDRS)
	@mkdir -p $(BUILD)
	$(OSC) -dAUTOTEST -o=$@ $(SRCS)

test: $(BUILD)/test.prg $(BUILD)/test-ef.crt
	VICE=$(VICE) $(PYTHON) tests/run_selftests.py $(BUILD)

repros:
	OSCAR64=$(OSCAR64) $(PYTHON) tests/oscar64-repros/run.py

# ---- running interactively -------------------------------------------------
run: $(CRT)
	$(VICE) -reu -reusize $(REUSIZE) -cartcrt $(CRT)

run-prg: $(PRG)
	$(VICE) -reu -reusize $(REUSIZE) -autostartprgmode 1 -autostart $(PRG)

# ---- NetHack source -----------------------------------------------------------
upstream:
	tools/fetch-nethack.sh

port-tree: upstream
	tools/prepare-port-tree.sh

memmap:
	$(PYTHON) tools/memmap.py $(BUILD)/*.map

clean:
	rm -rf $(BUILD)
