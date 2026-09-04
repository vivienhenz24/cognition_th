#!/bin/bash
# Static checks for .pa.yaml files (Rules 2,3,4). Every printed line is a bug.
awk '
FNR==1 { prevblock=0 }
{
  line=$0
  if (prevblock) {
    t=line; sub(/^[ \t]+/,"",t)
    if (t !~ /^=/) printf "%s:%d: BLOCK_MISSING_EQUALS: first line under |- must start with =\n", FILENAME, FNR
    prevblock=0
  }
  if (line ~ /\|-?[ \t]*=/)                       printf "%s:%d: EQUALS_ON_BLOCK_LINE: move = to the next line\n", FILENAME, FNR
  else if (line ~ /^[ \t]*[A-Za-z0-9_]+:[ \t]*\|[-+]?[ \t]*$/) prevblock=1
  if (line ~ /^[ \t]*[A-Za-z0-9_]+: =.*[{#]/)     printf "%s:%d: BRACE_OR_HASH_SINGLE_LINE: use |- block\n", FILENAME, FNR
  else if (line ~ /^[ \t]*[A-Za-z0-9_]+: =.*:/)   printf "%s:%d: COLON_SINGLE_LINE: use |- block\n", FILENAME, FNR
  if (line ~ /^[ \t]*[A-Za-z0-9_]+: [\047"]/)      printf "%s:%d: QUOTED_FORMULA: remove YAML quotes, start with =\n", FILENAME, FNR
  if (line ~ /^[ \t]*#/)                           printf "%s:%d: YAML_COMMENT: remove # comment\n", FILENAME, FNR
  if (line ~ /FontSize:|\.SelectedItems|\.Result([^A-Za-z_]|$)|SelectedText/) printf "%s:%d: BAD_PROPERTY: see Rule 7\n", FILENAME, FNR
  if (line ~ /[^A-Za-z]Contains\(|\.Contains\(/)          printf "%s:%d: NO_CONTAINS: use the in operator (Step 2c)\n", FILENAME, FNR
  if (line ~ /Search\(/)                             printf "%s:%d: SEARCH_FN: use Filter(..., text in col) or IsMatch (Step 2c)\n", FILENAME, FNR
  if (line ~ /ClearCollect\([A-Za-z_]+\)|ClearCollect\([A-Za-z_]+, *\{\}\)/) printf "%s:%d: CLEARCOLLECT_ARGS: seed a typed row then Clear (Step 2c)\n", FILENAME, FNR
  if (line ~ /reviewed_date: *Blank\(\)/)            printf "%s:%d: UNTYPED_BLANK: use DateTimeValue(\"\") (Step 2c)\n", FILENAME, FNR
  if (line ~ /CountRows\([A-Za-z_]+\.AllItems\)/)     printf "%s:%d: ALLITEMSCOUNT: use gal.AllItemsCount (Step 2c)\n", FILENAME, FNR
  if (FILENAME !~ /App\.pa\.yaml$/ && line ~ /RGBA\(/)   printf "%s:%d: RAW_COLOUR: use Theme.* (C1)\n", FILENAME, FNR
  if (line ~ /&&|\|\||[(, ]![A-Za-z(]/)                 printf "%s:%d: OPERATOR_STYLE: use And / Or / Not (C5)\n", FILENAME, FNR
  if (line ~ /Parent\.(Height|Width) *- *[0-9]/)         printf "%s:%d: MAGIC_LAYOUT: use FillPortions, not Parent.Height - N (C4)\n", FILENAME, FNR
  if (line ~ /Text: *=\"[^\"]*:\"/)                      printf "%s:%d: TRAILING_COLON_LABEL: drop the colon (C5)\n", FILENAME, FNR
  if (line ~ /varShow[A-Za-z]*|UpdateContext\(/)         printf "%s:%d: VARIABLE_POLICY: only varSelected and varConfirmMode (C6)\n", FILENAME, FNR
  if (line ~ /Padding(Top|Bottom|Left|Right): =[0-9]|LayoutGap: =[0-9]/) printf "%s:%d: RAW_SPACING: use Space.* (C4)\n", FILENAME, FNR
  if (line ~ /Appearance: =[A-Za-z]+$|Appearance: =[A-Za-z]+\.[A-Za-z]+\.[A-Za-z]+$/) printf "%s:%d: ENUM_NAMESPACE: use the quoted-namespace form from Rule 6\n", FILENAME, FNR
}' "${1:-$(cd "$(dirname "$0")/../../.." && pwd)/kyc-example/generated}"/*.pa.yaml
