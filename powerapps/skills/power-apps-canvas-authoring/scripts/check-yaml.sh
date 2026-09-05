#!/bin/bash
# Static checks for .pa.yaml files (Rules 2,3,4). Every printed line is a bug.
awk '
function problem(message) {
  printf "%s:%d: %s\n", FILENAME, FNR, message
  errors=1
}
FNR==1 { prevblock=0 }
{
  line=$0
  if (prevblock) {
    t=line; sub(/^[ \t]+/,"",t)
    if (t !~ /^=/) problem("BLOCK_MISSING_EQUALS: first line under |- must start with =")
    prevblock=0
  }
  if (line ~ /\|-?[ \t]*=/)                       problem("EQUALS_ON_BLOCK_LINE: move = to the next line")
  else if (line ~ /^[ \t]*[A-Za-z0-9_]+:[ \t]*\|[-+]?[ \t]*$/) prevblock=1
  if (line ~ /^[ \t]*[A-Za-z0-9_]+: =.*[{#]/)     problem("BRACE_OR_HASH_SINGLE_LINE: use |- block")
  else if (line ~ /^[ \t]*[A-Za-z0-9_]+: =.*:/)   problem("COLON_SINGLE_LINE: use |- block")
  if (line ~ /^[ \t]*[A-Za-z0-9_]+: [\047"]/)      problem("QUOTED_FORMULA: remove YAML quotes, start with =")
  if (line ~ /^[ \t]*#/)                           problem("YAML_COMMENT: remove # comment")
  if (line ~ /FontSize:|\.SelectedItems|\.Result([^A-Za-z_]|$)|SelectedText/) problem("BAD_PROPERTY: see Rule 7")
  if (line ~ /[^A-Za-z]Contains\(|\.Contains\(/)   problem("NO_CONTAINS: use the in operator (Step 2c)")
  if (line ~ /Search\(/)                           problem("SEARCH_FN: use Filter(..., text in col) or IsMatch (Step 2c)")
  if (line ~ /ClearCollect\([A-Za-z_]+\)|ClearCollect\([A-Za-z_]+, *\{\}\)/) problem("CLEARCOLLECT_ARGS: seed a typed row then Clear (Step 2c)")
  if (line ~ /reviewed_date: *Blank\(\)/)          problem("UNTYPED_BLANK: use DateTimeValue(\"\") (Step 2c)")
  if (line ~ /CountRows\([A-Za-z_]+\.AllItems\)/)  problem("ALLITEMSCOUNT: use gal.AllItemsCount (Step 2c)")
  if (FILENAME !~ /App\.pa\.yaml$/ && line ~ /RGBA\(/) problem("RAW_COLOUR: use Theme.* (C1)")
  if (line ~ /&&|\|\||[(, ]![A-Za-z(]/)            problem("OPERATOR_STYLE: use And / Or / Not (C5)")
  if (line ~ /Parent\.(Height|Width) *- *[0-9]/)   problem("MAGIC_LAYOUT: use FillPortions, not Parent.Height - N (C4)")
  if (line ~ /Text: *=\"[^\"]*:\"/)                problem("TRAILING_COLON_LABEL: drop the colon (C5)")
  if (line ~ /varShow[A-Za-z]*|UpdateContext\(/)   problem("VARIABLE_POLICY: only varSelected and varConfirmMode (C6)")
  if (line ~ /Padding(Top|Bottom|Left|Right): =[0-9]|LayoutGap: =[0-9]/) problem("RAW_SPACING: use Space.* (C4)")
  if (line ~ /Appearance: =[A-Za-z]+$|Appearance: =[A-Za-z]+\.[A-Za-z]+\.[A-Za-z]+$/) problem("ENUM_NAMESPACE: use the quoted-namespace form from Rule 6")
}
END { exit errors ? 1 : 0 }
' "${1:-$(cd "$(dirname "$0")/../../.." && pwd)/kyc-example/generated}"/*.pa.yaml
