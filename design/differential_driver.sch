v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {differential_driver -- USB 2.0 FS single-ended DP/DM output stages (spec Sec.6)
Two symmetric single-ended drivers (DP half, DM half). Each: a small
CMOS predriver -> RC gate-slew resistor -> large complementary output
stage -> series output resistor (rm1) to the pad. TXDP/TXDM are opaque
digital inputs from the (out-of-scope) NRZI/encode logic; this cell
defines TXDx=1 => Dx driven high (net non-inversion: predriver inverts
once, the output stage's shared-gate CMOS pair inverts again).
TXOE (active-high) is the output enable: TXOE=0 turns BOTH output
transistors off on BOTH pads (DP/DM high-Z) for every TXDP/TXDM value.
Because the output stage's PMOS and NMOS share no gate net any more,
each half has two gated predrivers: NAND(TXDx,TXOE) -> R_slew -> PMOS
gate (held at VDD when disabled) and NOR(TXDx,!TXOE) -> R_slew -> NMOS
gate (held at VSS when disabled). With TXOE=1 each reduces to the #96
predriver inverter (P 8u / N 2.5u per path), so the output-stage
topology and sizing are unchanged; the gate load is split across two
equal slew resistors. See design/README.md (#114).
Design-intent targets (NOT yet PVT-simulated -- see #26):
  rise/fall 10-90% into 50pF: 4-20ns   (Sec.6)
  rise/fall matching: within 10%        (Sec.6)
  crossover voltage: 1.3-2.0V            (Sec.6)
  output resistance: 28-44 ohm           (Sec.6)} -900 -900 0 0 0.35 0.35 {}
T {Sizing rationale (issue #96 re-size; replaces the issue #30 first-order hand calc):
Output stage per half: PMOS W=80u as 4 parallel m=1 devices, NMOS W=30u as 4 parallel m=1 devices (Wp:Wn = 8:3, wider
than the 2:1 mobility ratio on purpose: PMOS is the weaker puller, worst
at the fs corner). Large enough that the FETs act as a near-linear Ron
in series with R_series rather than as current-limited sources, which holds
rise/fall matching inside +/-10 % across fs/sf; the old 60/30 stage was
saturation-limited and failed matching at 36/45 corners. Predriver
8u/2.5u (was 4u/2u): its Wp:Wn sets the relative P/N turn-on timing and so
centres the D+/D- crossover inside 1.3-2.0 V.
R_series (rm1, metal1) unchanged: 36 ohm nominal (L/W=400, W=2u L=800u),
rsh_rm1=0.09 +/-0.012 ohm/sq, inside the 28-44 ohm band without a trim.
R_series x 50pF alone is only ~3.4 ns (10-90 %) at the ff corner, below the
4 ns floor, so FET Ron and the R_slew gate RC must supply the rest; the
output stage is therefore deliberately NOT sized any larger. R_slew is
unchanged.
Evidence: sim/driver-signal-quality (record id in design/README.md).
TXOE gating (#114): the NAND/NOR predrivers use the #96 predriver sizes per
path (NAND: PMOS 8u parallel, NMOS 2x5u series; NOR: PMOS 2x16u series,
NMOS 2.5u parallel) so TXOE=1 drive strength matches the inverter. The
re-sizing is NOT yet re-verified across PVT -- see the #114 evidence run.} -900 -700 0 0 0.3 0.3 {}
N -1080 -530 -1080 -570 {}
C {devices/lab_pin.sym} -1080 -570 0 0 {name=l1 lab=VDD}
N -1080 -470 -1080 -430 {}
C {devices/lab_pin.sym} -1080 -430 0 0 {name=l2 lab=TXOEB}
N -1120 -500 -1180 -500 {}
C {devices/lab_pin.sym} -1180 -500 0 0 {name=l3 lab=TXOE}
N -1080 -500 -1020 -500 {}
C {devices/lab_pin.sym} -1020 -500 0 0 {name=l4 lab=VDD}
C {symbols/pfet_03v3.sym} -1100 -500 0 0 {name=MPOEB
L=0.28u
W=4u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -880 -530 -880 -570 {}
C {devices/lab_pin.sym} -880 -570 0 0 {name=l5 lab=TXOEB}
N -880 -470 -880 -430 {}
C {devices/lab_pin.sym} -880 -430 0 0 {name=l6 lab=VSS}
N -920 -500 -980 -500 {}
C {devices/lab_pin.sym} -980 -500 0 0 {name=l7 lab=TXOE}
N -880 -500 -820 -500 {}
C {devices/lab_pin.sym} -820 -500 0 0 {name=l8 lab=VSS}
C {symbols/nfet_03v3.sym} -900 -500 0 0 {name=MNOEB
L=0.28u
W=2u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -2280 -30 -2280 -70 {}
C {devices/lab_pin.sym} -2280 -70 0 0 {name=ql9 lab=VDD}
N -2280 30 -2280 70 {}
C {devices/lab_pin.sym} -2280 70 0 0 {name=ql10 lab=DP_PREP}
N -2320 0 -2380 0 {}
C {devices/lab_pin.sym} -2380 0 0 0 {name=ql11 lab=TXDP}
N -2280 0 -2220 0 {}
C {devices/lab_pin.sym} -2220 0 0 0 {name=ql12 lab=VDD}
C {symbols/pfet_03v3.sym} -2300 0 0 0 {name=MP1ADP
L=0.28u
W=8u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -2020 -30 -2020 -70 {}
C {devices/lab_pin.sym} -2020 -70 0 0 {name=ql13 lab=VDD}
N -2020 30 -2020 70 {}
C {devices/lab_pin.sym} -2020 70 0 0 {name=ql14 lab=DP_PREP}
N -2060 0 -2120 0 {}
C {devices/lab_pin.sym} -2120 0 0 0 {name=ql15 lab=TXOE}
N -2020 0 -1960 0 {}
C {devices/lab_pin.sym} -1960 0 0 0 {name=ql16 lab=VDD}
C {symbols/pfet_03v3.sym} -2040 0 0 0 {name=MP1BDP
L=0.28u
W=8u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -1760 -30 -1760 -70 {}
C {devices/lab_pin.sym} -1760 -70 0 0 {name=ql17 lab=DP_PREP}
N -1760 30 -1760 70 {}
C {devices/lab_pin.sym} -1760 70 0 0 {name=ql18 lab=DP_NX}
N -1800 0 -1860 0 {}
C {devices/lab_pin.sym} -1860 0 0 0 {name=ql19 lab=TXDP}
N -1760 0 -1700 0 {}
C {devices/lab_pin.sym} -1700 0 0 0 {name=ql20 lab=VSS}
C {symbols/nfet_03v3.sym} -1780 0 0 0 {name=MN1ADP
L=0.28u
W=5u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -1500 -30 -1500 -70 {}
C {devices/lab_pin.sym} -1500 -70 0 0 {name=ql21 lab=DP_NX}
N -1500 30 -1500 70 {}
C {devices/lab_pin.sym} -1500 70 0 0 {name=ql22 lab=VSS}
N -1540 0 -1600 0 {}
C {devices/lab_pin.sym} -1600 0 0 0 {name=ql23 lab=TXOE}
N -1500 0 -1440 0 {}
C {devices/lab_pin.sym} -1440 0 0 0 {name=ql24 lab=VSS}
C {symbols/nfet_03v3.sym} -1520 0 0 0 {name=MN1BDP
L=0.28u
W=5u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -1260 -30 -1260 -70 {}
C {devices/lab_pin.sym} -1260 -70 0 0 {name=ql25 lab=DP_PREP}
N -1260 30 -1260 70 {}
C {devices/lab_pin.sym} -1260 70 0 0 {name=ql26 lab=DP_GATEP}
N -1280 0 -1340 0 {}
C {devices/lab_pin.sym} -1340 0 0 0 {name=ql27 lab=VSS}
C {symbols/ppolyf_u.sym} -1260 0 0 0 {name=RSLEWPDP
W=1u
L=2u
model=ppolyf_u
spiceprefix=X
m=1
}
N -2280 270 -2280 230 {}
C {devices/lab_pin.sym} -2280 230 0 0 {name=ql28 lab=VDD}
N -2280 330 -2280 370 {}
C {devices/lab_pin.sym} -2280 370 0 0 {name=ql29 lab=DP_PX}
N -2320 300 -2380 300 {}
C {devices/lab_pin.sym} -2380 300 0 0 {name=ql30 lab=TXDP}
N -2280 300 -2220 300 {}
C {devices/lab_pin.sym} -2220 300 0 0 {name=ql31 lab=VDD}
C {symbols/pfet_03v3.sym} -2300 300 0 0 {name=MP3ADP
L=0.28u
W=16u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -2020 270 -2020 230 {}
C {devices/lab_pin.sym} -2020 230 0 0 {name=ql32 lab=DP_PX}
N -2020 330 -2020 370 {}
C {devices/lab_pin.sym} -2020 370 0 0 {name=ql33 lab=DP_PREN}
N -2060 300 -2120 300 {}
C {devices/lab_pin.sym} -2120 300 0 0 {name=ql34 lab=TXOEB}
N -2020 300 -1960 300 {}
C {devices/lab_pin.sym} -1960 300 0 0 {name=ql35 lab=VDD}
C {symbols/pfet_03v3.sym} -2040 300 0 0 {name=MP3BDP
L=0.28u
W=16u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -1760 270 -1760 230 {}
C {devices/lab_pin.sym} -1760 230 0 0 {name=ql36 lab=DP_PREN}
N -1760 330 -1760 370 {}
C {devices/lab_pin.sym} -1760 370 0 0 {name=ql37 lab=VSS}
N -1800 300 -1860 300 {}
C {devices/lab_pin.sym} -1860 300 0 0 {name=ql38 lab=TXDP}
N -1760 300 -1700 300 {}
C {devices/lab_pin.sym} -1700 300 0 0 {name=ql39 lab=VSS}
C {symbols/nfet_03v3.sym} -1780 300 0 0 {name=MN3ADP
L=0.28u
W=2.5u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -1500 270 -1500 230 {}
C {devices/lab_pin.sym} -1500 230 0 0 {name=ql40 lab=DP_PREN}
N -1500 330 -1500 370 {}
C {devices/lab_pin.sym} -1500 370 0 0 {name=ql41 lab=VSS}
N -1540 300 -1600 300 {}
C {devices/lab_pin.sym} -1600 300 0 0 {name=ql42 lab=TXOEB}
N -1500 300 -1440 300 {}
C {devices/lab_pin.sym} -1440 300 0 0 {name=ql43 lab=VSS}
C {symbols/nfet_03v3.sym} -1520 300 0 0 {name=MN3BDP
L=0.28u
W=2.5u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -1260 270 -1260 230 {}
C {devices/lab_pin.sym} -1260 230 0 0 {name=ql44 lab=DP_PREN}
N -1260 330 -1260 370 {}
C {devices/lab_pin.sym} -1260 370 0 0 {name=ql45 lab=DP_GATEN}
N -1280 300 -1340 300 {}
C {devices/lab_pin.sym} -1340 300 0 0 {name=ql46 lab=VSS}
C {symbols/ppolyf_u.sym} -1260 300 0 0 {name=RSLEWNDP
W=1u
L=2u
model=ppolyf_u
spiceprefix=X
m=1
}
N -160 -30 -160 -70 {}
C {devices/lab_pin.sym} -160 -70 0 0 {name=l12 lab=VDD}
N -200 0 -260 0 {}
C {devices/lab_pin.sym} -260 0 0 0 {name=l13 lab=DP_GATEP}
N -160 30 -160 70 {}
C {devices/lab_pin.sym} -160 70 0 0 {name=l14 lab=DP_OUTINT}
N -160 0 -100 0 {}
C {devices/lab_pin.sym} -100 0 0 0 {name=l15 lab=VDD}
C {symbols/pfet_03v3.sym} -180 0 0 0 {name=MP2DP_1
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -160 130 -160 90 {}
C {devices/lab_pin.sym} -160 90 0 0 {name=l43 lab=VDD}
N -200 160 -260 160 {}
C {devices/lab_pin.sym} -260 160 0 0 {name=l44 lab=DP_GATEP}
N -160 190 -160 230 {}
C {devices/lab_pin.sym} -160 230 0 0 {name=l45 lab=DP_OUTINT}
N -160 160 -100 160 {}
C {devices/lab_pin.sym} -100 160 0 0 {name=l46 lab=VDD}
C {symbols/pfet_03v3.sym} -180 160 0 0 {name=MP2DP_2
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -160 290 -160 250 {}
C {devices/lab_pin.sym} -160 250 0 0 {name=l47 lab=VDD}
N -200 320 -260 320 {}
C {devices/lab_pin.sym} -260 320 0 0 {name=l48 lab=DP_GATEP}
N -160 350 -160 390 {}
C {devices/lab_pin.sym} -160 390 0 0 {name=l49 lab=DP_OUTINT}
N -160 320 -100 320 {}
C {devices/lab_pin.sym} -100 320 0 0 {name=l50 lab=VDD}
C {symbols/pfet_03v3.sym} -180 320 0 0 {name=MP2DP_3
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -160 450 -160 410 {}
C {devices/lab_pin.sym} -160 410 0 0 {name=l51 lab=VDD}
N -200 480 -260 480 {}
C {devices/lab_pin.sym} -260 480 0 0 {name=l52 lab=DP_GATEP}
N -160 510 -160 550 {}
C {devices/lab_pin.sym} -160 550 0 0 {name=l53 lab=DP_OUTINT}
N -160 480 -100 480 {}
C {devices/lab_pin.sym} -100 480 0 0 {name=l54 lab=VDD}
C {symbols/pfet_03v3.sym} -180 480 0 0 {name=MP2DP_4
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 80 30 80 70 {}
C {devices/lab_pin.sym} 80 70 0 0 {name=l16 lab=VSS}
N 40 0 -20 0 {}
C {devices/lab_pin.sym} -20 0 0 0 {name=l17 lab=DP_GATEN}
N 80 -30 80 -70 {}
C {devices/lab_pin.sym} 80 -70 0 0 {name=l18 lab=DP_OUTINT}
N 80 0 140 0 {}
C {devices/lab_pin.sym} 140 0 0 0 {name=l19 lab=VSS}
C {symbols/nfet_03v3.sym} 60 0 0 0 {name=MN2DP_1
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 80 190 80 230 {}
C {devices/lab_pin.sym} 80 230 0 0 {name=l55 lab=VSS}
N 40 160 -20 160 {}
C {devices/lab_pin.sym} -20 160 0 0 {name=l56 lab=DP_GATEN}
N 80 130 80 90 {}
C {devices/lab_pin.sym} 80 90 0 0 {name=l57 lab=DP_OUTINT}
N 80 160 140 160 {}
C {devices/lab_pin.sym} 140 160 0 0 {name=l58 lab=VSS}
C {symbols/nfet_03v3.sym} 60 160 0 0 {name=MN2DP_2
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 80 350 80 390 {}
C {devices/lab_pin.sym} 80 390 0 0 {name=l59 lab=VSS}
N 40 320 -20 320 {}
C {devices/lab_pin.sym} -20 320 0 0 {name=l60 lab=DP_GATEN}
N 80 290 80 250 {}
C {devices/lab_pin.sym} 80 250 0 0 {name=l61 lab=DP_OUTINT}
N 80 320 140 320 {}
C {devices/lab_pin.sym} 140 320 0 0 {name=l62 lab=VSS}
C {symbols/nfet_03v3.sym} 60 320 0 0 {name=MN2DP_3
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 80 510 80 550 {}
C {devices/lab_pin.sym} 80 550 0 0 {name=l63 lab=VSS}
N 40 480 -20 480 {}
C {devices/lab_pin.sym} -20 480 0 0 {name=l64 lab=DP_GATEN}
N 80 450 80 410 {}
C {devices/lab_pin.sym} 80 410 0 0 {name=l65 lab=DP_OUTINT}
N 80 480 140 480 {}
C {devices/lab_pin.sym} 140 480 0 0 {name=l66 lab=VSS}
C {symbols/nfet_03v3.sym} 60 480 0 0 {name=MN2DP_4
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 300 -30 300 -70 {}
C {devices/lab_pin.sym} 300 -70 0 0 {name=l20 lab=DP_OUTINT}
N 300 30 300 70 {}
C {devices/lab_pin.sym} 300 70 0 0 {name=l21 lab=DP}
C {symbols/rm1.sym} 300 0 0 0 {name=RSERDP
W=2u
L=800u
model=rm1
spiceprefix=X
m=1
}
N 2520 -30 2520 -70 {}
C {devices/lab_pin.sym} 2520 -70 0 0 {name=ql57 lab=VDD}
N 2520 30 2520 70 {}
C {devices/lab_pin.sym} 2520 70 0 0 {name=ql58 lab=DM_PREP}
N 2480 0 2420 0 {}
C {devices/lab_pin.sym} 2420 0 0 0 {name=ql59 lab=TXDM}
N 2520 0 2580 0 {}
C {devices/lab_pin.sym} 2580 0 0 0 {name=ql60 lab=VDD}
C {symbols/pfet_03v3.sym} 2500 0 0 0 {name=MP1ADM
L=0.28u
W=8u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 2780 -30 2780 -70 {}
C {devices/lab_pin.sym} 2780 -70 0 0 {name=ql61 lab=VDD}
N 2780 30 2780 70 {}
C {devices/lab_pin.sym} 2780 70 0 0 {name=ql62 lab=DM_PREP}
N 2740 0 2680 0 {}
C {devices/lab_pin.sym} 2680 0 0 0 {name=ql63 lab=TXOE}
N 2780 0 2840 0 {}
C {devices/lab_pin.sym} 2840 0 0 0 {name=ql64 lab=VDD}
C {symbols/pfet_03v3.sym} 2760 0 0 0 {name=MP1BDM
L=0.28u
W=8u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 3040 -30 3040 -70 {}
C {devices/lab_pin.sym} 3040 -70 0 0 {name=ql65 lab=DM_PREP}
N 3040 30 3040 70 {}
C {devices/lab_pin.sym} 3040 70 0 0 {name=ql66 lab=DM_NX}
N 3000 0 2940 0 {}
C {devices/lab_pin.sym} 2940 0 0 0 {name=ql67 lab=TXDM}
N 3040 0 3100 0 {}
C {devices/lab_pin.sym} 3100 0 0 0 {name=ql68 lab=VSS}
C {symbols/nfet_03v3.sym} 3020 0 0 0 {name=MN1ADM
L=0.28u
W=5u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 3300 -30 3300 -70 {}
C {devices/lab_pin.sym} 3300 -70 0 0 {name=ql69 lab=DM_NX}
N 3300 30 3300 70 {}
C {devices/lab_pin.sym} 3300 70 0 0 {name=ql70 lab=VSS}
N 3260 0 3200 0 {}
C {devices/lab_pin.sym} 3200 0 0 0 {name=ql71 lab=TXOE}
N 3300 0 3360 0 {}
C {devices/lab_pin.sym} 3360 0 0 0 {name=ql72 lab=VSS}
C {symbols/nfet_03v3.sym} 3280 0 0 0 {name=MN1BDM
L=0.28u
W=5u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 3540 -30 3540 -70 {}
C {devices/lab_pin.sym} 3540 -70 0 0 {name=ql73 lab=DM_PREP}
N 3540 30 3540 70 {}
C {devices/lab_pin.sym} 3540 70 0 0 {name=ql74 lab=DM_GATEP}
N 3520 0 3460 0 {}
C {devices/lab_pin.sym} 3460 0 0 0 {name=ql75 lab=VSS}
C {symbols/ppolyf_u.sym} 3540 0 0 0 {name=RSLEWPDM
W=1u
L=2u
model=ppolyf_u
spiceprefix=X
m=1
}
N 2520 270 2520 230 {}
C {devices/lab_pin.sym} 2520 230 0 0 {name=ql76 lab=VDD}
N 2520 330 2520 370 {}
C {devices/lab_pin.sym} 2520 370 0 0 {name=ql77 lab=DM_PX}
N 2480 300 2420 300 {}
C {devices/lab_pin.sym} 2420 300 0 0 {name=ql78 lab=TXDM}
N 2520 300 2580 300 {}
C {devices/lab_pin.sym} 2580 300 0 0 {name=ql79 lab=VDD}
C {symbols/pfet_03v3.sym} 2500 300 0 0 {name=MP3ADM
L=0.28u
W=16u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 2780 270 2780 230 {}
C {devices/lab_pin.sym} 2780 230 0 0 {name=ql80 lab=DM_PX}
N 2780 330 2780 370 {}
C {devices/lab_pin.sym} 2780 370 0 0 {name=ql81 lab=DM_PREN}
N 2740 300 2680 300 {}
C {devices/lab_pin.sym} 2680 300 0 0 {name=ql82 lab=TXOEB}
N 2780 300 2840 300 {}
C {devices/lab_pin.sym} 2840 300 0 0 {name=ql83 lab=VDD}
C {symbols/pfet_03v3.sym} 2760 300 0 0 {name=MP3BDM
L=0.28u
W=16u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 3040 270 3040 230 {}
C {devices/lab_pin.sym} 3040 230 0 0 {name=ql84 lab=DM_PREN}
N 3040 330 3040 370 {}
C {devices/lab_pin.sym} 3040 370 0 0 {name=ql85 lab=VSS}
N 3000 300 2940 300 {}
C {devices/lab_pin.sym} 2940 300 0 0 {name=ql86 lab=TXDM}
N 3040 300 3100 300 {}
C {devices/lab_pin.sym} 3100 300 0 0 {name=ql87 lab=VSS}
C {symbols/nfet_03v3.sym} 3020 300 0 0 {name=MN3ADM
L=0.28u
W=2.5u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 3300 270 3300 230 {}
C {devices/lab_pin.sym} 3300 230 0 0 {name=ql88 lab=DM_PREN}
N 3300 330 3300 370 {}
C {devices/lab_pin.sym} 3300 370 0 0 {name=ql89 lab=VSS}
N 3260 300 3200 300 {}
C {devices/lab_pin.sym} 3200 300 0 0 {name=ql90 lab=TXOEB}
N 3300 300 3360 300 {}
C {devices/lab_pin.sym} 3360 300 0 0 {name=ql91 lab=VSS}
C {symbols/nfet_03v3.sym} 3280 300 0 0 {name=MN3BDM
L=0.28u
W=2.5u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 3540 270 3540 230 {}
C {devices/lab_pin.sym} 3540 230 0 0 {name=ql92 lab=DM_PREN}
N 3540 330 3540 370 {}
C {devices/lab_pin.sym} 3540 370 0 0 {name=ql93 lab=DM_GATEN}
N 3520 300 3460 300 {}
C {devices/lab_pin.sym} 3460 300 0 0 {name=ql94 lab=VSS}
C {symbols/ppolyf_u.sym} 3540 300 0 0 {name=RSLEWNDM
W=1u
L=2u
model=ppolyf_u
spiceprefix=X
m=1
}
N 1240 -30 1240 -70 {}
C {devices/lab_pin.sym} 1240 -70 0 0 {name=l33 lab=VDD}
N 1200 0 1140 0 {}
C {devices/lab_pin.sym} 1140 0 0 0 {name=l34 lab=DM_GATEP}
N 1240 30 1240 70 {}
C {devices/lab_pin.sym} 1240 70 0 0 {name=l35 lab=DM_OUTINT}
N 1240 0 1300 0 {}
C {devices/lab_pin.sym} 1300 0 0 0 {name=l36 lab=VDD}
C {symbols/pfet_03v3.sym} 1220 0 0 0 {name=MP2DM_1
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1240 130 1240 90 {}
C {devices/lab_pin.sym} 1240 90 0 0 {name=l67 lab=VDD}
N 1200 160 1140 160 {}
C {devices/lab_pin.sym} 1140 160 0 0 {name=l68 lab=DM_GATEP}
N 1240 190 1240 230 {}
C {devices/lab_pin.sym} 1240 230 0 0 {name=l69 lab=DM_OUTINT}
N 1240 160 1300 160 {}
C {devices/lab_pin.sym} 1300 160 0 0 {name=l70 lab=VDD}
C {symbols/pfet_03v3.sym} 1220 160 0 0 {name=MP2DM_2
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1240 290 1240 250 {}
C {devices/lab_pin.sym} 1240 250 0 0 {name=l71 lab=VDD}
N 1200 320 1140 320 {}
C {devices/lab_pin.sym} 1140 320 0 0 {name=l72 lab=DM_GATEP}
N 1240 350 1240 390 {}
C {devices/lab_pin.sym} 1240 390 0 0 {name=l73 lab=DM_OUTINT}
N 1240 320 1300 320 {}
C {devices/lab_pin.sym} 1300 320 0 0 {name=l74 lab=VDD}
C {symbols/pfet_03v3.sym} 1220 320 0 0 {name=MP2DM_3
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1240 450 1240 410 {}
C {devices/lab_pin.sym} 1240 410 0 0 {name=l75 lab=VDD}
N 1200 480 1140 480 {}
C {devices/lab_pin.sym} 1140 480 0 0 {name=l76 lab=DM_GATEP}
N 1240 510 1240 550 {}
C {devices/lab_pin.sym} 1240 550 0 0 {name=l77 lab=DM_OUTINT}
N 1240 480 1300 480 {}
C {devices/lab_pin.sym} 1300 480 0 0 {name=l78 lab=VDD}
C {symbols/pfet_03v3.sym} 1220 480 0 0 {name=MP2DM_4
L=0.28u
W=80u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1480 30 1480 70 {}
C {devices/lab_pin.sym} 1480 70 0 0 {name=l37 lab=VSS}
N 1440 0 1380 0 {}
C {devices/lab_pin.sym} 1380 0 0 0 {name=l38 lab=DM_GATEN}
N 1480 -30 1480 -70 {}
C {devices/lab_pin.sym} 1480 -70 0 0 {name=l39 lab=DM_OUTINT}
N 1480 0 1540 0 {}
C {devices/lab_pin.sym} 1540 0 0 0 {name=l40 lab=VSS}
C {symbols/nfet_03v3.sym} 1460 0 0 0 {name=MN2DM_1
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 1480 190 1480 230 {}
C {devices/lab_pin.sym} 1480 230 0 0 {name=l79 lab=VSS}
N 1440 160 1380 160 {}
C {devices/lab_pin.sym} 1380 160 0 0 {name=l80 lab=DM_GATEN}
N 1480 130 1480 90 {}
C {devices/lab_pin.sym} 1480 90 0 0 {name=l81 lab=DM_OUTINT}
N 1480 160 1540 160 {}
C {devices/lab_pin.sym} 1540 160 0 0 {name=l82 lab=VSS}
C {symbols/nfet_03v3.sym} 1460 160 0 0 {name=MN2DM_2
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 1480 350 1480 390 {}
C {devices/lab_pin.sym} 1480 390 0 0 {name=l83 lab=VSS}
N 1440 320 1380 320 {}
C {devices/lab_pin.sym} 1380 320 0 0 {name=l84 lab=DM_GATEN}
N 1480 290 1480 250 {}
C {devices/lab_pin.sym} 1480 250 0 0 {name=l85 lab=DM_OUTINT}
N 1480 320 1540 320 {}
C {devices/lab_pin.sym} 1540 320 0 0 {name=l86 lab=VSS}
C {symbols/nfet_03v3.sym} 1460 320 0 0 {name=MN2DM_3
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 1480 510 1480 550 {}
C {devices/lab_pin.sym} 1480 550 0 0 {name=l87 lab=VSS}
N 1440 480 1380 480 {}
C {devices/lab_pin.sym} 1380 480 0 0 {name=l88 lab=DM_GATEN}
N 1480 450 1480 410 {}
C {devices/lab_pin.sym} 1480 410 0 0 {name=l89 lab=DM_OUTINT}
N 1480 480 1540 480 {}
C {devices/lab_pin.sym} 1540 480 0 0 {name=l90 lab=VSS}
C {symbols/nfet_03v3.sym} 1460 480 0 0 {name=MN2DM_4
L=0.28u
W=30u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 1700 -30 1700 -70 {}
C {devices/lab_pin.sym} 1700 -70 0 0 {name=l41 lab=DM_OUTINT}
N 1700 30 1700 70 {}
C {devices/lab_pin.sym} 1700 70 0 0 {name=l42 lab=DM}
C {symbols/rm1.sym} 1700 0 0 0 {name=RSERDM
W=2u
L=800u
model=rm1
spiceprefix=X
m=1
}
N -1200 -400 -1160 -400 {lab=VDD}
C {devices/iopin.sym} -1200 -400 0 0 {name=p_vdd lab=VDD}
N -1200 -340 -1160 -340 {lab=VSS}
C {devices/iopin.sym} -1200 -340 0 0 {name=p_vss lab=VSS}
N -1200 -280 -1240 -280 {lab=TXDP}
C {devices/ipin.sym} -1200 -280 0 1 {name=p_txdp lab=TXDP}
N -1200 -220 -1240 -220 {lab=TXDM}
C {devices/ipin.sym} -1200 -220 0 1 {name=p_txdm lab=TXDM}
N -1200 -160 -1240 -160 {}
C {devices/ipin.sym} -1200 -160 0 1 {name=p_txoe lab=TXOE}
N 1600 -280 1640 -280 {lab=DP}
C {devices/iopin.sym} 1600 -280 0 0 {name=p_dp lab=DP}
N 1600 -220 1640 -220 {lab=DM}
C {devices/iopin.sym} 1600 -220 0 0 {name=p_dm lab=DM}
