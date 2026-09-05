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
T {FLATTENED SWITCH ARRAY (issue #56, operator ruling 2026-09-05).
Each of the six W=1000u pull-up switch devices below was previously drawn
as a single nf=10 instance. It is now drawn as 10 separate one-finger
devices of W=100u in parallel -- one device per drawn gate -- because klt's
subckt-call -> plain-element netlist conversion (the ingestion path used by
klt layout-plan and klt lvs) refuses to represent a multi-finger device and
its own error text prescribes exactly this transformation. Total drawn gate
width per switch is unchanged (10 x 100u = 1000u). Upstream tool gap:
klayout-tools#1487; if native nf expansion lands, a future decision record
may restore the idiomatic nf=10 form. Equivalence is measured, not assumed --
see sim/dplus-pullup-tolerance/records/ and spec/usb2-device-phy.md Sec.12.} -1400 380 0 0 0.28 0.28 {}
N -1380 470 -1380 430 {}
C {devices/lab_pin.sym} -1380 430 0 0 {name=l100 lab=VPU_REG}
N -1420 500 -1460 500 {}
C {devices/lab_pin.sym} -1460 500 0 0 {name=l101 lab=PU_ENB}
N -1380 530 -1380 570 {}
C {devices/lab_pin.sym} -1380 570 0 0 {name=l102 lab=NODE0}
N -1380 500 -1340 500 {}
C {devices/lab_pin.sym} -1340 500 0 0 {name=l103 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -1400 500 0 0 {name=MEN_F0
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -1120 470 -1120 430 {}
C {devices/lab_pin.sym} -1120 430 0 0 {name=l104 lab=VPU_REG}
N -1160 500 -1200 500 {}
C {devices/lab_pin.sym} -1200 500 0 0 {name=l105 lab=PU_ENB}
N -1120 530 -1120 570 {}
C {devices/lab_pin.sym} -1120 570 0 0 {name=l106 lab=NODE0}
N -1120 500 -1080 500 {}
C {devices/lab_pin.sym} -1080 500 0 0 {name=l107 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -1140 500 0 0 {name=MEN_F1
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -860 470 -860 430 {}
C {devices/lab_pin.sym} -860 430 0 0 {name=l108 lab=VPU_REG}
N -900 500 -940 500 {}
C {devices/lab_pin.sym} -940 500 0 0 {name=l109 lab=PU_ENB}
N -860 530 -860 570 {}
C {devices/lab_pin.sym} -860 570 0 0 {name=l110 lab=NODE0}
N -860 500 -820 500 {}
C {devices/lab_pin.sym} -820 500 0 0 {name=l111 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -880 500 0 0 {name=MEN_F2
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -600 470 -600 430 {}
C {devices/lab_pin.sym} -600 430 0 0 {name=l112 lab=VPU_REG}
N -640 500 -680 500 {}
C {devices/lab_pin.sym} -680 500 0 0 {name=l113 lab=PU_ENB}
N -600 530 -600 570 {}
C {devices/lab_pin.sym} -600 570 0 0 {name=l114 lab=NODE0}
N -600 500 -560 500 {}
C {devices/lab_pin.sym} -560 500 0 0 {name=l115 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -620 500 0 0 {name=MEN_F3
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -340 470 -340 430 {}
C {devices/lab_pin.sym} -340 430 0 0 {name=l116 lab=VPU_REG}
N -380 500 -420 500 {}
C {devices/lab_pin.sym} -420 500 0 0 {name=l117 lab=PU_ENB}
N -340 530 -340 570 {}
C {devices/lab_pin.sym} -340 570 0 0 {name=l118 lab=NODE0}
N -340 500 -300 500 {}
C {devices/lab_pin.sym} -300 500 0 0 {name=l119 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -360 500 0 0 {name=MEN_F4
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -80 470 -80 430 {}
C {devices/lab_pin.sym} -80 430 0 0 {name=l120 lab=VPU_REG}
N -120 500 -160 500 {}
C {devices/lab_pin.sym} -160 500 0 0 {name=l121 lab=PU_ENB}
N -80 530 -80 570 {}
C {devices/lab_pin.sym} -80 570 0 0 {name=l122 lab=NODE0}
N -80 500 -40 500 {}
C {devices/lab_pin.sym} -40 500 0 0 {name=l123 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -100 500 0 0 {name=MEN_F5
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 180 470 180 430 {}
C {devices/lab_pin.sym} 180 430 0 0 {name=l124 lab=VPU_REG}
N 140 500 100 500 {}
C {devices/lab_pin.sym} 100 500 0 0 {name=l125 lab=PU_ENB}
N 180 530 180 570 {}
C {devices/lab_pin.sym} 180 570 0 0 {name=l126 lab=NODE0}
N 180 500 220 500 {}
C {devices/lab_pin.sym} 220 500 0 0 {name=l127 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 160 500 0 0 {name=MEN_F6
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 440 470 440 430 {}
C {devices/lab_pin.sym} 440 430 0 0 {name=l128 lab=VPU_REG}
N 400 500 360 500 {}
C {devices/lab_pin.sym} 360 500 0 0 {name=l129 lab=PU_ENB}
N 440 530 440 570 {}
C {devices/lab_pin.sym} 440 570 0 0 {name=l130 lab=NODE0}
N 440 500 480 500 {}
C {devices/lab_pin.sym} 480 500 0 0 {name=l131 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 420 500 0 0 {name=MEN_F7
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 700 470 700 430 {}
C {devices/lab_pin.sym} 700 430 0 0 {name=l132 lab=VPU_REG}
N 660 500 620 500 {}
C {devices/lab_pin.sym} 620 500 0 0 {name=l133 lab=PU_ENB}
N 700 530 700 570 {}
C {devices/lab_pin.sym} 700 570 0 0 {name=l134 lab=NODE0}
N 700 500 740 500 {}
C {devices/lab_pin.sym} 740 500 0 0 {name=l135 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 680 500 0 0 {name=MEN_F8
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 960 470 960 430 {}
C {devices/lab_pin.sym} 960 430 0 0 {name=l136 lab=VPU_REG}
N 920 500 880 500 {}
C {devices/lab_pin.sym} 880 500 0 0 {name=l137 lab=PU_ENB}
N 960 530 960 570 {}
C {devices/lab_pin.sym} 960 570 0 0 {name=l138 lab=NODE0}
N 960 500 1000 500 {}
C {devices/lab_pin.sym} 1000 500 0 0 {name=l139 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 940 500 0 0 {name=MEN_F9
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -1380 770 -1380 730 {}
C {devices/lab_pin.sym} -1380 730 0 0 {name=l140 lab=NODE1}
N -1420 800 -1460 800 {}
C {devices/lab_pin.sym} -1460 800 0 0 {name=l141 lab=TRIM0B}
N -1380 830 -1380 870 {}
C {devices/lab_pin.sym} -1380 870 0 0 {name=l142 lab=NODE2}
N -1380 800 -1340 800 {}
C {devices/lab_pin.sym} -1340 800 0 0 {name=l143 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -1400 800 0 0 {name=MSW0_F0
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -1120 770 -1120 730 {}
C {devices/lab_pin.sym} -1120 730 0 0 {name=l144 lab=NODE1}
N -1160 800 -1200 800 {}
C {devices/lab_pin.sym} -1200 800 0 0 {name=l145 lab=TRIM0B}
N -1120 830 -1120 870 {}
C {devices/lab_pin.sym} -1120 870 0 0 {name=l146 lab=NODE2}
N -1120 800 -1080 800 {}
C {devices/lab_pin.sym} -1080 800 0 0 {name=l147 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -1140 800 0 0 {name=MSW0_F1
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -860 770 -860 730 {}
C {devices/lab_pin.sym} -860 730 0 0 {name=l148 lab=NODE1}
N -900 800 -940 800 {}
C {devices/lab_pin.sym} -940 800 0 0 {name=l149 lab=TRIM0B}
N -860 830 -860 870 {}
C {devices/lab_pin.sym} -860 870 0 0 {name=l150 lab=NODE2}
N -860 800 -820 800 {}
C {devices/lab_pin.sym} -820 800 0 0 {name=l151 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -880 800 0 0 {name=MSW0_F2
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -600 770 -600 730 {}
C {devices/lab_pin.sym} -600 730 0 0 {name=l152 lab=NODE1}
N -640 800 -680 800 {}
C {devices/lab_pin.sym} -680 800 0 0 {name=l153 lab=TRIM0B}
N -600 830 -600 870 {}
C {devices/lab_pin.sym} -600 870 0 0 {name=l154 lab=NODE2}
N -600 800 -560 800 {}
C {devices/lab_pin.sym} -560 800 0 0 {name=l155 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -620 800 0 0 {name=MSW0_F3
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -340 770 -340 730 {}
C {devices/lab_pin.sym} -340 730 0 0 {name=l156 lab=NODE1}
N -380 800 -420 800 {}
C {devices/lab_pin.sym} -420 800 0 0 {name=l157 lab=TRIM0B}
N -340 830 -340 870 {}
C {devices/lab_pin.sym} -340 870 0 0 {name=l158 lab=NODE2}
N -340 800 -300 800 {}
C {devices/lab_pin.sym} -300 800 0 0 {name=l159 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -360 800 0 0 {name=MSW0_F4
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -80 770 -80 730 {}
C {devices/lab_pin.sym} -80 730 0 0 {name=l160 lab=NODE1}
N -120 800 -160 800 {}
C {devices/lab_pin.sym} -160 800 0 0 {name=l161 lab=TRIM0B}
N -80 830 -80 870 {}
C {devices/lab_pin.sym} -80 870 0 0 {name=l162 lab=NODE2}
N -80 800 -40 800 {}
C {devices/lab_pin.sym} -40 800 0 0 {name=l163 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -100 800 0 0 {name=MSW0_F5
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 180 770 180 730 {}
C {devices/lab_pin.sym} 180 730 0 0 {name=l164 lab=NODE1}
N 140 800 100 800 {}
C {devices/lab_pin.sym} 100 800 0 0 {name=l165 lab=TRIM0B}
N 180 830 180 870 {}
C {devices/lab_pin.sym} 180 870 0 0 {name=l166 lab=NODE2}
N 180 800 220 800 {}
C {devices/lab_pin.sym} 220 800 0 0 {name=l167 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 160 800 0 0 {name=MSW0_F6
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 440 770 440 730 {}
C {devices/lab_pin.sym} 440 730 0 0 {name=l168 lab=NODE1}
N 400 800 360 800 {}
C {devices/lab_pin.sym} 360 800 0 0 {name=l169 lab=TRIM0B}
N 440 830 440 870 {}
C {devices/lab_pin.sym} 440 870 0 0 {name=l170 lab=NODE2}
N 440 800 480 800 {}
C {devices/lab_pin.sym} 480 800 0 0 {name=l171 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 420 800 0 0 {name=MSW0_F7
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 700 770 700 730 {}
C {devices/lab_pin.sym} 700 730 0 0 {name=l172 lab=NODE1}
N 660 800 620 800 {}
C {devices/lab_pin.sym} 620 800 0 0 {name=l173 lab=TRIM0B}
N 700 830 700 870 {}
C {devices/lab_pin.sym} 700 870 0 0 {name=l174 lab=NODE2}
N 700 800 740 800 {}
C {devices/lab_pin.sym} 740 800 0 0 {name=l175 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 680 800 0 0 {name=MSW0_F8
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 960 770 960 730 {}
C {devices/lab_pin.sym} 960 730 0 0 {name=l176 lab=NODE1}
N 920 800 880 800 {}
C {devices/lab_pin.sym} 880 800 0 0 {name=l177 lab=TRIM0B}
N 960 830 960 870 {}
C {devices/lab_pin.sym} 960 870 0 0 {name=l178 lab=NODE2}
N 960 800 1000 800 {}
C {devices/lab_pin.sym} 1000 800 0 0 {name=l179 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 940 800 0 0 {name=MSW0_F9
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -1380 1070 -1380 1030 {}
C {devices/lab_pin.sym} -1380 1030 0 0 {name=l180 lab=NODE2}
N -1420 1100 -1460 1100 {}
C {devices/lab_pin.sym} -1460 1100 0 0 {name=l181 lab=TRIM1B}
N -1380 1130 -1380 1170 {}
C {devices/lab_pin.sym} -1380 1170 0 0 {name=l182 lab=NODE3}
N -1380 1100 -1340 1100 {}
C {devices/lab_pin.sym} -1340 1100 0 0 {name=l183 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -1400 1100 0 0 {name=MSW1_F0
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -1120 1070 -1120 1030 {}
C {devices/lab_pin.sym} -1120 1030 0 0 {name=l184 lab=NODE2}
N -1160 1100 -1200 1100 {}
C {devices/lab_pin.sym} -1200 1100 0 0 {name=l185 lab=TRIM1B}
N -1120 1130 -1120 1170 {}
C {devices/lab_pin.sym} -1120 1170 0 0 {name=l186 lab=NODE3}
N -1120 1100 -1080 1100 {}
C {devices/lab_pin.sym} -1080 1100 0 0 {name=l187 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -1140 1100 0 0 {name=MSW1_F1
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -860 1070 -860 1030 {}
C {devices/lab_pin.sym} -860 1030 0 0 {name=l188 lab=NODE2}
N -900 1100 -940 1100 {}
C {devices/lab_pin.sym} -940 1100 0 0 {name=l189 lab=TRIM1B}
N -860 1130 -860 1170 {}
C {devices/lab_pin.sym} -860 1170 0 0 {name=l190 lab=NODE3}
N -860 1100 -820 1100 {}
C {devices/lab_pin.sym} -820 1100 0 0 {name=l191 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -880 1100 0 0 {name=MSW1_F2
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -600 1070 -600 1030 {}
C {devices/lab_pin.sym} -600 1030 0 0 {name=l192 lab=NODE2}
N -640 1100 -680 1100 {}
C {devices/lab_pin.sym} -680 1100 0 0 {name=l193 lab=TRIM1B}
N -600 1130 -600 1170 {}
C {devices/lab_pin.sym} -600 1170 0 0 {name=l194 lab=NODE3}
N -600 1100 -560 1100 {}
C {devices/lab_pin.sym} -560 1100 0 0 {name=l195 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -620 1100 0 0 {name=MSW1_F3
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -340 1070 -340 1030 {}
C {devices/lab_pin.sym} -340 1030 0 0 {name=l196 lab=NODE2}
N -380 1100 -420 1100 {}
C {devices/lab_pin.sym} -420 1100 0 0 {name=l197 lab=TRIM1B}
N -340 1130 -340 1170 {}
C {devices/lab_pin.sym} -340 1170 0 0 {name=l198 lab=NODE3}
N -340 1100 -300 1100 {}
C {devices/lab_pin.sym} -300 1100 0 0 {name=l199 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -360 1100 0 0 {name=MSW1_F4
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -80 1070 -80 1030 {}
C {devices/lab_pin.sym} -80 1030 0 0 {name=l200 lab=NODE2}
N -120 1100 -160 1100 {}
C {devices/lab_pin.sym} -160 1100 0 0 {name=l201 lab=TRIM1B}
N -80 1130 -80 1170 {}
C {devices/lab_pin.sym} -80 1170 0 0 {name=l202 lab=NODE3}
N -80 1100 -40 1100 {}
C {devices/lab_pin.sym} -40 1100 0 0 {name=l203 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -100 1100 0 0 {name=MSW1_F5
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 180 1070 180 1030 {}
C {devices/lab_pin.sym} 180 1030 0 0 {name=l204 lab=NODE2}
N 140 1100 100 1100 {}
C {devices/lab_pin.sym} 100 1100 0 0 {name=l205 lab=TRIM1B}
N 180 1130 180 1170 {}
C {devices/lab_pin.sym} 180 1170 0 0 {name=l206 lab=NODE3}
N 180 1100 220 1100 {}
C {devices/lab_pin.sym} 220 1100 0 0 {name=l207 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 160 1100 0 0 {name=MSW1_F6
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 440 1070 440 1030 {}
C {devices/lab_pin.sym} 440 1030 0 0 {name=l208 lab=NODE2}
N 400 1100 360 1100 {}
C {devices/lab_pin.sym} 360 1100 0 0 {name=l209 lab=TRIM1B}
N 440 1130 440 1170 {}
C {devices/lab_pin.sym} 440 1170 0 0 {name=l210 lab=NODE3}
N 440 1100 480 1100 {}
C {devices/lab_pin.sym} 480 1100 0 0 {name=l211 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 420 1100 0 0 {name=MSW1_F7
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 700 1070 700 1030 {}
C {devices/lab_pin.sym} 700 1030 0 0 {name=l212 lab=NODE2}
N 660 1100 620 1100 {}
C {devices/lab_pin.sym} 620 1100 0 0 {name=l213 lab=TRIM1B}
N 700 1130 700 1170 {}
C {devices/lab_pin.sym} 700 1170 0 0 {name=l214 lab=NODE3}
N 700 1100 740 1100 {}
C {devices/lab_pin.sym} 740 1100 0 0 {name=l215 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 680 1100 0 0 {name=MSW1_F8
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 960 1070 960 1030 {}
C {devices/lab_pin.sym} 960 1030 0 0 {name=l216 lab=NODE2}
N 920 1100 880 1100 {}
C {devices/lab_pin.sym} 880 1100 0 0 {name=l217 lab=TRIM1B}
N 960 1130 960 1170 {}
C {devices/lab_pin.sym} 960 1170 0 0 {name=l218 lab=NODE3}
N 960 1100 1000 1100 {}
C {devices/lab_pin.sym} 1000 1100 0 0 {name=l219 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 940 1100 0 0 {name=MSW1_F9
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -1380 1370 -1380 1330 {}
C {devices/lab_pin.sym} -1380 1330 0 0 {name=l220 lab=NODE3}
N -1420 1400 -1460 1400 {}
C {devices/lab_pin.sym} -1460 1400 0 0 {name=l221 lab=TRIM2B}
N -1380 1430 -1380 1470 {}
C {devices/lab_pin.sym} -1380 1470 0 0 {name=l222 lab=NODE4}
N -1380 1400 -1340 1400 {}
C {devices/lab_pin.sym} -1340 1400 0 0 {name=l223 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -1400 1400 0 0 {name=MSW2_F0
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -1120 1370 -1120 1330 {}
C {devices/lab_pin.sym} -1120 1330 0 0 {name=l224 lab=NODE3}
N -1160 1400 -1200 1400 {}
C {devices/lab_pin.sym} -1200 1400 0 0 {name=l225 lab=TRIM2B}
N -1120 1430 -1120 1470 {}
C {devices/lab_pin.sym} -1120 1470 0 0 {name=l226 lab=NODE4}
N -1120 1400 -1080 1400 {}
C {devices/lab_pin.sym} -1080 1400 0 0 {name=l227 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -1140 1400 0 0 {name=MSW2_F1
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -860 1370 -860 1330 {}
C {devices/lab_pin.sym} -860 1330 0 0 {name=l228 lab=NODE3}
N -900 1400 -940 1400 {}
C {devices/lab_pin.sym} -940 1400 0 0 {name=l229 lab=TRIM2B}
N -860 1430 -860 1470 {}
C {devices/lab_pin.sym} -860 1470 0 0 {name=l230 lab=NODE4}
N -860 1400 -820 1400 {}
C {devices/lab_pin.sym} -820 1400 0 0 {name=l231 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -880 1400 0 0 {name=MSW2_F2
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -600 1370 -600 1330 {}
C {devices/lab_pin.sym} -600 1330 0 0 {name=l232 lab=NODE3}
N -640 1400 -680 1400 {}
C {devices/lab_pin.sym} -680 1400 0 0 {name=l233 lab=TRIM2B}
N -600 1430 -600 1470 {}
C {devices/lab_pin.sym} -600 1470 0 0 {name=l234 lab=NODE4}
N -600 1400 -560 1400 {}
C {devices/lab_pin.sym} -560 1400 0 0 {name=l235 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -620 1400 0 0 {name=MSW2_F3
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -340 1370 -340 1330 {}
C {devices/lab_pin.sym} -340 1330 0 0 {name=l236 lab=NODE3}
N -380 1400 -420 1400 {}
C {devices/lab_pin.sym} -420 1400 0 0 {name=l237 lab=TRIM2B}
N -340 1430 -340 1470 {}
C {devices/lab_pin.sym} -340 1470 0 0 {name=l238 lab=NODE4}
N -340 1400 -300 1400 {}
C {devices/lab_pin.sym} -300 1400 0 0 {name=l239 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -360 1400 0 0 {name=MSW2_F4
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -80 1370 -80 1330 {}
C {devices/lab_pin.sym} -80 1330 0 0 {name=l240 lab=NODE3}
N -120 1400 -160 1400 {}
C {devices/lab_pin.sym} -160 1400 0 0 {name=l241 lab=TRIM2B}
N -80 1430 -80 1470 {}
C {devices/lab_pin.sym} -80 1470 0 0 {name=l242 lab=NODE4}
N -80 1400 -40 1400 {}
C {devices/lab_pin.sym} -40 1400 0 0 {name=l243 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -100 1400 0 0 {name=MSW2_F5
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 180 1370 180 1330 {}
C {devices/lab_pin.sym} 180 1330 0 0 {name=l244 lab=NODE3}
N 140 1400 100 1400 {}
C {devices/lab_pin.sym} 100 1400 0 0 {name=l245 lab=TRIM2B}
N 180 1430 180 1470 {}
C {devices/lab_pin.sym} 180 1470 0 0 {name=l246 lab=NODE4}
N 180 1400 220 1400 {}
C {devices/lab_pin.sym} 220 1400 0 0 {name=l247 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 160 1400 0 0 {name=MSW2_F6
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 440 1370 440 1330 {}
C {devices/lab_pin.sym} 440 1330 0 0 {name=l248 lab=NODE3}
N 400 1400 360 1400 {}
C {devices/lab_pin.sym} 360 1400 0 0 {name=l249 lab=TRIM2B}
N 440 1430 440 1470 {}
C {devices/lab_pin.sym} 440 1470 0 0 {name=l250 lab=NODE4}
N 440 1400 480 1400 {}
C {devices/lab_pin.sym} 480 1400 0 0 {name=l251 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 420 1400 0 0 {name=MSW2_F7
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 700 1370 700 1330 {}
C {devices/lab_pin.sym} 700 1330 0 0 {name=l252 lab=NODE3}
N 660 1400 620 1400 {}
C {devices/lab_pin.sym} 620 1400 0 0 {name=l253 lab=TRIM2B}
N 700 1430 700 1470 {}
C {devices/lab_pin.sym} 700 1470 0 0 {name=l254 lab=NODE4}
N 700 1400 740 1400 {}
C {devices/lab_pin.sym} 740 1400 0 0 {name=l255 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 680 1400 0 0 {name=MSW2_F8
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 960 1370 960 1330 {}
C {devices/lab_pin.sym} 960 1330 0 0 {name=l256 lab=NODE3}
N 920 1400 880 1400 {}
C {devices/lab_pin.sym} 880 1400 0 0 {name=l257 lab=TRIM2B}
N 960 1430 960 1470 {}
C {devices/lab_pin.sym} 960 1470 0 0 {name=l258 lab=NODE4}
N 960 1400 1000 1400 {}
C {devices/lab_pin.sym} 1000 1400 0 0 {name=l259 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 940 1400 0 0 {name=MSW2_F9
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -1380 1670 -1380 1630 {}
C {devices/lab_pin.sym} -1380 1630 0 0 {name=l260 lab=NODE4}
N -1420 1700 -1460 1700 {}
C {devices/lab_pin.sym} -1460 1700 0 0 {name=l261 lab=TRIM3B}
N -1380 1730 -1380 1770 {}
C {devices/lab_pin.sym} -1380 1770 0 0 {name=l262 lab=NODE5}
N -1380 1700 -1340 1700 {}
C {devices/lab_pin.sym} -1340 1700 0 0 {name=l263 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -1400 1700 0 0 {name=MSW3_F0
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -1120 1670 -1120 1630 {}
C {devices/lab_pin.sym} -1120 1630 0 0 {name=l264 lab=NODE4}
N -1160 1700 -1200 1700 {}
C {devices/lab_pin.sym} -1200 1700 0 0 {name=l265 lab=TRIM3B}
N -1120 1730 -1120 1770 {}
C {devices/lab_pin.sym} -1120 1770 0 0 {name=l266 lab=NODE5}
N -1120 1700 -1080 1700 {}
C {devices/lab_pin.sym} -1080 1700 0 0 {name=l267 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -1140 1700 0 0 {name=MSW3_F1
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -860 1670 -860 1630 {}
C {devices/lab_pin.sym} -860 1630 0 0 {name=l268 lab=NODE4}
N -900 1700 -940 1700 {}
C {devices/lab_pin.sym} -940 1700 0 0 {name=l269 lab=TRIM3B}
N -860 1730 -860 1770 {}
C {devices/lab_pin.sym} -860 1770 0 0 {name=l270 lab=NODE5}
N -860 1700 -820 1700 {}
C {devices/lab_pin.sym} -820 1700 0 0 {name=l271 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -880 1700 0 0 {name=MSW3_F2
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -600 1670 -600 1630 {}
C {devices/lab_pin.sym} -600 1630 0 0 {name=l272 lab=NODE4}
N -640 1700 -680 1700 {}
C {devices/lab_pin.sym} -680 1700 0 0 {name=l273 lab=TRIM3B}
N -600 1730 -600 1770 {}
C {devices/lab_pin.sym} -600 1770 0 0 {name=l274 lab=NODE5}
N -600 1700 -560 1700 {}
C {devices/lab_pin.sym} -560 1700 0 0 {name=l275 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -620 1700 0 0 {name=MSW3_F3
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -340 1670 -340 1630 {}
C {devices/lab_pin.sym} -340 1630 0 0 {name=l276 lab=NODE4}
N -380 1700 -420 1700 {}
C {devices/lab_pin.sym} -420 1700 0 0 {name=l277 lab=TRIM3B}
N -340 1730 -340 1770 {}
C {devices/lab_pin.sym} -340 1770 0 0 {name=l278 lab=NODE5}
N -340 1700 -300 1700 {}
C {devices/lab_pin.sym} -300 1700 0 0 {name=l279 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -360 1700 0 0 {name=MSW3_F4
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -80 1670 -80 1630 {}
C {devices/lab_pin.sym} -80 1630 0 0 {name=l280 lab=NODE4}
N -120 1700 -160 1700 {}
C {devices/lab_pin.sym} -160 1700 0 0 {name=l281 lab=TRIM3B}
N -80 1730 -80 1770 {}
C {devices/lab_pin.sym} -80 1770 0 0 {name=l282 lab=NODE5}
N -80 1700 -40 1700 {}
C {devices/lab_pin.sym} -40 1700 0 0 {name=l283 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -100 1700 0 0 {name=MSW3_F5
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 180 1670 180 1630 {}
C {devices/lab_pin.sym} 180 1630 0 0 {name=l284 lab=NODE4}
N 140 1700 100 1700 {}
C {devices/lab_pin.sym} 100 1700 0 0 {name=l285 lab=TRIM3B}
N 180 1730 180 1770 {}
C {devices/lab_pin.sym} 180 1770 0 0 {name=l286 lab=NODE5}
N 180 1700 220 1700 {}
C {devices/lab_pin.sym} 220 1700 0 0 {name=l287 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 160 1700 0 0 {name=MSW3_F6
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 440 1670 440 1630 {}
C {devices/lab_pin.sym} 440 1630 0 0 {name=l288 lab=NODE4}
N 400 1700 360 1700 {}
C {devices/lab_pin.sym} 360 1700 0 0 {name=l289 lab=TRIM3B}
N 440 1730 440 1770 {}
C {devices/lab_pin.sym} 440 1770 0 0 {name=l290 lab=NODE5}
N 440 1700 480 1700 {}
C {devices/lab_pin.sym} 480 1700 0 0 {name=l291 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 420 1700 0 0 {name=MSW3_F7
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 700 1670 700 1630 {}
C {devices/lab_pin.sym} 700 1630 0 0 {name=l292 lab=NODE4}
N 660 1700 620 1700 {}
C {devices/lab_pin.sym} 620 1700 0 0 {name=l293 lab=TRIM3B}
N 700 1730 700 1770 {}
C {devices/lab_pin.sym} 700 1770 0 0 {name=l294 lab=NODE5}
N 700 1700 740 1700 {}
C {devices/lab_pin.sym} 740 1700 0 0 {name=l295 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 680 1700 0 0 {name=MSW3_F8
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 960 1670 960 1630 {}
C {devices/lab_pin.sym} 960 1630 0 0 {name=l296 lab=NODE4}
N 920 1700 880 1700 {}
C {devices/lab_pin.sym} 880 1700 0 0 {name=l297 lab=TRIM3B}
N 960 1730 960 1770 {}
C {devices/lab_pin.sym} 960 1770 0 0 {name=l298 lab=NODE5}
N 960 1700 1000 1700 {}
C {devices/lab_pin.sym} 1000 1700 0 0 {name=l299 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 940 1700 0 0 {name=MSW3_F9
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -1380 1970 -1380 1930 {}
C {devices/lab_pin.sym} -1380 1930 0 0 {name=l300 lab=NODE5}
N -1420 2000 -1460 2000 {}
C {devices/lab_pin.sym} -1460 2000 0 0 {name=l301 lab=TRIM4B}
N -1380 2030 -1380 2070 {}
C {devices/lab_pin.sym} -1380 2070 0 0 {name=l302 lab=DP}
N -1380 2000 -1340 2000 {}
C {devices/lab_pin.sym} -1340 2000 0 0 {name=l303 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -1400 2000 0 0 {name=MSW4_F0
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -1120 1970 -1120 1930 {}
C {devices/lab_pin.sym} -1120 1930 0 0 {name=l304 lab=NODE5}
N -1160 2000 -1200 2000 {}
C {devices/lab_pin.sym} -1200 2000 0 0 {name=l305 lab=TRIM4B}
N -1120 2030 -1120 2070 {}
C {devices/lab_pin.sym} -1120 2070 0 0 {name=l306 lab=DP}
N -1120 2000 -1080 2000 {}
C {devices/lab_pin.sym} -1080 2000 0 0 {name=l307 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -1140 2000 0 0 {name=MSW4_F1
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -860 1970 -860 1930 {}
C {devices/lab_pin.sym} -860 1930 0 0 {name=l308 lab=NODE5}
N -900 2000 -940 2000 {}
C {devices/lab_pin.sym} -940 2000 0 0 {name=l309 lab=TRIM4B}
N -860 2030 -860 2070 {}
C {devices/lab_pin.sym} -860 2070 0 0 {name=l310 lab=DP}
N -860 2000 -820 2000 {}
C {devices/lab_pin.sym} -820 2000 0 0 {name=l311 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -880 2000 0 0 {name=MSW4_F2
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -600 1970 -600 1930 {}
C {devices/lab_pin.sym} -600 1930 0 0 {name=l312 lab=NODE5}
N -640 2000 -680 2000 {}
C {devices/lab_pin.sym} -680 2000 0 0 {name=l313 lab=TRIM4B}
N -600 2030 -600 2070 {}
C {devices/lab_pin.sym} -600 2070 0 0 {name=l314 lab=DP}
N -600 2000 -560 2000 {}
C {devices/lab_pin.sym} -560 2000 0 0 {name=l315 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -620 2000 0 0 {name=MSW4_F3
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -340 1970 -340 1930 {}
C {devices/lab_pin.sym} -340 1930 0 0 {name=l316 lab=NODE5}
N -380 2000 -420 2000 {}
C {devices/lab_pin.sym} -420 2000 0 0 {name=l317 lab=TRIM4B}
N -340 2030 -340 2070 {}
C {devices/lab_pin.sym} -340 2070 0 0 {name=l318 lab=DP}
N -340 2000 -300 2000 {}
C {devices/lab_pin.sym} -300 2000 0 0 {name=l319 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -360 2000 0 0 {name=MSW4_F4
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N -80 1970 -80 1930 {}
C {devices/lab_pin.sym} -80 1930 0 0 {name=l320 lab=NODE5}
N -120 2000 -160 2000 {}
C {devices/lab_pin.sym} -160 2000 0 0 {name=l321 lab=TRIM4B}
N -80 2030 -80 2070 {}
C {devices/lab_pin.sym} -80 2070 0 0 {name=l322 lab=DP}
N -80 2000 -40 2000 {}
C {devices/lab_pin.sym} -40 2000 0 0 {name=l323 lab=VPU_REG}
C {symbols/pfet_03v3.sym} -100 2000 0 0 {name=MSW4_F5
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 180 1970 180 1930 {}
C {devices/lab_pin.sym} 180 1930 0 0 {name=l324 lab=NODE5}
N 140 2000 100 2000 {}
C {devices/lab_pin.sym} 100 2000 0 0 {name=l325 lab=TRIM4B}
N 180 2030 180 2070 {}
C {devices/lab_pin.sym} 180 2070 0 0 {name=l326 lab=DP}
N 180 2000 220 2000 {}
C {devices/lab_pin.sym} 220 2000 0 0 {name=l327 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 160 2000 0 0 {name=MSW4_F6
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 440 1970 440 1930 {}
C {devices/lab_pin.sym} 440 1930 0 0 {name=l328 lab=NODE5}
N 400 2000 360 2000 {}
C {devices/lab_pin.sym} 360 2000 0 0 {name=l329 lab=TRIM4B}
N 440 2030 440 2070 {}
C {devices/lab_pin.sym} 440 2070 0 0 {name=l330 lab=DP}
N 440 2000 480 2000 {}
C {devices/lab_pin.sym} 480 2000 0 0 {name=l331 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 420 2000 0 0 {name=MSW4_F7
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 700 1970 700 1930 {}
C {devices/lab_pin.sym} 700 1930 0 0 {name=l332 lab=NODE5}
N 660 2000 620 2000 {}
C {devices/lab_pin.sym} 620 2000 0 0 {name=l333 lab=TRIM4B}
N 700 2030 700 2070 {}
C {devices/lab_pin.sym} 700 2070 0 0 {name=l334 lab=DP}
N 700 2000 740 2000 {}
C {devices/lab_pin.sym} 740 2000 0 0 {name=l335 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 680 2000 0 0 {name=MSW4_F8
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
N 960 1970 960 1930 {}
C {devices/lab_pin.sym} 960 1930 0 0 {name=l336 lab=NODE5}
N 920 2000 880 2000 {}
C {devices/lab_pin.sym} 880 2000 0 0 {name=l337 lab=TRIM4B}
N 960 2030 960 2070 {}
C {devices/lab_pin.sym} 960 2070 0 0 {name=l338 lab=DP}
N 960 2000 1000 2000 {}
C {devices/lab_pin.sym} 1000 2000 0 0 {name=l339 lab=VPU_REG}
C {symbols/pfet_03v3.sym} 940 2000 0 0 {name=MSW4_F9
L=0.28u
W=100u
nf=1
m=1
model=pfet_03v3
spiceprefix=X
}
