v {xschem version=3.4.7 file_version=1.2}
G {}
K {}
V {}
S {}
E {}
T {dplus_pullup -- integrated D+ speed-signaling pull-up (spec Sec.5)
1.5k nominal, target +/-5% (1.425-1.575k) across the full PVT envelope
(spec Sec.7 / Sec.8.1), enable-controlled for soft-connect/soft-disconnect.

DESIGN CHOICE (this cell): a binary-weighted TRIM LADDER, not active
regulation. gf180mcu poly resistors are not inherently +/-5% across
process on their own (ppolyf_u rsh=350 +/-20% per
libs.tech/ngspice/sm141064.ngspice's ss/ff .lib sections) -- a bare
untrimmed resistor cannot meet the target (spec Sec.5's own flag).
A trim ladder was chosen over an active (servo/reference) regulation
scheme because it needs no on-chip voltage/current reference of its
own (this repo has no bandgap block in scope -- CLAUDE.md's scope
discipline), no feedback loop stability concern, and is a one-time
test-time operation (trim code held in whatever OTP/fuse/scan
mechanism the integrator's test flow uses -- out of scope for this
schematic, same boundary treatment as PU_EN itself: TRIM<4:0> are
presented here purely as digital control inputs).

VPU_REG (the 'internally regulated 3.0-3.6V' rail of spec Sec.5) is an
INPUT to this cell, assumed supplied by an upstream regulator block --
not built here (out of scope for #30; that regulator, if it does not
already exist elsewhere in this repo, is a natural follow-up issue).} -1400 -900 0 0 0.32 0.32 {}
T {Trim math (first-order sheet-rho-only argument -- NOT a PVT-verified
claim; #26 owns verification). All resistors: ppolyf_u, W=4u, nominal
rsh=350 ohm/sq (L sized per R=rsh*L/W).
  R_BASE = 1000 ohm  (L=11.43u)
  5-bit binary ladder, LSB=30 ohm: R0=30 R1=60 R2=120 R3=240 R4=480
    (L = 0.343u / 0.686u / 1.371u / 2.743u / 5.486u)
  total additive range: 0-930 ohm (31 codes, ~2% of nominal per LSB)
Let f = process sheet-rho factor relative to typical (observed spread
~0.8-1.2 from the ss/ff .lib corners above; R_BASE and every trim
segment are the same poly flavour so they all scale by the same f).
Achievable range at a given corner: [R_BASE*f, (R_BASE+930)*f].
  f=1.2 (slow/high-R corner): [1200, 2316]  -- contains [1425,1575]
  f=1.0 (typical):            [1000, 1930]  -- contains [1425,1575]
  f=0.8 (fast/low-R corner):  [800,  1544]  -- contains [1425,1575]
so a trim code exists at every corner that lands inside the +/-5%
band; 30 ohm LSB (~2% of nominal) leaves headroom under the 75 ohm
(+/-5%) tolerance window. This argument covers sheet-rho spread only,
not temperature/voltage/mismatch -- #26's PVT sweep is what turns
this from design intent into a verified claim.} -1400 -650 0 0 0.28 0.28 {}
T {Enable + trim polarity: PU_EN/TRIM<4:0> are active-high digital inputs.
Each drives a small CMOS inverter (supplied from VPU_REG/VSS) whose
output gates a PMOS pass switch referenced to VPU_REG (source/well tied
to VPU_REG, so no body-diode forward-bias risk while D+ sits near its
pulled-up level). TRIM<i>=1 => switch ON => segment i bypassed/shorted
(removed from the series path); TRIM<i>=0 => switch OFF => segment
included. Untrimmed/unprogrammed default (all-0, the typical OTP/fuse
power-up state) therefore yields MAXIMUM series resistance (weakest,
safest pull-up) rather than minimum -- a deliberate fail-safe choice.} -1400 -420 0 0 0.28 0.28 {}
N -980 -630 -980 -670 {}
C {devices/lab_pin.sym} -980 -670 0 0 {name=l1 lab=VPU_REG}
N -1020 -600 -1080 -600 {}
C {devices/lab_pin.sym} -1080 -600 0 0 {name=l2 lab=PU_EN}
N -980 -570 -980 -530 {}
C {devices/lab_pin.sym} -980 -530 0 0 {name=l3 lab=PU_ENB}
N -980 -600 -920 -600 {}
C {devices/lab_pin.sym} -920 -600 0 0 {name=l4 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -1000 -600 0 0 {name=MP_EN
L=0.28u
W=2u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -740 -570 -740 -530 {}
C {devices/lab_pin.sym} -740 -530 0 0 {name=l5 lab=VSS}
N -780 -600 -840 -600 {}
C {devices/lab_pin.sym} -840 -600 0 0 {name=l6 lab=PU_EN}
N -740 -630 -740 -670 {}
C {devices/lab_pin.sym} -740 -670 0 0 {name=l7 lab=PU_ENB}
N -740 -600 -680 -600 {}
C {devices/lab_pin.sym} -680 -600 0 0 {name=l8 lab=VSS}
C {symbols/nfet_03v3.sym} -760 -600 0 0 {name=MN_EN
L=0.28u
W=1u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -480 -630 -480 -670 {}
C {devices/lab_pin.sym} -480 -670 0 0 {name=l9 lab=VPU_REG}
N -520 -600 -580 -600 {}
C {devices/lab_pin.sym} -580 -600 0 0 {name=l10 lab=TRIM0}
N -480 -570 -480 -530 {}
C {devices/lab_pin.sym} -480 -530 0 0 {name=l11 lab=TRIM0B}
N -480 -600 -420 -600 {}
C {devices/lab_pin.sym} -420 -600 0 0 {name=l12 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -500 -600 0 0 {name=MP_T0
L=0.28u
W=2u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -240 -570 -240 -530 {}
C {devices/lab_pin.sym} -240 -530 0 0 {name=l13 lab=VSS}
N -280 -600 -340 -600 {}
C {devices/lab_pin.sym} -340 -600 0 0 {name=l14 lab=TRIM0}
N -240 -630 -240 -670 {}
C {devices/lab_pin.sym} -240 -670 0 0 {name=l15 lab=TRIM0B}
N -240 -600 -180 -600 {}
C {devices/lab_pin.sym} -180 -600 0 0 {name=l16 lab=VSS}
C {symbols/nfet_03v3.sym} -260 -600 0 0 {name=MN_T0
L=0.28u
W=1u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 20 -630 20 -670 {}
C {devices/lab_pin.sym} 20 -670 0 0 {name=l17 lab=VPU_REG}
N -20 -600 -80 -600 {}
C {devices/lab_pin.sym} -80 -600 0 0 {name=l18 lab=TRIM1}
N 20 -570 20 -530 {}
C {devices/lab_pin.sym} 20 -530 0 0 {name=l19 lab=TRIM1B}
N 20 -600 80 -600 {}
C {devices/lab_pin.sym} 80 -600 0 0 {name=l20 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 0 -600 0 0 {name=MP_T1
L=0.28u
W=2u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 260 -570 260 -530 {}
C {devices/lab_pin.sym} 260 -530 0 0 {name=l21 lab=VSS}
N 220 -600 160 -600 {}
C {devices/lab_pin.sym} 160 -600 0 0 {name=l22 lab=TRIM1}
N 260 -630 260 -670 {}
C {devices/lab_pin.sym} 260 -670 0 0 {name=l23 lab=TRIM1B}
N 260 -600 320 -600 {}
C {devices/lab_pin.sym} 320 -600 0 0 {name=l24 lab=VSS}
C {symbols/nfet_03v3.sym} 240 -600 0 0 {name=MN_T1
L=0.28u
W=1u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 520 -630 520 -670 {}
C {devices/lab_pin.sym} 520 -670 0 0 {name=l25 lab=VPU_REG}
N 480 -600 420 -600 {}
C {devices/lab_pin.sym} 420 -600 0 0 {name=l26 lab=TRIM2}
N 520 -570 520 -530 {}
C {devices/lab_pin.sym} 520 -530 0 0 {name=l27 lab=TRIM2B}
N 520 -600 580 -600 {}
C {devices/lab_pin.sym} 580 -600 0 0 {name=l28 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 500 -600 0 0 {name=MP_T2
L=0.28u
W=2u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 760 -570 760 -530 {}
C {devices/lab_pin.sym} 760 -530 0 0 {name=l29 lab=VSS}
N 720 -600 660 -600 {}
C {devices/lab_pin.sym} 660 -600 0 0 {name=l30 lab=TRIM2}
N 760 -630 760 -670 {}
C {devices/lab_pin.sym} 760 -670 0 0 {name=l31 lab=TRIM2B}
N 760 -600 820 -600 {}
C {devices/lab_pin.sym} 820 -600 0 0 {name=l32 lab=VSS}
C {symbols/nfet_03v3.sym} 740 -600 0 0 {name=MN_T2
L=0.28u
W=1u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 1020 -630 1020 -670 {}
C {devices/lab_pin.sym} 1020 -670 0 0 {name=l33 lab=VPU_REG}
N 980 -600 920 -600 {}
C {devices/lab_pin.sym} 920 -600 0 0 {name=l34 lab=TRIM3}
N 1020 -570 1020 -530 {}
C {devices/lab_pin.sym} 1020 -530 0 0 {name=l35 lab=TRIM3B}
N 1020 -600 1080 -600 {}
C {devices/lab_pin.sym} 1080 -600 0 0 {name=l36 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 1000 -600 0 0 {name=MP_T3
L=0.28u
W=2u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1260 -570 1260 -530 {}
C {devices/lab_pin.sym} 1260 -530 0 0 {name=l37 lab=VSS}
N 1220 -600 1160 -600 {}
C {devices/lab_pin.sym} 1160 -600 0 0 {name=l38 lab=TRIM3}
N 1260 -630 1260 -670 {}
C {devices/lab_pin.sym} 1260 -670 0 0 {name=l39 lab=TRIM3B}
N 1260 -600 1320 -600 {}
C {devices/lab_pin.sym} 1320 -600 0 0 {name=l40 lab=VSS}
C {symbols/nfet_03v3.sym} 1240 -600 0 0 {name=MN_T3
L=0.28u
W=1u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N 1520 -630 1520 -670 {}
C {devices/lab_pin.sym} 1520 -670 0 0 {name=l41 lab=VPU_REG}
N 1480 -600 1420 -600 {}
C {devices/lab_pin.sym} 1420 -600 0 0 {name=l42 lab=TRIM4}
N 1520 -570 1520 -530 {}
C {devices/lab_pin.sym} 1520 -530 0 0 {name=l43 lab=TRIM4B}
N 1520 -600 1580 -600 {}
C {devices/lab_pin.sym} 1580 -600 0 0 {name=l44 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 1500 -600 0 0 {name=MP_T4
L=0.28u
W=2u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 1760 -570 1760 -530 {}
C {devices/lab_pin.sym} 1760 -530 0 0 {name=l45 lab=VSS}
N 1720 -600 1660 -600 {}
C {devices/lab_pin.sym} 1660 -600 0 0 {name=l46 lab=TRIM4}
N 1760 -630 1760 -670 {}
C {devices/lab_pin.sym} 1760 -670 0 0 {name=l47 lab=TRIM4B}
N 1760 -600 1820 -600 {}
C {devices/lab_pin.sym} 1820 -600 0 0 {name=l48 lab=VSS}
C {symbols/nfet_03v3.sym} 1740 -600 0 0 {name=MN_T4
L=0.28u
W=1u
nf=1
m=1
model=nfet_03v3
spiceprefix=X
}
N -980 -330 -980 -370 {}
C {devices/lab_pin.sym} -980 -370 0 0 {name=l49 lab=VPU_REG}
N -1020 -300 -1080 -300 {}
C {devices/lab_pin.sym} -1080 -300 0 0 {name=l50 lab=PU_ENB}
N -980 -270 -980 -230 {}
C {devices/lab_pin.sym} -980 -230 0 0 {name=l51 lab=NODE0}
N -980 -300 -920 -300 {}
C {devices/lab_pin.sym} -920 -300 0 0 {name=l52 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -1000 -300 0 0 {name=MEN
L=0.28u
W=1000u
nf=10
m=1
model=pfet_03v3
spiceprefix=X
}
N -400 -330 -400 -370 {}
C {devices/lab_pin.sym} -400 -370 0 0 {name=l53 lab=NODE0}
N -400 -270 -400 -230 {}
C {devices/lab_pin.sym} -400 -230 0 0 {name=l54 lab=NODE1}
N -420 -300 -480 -300 {}
C {devices/lab_pin.sym} -480 -300 0 0 {name=l55 lab=VSS}
C {symbols/ppolyf_u.sym} -400 -300 0 0 {name=RBASE
W=4u
L=11.43u
model=ppolyf_u
spiceprefix=X
m=1
}
N 200 -330 200 -370 {}
C {devices/lab_pin.sym} 200 -370 0 0 {name=l56 lab=NODE1}
N 200 -270 200 -230 {}
C {devices/lab_pin.sym} 200 -230 0 0 {name=l57 lab=NODE2}
N 180 -300 120 -300 {}
C {devices/lab_pin.sym} 120 -300 0 0 {name=l58 lab=VSS}
C {symbols/ppolyf_u.sym} 200 -300 0 0 {name=R0
W=4u
L=0.343u
model=ppolyf_u
spiceprefix=X
m=1
}
N 220 -170 220 -210 {}
C {devices/lab_pin.sym} 220 -210 0 0 {name=l59 lab=NODE1}
N 180 -140 120 -140 {}
C {devices/lab_pin.sym} 120 -140 0 0 {name=l60 lab=TRIM0B}
N 220 -110 220 -70 {}
C {devices/lab_pin.sym} 220 -70 0 0 {name=l61 lab=NODE2}
N 220 -140 280 -140 {}
C {devices/lab_pin.sym} 280 -140 0 0 {name=l62 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 200 -140 0 0 {name=MSW0
L=0.28u
W=1000u
nf=10
m=1
model=pfet_03v3
spiceprefix=X
}
N 700 -330 700 -370 {}
C {devices/lab_pin.sym} 700 -370 0 0 {name=l63 lab=NODE2}
N 700 -270 700 -230 {}
C {devices/lab_pin.sym} 700 -230 0 0 {name=l64 lab=NODE3}
N 680 -300 620 -300 {}
C {devices/lab_pin.sym} 620 -300 0 0 {name=l65 lab=VSS}
C {symbols/ppolyf_u.sym} 700 -300 0 0 {name=R1
W=4u
L=0.686u
model=ppolyf_u
spiceprefix=X
m=1
}
N 720 -170 720 -210 {}
C {devices/lab_pin.sym} 720 -210 0 0 {name=l66 lab=NODE2}
N 680 -140 620 -140 {}
C {devices/lab_pin.sym} 620 -140 0 0 {name=l67 lab=TRIM1B}
N 720 -110 720 -70 {}
C {devices/lab_pin.sym} 720 -70 0 0 {name=l68 lab=NODE3}
N 720 -140 780 -140 {}
C {devices/lab_pin.sym} 780 -140 0 0 {name=l69 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 700 -140 0 0 {name=MSW1
L=0.28u
W=1000u
nf=10
m=1
model=pfet_03v3
spiceprefix=X
}
N 1200 -330 1200 -370 {}
C {devices/lab_pin.sym} 1200 -370 0 0 {name=l70 lab=NODE3}
N 1200 -270 1200 -230 {}
C {devices/lab_pin.sym} 1200 -230 0 0 {name=l71 lab=NODE4}
N 1180 -300 1120 -300 {}
C {devices/lab_pin.sym} 1120 -300 0 0 {name=l72 lab=VSS}
C {symbols/ppolyf_u.sym} 1200 -300 0 0 {name=R2
W=4u
L=1.371u
model=ppolyf_u
spiceprefix=X
m=1
}
N 1220 -170 1220 -210 {}
C {devices/lab_pin.sym} 1220 -210 0 0 {name=l73 lab=NODE3}
N 1180 -140 1120 -140 {}
C {devices/lab_pin.sym} 1120 -140 0 0 {name=l74 lab=TRIM2B}
N 1220 -110 1220 -70 {}
C {devices/lab_pin.sym} 1220 -70 0 0 {name=l75 lab=NODE4}
N 1220 -140 1280 -140 {}
C {devices/lab_pin.sym} 1280 -140 0 0 {name=l76 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 1200 -140 0 0 {name=MSW2
L=0.28u
W=1000u
nf=10
m=1
model=pfet_03v3
spiceprefix=X
}
N 1700 -330 1700 -370 {}
C {devices/lab_pin.sym} 1700 -370 0 0 {name=l77 lab=NODE4}
N 1700 -270 1700 -230 {}
C {devices/lab_pin.sym} 1700 -230 0 0 {name=l78 lab=NODE5}
N 1680 -300 1620 -300 {}
C {devices/lab_pin.sym} 1620 -300 0 0 {name=l79 lab=VSS}
C {symbols/ppolyf_u.sym} 1700 -300 0 0 {name=R3
W=4u
L=2.743u
model=ppolyf_u
spiceprefix=X
m=1
}
N 1720 -170 1720 -210 {}
C {devices/lab_pin.sym} 1720 -210 0 0 {name=l80 lab=NODE4}
N 1680 -140 1620 -140 {}
C {devices/lab_pin.sym} 1620 -140 0 0 {name=l81 lab=TRIM3B}
N 1720 -110 1720 -70 {}
C {devices/lab_pin.sym} 1720 -70 0 0 {name=l82 lab=NODE5}
N 1720 -140 1780 -140 {}
C {devices/lab_pin.sym} 1780 -140 0 0 {name=l83 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 1700 -140 0 0 {name=MSW3
L=0.28u
W=1000u
nf=10
m=1
model=pfet_03v3
spiceprefix=X
}
N 2200 -330 2200 -370 {}
C {devices/lab_pin.sym} 2200 -370 0 0 {name=l84 lab=NODE5}
N 2200 -270 2200 -230 {}
C {devices/lab_pin.sym} 2200 -230 0 0 {name=l85 lab=DP}
N 2180 -300 2120 -300 {}
C {devices/lab_pin.sym} 2120 -300 0 0 {name=l86 lab=VSS}
C {symbols/ppolyf_u.sym} 2200 -300 0 0 {name=R4
W=4u
L=5.486u
model=ppolyf_u
spiceprefix=X
m=1
}
N 2220 -170 2220 -210 {}
C {devices/lab_pin.sym} 2220 -210 0 0 {name=l87 lab=NODE5}
N 2180 -140 2120 -140 {}
C {devices/lab_pin.sym} 2120 -140 0 0 {name=l88 lab=TRIM4B}
N 2220 -110 2220 -70 {}
C {devices/lab_pin.sym} 2220 -70 0 0 {name=l89 lab=DP}
N 2220 -140 2280 -140 {}
C {devices/lab_pin.sym} 2280 -140 0 0 {name=l90 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 2200 -140 0 0 {name=MSW4
L=0.28u
W=1000u
nf=10
m=1
model=pfet_03v3
spiceprefix=X
}
N 2400 -200 2440 -200 {lab=DP}
C {devices/iopin.sym} 2400 -200 0 0 {name=p_dp lab=DP}
N -1400 -200 -1440 -200 {lab=VPU_REG}
C {devices/ipin.sym} -1400 -200 0 1 {name=p_vpu lab=VPU_REG}
N -1400 -140 -1360 -140 {lab=VSS}
C {devices/iopin.sym} -1400 -140 0 0 {name=p_vss lab=VSS}
N -1400 -80 -1440 -80 {lab=PU_EN}
C {devices/ipin.sym} -1400 -80 0 1 {name=p_en lab=PU_EN}
N -1400 -20 -1440 -20 {lab=TRIM0}
C {devices/ipin.sym} -1400 -20 0 1 {name=p_trim0 lab=TRIM0}
N -1400 40 -1440 40 {lab=TRIM1}
C {devices/ipin.sym} -1400 40 0 1 {name=p_trim1 lab=TRIM1}
N -1400 100 -1440 100 {lab=TRIM2}
C {devices/ipin.sym} -1400 100 0 1 {name=p_trim2 lab=TRIM2}
N -1400 160 -1440 160 {lab=TRIM3}
C {devices/ipin.sym} -1400 160 0 1 {name=p_trim3 lab=TRIM3}
N -1400 220 -1440 220 {lab=TRIM4}
C {devices/ipin.sym} -1400 220 0 1 {name=p_trim4 lab=TRIM4}
