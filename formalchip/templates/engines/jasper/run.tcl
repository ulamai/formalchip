# FormalChip Jasper template
# Expected environment variables:
# - FORMALCHIP_RTL_FILES   (pathsep-delimited file list)
# - FORMALCHIP_PROPERTY_FILE
# - FORMALCHIP_TOP

set rtl_raw $::env(FORMALCHIP_RTL_FILES)
set prop_file $::env(FORMALCHIP_PROPERTY_FILE)
set top $::env(FORMALCHIP_TOP)

set sep ":"
if {[string first ";" $rtl_raw] >= 0} {
  set sep ";"
}
set rtl_files [split $rtl_raw $sep]

analyze -sv $rtl_files
analyze -sv $prop_file
elaborate $top

# Tune app/abstractions/assumptions based on project intent.
set_proofgrid_mode local
prove -all
report -summary > jasper_proof_report.rpt

exit
