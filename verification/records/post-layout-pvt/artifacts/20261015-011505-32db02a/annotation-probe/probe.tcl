# SPEF annotation probe for record 20261008-195826-74ccfac (PR #104 review
# of record 20261008-200000-8139bb6).
# Same inputs as the `klt sta` run (LEFs, DEF, liberty corner, 83.333 ns
# clock, ideal clock as klt emits it), plus diagnostics klt does not print:
# the list of unannotated / partially-annotated drivers and the
# before/after-read_spef path reports. The caller sets `pdk_root`,
# `corner` and `spef` and then sources this file (run.sh does that, so
# no environment has to cross `sudo docker`). Paths are repo-relative;
# run from the repo root. The clock is left ideal, exactly as in the
# klt-generated script, so the before-read_spef report is directly
# comparable with the cited envelope's numbers.
set pdk $pdk_root/gf180mcuD/libs.ref/gf180mcu_fd_sc_mcu9t5v0
read_lef $pdk/techlef/gf180mcu_fd_sc_mcu9t5v0__nom.tlef
read_lef $pdk/lef/gf180mcu_fd_sc_mcu9t5v0.lef
read_def layout/digital/usb_utmi_phy.def
read_liberty $pdk/lib/gf180mcu_fd_sc_mcu9t5v0__${corner}.lib
create_clock -name clk -period 83.333 [get_ports clk]
puts "===PROBE_PRE_BEGIN==="
report_checks -path_delay min_max -digits 4
puts "===PROBE_PRE_END==="
read_spef $spef
puts "===PROBE_ANNOTATION_BEGIN==="
report_parasitic_annotation -report_unannotated
puts "===PROBE_ANNOTATION_END==="
puts "===PROBE_POST_BEGIN==="
report_checks -path_delay min_max -digits 4
puts "===PROBE_POST_END==="
puts "===PROBE_NET_BEGIN==="
# _013_: an ordinary internal net. rx_receiving / line_state[0] /
# line_state[1]: the three nets whose DEF PIN name (RxActive,
# LineState[0], LineState[1]) differs from the DEF NET name.
foreach probe_net {_013_ rx_receiving line_state[0] line_state[1]} {
    report_net -digits 4 $probe_net
}
puts "===PROBE_NET_END==="
report_worst_slack -max -digits 4
report_worst_slack -min -digits 4
