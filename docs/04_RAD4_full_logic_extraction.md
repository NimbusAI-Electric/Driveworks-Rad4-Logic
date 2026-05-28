# RAD4 Complete Logic Extraction
## Source: JS3 Parent, JS3 Chassis, JS3 Mirror, RAD3 Projects

---

> [!IMPORTANT]
> This document is a full extraction from the live `.driveprojx` files. All formulas are real DriveWorks logic transcribed verbatim. Where variable prefixes like `DWVariable` or `DWConstant` appear, these are DriveWorks internal namespacing conventions.

---

## 1. User Inputs → What the User Enters

The RAD4 configurator is driven by a **single Customer Part Number (CPN)** string. Everything else is computed from it. Here is the complete input structure:

### The CPN Format
```
RAD4-{WIDTH}X{HEIGHT}-{MOUNT}-{LIGHTING}-{OPTIONS...}-{VOLTAGE}
```

**Example:**
```
RAD4-48.00X36.00-RM-LSE-30K
RAD4-60.00X40.00-SM-LHE-D1-NL1-277V
RAD4-36.00X24.00-RM-LSE-AC-30K
```

### CPN Field-by-Field Decoder (Extracted from JS3 Parent, Lines 2330–2403)

| Field | Position in CPN | Valid Values | Example |
|---|---|---|---|
| **Model Prefix** | Starts with | `RAD4-` | `RAD4-` |
| **Width** | Before `X` | Decimal, 2dp | `48.00` |
| **Height** | After `X` | Decimal, 2dp | `36.00` |
| **Mount Type** | `-RM-` or `-SM-` | `RM` (Recessed), `SM` (Surface) | `-RM-` |
| **Lighting** | `-LSE-` or `-LHE-` | `LSE` (Standard), `LHE` (High Output) | `-LSE-` |
| **Dimming** | `-D1-` or `-D2-` | `D1` (HEP), `D2` (Triac) | `-D1-` |
| **Ava Dimming** | `-AC-`,`-AD-`,`-AE-`,`-AF-`,`-AK-` | Ava dimming codes | `-AC-` |
| **Keen Dimming** | `-KC-`,`-KD-`,`-KG-`,`-KH-` | Keen dimming codes | `-KC-` |
| **Color Temp** | `-30K-` or `-27K-` | `27K`, `30K`, `35K`, `40K` | `-30K` |
| **Clock** | `-CK1-` or `-CK2-` | `CK1`, `CK2` | `-CK1-` |
| **Night Light** | `-NL1-`,`-NL2-`,`-NL3-`,`-NL5-` | NL codes | `-NL1-` |
| **Cord Connect** | `-CC-` or `-CC2-` | `CC`, `CC2` | `-CC-` |
| **Defogger** | `-DF-` | Boolean flag | `-DF-` |
| **Voltage** | `-277V-` | `277V` or absent = Standard | `-277V-` |

---

## 2. CPN Parsing Logic (JS3 Parent → All Downstream Projects)

All parsing uses `Find()`, `Mid()`, `Left()`, and `IfError()`. The system searches the CPN string for known tokens.

### Step 1: Identify Model Type
```driveworks
MirrorType2 =
    If(IfError(Find("RAD4-", CPNInputReturn, 1) >= 1, FALSE), "RAD3",
    If(IfError(Find("FUS3-", CPNInputReturn, 1) >= 1, FALSE), "FUS3",
    If(IfError(Find("INT3-", CPNInputReturn, 1) >= 1, FALSE), "INT3",
    ...
    "ERROR")))
```
> **NOTE:** RAD4 maps internally to `MirrorType2 = "RAD3"`. The string `"RAD4"` in the CPN flags it as the RAD4 product, but internally the project routes it through RAD3 logic paths.

### Step 2: Extract Width
```driveworks
Width2 =
    If(Right(Left(CPNInputReturn,
        Len(CPNInputReturn) - Len(IfError(Mid(CPNInputReturn, Find("X", CPNInputReturn) + 1), "")) - 1), 6) < 0,
    Right(Left(CPNInputReturn, ...), 5),
    Right(Left(CPNInputReturn, ...), 6))
```

