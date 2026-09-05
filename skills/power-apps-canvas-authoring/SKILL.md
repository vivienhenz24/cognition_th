---
name: power-apps-canvas-authoring
description: Build and modify Power Apps canvas apps as .pa.yaml source through the canvas-authoring MCP server. Use whenever a task mentions Power Apps, canvas apps, Power Fx, .pa.yaml, or the canvas-authoring / compile_canvas / sync_canvas tools.
---

# Power Apps canvas authoring via MCP

This skill is the complete operating procedure. Prefer a full Power Apps Studio edit URL
plus `WORKDIR` (the folder for the generated `.pa.yaml` files). For compatibility with
the local starter-kit flow, `ENVIRONMENT_ID` and `APP_ID` may be supplied separately.
Everything else is here. Follow the sections in order.

Ground rules:
- The plugin and MCP server are installed before the authoring task begins. Do not
  reconfigure them from inside the task or run `devin mcp`, `devin plugins`, or `dnx`.
- Use only the MCP tools named below, Read/Write/Edit on `.pa.yaml` files, and the one
  checker script in section 3.
- Ask only for a missing Studio URL or connection value. Never ask for a password,
  access token, or connection string.

## 1. Preflight and connect

Before connecting, confirm that the Power Apps Studio edit tab is open, signed in,
coauthoring is enabled under Settings → Updates, and the tab will remain open for the
whole authoring session.

When a Studio URL is supplied, extract:

- `environment_id`: the path segment after `/e/`.
- `app_id`: URL-decode the `app-id` query parameter and take its final path segment.
- `environment_category`: map the URL hostname using this table:

| Hostname | Category |
|---|---|
| `make.powerapps.com` | `prod` |
| `make.preview.powerapps.com` | `prod` |
| `make.preprod.powerapps.com` | `preprod` |
| `make.gov.powerapps.us` | `gov` |
| `make.high.powerapps.us` | `high` |
| `make.apps.appsplatform.us` | `dod` |
| `make.powerapps.cn` | `china` |
| Any other hostname | `test` |

If separate IDs are supplied, use them and default `environment_category` to `prod`
unless the task identifies another Power Apps cloud.

Call:

```
mcp__canvas-authoring__connect(
  environment_id       = "<parsed or supplied environment ID>",
  app_id               = "<parsed or supplied app ID>",
  environment_category = "<mapped category>"
)
```

On Devin cloud, Microsoft sign-in may open in the session's Desktop browser. Let the user
complete interactive sign-in or MFA there; credentials must never be pasted into chat.
Omit optional authentication parameters on the first call. On 401/403, retry once with
`force_account_select = true`. Use `login_hint` or `tenant_id` only when the user already
provided them. Use `auth_flow = "devicecode"` only on a genuinely headless host whose MCP
client supports elicitation.

If the `connect` tool is unavailable, run `dotnet --list-sdks`. A 10.x or later SDK must
be present. Otherwise report that the plugin/environment setup is incomplete and that a
new Devin session is required after it is fixed.

## 2. Sync and discover

1. `sync_canvas(directory="<WORKDIR>")`. This writes `App.pa.yaml`, `Screen1.pa.yaml`,
   `_EditorState.pa.yaml`. Never edit `_EditorState.pa.yaml`.
2. `list_controls()`. Note the exact control names available.
3. `describe_control(name=...)` for every control type you will use (at minimum Screen,
   GroupContainer, Label, Button, TextInput, DropDown, Gallery). Copy the `Control:`
   value, `Variant`, property names, and enum names verbatim. Never guess a property or
   enum name.

## 3. .pa.yaml syntax rules (non-negotiable)

Source: Microsoft Power Fx YAML formula grammar and the pa.yaml v3.0 schema.

### Rule 1 — every property value starts with `=`

```yaml
Text: ="Hello"
Width: =Parent.Width - 20
Visible: =true
```

A value with no `=` is a compile error ("Power Fx expressions must start with '='").

### Rule 2 — a single-line formula may NOT contain `:` or `#` anywhere

Not even inside a quoted string. YAML reads `:` as a new key and `#` as a comment.
This is the cause of "While scanning a plain scalar value, found invalid mapping".

