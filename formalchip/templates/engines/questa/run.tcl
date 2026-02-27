# FormalChip Questa Formal template
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

vlib work
vmap work work
foreach f $rtl_files {
  vlog -sv $f
}
vlog -sv $prop_file

# Questa flow placeholders; adjust to your environment.
vsim -c -do "
  formal compile -d $top;
  formal verify -all;
  quit -f;
" $top