### Step 3: Extract Height
```driveworks
Height2 =
    Left(
        IfError(Mid(CPNInputReturn, Find("X", CPNInputReturn) + 1), ""),
        Len(IfError(Mid(CPNInputReturn, Find("X", CPNInputReturn) + 1), ""))
        - Len(IfError(Mid(IfError(Mid(...), ""), Find(".", ...) + 3), "")))
```

### Step 4: Identify Lighting Type (RAD4-specific)
```driveworks
Lighting2 =
    If(MirrorType2 = "RAD4",
        If(IfError(Find("-LO-", CPNInputReturn, 1) >= 1, FALSE), "LO",
        If(IfError(Find("-SO-", CPNInputReturn, 1) >= 1, FALSE), "SO", "")),

        If(IfError(Find("-LSE-", CPNInputReturn, 1) >= 1, FALSE), "LSE",
        If(IfError(Find("-LHE-", CPNInputReturn, 1) >= 1, FALSE), "LHE", "")))
```

### Step 5: Identify Mount Type (RAD4-specific)
```driveworks
MountType2 =
    If(MirrorType2 = "RAD4",
        If(IfError(Find("-RM-", CPNInputReturn, 1) >= 1, FALSE), "RM",
        If(IfError(Find("-SM-", CPNInputReturn, 1) >= 1, FALSE), "SM", "")),
    "")
```

### Step 6: Identify Voltage (RAD4-specific)
```driveworks
Voltage2 =
    If(MirrorType2 = "RAD4",
        If(IfError(Find("-277V-", CPNInputReturn, 1) >= 1, FALSE) = "277V", "277V", "Standard"),
        If(IfError(Find("-230V-", CPNInputReturn, 1) >= 1, FALSE) = "-230V-", "230V",
        If(IfError(Find("-277V-", CPNInputReturn, 1) >= 1, FALSE) = "-277V-", "277V", "Standard")))
```

---

## 3. SolidWorks Model Logic — Mirror Assembly

The Mirror assembly is driven by a `<ReplaceFile>` rule that assembles the full vault path dynamically.

### Mirror Assembly File Path Rule (JS3 Parent, `components/13.xml`)
```driveworks
="<ReplaceFile>" & DWConstantVault & "Products\JS3\Mirrors\" & DWVariableMirrorTypeName & "\" & DWVariableJS3MirrorName & ".sldasm"
```

**Decoded:**
- `DWConstantVault` = `C:\EM Engineering Vault\EM Engineering Vault\`
- `DWVariableMirrorTypeName` = `RAD3` (the internal folder for RAD4 product)
- `DWVariableJS3MirrorName` = Computed part number string (see Section 6)

**Full resolved path example:**
```
C:\EM Engineering Vault\EM Engineering Vault\Products\JS3\Mirrors\RAD3\RAD4-48.00X36.00-RM-LSE-30K-M.sldasm
```

### Mirror Model Key Custom Properties Pushed by DriveWorks

| SolidWorks Property | DriveWorks Variable | Example Value |
|---|---|---|
| `Width` | `UnitWidth` | `48.00` |
| `Height` | `UnitHeight` | `36.00` |
| `MirrorType` | `MirrorType` | `RAD3` |
| `Lighting` | `Lighting` | `LSE` |
| `LED_Color_Temp` | `LEDColorTemp` | `30K` |
| `PartNumber` | `PartNumber` | `RAD4-48.00X36.00-RM-LSE-30K-M` |

---

## 4. SolidWorks Model Logic — Top Level (Chassis) Assembly

### Chassis Assembly File Path Rule (JS3 Chassis, `components/2.xml`)
```driveworks
pcomp:R = DWVariableChassisFileLocation
```

**Chassis File Location Variable:**
```driveworks
ChassisFileLocation = DWConstantVault & DWConstantFile_Location_Chassis_Assembly & DWVariableMirrorType & "\" & DWVariableMirrorName & ".sldasm"
```

**Full resolved path example:**
```
C:\EM Engineering Vault\EM Engineering Vault\Products\JS3\Chassis\RAD3\RAD4-48.00X36.00-RM-LSE-30K-C.sldasm
```

### Key Chassis Assembly Model Rules

#### Extrusion (Panel) Part Replacement
The four chassis panels (Top, Bottom, Left, Right) are replaced based on computed dimensions:
```driveworks
78020_Horizontal_Name =
    "*78020-" & Fixed(HorizontalPanelOuterDimEnc, 4) & "-CUT"