Anything with a record literal `{a: 1}`, a `Table({...})`, a `Patch(..., {...})`,
`Collect(..., {...})`, `UpdateContext({...})`, `Navigate(x, None, {...})`, a time
like `1:30`, a URL, or a `#` **must** use the multi-line form (Rule 3).

WRONG (all three were tried and all fail):
```yaml
Items: =Table({id: 1, name: "A"}, {id: 2, name: "B"})
Items: =Table('{id: 1, name: "A"}')
Items: =Table('={id: 1, name: "A"}')
```

RIGHT:
```yaml
Items: |-
  =Table(
    {id: 1, name: "A"},
    {id: 2, name: "B"}
  )
```

### Rule 3 — multi-line form: `|-` on the property line, `=` on the FIRST content line

```yaml
OnSelect: |-
  =If("@" in txtEmail.Value,
    Patch(KYC_Requests, LookUp(KYC_Requests, id = varSelected.id), {status: "Approved"});
    Collect(Audit_Log, {action_type: "Approve", user: User().Email, timestamp: Now(), record_id: varSelected.id, details: "ok"});
    Notify("Approved", NotificationType.Success);
    Back(),
    Notify("Supervisor email required", NotificationType.Error)
  )
```

- `|-` is alone at the end of the property line. Nothing after it.
- The `=` is the first character of the next line, indented 2 spaces deeper than the
  property name.
- Every following line of the formula is indented at least as deep as that `=`.
- Do not put `=` on the `|-` line. Do not omit the `=`. Do not add a second `=`.
- Inside the block, `:` and `#` are fine.

### Rule 4 — never wrap a formula in YAML quotes

No `'...'` and no `"..."` around a formula. No backslash escapes. If YAML quoting seems
needed, the answer is always Rule 3 (multi-line block), never quotes.

### Rule 5 — no `#` comments anywhere in the file

Use `//` inside a formula if you need a comment, and only inside a multi-line block.

### Rule 6 — enums: copy the exact text `describe_control` prints

Modern controls use a quoted namespace. Bare values are wrong.

```yaml
Appearance: ='ButtonCanvas.Appearance'.Primary      # not =Primary, not =ButtonCanvas.Appearance.Primary
Mode:       ='TextInputCanvas.Mode'.MultiLine        # verify exact name with describe_control
Align:      =Align.Center
FontWeight: =FontWeight.Bold
Font:       =Font.'Segoe UI'
LayoutDirection: =LayoutDirection.Vertical
```

If `describe_control` shows an enum type with a dot in its name (e.g.
`ButtonCanvas.Appearance`), wrap that type name in single quotes, then `.Value`.
If unsure, omit the property entirely; the default is fine.

### Rule 7 — property names: use only what `describe_control` lists

Known traps from earlier runs:
- Label font size is `Size`, not `FontSize`.
- Modern TextInput text is `.Value`, not `.Text`. Its placeholder is `Placeholder`.
- Modern DropDown selection is `.Selected.Value`. An `Items` of `["All","Low"]` is a
  one-column table whose column is `Value`, so the filter test is
  `ddRisk.Selected.Value = "Low"`. Do not use `SelectedItems` / `.Result`.
- Gallery template children use `Parent.TemplateWidth` and `Parent.TemplateHeight`.

### Rule 8 — file structure (2-space indent, exactly this shape)

```yaml
Screens:
  Screen1:
    Properties:
      Fill: =RGBA(245, 245, 245, 1)
    Children:
      - conDashRoot:
          Control: GroupContainer
          Variant: AutoLayout
          Properties:
            Width: =Parent.Width
            Height: =Parent.Height
            LayoutDirection: =LayoutDirection.Vertical
          Children:
            - lblDashTitle:
                Control: Label
                Properties:
                  Text: ="KYC Review Queue"
            - galDashPending:
                Control: Gallery
                Variant: Vertical
                Properties:
                  Items: =Filter(KYC_Requests, status = "Pending")
                  TemplateSize: =80
                  OnSelect: |-
                    =Set(varSelected, ThisItem);
                    Navigate(ReviewDetail, ScreenTransition.Fade)
                Children:
                  - lblDashRowName:
                      Control: Label
                      Properties:
                        Text: =ThisItem.customer_name
                        Width: =Parent.TemplateWidth - 40
```

- Each `Children` entry is `- Name:` and the mapping under it is indented 4 more spaces.
- `Control:` and `Variant:` are plain strings, no `=`.
- Order in `Children` is z-order: first = bottom.
- `App.pa.yaml` starts with `App:` then `Properties:`. Screen files start with `Screens:`.
- Only one `OnStart`; seed collections there with `ClearCollect` in a multi-line block.

### Rule 9 — self-check before every compile

Before calling `compile_canvas`, scan each file you wrote and fix these by hand:

1. Any line matching `: =` that also contains `{`, `#`, or a second `:` → convert to Rule 3.
2. Any line ending in `|-` whose next line does not begin (after spaces) with `=` → add `=`.
3. Any line containing `|- =` or `|-=` → move the `=` to the next line.
4. Any `Properties:` value that begins with `'` or `"` instead of `=` → remove quotes, add `=`.
5. Any `Appearance:`, `Mode:` or other modern enum written without the quoted namespace → fix per Rule 6.
6. Any `FontSize`, `.SelectedItems`, `.Result`, `SelectedText` → fix per Rule 7.

You may run exactly one shell command for this check, nothing else:
```
skills/power-apps-canvas-authoring/scripts/check-yaml.sh <WORKDIR>   (run from the repo root)
```
It prints one line per problem with the file, line number, and which rule to apply.
Every line it prints is a bug. Fix all of them, re-run it, and only call `compile_canvas`
when it prints nothing.


## 4. Power Fx rules and proven formula patterns

Power Fx is not JavaScript and not C#. Every function below was tried in an earlier run and
does not exist or has a different signature. Use only the right-hand column.

| Do NOT write | Why | Write instead |
|---|---|---|
| `Contains(text, "x")` | No such function | `"x" in text` (case-insensitive substring) |
| `customer_name.Contains(...)` | No method syntax | `txtSearch.Value in customer_name` |
| `Search(txt, "@", "*")` on a text value | `Search` works on tables only | `"@" in txt` or `IsMatch(txt, Match.Email)` |
| `Search(table, text)` with 2 args | Needs 3+: `Search(table, text, "col")` | prefer `Filter(table, text in col)` |
| `customer_name = txtSearch.Value` as a "search" | Exact match, not search; violates spec | `txtSearch.Value in customer_name` |
| `ClearCollect(Audit_Log)` | Needs 2+ args | seed one typed row, then `Clear` (see OnStart below) |
| `ClearCollect(Audit_Log, {})` | Empty record has no columns; later `Collect` fails | same as above |
| `reviewed_date: Blank()` in seed rows | Untyped blank; later `Patch(..., reviewed_date: Now())` fails with type mismatch | `reviewed_date: DateTimeValue("")` (a blank that is typed DateTime) |
| Removing `reviewed_date` from `Patch` to dodge the type error | Violates spec | fix the seed type instead |
| `CountRows(gal.AllItems)` | App-checker performance warning | `gal.AllItemsCount` |
| `!IsBlank(x)` | Works, but prefer | `Not(IsBlank(x))` |
| `reviewed_date = Today()` | DateTime never equals a Date | `IsToday(reviewed_date)` |
| `Set(varSelected, ThisItem)` then `Patch(..., varSelected, ...)` | Fine, but after Patch the var is stale | re-`LookUp` by id as shown below |
| `Navigate(...)` inside `App.OnStart` | Not allowed | `StartScreen: =Screen1` |

### A fix must never weaken the spec

If a formula errors, fix the formula. Do not drop a required field, downgrade substring
search to equality, remove the audit row, or remove the supervisor check. If you cannot
make a required feature compile after two attempts, leave it in, list it as an open error
in the report, and move on.

### Proven formula patterns (worked example: a review-queue app with `KYC_Requests` and `Audit_Log` collections)