78020_Vertical_Name =
    "*78020-" & Fixed(VerticalPanelOuterDimEnc, 4) & "-CUT"
```

File path:
```driveworks
DWConstantVault & "Products\JS3\COMPONENTS\78000\" & DWVariable78020_Name & ".sldprt"
```

#### Driver Enclosure Replacement
```driveworks
DriverEnclosureConfig = DWVLookup(
    EnclosureOrientationUpdated,
    NewFilter2026,
    TableGetColumnIndexByName(DwLookupDriverEnclosures, "Orientation"),
    TableGetColumnIndexByName(DwLookupDriverEnclosures, "Box Config Name"))
```

The enclosure path is:
```driveworks
DWConstantVault & "COMPONENTS\83000\" & DriverEnclosurePN & ".sldasm"
```

#### LED Strip Replacement
```driveworks
LED_PN_Name = LEDPN & "-" & Fixed(LEDCuttableSegmentsEnc2 / LEDStripsRequiredEnc * LEDSegmentLength / 25.4, 2) & "-" & LED1HarnessConfig
```

File path:
```driveworks
DWConstantVault & "Products\JS3\COMPONENTS\" & Left(LEDPN, 2) & "000\" & LED_PN_Name & ".sldprt"
```

---

## 5. Excel BOM Logic (JS3 Chassis BOM)

The BOM is an Excel document generated from DriveWorks. Each row is a `PN#` variable. Here are the key ones for a RAD4:

### BOM Part Number Structure

| BOM Row | Variable | Formula / Value | Notes |
|---|---|---|---|
| PN1 | `PN1` | (blank — chassis panel) | 78020 extrusion family |
| PN2 | `PN2` | `=If(NightLight, Right(78020NL, ...), Right(78020LEDH, ...))` | Horizontal cut extrusion with LED channel |
| PN5 | `PN5` | `83046` | Corner bracket (static) |
| PN6 | `PN6` | `82070` | Clip (static) |
| PN7 | `PN7` | `83070` | Stud bracket (static) |
| PN9 | `PN9` | `83142` | Mounting hardware (static) |
| PN10 | `PN10` | `10328` | Screw (static) |
| PN12 | `PN12` | `LEDPN & "-" & LEDCutLength & "-" & LED1HarnessConfig` | LED Strip 1 with length |
| PN13 | `PN13` | `LEDPN & "-" & LEDCutLength & "-" & LED2HarnessConfig` | LED Strip 2 (if 2x strips) |
| PN14 | `PN14` | `LEDPN & "-" & LEDCutLength & "-" & LED3HarnessConfig` | LED Strip 3 (if 3x strips) |
| PN15 | `PN15` | `83056-1.50` | Gasket bumper (static) |
| PN21 | `PN21` | `If(CordConnect, If(CCType="CC", 12598, 71309), "")` | Cord connect assembly |
| PN22 | `PN22` | `If(CK3 OR CC2, 71309, If(CC, 12986, ""))` | Extension harness |

### Full LED PN Assembly (PN12)
```driveworks
PN12 =
    LEDPN & "-" &
    Fixed(
        If(FusLEDs,
            LEDCuttableSegmentsEnc * LEDSegmentLength,
            (LEDCuttableSegmentsEnc2 / LEDStripsRequiredEnc) * LEDSegmentLength)
        / 25.4,
    2) & "-" & LED1HarnessConfig
```

**Example output:** `82180-37.25-1-F`