**App.OnStart** (multi-line block; note the typed blank and the seed-then-Clear pattern):
```yaml
    OnStart: |-
      =ClearCollect(KYC_Requests,
        {id: 1, customer_name: "Alice Johnson", customer_email: "alice.johnson@example.com", risk_score: 2, submission_date: DateAdd(Today(), -5, TimeUnit.Days), status: "Pending", reviewer_notes: "", reviewed_by: "", reviewed_date: DateTimeValue("")},
        {id: 2, customer_name: "Bob Smith", customer_email: "bob.smith@example.com", risk_score: 5, submission_date: DateAdd(Today(), -4, TimeUnit.Days), status: "Pending", reviewer_notes: "", reviewed_by: "", reviewed_date: DateTimeValue("")}
      );
      ClearCollect(Audit_Log, {action_type: "", user: "", timestamp: Now(), record_id: 0, details: ""});
      Clear(Audit_Log);
      Set(varSelected, Blank());
      Set(varConfirmMode, "")
```
Add the remaining six seed rows inside the same `ClearCollect`, one record per line.

**Dashboard gallery Items** (`PendingRequests` and `RiskBands` come from section 5, C1):
```yaml
                  Items: |-
                    =Filter(PendingRequests,
                      ddDashRisk.Selected.Value = "All"
                        Or (risk_score >= LookUp(RiskBands, Name = ddDashRisk.Selected.Value).Min
                            And risk_score <= LookUp(RiskBands, Name = ddDashRisk.Selected.Value).Max),
                      IsBlank(txtDashSearch.Value) Or txtDashSearch.Value in customer_name
                    )
```

**KPI counts:** `CountRows(PendingRequests)`, `CountRows(ApprovedToday)`,
`CountRows(RejectedToday)` inside the KPI gallery table (section 5, C2).

**Empty state label:** `Visible: =galDashPending.AllItemsCount = 0`

**Risk colour:**
```yaml
Color: =LookUp(RiskBands, ThisItem.risk_score >= Min And ThisItem.risk_score <= Max).Color
```

**Gallery row OnSelect:**
```yaml
                  OnSelect: |-
                    =Set(varSelected, ThisItem);
                    Navigate(ReviewDetail, ScreenTransition.Fade)
```

**Approve / Reject / Confirm buttons:** use exactly the single-panel pattern in section 5, C3.
Do not write separate Patch sequences for approve and reject.

**History gallery Items** (status dropdown Items is `=["All", "Approved", "Rejected"]`):
```yaml
                  Items: |-
                    =SortByColumns(
                      Filter(ReviewedRequests,
                        ddHistStatus.Selected.Value = "All" Or status = ddHistStatus.Selected.Value
                      ),
                      "reviewed_date", SortOrder.Descending
                    )
```

**Date display:** `Text: =Text(ThisItem.submission_date, "yyyy-mm-dd")` and
`Text: =If(IsBlank(ThisItem.reviewed_date), "-", Text(ThisItem.reviewed_date, "yyyy-mm-dd hh:mm"))`.

Any formula not covered here must use only functions from this list:
`If`, `Switch`, `Filter`, `LookUp`, `Sort`, `SortByColumns`, `CountRows`, `First`, `IsBlank`,
`IsToday`, `Not`, `And`, `Or`, `in`, `Text`, `Value`, `Date`, `DateTimeValue`, `Now`, `Today`,
`Patch`, `Collect`, `ClearCollect`, `Clear`, `Set`, `Navigate`, `Back`, `Notify`, `User`,
`RGBA` (only inside `Theme`), `Concatenate`, `&`, `IsMatch`, `Len`, `Trim`, `Lower`, `Table`,
`ShowColumns`, `RenameColumns`, `DateAdd`, `Select`.


## 5. Clean, scalable build conventions (mandatory)

The previous build compiled but was not maintainable. Measured problems: 45 `RGBA(...)`
literals across three screens with 12 distinct colours and four different greys; the KPI
card copied three times; the name-search test repeated five times inside one `Switch`;
gallery heights like `Parent.Height - 220`; `&&`, `||`, `!` mixed with `And`, `Or`, `Not`.
Follow these conventions so none of that happens again.

### C1 — One source of truth for theme and derived data: App named formulas

Put this in `App.pa.yaml` under `Properties:` (named formulas are declarative, recompute
automatically, and cannot be accidentally overwritten):