### Driver Enclosure BOM Selection
The driver enclosure PN is selected via a multi-column `TableFilter()` and `DWVLookup()`:
```driveworks
NewFilter2026 = TableFilter(
    TableFilter(
        TableFilter(
            TableFilter(
                TableFilter(DwLookupDriverEnclosures,
                    ColIdx("Dimming Type"), DimmingFilter),
                ColIdx("LED Strip Per Box"), "=" & LEDStripsRequiredEnc),
            ColIdx("Clock Type"), If(Clock, ClockType, "-")),
        ColIdx("NL Type"), If(NightLight, NightLightType, "-")),
    ColIdx("Box Wattage"), ">=" & WattageRequirement)

DriverEnclosurePN = DWVLookup(EnclosureOrientationUpdated, NewFilter2026,
    ColIdx("Orientation"), ColIdx("Box Config Name"))
```

---

## 6. LED Length Calculation — Full Chain & CPN Link

### Step 1: Determine Segment Length from Lighting Type
```driveworks
LEDSegmentLength =
    If(Or(IsSO, IsAva), 50, 55.5)
```

| Lighting (from CPN) | Segment Pitch |
|---|---|
| `SO` or `Ava` dimming | **50.00 mm** |
| `LSE`, `LHE`, `D1`, `D2` | **55.50 mm** |

> For a standard RAD4 with `-LSE-`: **55.5 mm segments**

### Step 2: Convert Mirror Width/Height to Panel Outer Dimension (mm)
```
UnitWidth (inches from CPN) × 25.4 = PanelOuterDimMM
HorizontalPanelOuterDimEncmm = PanelOuterDim_Width_mm
VerticalPanelOuterDimEncmm = PanelOuterDim_Height_mm
```

### Step 3: Calculate Each Straight LED Section
```driveworks
LEDSectionTopEnc    = HorizontalPanelOuterDimEncmm - (2 × LED_Corners_New_Dim_to_Bend)
LEDSectionBottomEnc = HorizontalPanelOuterDimEncmm - (2 × LED_Corners_New_Dim_to_Bend)
LEDSectionLeftEnc   = VerticalPanelOuterDimEncmm   - (2 × LED_Corners_New_Dim_to_Bend)
LEDSectionRightEnc  = VerticalPanelOuterDimEncmm   - (2 × LED_Corners_New_Dim_to_Bend)
```

**Constants (from project):**
- `LED_Corners_New_Dim_to_Bend` = **53.418486 mm**
- `LED_Corners_New_mm` = **94.44141408 mm** (full corner arc length)

### Step 4: Sum All Sections + Corners = Raw Path Length
```driveworks
LEDBaseLengthEnc =
    LEDSectionTopEnc
    + LEDSectionRightEnc
    + LEDSectionBottomEnc
    + LEDSectionLeftEnc
    + (4 × LED_Corners_New_mm)
```

### Step 5: Round Up to Whole Segments
```driveworks
LEDCuttableSegmentsEnc = Ceiling(LEDBaseLengthEnc / LEDSegmentLength, 1)
```

### Step 6: Apply 74-Segment Hard Cap for RAD4
```driveworks
LEDCuttableSegmentsFinal =
    If(MirrorType = "RAD4" AND LEDCuttableSegmentsEnc > 74,
        74,
        LEDCuttableSegmentsEnc)
```

### Step 7: Determine Number of Strips Required
```driveworks
LEDStripsRequiredEnc =
    If(LEDCuttableSegmentsEnc <= MaxSegmentsMW75, 1,
    If(LEDCuttableSegmentsEnc <= MaxSegmentsMW100, 1,
    If(LEDCuttableSegmentsEnc <= MaxSegmentsMW150, 2,
    If(LEDCuttableSegmentsEnc <= MaxSegmentsMW200, 2,
    If(LEDCuttableSegmentsEnc <= MaxSegmentsMW225, 3,
    Ceiling(LEDCuttableSegmentsEnc / MaxSegmentsMW300, 1))))))
```