```yaml
    Formulas: |-
      =Theme = {
        Primary: RGBA(0, 120, 212, 1),
        Accent: RGBA(0, 153, 188, 1),
        Success: RGBA(16, 124, 16, 1),
        Warning: RGBA(202, 80, 16, 1),
        Danger: RGBA(196, 43, 28, 1),
        Text: RGBA(32, 31, 30, 1),
        TextMuted: RGBA(96, 94, 92, 1),
        Border: RGBA(225, 223, 221, 1),
        Surface: RGBA(255, 255, 255, 1),
        Background: RGBA(243, 242, 241, 1)
      };
      Space = {XS: 4, S: 8, M: 16, L: 24};
      RiskBands = Table(
        {Name: "Low", Min: 1, Max: 3, Color: Theme.Success},
        {Name: "Medium", Min: 4, Max: 7, Color: Theme.Warning},
        {Name: "High", Min: 8, Max: 10, Color: Theme.Danger}
      );
      PendingRequests = Filter(KYC_Requests, status = "Pending");
      ReviewedRequests = Filter(KYC_Requests, status <> "Pending");
      ApprovedToday = Filter(KYC_Requests, status = "Approved" And IsToday(reviewed_date));
      RejectedToday = Filter(KYC_Requests, status = "Rejected" And IsToday(reviewed_date))
```

- Screen files reference `Theme.Primary`, `Space.M`, `PendingRequests`, etc.
  **Zero `RGBA(` literals are allowed in any screen file.** The only `RGBA(` calls in the
  whole app are inside `Theme`.
- Risk colour in one place: `LookUp(RiskBands, ThisItem.risk_score >= Min And ThisItem.risk_score <= Max).Color`.
- Risk dropdown Items: `=Table({Value: "All"}, ShowColumns(RenameColumns(RiskBands, "Name", "Value"), "Value"))` (multi-line block). Filter test:
  `ddDashRisk.Selected.Value = "All" Or (risk_score >= LookUp(RiskBands, Name = ddDashRisk.Selected.Value).Min And risk_score <= LookUp(RiskBands, Name = ddDashRisk.Selected.Value).Max)`.
- If `compile_canvas` reports that `Formulas` is not a valid App property, fall back to
  `Set(Theme, {...}); Set(RiskBands, ...)` as the first statements of `OnStart` and
  keep everything else identical. Do not fall back for any other reason.

### C2 — Never duplicate a block of controls; use a gallery over a table

Three KPI cards are one horizontal Gallery whose Items is a 3-row table, not three
copied containers:

```yaml
              - galDashKpis:
                  Control: Gallery
                  Variant: Horizontal
                  Properties:
                    Height: =110
                    Items: |-
                      =Table(
                        {Label: "Pending", Count: CountRows(PendingRequests), Color: Theme.Primary},
                        {Label: "Approved today", Count: CountRows(ApprovedToday), Color: Theme.Success},
                        {Label: "Rejected today", Count: CountRows(RejectedToday), Color: Theme.Danger}
                      )
                    TemplateSize: =240
                    Width: =Parent.Width
                  Children:
                    - conDashKpiCard:
                        Control: GroupContainer
                        Variant: AutoLayout
                        Properties:
                          Fill: =Theme.Surface
                          Height: =Parent.TemplateHeight
                          LayoutDirection: =LayoutDirection.Vertical
                          PaddingBottom: =Space.M
                          PaddingLeft: =Space.M
                          PaddingRight: =Space.M
                          PaddingTop: =Space.M
                          Width: =Parent.TemplateWidth - Space.M
                        Children:
                          - lblDashKpiLabel:
                              Control: Label
                              Properties:
                                Color: =Theme.TextMuted
                                Size: =14
                                Text: =ThisItem.Label
                          - lblDashKpiCount:
                              Control: Label
                              Properties:
                                Color: =ThisItem.Color
                                FontWeight: =FontWeight.Bold
                                Size: =32
                                Text: =ThisItem.Count
```

Same idea for the detail screen field grid: one gallery over
`Table({Label: "Customer", Value: varSelected.customer_name}, {Label: "Email", ...}, ...)`
instead of six hand-written label pairs.