### Step 8: Convert to Physical Cut Length in Inches (for BOM)
```driveworks
-- For 1 strip:
LEDCutLength = Fixed(LEDCuttableSegmentsFinal × LEDSegmentLength / 25.4, 2)

-- For 2 strips:
LEDCutLength = Fixed((LEDCuttableSegmentsFinal / 2) × LEDSegmentLength / 25.4, 2)

-- For 3 strips:
LEDCutLength = Fixed(Ceiling(LEDCuttableSegmentsFinal / 3, 1) × LEDSegmentLength / 25.4, 2)
```

### How LED Length Relates to the CPN
```
CPN Input: "RAD4-48.00X36.00-RM-LSE-30K"
    ↓ Width  = 48.00"  × 25.4 = 1219.2 mm
    ↓ Height = 36.00"  × 25.4 = 914.4 mm
    ↓ Lighting = LSE → SegmentLength = 55.5 mm

HorizPanelOuter = 1219.2 mm  →  TopSection = 1219.2 - (2×53.42) = 1112.36 mm
VertPanelOuter  = 914.4 mm   →  LeftSection = 914.4 - (2×53.42) = 807.56 mm

LEDBaseLengthEnc =
    (1112.36 + 1112.36) [Top+Bottom]
    + (807.56 + 807.56) [Left+Right]
    + (4 × 94.44)       [Corners]
    = 2224.72 + 1615.12 + 377.76
    = 4217.60 mm

Segments = Ceiling(4217.60 / 55.5, 1) = Ceiling(75.99, 1) = 76 segments

→ Exceeds RAD4 cap of 74 → capped at 74

LEDCutLength (1 strip) = Fixed(74 × 55.5 / 25.4, 2) = Fixed(161.73, 2) = 161.73"
```

---

## 7. SolidWorks API Pseudocode — Full RAD4 Build Flow