### C3 — One confirm panel, one commit formula

Approve and Reject share one panel and one write path. Keep a single text variable
`varConfirmMode` with values `""`, `"Approve"`, `"Reject"`.

- Approve button: `=Set(varConfirmMode, "Approve"); If(varSelected.risk_score <= 7, Select(btnDetailConfirm))`
  Low risk commits immediately through the shared Confirm button; high risk shows the panel.
  `Select(control)` runs that control's `OnSelect`. Do not copy the commit formula.
- Reject button: `=Set(varConfirmMode, "Reject")`.
- Panel `Visible: =Not(IsBlank(varConfirmMode))`.
- Supervisor input `Visible: =varConfirmMode = "Approve" And varSelected.risk_score > 7`.
- One Confirm button whose `OnSelect` is the **only** place `Patch`, `Collect(Audit_Log)`,
  `Notify`, and `Back()` appear on that screen:

```yaml
                  OnSelect: |-
                    =If(varConfirmMode = "Reject" And IsBlank(txtDetailNotes.Value),
                      Notify("Reviewer notes are required to reject", NotificationType.Error),
                      varConfirmMode = "Approve" And varSelected.risk_score > 7 And Not(IsMatch(txtDetailSupervisor.Value, Match.Email)),
                      Notify("Enter a valid supervisor email", NotificationType.Error),
                      Patch(KYC_Requests, LookUp(KYC_Requests, id = varSelected.id),
                        {status: If(varConfirmMode = "Reject", "Rejected", "Approved"),
                         reviewed_by: User().Email, reviewed_date: Now(), reviewer_notes: txtDetailNotes.Value});
                      Collect(Audit_Log,
                        {action_type: varConfirmMode, user: User().Email, timestamp: Now(), record_id: varSelected.id,
                         details: "Status Pending -> " & If(varConfirmMode = "Reject", "Rejected", "Approved") &
                                  If(IsBlank(txtDetailSupervisor.Value), "", "; supervisor " & txtDetailSupervisor.Value) &
                                  "; notes: " & txtDetailNotes.Value});
                      Notify("Request " & If(varConfirmMode = "Reject", "rejected", "approved"), NotificationType.Success);
                      Set(varConfirmMode, "");
                      Back()
                    )
```

### C4 — Layout without magic numbers

- Every screen: one root `GroupContainer` (`AutoLayout`, Vertical, `Width = Parent.Width`,
  `Height = Parent.Height`, padding `Space.L`, gap `Space.M`).
- Header, filter bar, KPI row: `FillPortions: =0` plus a fixed `Height`.
- The main gallery: `FillPortions: =1` and **no** `Height`. Never write `Parent.Height - N`.
- Side-by-side equal columns: each child `FillPortions: =1`, no fixed `Width`.
- All padding and gaps use `Space.*`. No raw `15`, `20`, `30`.
- Nesting depth: at most 5 containers deep. If deeper, restructure.

### C5 — Formula style

- Boolean operators: `And`, `Or`, `Not(...)`. Never `&&`, `||`, `!`.
- Filters build on the named formulas: `Filter(PendingRequests, ...)`, never
  `Filter(KYC_Requests, status = "Pending" And ...)` repeated per screen.
- One condition per line inside multi-line `Filter` and `If`.
- No label text ending in a colon (write `"Risk filter"`, not `"Risk filter:"`). This
  also avoids YAML Rule 2.
- Every `Collect(Audit_Log, ...)` `details` text says what changed (old status, new status,
  supervisor if any, notes). Never `"ok"`.
- Every input gets `Placeholder` and `AccessibleLabel`. Every gallery gets a sibling empty
  state label (`Visible: =galX.AllItemsCount = 0`) styled with `Theme.TextMuted`.
- Seed dates relative to today so KPIs and history are testable:
  `submission_date: DateAdd(Today(), -3, TimeUnit.Days)`.

### C6 — Variables

- `varSelected` (record) and `varConfirmMode` (text) are the only global variables.
  Both are initialised at the end of `OnStart`: `Set(varSelected, Blank()); Set(varConfirmMode, "")`.
- No `UpdateContext`, no per-screen `varShow...` flags.

### C7 — Naming and file hygiene

- Control names: type prefix + screen tag + purpose: `con`, `lbl`, `btn`, `txt`, `dd`,
  `gal` + `Dash` / `Detail` / `Hist` (e.g. `galDashPending`, `txtDetailNotes`).
- Properties inside a control are listed alphabetically. This matches what `sync_canvas`
  writes back and keeps diffs small.
- Target size: Dashboard and History under 150 lines each, ReviewDetail under 220.


## 6. Build rules

- `App.pa.yaml`: `OnStart` seeds collections; `StartScreen` set to the first screen. Never
  `Navigate` from `OnStart`.
- Reuse the existing `Screen1` key for the first screen. One file per screen.
- Control names must be unique across the whole app (section 5, C7).
- Responsive layout: one root GroupContainer per screen (section 5, C4).
- No hard-coded secrets, emails, or keys in formulas. Current user is `User().Email`.

## 7. Validate loop

1. Run `check-yaml.sh` (section 3, Rule 9). Fix everything it flags until it prints nothing.
2. `compile_canvas(directory="<WORKDIR>")`
3. For **each** error, read the exact line number it names, print that line, classify it
   with the table below, apply the matching fix, and move to the next error. Fix in place
   with targeted edits. Do not regenerate whole files.

   | Error text contains | Cause | Fix |
   |---|---|---|
   | `Power Fx expressions must start with '='` | Missing `=` (usually first line under `\|-`) | Rule 3 |
   | `found invalid mapping` / `mapping values are not allowed` | `:` inside a single-line formula | Rule 2 → Rule 3 |
   | `found character that cannot start any token` / `#` | `#` in a single-line formula, or quotes around formula | Rule 3 / Rule 4 |
   | `bad indentation` / `could not find expected ':'` | Wrong indent depth in a block or `Children` list | Rule 3 / Rule 8 |
   | `Unknown property` / `is not a property of` | Property name not in `describe_control` | Rule 7 |
   | `Name isn't valid` / `Unexpected characters` in an enum | Enum written without quoted namespace | Rule 6 |
   | `Invalid argument type` on `.Selected` / `.Text` / `.Value` | Wrong member for modern control | Rule 7 |
   | `unknown or unsupported function` | Function does not exist in Power Fx | section 4 table |
   | `Invalid number of arguments` | Wrong signature (`Search`, `ClearCollect`) | section 4 table |
   | `does not match the expected type 'Blank'` | Seed row used untyped `Blank()` | `DateTimeValue("")` in seed |
   | `Name isn't valid` on a column | Column missing from the seed rows | add it back to every seed row |
   | `Use AllItemsCount instead of CountRows` | App-checker perf rule | `gal.AllItemsCount` |

4. **Never apply the same edit to the same line twice.** If a line errors again after a fix,
   the fix was wrong: convert that property to the Rule 3 multi-line form and remove any
   quotes, then re-check Rules 6 and 7 for that control.
5. Repeat until zero errors. Cap at 8 compile rounds; if still failing, list the remaining
   errors with their line text and stop.
6. `sync_canvas` again so the app appears in the open Studio tab.
7. `get_appchecker_errors()` if the tool exists in the list from section 1; otherwise skip.


## 8. Report

Print a short summary: files written, screens, control count per screen, line count per
file, number of `RGBA(` literals outside `App.pa.yaml` (must be 0), number of
`&&`/`||`/`!` occurrences (must be 0), compile status, and any open errors. Then stop.

## 9. Reference

- [Power Fx YAML formula grammar](https://learn.microsoft.com/en-us/power-platform/power-fx/yaml-formula-grammar)
- [Canvas app source files (pa.yaml)](https://learn.microsoft.com/en-us/power-apps/maker/canvas-apps/power-apps-yaml)
- [pa.yaml v3.0 schema](https://raw.githubusercontent.com/microsoft/PowerApps-Tooling/refs/heads/master/schemas/pa-yaml/v3.0/pa.schema.yaml)
- Checker: `scripts/check-yaml.sh <WORKDIR>` (next to this file)