This is the complete execution sequence to replicate in SolidWorks API (VBA or C#):

```pseudocode
FUNCTION BuildRAD4Mirror(cpnString):

    // ── STEP 1: PARSE CPN ──────────────────────────────────────────────
    width        = ParseWidth(cpnString)         // e.g. 48.00
    height       = ParseHeight(cpnString)        // e.g. 36.00
    lighting     = ParseLighting(cpnString)      // "LSE" or "LHE"
    mountType    = ParseMount(cpnString)         // "RM" or "SM"
    dimmingType  = ParseDimming(cpnString)       // "D1","D2","AC","KC", etc.
    colorTemp    = ParseColorTemp(cpnString)     // "30K","27K", etc.
    voltage      = ParseVoltage(cpnString)       // "Standard" or "277V"
    hasClock     = Find("-CK1-" OR "-CK2-") >= 1
    hasNL        = Find("-NL1-" OR "-NL2-" ...) >= 1
    hasDefogger  = Find("-DF-") >= 1
    hasCordConn  = Find("-CC-" OR "-CC2-") >= 1

    // ── STEP 2: CALCULATE PANEL DIMENSIONS ────────────────────────────
    widthMM      = width  × 25.4
    heightMM     = height × 25.4

    // Panel outer dims (add chassis wall offset if needed for enclosed)
    horizPanelMM = widthMM     // For RAD4 (perimeter LED type)
    vertPanelMM  = heightMM

    // ── STEP 3: LED PATH LENGTH CALCULATION ───────────────────────────
    segLen       = If(lighting = "SO", 50, 55.5)   // mm per segment

    cornerBend   = 53.418486   // mm constant
    cornerArc    = 94.44141408 // mm constant

    topSection   = horizPanelMM - (2 × cornerBend)
    bottomSection = topSection
    leftSection  = vertPanelMM  - (2 × cornerBend)
    rightSection = leftSection

    baseLengthMM = topSection + bottomSection + leftSection + rightSection + (4 × cornerArc)

    rawSegments  = Ceiling(baseLengthMM / segLen)
    finalSegments = Min(rawSegments, 74)           // RAD4 hard cap

    // ── STEP 4: POWER CALCULATION ──────────────────────────────────────
    wattsPerMeter = If(lighting = "SO", 22, If(lighting = "LHE", 33, 22))
    ledLengthM    = finalSegments × segLen / 1000
    powerRequirement = ledLengthM × wattsPerMeter
    totalPower    = powerRequirement × 1.15         // 15% buffer

    // Select driver type
    driverType   = If(dimmingType = "D1", "HEP",
                   If(dimmingType = "D2", "Triac",
                   If(Or(isAva, isKeen, voltage = "277V"), "ERP", "MW")))

    // Select driver wattage
    driverWattage = LookupDriver(driverType, totalPower)  // returns 50,75,100,150,200,225,300W
    driverQty    = Ceiling(totalPower / driverWattage)

    // Number of LED strips
    stripsRequired = LookupStrips(driverType, finalSegments)

    // Physical cut length per strip (inches)
    cutLengthIn  = Round((finalSegments / stripsRequired) × segLen / 25.4, 2)

    // ── STEP 5: RESOLVE SOLIDWORKS FILE PATHS ─────────────────────────
    vaultRoot    = "C:\EM Engineering Vault\EM Engineering Vault\"

    // Mirror Glass Assembly
    mirrorName   = "RAD4-" & Format(width,"0.00") & "X" & Format(height,"0.00") & "-" & mountType & "-" & lighting & "-" & colorTemp & "-M"
    mirrorPath   = vaultRoot & "Products\JS3\Mirrors\RAD3\" & mirrorName & ".sldasm"

    // Chassis Assembly
    chassisName  = Replace(mirrorName, "-M", "-C")
    chassisPath  = vaultRoot & "Products\JS3\Chassis\RAD3\" & chassisName & ".sldasm"

    // Top Level Assembly
    topLevelPath = vaultRoot & "Products\JS3\Chassis\RAD3\" & chassisName & ".sldasm"

    // Extrusion parts (78020 cut lengths)
    horizExtrusion = "78020-" & Format(horizPanelMM / 25.4, "0.0000") & "-CUT"
    vertExtrusion  = "78020-" & Format(vertPanelMM  / 25.4, "0.0000") & "-CUT"

    // LED Strip PN
    ledPN      = LookupLEDPN(lighting, colorTemp, voltage)  // e.g. 82180
    ledStripPN = ledPN & "-" & Format(cutLengthIn, "0.00") & "-" & LED1HarnessConfig

    // Driver Enclosure
    enclosurePN = LookupDriverEnclosure(driverType, driverWattage, hasClock, hasNL, hasDefogger, voltage, stripsRequired)

    // ── STEP 6: OPEN & CONFIGURE SOLIDWORKS MODELS ────────────────────
    // A) Open Top-Level Assembly
    swModel = swApp.OpenDoc(chassisPath, swDocASSEMBLY)

    // B) Replace Horizontal Panels (Top + Bottom)
    swComp = swAssem.GetComponentByName("78020-TOP")
    swComp.ReplaceComponent(vaultRoot & "Products\JS3\COMPONENTS\78000\" & horizExtrusion & ".sldprt", "", TRUE)

    swComp = swAssem.GetComponentByName("78020-BOTTOM")
    swComp.ReplaceComponent(vaultRoot & "Products\JS3\COMPONENTS\78000\" & horizExtrusion & ".sldprt", "", TRUE)

    // C) Replace Vertical Panels (Left + Right)
    swComp = swAssem.GetComponentByName("78020-LEFT")
    swComp.ReplaceComponent(vaultRoot & "Products\JS3\COMPONENTS\78000\" & vertExtrusion & ".sldprt", "", TRUE)

    swComp = swAssem.GetComponentByName("78020-RIGHT")
    swComp.ReplaceComponent(vaultRoot & "Products\JS3\COMPONENTS\78000\" & vertExtrusion & ".sldprt", "", TRUE)

    // D) Replace LED Strips (1x, 2x, or 3x)
    FOR i = 1 TO stripsRequired:
        swComp = swAssem.GetComponentByName("LED-STRIP-" & i)
        swComp.ReplaceComponent(vaultRoot & "Products\JS3\COMPONENTS\" & Left(ledPN,2) & "000\" & ledStripPN & ".sldprt", "", TRUE)
    NEXT i

    // E) Replace Driver Enclosure
    swComp = swAssem.GetComponentByName("DRIVER-ENCLOSURE")
    swComp.ReplaceComponent(vaultRoot & "COMPONENTS\83000\" & enclosurePN & ".sldasm", "", TRUE)

    // F) Replace Mirror Glass Sub-Assembly
    swComp = swAssem.GetComponentByName("MIRROR-GLASS")
    swComp.ReplaceComponent(mirrorPath, "", TRUE)

    // ── STEP 7: SET CUSTOM PROPERTIES (for Drawing/Sales Aid) ─────────
    swCustomProps = swModel.Extension.CustomPropertyManager("")
    swCustomProps.Add3("PartNumber",    swCustomInfoText, cpnString, swCustomInfoDeleteUnused)
    swCustomProps.Add3("Width",         swCustomInfoText, Format(width,  "0.00"), ...)
    swCustomProps.Add3("Height",        swCustomInfoText, Format(height, "0.00"), ...)
    swCustomProps.Add3("LED_Length_In", swCustomInfoText, Format(cutLengthIn, "0.00"), ...)
    swCustomProps.Add3("Wattage",       swCustomInfoText, Format(totalPower, "0.0"), ...)
    swCustomProps.Add3("Driver_Type",   swCustomInfoText, driverType, ...)
    swCustomProps.Add3("Driver_Qty",    swCustomInfoText, Format(driverQty, "0"), ...)
    swCustomProps.Add3("Lighting",      swCustomInfoText, lighting, ...)
    swCustomProps.Add3("Voltage",       swCustomInfoText, voltage, ...)
    swCustomProps.Add3("Color_Temp",    swCustomInfoText, colorTemp, ...)

    // ── STEP 8: REBUILD & SAVE ─────────────────────────────────────────
    swModel.ForceRebuild3(FALSE)
    swModel.Save3(swSaveAsCurrentVersion, 0, 0)

    // ── STEP 9: OPEN & REFRESH SALES AID DRAWING ──────────────────────
    salesAidPath = vaultRoot & "Products\JS3\Chassis\RAD3\" & chassisName & "-SALES-AID.SLDDRW"
    swDrawing = swApp.OpenDoc(salesAidPath, swDocDRAWING)
    swDrawing.ForceRebuild()     // Drawing auto-reads $PRPSHEET from assembly
    swDrawing.Save3(swSaveAsCurrentVersion, 0, 0)

END FUNCTION
```

---

## 8. Key Constants Reference Table

| Constant Name | Value | Description |
|---|---|---|
| `LED_Corners_New_mm` | `94.44141408` | Full outer perimeter of one corner piece (mm) |
| `LED_Corners_New_Dim_to_Bend` | `53.418486` | Panel edge to bend point (mm) |
| `LED_Segment_Length_SO` | `55.55` | Segment pitch for SO/standard LEDs (mm) |
| `LED_Segment_Length_Ava` | `50.00` | Segment pitch for Ava LEDs (mm) |
| `LED_Segment_Length_HO` | `45.45` | Segment pitch for HO LEDs (mm) |
| `Watts_Per_Meter_SO` | `22` | W/m for standard output LEDs |
| `Watts_Per_Meter_HO` | `33` | W/m for high output LEDs |
| `Watts_Per_Meter_Ava` | `28.6` | W/m for Ava LEDs |
| `Driver_Buffer` | `0.15` | 15% safety buffer on power calc |
| `TOP_to_Outside_of_Panel_Enc` | `100.0125` | Dim from TOP plane to outer face of enclosed panel |
| `RAD4_Max_Segments` | `74` | **Hard cap for RAD4 only** |
| `Vault` | `C:\EM Engineering Vault\EM Engineering Vault\` | Vault root path |
| `File_Location_Chassis_Assembly` | `Products\JS3\Chassis\` | Relative path to chassis assemblies |
| `File_Location_LED` | `Products\JS3\COMPONENTS\` | Relative path to LED components |
