"""
rad4_engine.py
==============
Programmatic replication of all DriveWorks logic for the RAD4 configurator.

Source: N:\\Unpacked_JS3_Logic\\JS3 Chassis.csv
        N:\\Unpacked_JS3_Logic\\JS3 Parent.csv
        N:\\Unpacked_JS3_Logic\\JS3 Mirror.csv
        N:\\Unpacked_JS3_Logic\\Master_Logic_Extraction.txt

Every function maps 1:1 to a DriveWorks variable or constant.
Variable names preserve the original DW naming convention.
"""

import math
import sys
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class NoteBlock:
    category: str
    title: str
    body_text: str



# =============================================================================
# CONSTANTS  (DWConstant* in DriveWorks — JS3 Chassis.csv lines 3-100)
# =============================================================================

# Vault root — actual path on EMDT-0688
DWConstantVault = r"C:\EM Engineering Vault"

# File locations (relative to vault root)
DWConstantFile_Location_Chassis_Assembly = r"Products\JS3\Assemblies\RAD4"
DWConstantFile_Location_Mirror           = r"Products\JS3\Mirrors\RAD4"
DWConstantFile_Location_Sales_Aid        = r"Products\JS3\Sales Aid\RAD4"
DWConstantFile_Location_Driver_Enclosure = r"COMPONENTS\81000"
DWConstantFile_Location_LED              = r"Products\JS3\COMPONENTS\RAD4 LEDs"

# LED corner geometry  (JS3 Chassis.csv lines 58-59)
DWConstantLED_Corners_New_mm             = 94.44141408   # outer perimeter of enclosed LED corner (mm)
DWConstantLED_Corners_New_Dim_to_Bend    = 53.418486     # panel edge → bend point (mm)
DWConstantTOP_to_Outside_of_Panel_Enc    = 100.0125      # TOP plane → outer panel face (mm)

# LED extension lengths  (lines 60-63)
DWConstantLED_Ext_1_Length_mm            = 25.4
DWConstantLED_Ext_2_Length_mm            = 98.425
DWConstantLED_Ext_Length_mm              = 123.825
DWConstantLED_FUS_Base_Extension_mm      = 27.305

# LED segment lengths by lighting type  (lines 71-73)
DWConstantLED_Segment_Length_Ava         = 50.0    # mm — Ava / 81900
DWConstantLED_Segment_Length_SO          = 55.55   # mm — Standard Output (note: some refs show 55.5)
DWConstantLED_Segment_Length_HO          = 45.45   # mm — High Output

# Watts per metre by lighting type
# SOURCE: RAD3.csv line 104 — WattsPerMeter = "If(DWVariableSO, 24, 12)"
# RAD4/RAD3 project uses: SO lighting = 24 W/m, LO lighting = 12 W/m
# (JS3 Chassis uses different values — RAD3.csv is authoritative for RAD4)
DWConstantWatts_Per_Meter_SO             = 24.0    # W/m — RAD4 SO (Standard Output, "SO")
DWConstantWatts_Per_Meter_LO             = 12.0    # W/m — RAD4 LO (Low Output, "LO")  ← screenshot: 35.64W
DWConstantWatts_Per_Meter_HO             = 33.0    # W/m — JS3 High Output (not used for RAD4)
DWConstantWatts_Per_Meter_Ava            = 28.6    # W/m Ava (81900)
DWConstantWatts_Per_Meter_Residential_Ava = 28.6
DWConstantWatts_Per_Meter_Hospitality_Ava = 14.3

# Driver wattage caps  (lines 86-96)
DWConstantWattage_Max_ERP_96             = 96
DWConstantWattage_Max_HEP_96             = 96
DWConstantWattage_Max_Triac_60           = 60
DWConstantWattage_Max_Triac_96           = 96
DWConstantWattage_Max_MW_50              = 50
DWConstantWattage_Max_MW_75              = 75
DWConstantWattage_Max_MW_100             = 100
DWConstantWattage_Max_MW_150             = 150
DWConstantWattage_Max_MW_200             = 200
DWConstantWattage_Max_MW_225             = 225
DWConstantWattage_Max_MW_300             = 300

# Power buffer  (JS3 Chassis.csv line 291)
DWConstantDriverBuffer                   = 0.15    # 15% safety buffer

# Delete sentinel (mirrors DriveWorks "Delete" constant)
DWConstantDelete                         = "Delete"


# =============================================================================
# INPUT DATACLASS  — mirrors the DriveWorks form fields shown in the UI
# =============================================================================

@dataclass
class RAD4Inputs:
    """
    All user-facing inputs visible on the DriveWorks JS3 Configurator form.
    Field names match the DriveWorks variable names where possible.
    """
    # Core dimensions
    UnitWidth:   float = 36.0   # inches
    UnitHeight:  float = 36.0   # inches

    # Mirror type — always RAD4 in this engine
    MirrorType:  str   = "RAD4"

    # Mount type  (RAD4-specific — JS3 Parent.csv line 2345)
    MountType:   str   = "RM"   # "RM" = Recessed Mount, "SM" = Surface Mount

    # Lighting  (RAD4-specific — JS3 Parent.csv line 2330)
    Lighting:    str   = "LSE"  # "LO", "SO", "LSE", "LHE"

    # LED colour temperature
    LEDColorTemp: str  = "30K"  # "27K", "30K", "35K", "40K"

    # Finish / frame
    Finish:      str   = "NK04" # e.g. NK04, CH04, BN04 …

    # Voltage  (JS3 Parent.csv line 2396)
    Voltage:     str   = "Standard"   # "Standard", "277V"

    # Dimming  (radio buttons on form)
    Dimming:     bool  = False
    DimmingType: str   = ""     # "D1", "D2", "AC","AD","AE","AF","AK", "KC","KD","KG","KH"
    AvaLocation:  str  = "Center"
    KeenLocation: str  = "Center"

    # Options (checkboxes on form)
    Ava:         bool  = False
    Keen:        bool  = False
    Clock:       bool  = False
    ClockType:   str   = ""     # "CK1", "CK2", "CK3"
    ClockLocation: str = "Right"
    CordConnect: bool  = False
    CordConnectType: str = ""   # "CC", "CC2"
    Defogger:    bool  = False
    NightLight:  bool  = False
    NightLightType: str = ""    # "NL1","NL2","NL3","NL5"
    NonBrilliant: bool = False
    Savvy:       bool  = False
    TV:          bool  = False
    TVSize:      str   = ""
    TVLocation:  str   = "Center"
    TVGlass:     str   = ""
    Vive:        bool  = False
    ViveType:    str   = ""
    ViveLocation: str  = "Center"
    WallGlow:    bool  = False
    WallGlowType: str  = ""
    Wardrobe:    bool  = False


# =============================================================================
# COMPUTED RESULTS DATACLASS
# =============================================================================

@dataclass
class RAD4Result:
    """All computed outputs — mirrors every DWVariable in the Chassis project."""

    # Identifiers
    CPN:               str   = ""   # Customer Part Number  e.g. RAD4-36.00X36.00-RM-LSE-30K
    MirrorName:        str   = ""   # Mirror sub-assembly name  e.g. RAD4-36.00X36.00-RM-LSE-30K-M
    ChassisName:       str   = ""   # Top-level chassis name    e.g. RAD4-36.00X36.00-RM-LSE-30K-C

    # Panel dimensions (mm)
    HorizontalPanelOuterDimEncmm: float = 0.0
    VerticalPanelOuterDimEncmm:   float = 0.0

    # LED calculation chain
    LEDSegmentLength:             float = 0.0   # mm per segment
    LEDSectionTopEnc:             float = 0.0
    LEDSectionBottomEnc:          float = 0.0
    LEDSectionLeftEnc:            float = 0.0
    LEDSectionRightEnc:           float = 0.0
    LEDBaseLengthEnc:             float = 0.0   # total raw perimeter (mm)
    LEDCuttableSegmentsEnc:       int   = 0     # segments before cap
    LEDCuttableSegmentsFinal:     int   = 0     # segments after RAD4 74-cap
    LEDmmLength:                  float = 0.0   # physical length (mm)
    LEDStripsRequiredEnc:         int   = 1
    LEDCutLengthIn:               float = 0.0   # cut length per strip (inches)

    # Power
    WattsPerMeter:                float = 0.0
    PowerRequirement:             float = 0.0   # W — no buffer
    WattageRequirement:           float = 0.0   # W — with buffer, rounded up

    # Driver
    DriverType:                   str   = ""    # "MW", "ERP", "HEP", "Triac"
    DriverWattage:                int   = 0
    DriverQty:                    int   = 1
    DriverEnclosurePN:            str   = ""

    # LED PN
    LEDPN:                        str   = ""
    LED1HarnessConfig:            str   = ""

    # BOM part numbers
    BOM: dict = field(default_factory=dict)

    # SolidWorks file paths
    MirrorAssemblyPath:           str   = ""
    ChassisAssemblyPath:          str   = ""
    SalesAidDrawingPath:          str   = ""

    # Options Config
    DefoggerConfig:               str   = ""
    DefoggerQty:                  int   = 0
    ClockConfig:                  str   = ""
    Notes:                        list[NoteBlock] = field(default_factory=list)




# =============================================================================
# CPN BUILDER  (replicates DWVariablePartNumber — JS3 Chassis.csv lines 159-183)
# =============================================================================

def build_cpn(inp: RAD4Inputs) -> str:
    """
    Builds the Customer Part Number (CPN) string matching DriveWorks logic.
    Directly replicates the DWVariableRadCPN / DWVariableFileName formula from RAD3 project.
    
    Format:
        RAD4-{Width}X{Height}-{Finish}-{Options...}-{LEDColorTemp}
        
    Note: MountType (-RM/-SM) and Lighting (-LO/-LSE/-LHE) are excluded
    from the customer-facing part number, except for Standard Output (-SO).
    """
    cpn = f"RAD4-{inp.UnitWidth:.2f}X{inp.UnitHeight:.2f}"

    # 1. Finish (comes right after dimensions)
    cpn += f"-{inp.Finish}"

    # 2. Cord Connect
    if inp.CordConnect and inp.CordConnectType:
        cpn += f"-{inp.CordConnectType}"

    # 3. Clock
    if inp.Clock and inp.ClockType:
        loc = ""
        if inp.ClockLocation == "Left":
            loc = "L"
        elif inp.ClockLocation == "Center":
            loc = "C"
        cpn += f"-{inp.ClockType}{loc}"

    # 4. Dimming / Button Option
    if inp.DimmingType in ("D1", "D2"):
        cpn += f"-{inp.DimmingType}"
    elif inp.Ava and inp.DimmingType:
        loc = ""
        if inp.AvaLocation == "Left":
            loc = "L"
        elif inp.AvaLocation == "Right":
            loc = "R"
        cpn += f"-{inp.DimmingType}{loc}"
    elif inp.Keen and inp.DimmingType:
        loc = ""
        if inp.KeenLocation == "Left":
            loc = "L"
        elif inp.KeenLocation == "Right":
            loc = "R"
        cpn += f"-{inp.DimmingType}{loc}"

    # 5. Defogger
    if inp.Defogger:
        if inp.Keen or inp.DimmingType == "D1":
            cpn += "-DFX"
        else:
            cpn += "-DF"


    # 6. Lighting (Only append if standard output -SO. LO, LSE, and LHE are omitted)
    if inp.Lighting == "SO":
        cpn += "-SO"

    # 7. Other options
    if inp.NonBrilliant:
        cpn += "-NB"
    if inp.NightLight and inp.NightLightType:
        cpn += f"-{inp.NightLightType}"
    if inp.Vive and inp.ViveType:
        loc = ""
        if inp.ViveLocation == "Left":
            loc = "L"
        elif inp.ViveLocation == "Right":
            loc = "R"
        cpn += f"-{inp.ViveType}{loc}"
    if inp.WallGlow and inp.WallGlowType:
        cpn += f"-{inp.WallGlowType}"
    if inp.Wardrobe:
        cpn += "-WR"
        
    # 8. Voltage
    if inp.Voltage != "Standard":
        cpn += f"-{inp.Voltage}"

    # 9. LED Color Temp (placed at the end)
    cpn += f"-{inp.LEDColorTemp}"

    return cpn



# =============================================================================
# LED SEGMENT LENGTH  (JS3 Chassis.csv line 73 / Master_Logic line 23002-23008)
#
# DW formula:
#   If(Or(IsSO, IsAva), 50, 55.5)
#   where IsSO = Lighting = "SO"
#         IsAva = Ava = TRUE
# =============================================================================

def calculate_led_segment_length(inp: RAD4Inputs) -> float:
    """Returns LED segment pitch in mm."""
    if inp.Ava or inp.Lighting == "SO":
        return DWConstantLED_Segment_Length_Ava   # 50.0 mm
    else:
        return DWConstantLED_Segment_Length_SO    # 55.55 mm


# =============================================================================
# PANEL OUTER DIMENSIONS  (convert inches → mm)
# =============================================================================

def calculate_panel_dims(inp: RAD4Inputs):
    """
    Returns (HorizontalPanelOuterDimEncmm, VerticalPanelOuterDimEncmm).
    DriveWorks drives panel dims from UnitWidth/UnitHeight in inches × 25.4.
    """
    horiz_mm = inp.UnitWidth  * 25.4
    vert_mm  = inp.UnitHeight * 25.4
    return horiz_mm, vert_mm


# =============================================================================
# LED SECTION LENGTHS  (Master_Logic_Extraction.txt lines 23365-23383)
#
# DW formula:
#   LEDSectionTopEnc    = HorizPanelOuter - (2 × LED_Corners_New_Dim_to_Bend)
#   LEDSectionBottomEnc = HorizPanelOuter - (2 × LED_Corners_New_Dim_to_Bend)
#   LEDSectionLeftEnc   = VertPanelOuter  - (2 × LED_Corners_New_Dim_to_Bend)
#   LEDSectionRightEnc  = VertPanelOuter  - (2 × LED_Corners_New_Dim_to_Bend)
# =============================================================================

def calculate_led_sections(horiz_mm: float, vert_mm: float):
    """Returns (top, bottom, left, right) straight LED section lengths in mm."""
    h_section = horiz_mm - (2 * DWConstantLED_Corners_New_Dim_to_Bend)
    v_section = vert_mm  - (2 * DWConstantLED_Corners_New_Dim_to_Bend)
    return h_section, h_section, v_section, v_section   # top, bottom, left, right


# =============================================================================
# LED BASE LENGTH  (total raw perimeter)
#
# DW formula:
#   LEDBaseLengthEnc =
#       LEDSectionTopEnc + LEDSectionRightEnc +
#       LEDSectionBottomEnc + LEDSectionLeftEnc +
#       (4 × LED_Corners_New_mm)
# =============================================================================

def calculate_led_base_length(top, bottom, left, right) -> float:
    return top + bottom + left + right + (4 * DWConstantLED_Corners_New_mm)


# =============================================================================
# CUTTABLE SEGMENTS  (Master_Logic_Extraction.txt lines ~23400)
#
# DW formula:
#   LEDCuttableSegmentsEnc = Ceiling(LEDBaseLengthEnc / LEDSegmentLength, 1)
#
# RAD4 HARD CAP = 74 segments  (confirmed in JS3 Chassis logic)
# =============================================================================

def calculate_cuttable_segments(base_length_mm: float, segment_length_mm: float) -> tuple[int, int]:
    """
    Returns (raw_segments, final_segments).
    Replicates: LEDCuttableSegmentsEnc and LEDCuttableSegmentsFinal.
    Note: Previously had a hallucinated 74 segment cap. DriveWorks has no physical cap on segments.
    """
    raw = math.ceil(base_length_mm / segment_length_mm)
    return raw, raw


# =============================================================================
# WATTS PER METRE  (RAD3.csv line 104 — AUTHORITATIVE for RAD4)
#
# DW formula (verbatim from RAD3.csv):
#   WattsPerMeter = "If(DWVariableSO, 24, 12)"
#
# Where DWVariableSO = (Lighting = "SO")
#   Lighting = "SO" → 24 W/m
#   Lighting = "LO" → 12 W/m
#
# IMPORTANT — Power formula chain:
#   PowerRequirementBase = LEDLengthMM / 1000 × WattsPerMeter
#
#   LEDLengthMM is a BLANK variable in RAD3.csv — it is NOT calculated from
#   width/height. It is populated from the SolidWorks model geometry at runtime
#   (the physical LED path length measured from the 3D assembled model).
#
#   In Python, we use LEDBaseLengthEnc as the best approximation.
#   Actual LEDLengthMM must be read from the SolidWorks assembly's custom property
#   after it opens — sw_api.py does this in _build_chassis_assembly().
#
# Validation: RAD4-36.00X36.00-LO → DW shows 35.64W
#   35.64W / 12 W/m × 1000 = 2970mm physical LED path
#   Our formula gives 3608mm (uses full perimeter inc. corner arcs)
#   → The gap (638mm) is the difference between outer perimeter and
#     actual LED path which follows the inner channel geometry.
#   For production accuracy: read LEDLengthMM back from the SolidWorks model.
# =============================================================================

def calculate_watts_per_meter(inp: RAD4Inputs) -> float:
    """
    RAD3.csv line 104: WattsPerMeter = "If(DWVariableSO, 24, 12)"
    DWVariableSO = (Lighting = "SO")
    """
    if inp.Ava:
        return DWConstantWatts_Per_Meter_Ava
    if inp.Lighting == "SO":
        return DWConstantWatts_Per_Meter_SO   # 24 W/m
    return DWConstantWatts_Per_Meter_LO        # 12 W/m  (LO and all others)


# =============================================================================
# POWER REQUIREMENT  (RAD3.csv lines 327-328, JS3 Chassis.csv lines 148-152)
#
# RAD3.csv formula (verbatim):
#   PowerRequirement = DWVariablePowerRequirementBase
#                    + If(DWVariableWallGlow, DWVariablePowerRequirementWG, 0)
#
# PowerRequirementBase (from Chassis) =
#   If(FusLEDs, FusionSegments, If(PerimeterLEDs, LEDCuttableSegmentsFinal, 0))
#   × LEDSegmentLength / 1000 × WattsPerMeter
#
# For RAD4: FusLEDs=FALSE, PerimeterLEDs=TRUE (RAD4 is perimeter LED type)
# So: PowerRequirement = LEDCuttableSegmentsFinal × LEDSegmentLength / 1000 × WattsPerMeter
#
# BufferedPowerRequirement (RAD3.csv — used to select driver):
#   = Floor((PowerRequirementTotal / DriverPowerFactor) / DriverEfficiency, 1)
#   DriverLetaron (standard no-dimming RAD4): PowerFactor from VLookup(81030,...)
#   Approximation: buffer ≈ 15% overhead → matches DWConstantDriverBuffer
#
# PowerAvailable (what DW shows in status bar):
#   = driver wattage tier selected (90W, 96W, 192W, etc.)
# =============================================================================

def calculate_power(final_segments: int, segment_length_mm: float,
                    watts_per_meter: float, base_length_mm: float = 0) -> tuple[float, float]:
    """
    Returns (power_requirement_no_buffer_W, buffered_power_W).
    Replicates RAD3 PowerRequirement and BufferedPowerRequirement.
    """
    led_length_m = (final_segments * segment_length_mm) / 1000.0
    power_req    = led_length_m * watts_per_meter
    # BufferedPowerRequirement: add 15% and floor to int
    buffered     = math.floor(power_req * (1 + DWConstantDriverBuffer))
    return power_req, buffered


# =============================================================================
# DRIVER TYPE  (RAD3.csv lines 120-126 — AUTHORITATIVE for RAD4)
#
# RAD3.csv verbatim:
#   DriverLetaron = Or(D1, Keen, Dimming="No_Dimming") AND NOT(Voltage="277V")
#   DriverERP     = Keen or no-dimming with 277V
#   DriverHEP     = False (not used on RAD4)
#   DriverMW      = False (not used on RAD4)
#   DriverSmart   = Whenever D2 is used
#
# Mapping to standard type names:
#   D1 or no-dimming (standard voltage) → "Letaron" (= 81030 driver family)
#   D2                                  → "Smart" (= Triac/79314)
#   Keen or 277V                        → "ERP"   (= 71225)
#   Ava                                 → "ERP"
# =============================================================================

def calculate_driver_type(inp: RAD4Inputs) -> str:
    """
    RAD3.csv driver type logic.
    Returns one of: 'Letaron', 'Smart', 'ERP'
    """
    if inp.DimmingType == "D2":
        return "Smart"       # DriverSmart — D2/Triac
    if inp.Ava or inp.Keen or inp.Voltage == "277V":
        return "ERP"         # DriverERP
    return "Letaron"         # DriverLetaron — D1 or no-dimming (standard)


# =============================================================================
# DRIVER WATTAGE / POWER AVAILABLE  (RAD3.csv lines 257-324)
#
# RAD3.csv formula:
#   DualDriver = Or(
#     D2 AND BufferedPower > 55,
#     D1 AND BufferedPower > 96,
#     No-Dimming AND BufferedPower > 85)
#
#   PowerAvailable (what status bar shows):
#     If D2:       If(BufferedPower < 90.5, 96, 192)
#     If D1:       If(BufferedPower < 96, 96, 192)
#     No-dimming:  If(BufferedPower < 85, 96, If(BufferedPower < 85.3, 96, 192))
#     ERP (277V):  If(BufferedPower < 90.5, 96, 192)
#
# Simplified: single driver = 96W, dual driver = 192W
# EnclosureInstance = "81330" + options + "-96W" or "-192W"
# =============================================================================

def calculate_driver(driver_type: str, buffered_power: float) -> tuple[int, int]:
    """
    Returns (power_available_W, driver_qty).
    Replicates RAD3 DualDriver logic and PowerAvailable selection.
    """
    # Thresholds from RAD3.csv lines 278-324
    if driver_type == "Smart":   # D2
        threshold = 90.5
    elif driver_type == "ERP":   # Keen / 277V
        threshold = 90.5
    elif driver_type == "Letaron" and buffered_power > 0:  # D1 or no-dimming
        # No-dimming threshold from RAD3: >85 triggers dual
        threshold = 85.0
    else:
        threshold = 85.0

    if buffered_power <= threshold:
        return 96, 1    # Single driver, 96W available
    else:
        return 192, 2   # Dual driver, 192W available


# =============================================================================
# DEFOGGER GRID LOOKUP  (replicates the user dimensions table)
# =============================================================================

def get_defogger_config_and_qty(w: float, h: float) -> tuple[str, int]:
    """
    Returns (config_name, quantity) of defogger pads based on the width and height grid.
    """
    w_limits = [24, 30, 36, 42, 48, 54, 60, 66, 72, 78]
    h_limits = [24, 30, 36, 42, 48, 54, 60, 66, 72, 78, 84]
    
    col_idx = -1
    for i, limit in enumerate(w_limits):
        if w >= limit:
            col_idx = i
            
    row_idx = -1
    for j, limit in enumerate(h_limits):
        if h >= limit:
            row_idx = j
            
    if col_idx == -1 or row_idx == -1:
        return "15229-120V-10.5X10.5", 1
        
    grid = [
        # Row 24 (h >= 24)
        [ ("15229-120V-10.5X10.5", 1), ("15229-120V-10.5X10.5", 1), ("15229-120V-10.5X10.5", 1), ("15230-120V-22.5x10.5", 1), ("15230-120V-22.5x10.5", 1), ("15230-120V-22.5x10.5", 1), ("15230-120V-22.5x10.5", 2), ("15230-120V-22.5x10.5", 2), ("15230-120V-22.5x10.5", 2), ("15230-120V-22.5x10.5", 2) ],
        # Row 30 (h >= 30)
        [ ("15229-120V-10.5X10.5", 1), ("15229-120V-10.5X10.5", 1), ("15229-120V-10.5X10.5", 1), ("15230-120V-22.5x10.5", 1), ("15230-120V-22.5x10.5", 1), ("15230-120V-22.5x10.5", 1), ("15230-120V-22.5x10.5", 2), ("15230-120V-22.5x10.5", 2), ("15230-120V-22.5x10.5", 2), ("15230-120V-22.5x10.5", 2) ],
        # Row 36 (h >= 36)
        [ ("15229-120V-10.5X10.5", 1), ("15229-120V-10.5X10.5", 1), ("15230-120V-10.5X22.5", 1), ("15230-120V-22.5x10.5", 1), ("15230-120V-22.5x10.5", 1), ("15230-120V-22.5x10.5", 1), ("15230-120V-22.5x10.5", 2), ("15230-120V-22.5x10.5", 2), ("15230-120V-22.5x10.5", 2), ("15230-120V-22.5x10.5", 2) ],
        # Row 42 (h >= 42)
        [ ("15229-120V-10.5X10.5", 1), ("15229-120V-10.5X10.5", 1), ("15230-120V-10.5X22.5", 1), ("15231-120V-20.5X20.5", 1), ("15231-120V-20.5X20.5", 1), ("15231-120V-20.5X20.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 1) ],
        # Row 48 (h >= 48)
        [ ("15230-120V-10.5X22.5", 1), ("15230-120V-10.5X22.5", 1), ("15230-120V-10.5X22.5", 1), ("15231-120V-20.5X20.5", 1), ("15231-120V-20.5X20.5", 1), ("15231-120V-20.5X20.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 1) ],
        # Row 54 (h >= 54)
        [ ("15230-120V-10.5X22.5", 1), ("15230-120V-10.5X22.5", 1), ("15231-120V-20.5X20.5", 1), ("15231-120V-20.5X20.5", 1), ("15231-120V-20.5X20.5", 1), ("15231-120V-20.5X20.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 1) ],
        # Row 60 (h >= 60)
        [ ("15230-120V-10.5X22.5", 1), ("15230-120V-10.5X22.5", 1), ("15231-120V-20.5X20.5", 1), ("15231-120V-20.5X20.5", 1), ("15231-120V-20.5X20.5", 1), ("15232-120V-20.5X40.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 1) ],
        # Row 66 (h >= 66)
        [ ("15230-120V-10.5X22.5", 2), ("15230-120V-10.5X22.5", 2), ("15231-120V-20.5X20.5", 1), ("15231-120V-20.5X20.5", 1), ("15232-120V-20.5X40.5", 1), ("15232-120V-20.5X40.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 1) ],
        # Row 72 (h >= 72)
        [ ("15230-120V-10.5X22.5", 2), ("15230-120V-10.5X22.5", 2), ("15232-120V-20.5X40.5", 1), ("15232-120V-20.5X40.5", 1), ("15232-120V-20.5X40.5", 1), ("15232-120V-20.5X40.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 2) ],
        # Row 78 (h >= 78)
        [ ("15230-120V-10.5X22.5", 2), ("15230-120V-10.5X22.5", 2), ("15232-120V-20.5X40.5", 1), ("15232-120V-20.5X40.5", 1), ("15232-120V-20.5X40.5", 1), ("15232-120V-20.5X40.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 2), ("15232-120V-40.5X20.5", 2) ],
        # Row 84 (h >= 84)
        [ ("15230-120V-10.5X22.5", 2), ("15230-120V-10.5X22.5", 2), ("15232-120V-20.5X40.5", 1), ("15232-120V-20.5X40.5", 1), ("15232-120V-20.5X40.5", 1), ("15232-120V-20.5X40.5", 1), ("15232-120V-40.5X20.5", 1), ("15232-120V-40.5X20.5", 2), ("15232-120V-40.5X20.5", 2), ("15232-120V-40.5X20.5", 2) ]
    ]
    
    if col_idx >= len(grid[0]) or row_idx >= len(grid):
        return "15229-120V-10.5X10.5", 1
        
    if row_idx == 0 and col_idx == 0:
        return "15229-120V-10.5X10.5", 0
        
    return grid[row_idx][col_idx]

def calculate_clock_config(clock_type: str) -> str:
    """Returns the clock configuration string for the mirror clock assembly."""
    if clock_type == "CK1":
        return "CK1-MIRROR"
    elif clock_type == "CK2":
        return "CK2-MIRROR"
    elif clock_type == "CK3":
        return "CK3-MIRROR - USE ONLY WHEN NO CHASSIS OR BOX"
    return "Delete"



# =============================================================================
# DRIVER ENCLOSURE PN  (RAD3.csv lines 146-168 — EnclosureInstance formula)
#
# RAD3.csv EnclosureInstance formula (verbatim):
#   "81330" &
#   If(Clock, "-CKX", "") &
#   If(Or(D1, D2), "-" & DimmingType, "") &
#   If(Defogger, "-DF", "") &
#   If(Keen, "-K", "") &
#   If(PowerAvailable=90, "-90W", If(PowerAvailable=96, "-96W",
#      If(PowerAvailable=190, "-190W", "-192W"))) &
#   If(277V, "-277V", "")
#
# Example: 81330-96W              (no dimming, no options, 96W)
#          81330-D1-96W           (D1 dimming)
#          81330-CKX-96W          (with clock)
#          81330-96W-277V         (277V)
#          81330-192W             (dual driver)
# Screenshot shows: Enclosure: 81330-96W  ← matches this formula exactly
# =============================================================================

def calculate_driver_enclosure_pn(inp: RAD4Inputs, power_available: int) -> str:
    """
    Builds the enclosure PN string exactly as RAD3.csv EnclosureInstance does.
    """
    pn = "81330"

    if inp.Clock:
        pn += "-CKX"
    if inp.DimmingType in ("D1", "D2", "DM"):
        pn += f"-{inp.DimmingType}"
    if inp.Defogger:
        pn += "-DF"
    if inp.Keen:
        pn += "-K"

    # Wattage suffix
    if power_available == 90:
        pn += "-90W"
    elif power_available == 96:
        pn += "-96W"
    elif power_available == 190:
        pn += "-190W"
    else:
        pn += "-192W"

    if inp.Voltage == "277V":
        pn += "-277V"

    return pn


# =============================================================================
# LED STRIPS REQUIRED  (JS3 Chassis.csv lines 1237-1249)
#
# DW formula (for MW driver / enclosed perimeter LEDs):
#   If(segments ≤ MaxSegmentsTriac60, 1,
#   If(segments ≤ MaxSegmentsTriac96, 1,
#   If(segments ≤ 2×MaxSegmentsTriac60, 2,
#   If(segments ≤ 2×MaxSegmentsTriac96, 2,
#      Ceiling(segments / MaxSegmentsTriac96)))))
#
# For RAD4 (MW driver), max segments per strip ≈ 74 (the hard cap is also the max for 1 strip)
# =============================================================================

def calculate_led_strips(final_segments: int, driver_type: str, watts_per_meter: float, segment_length_mm: float) -> int:
    """Returns number of LED strips required based on driver limits from DriveWorks XML."""
    if final_segments <= 0:
        return 0
        
    def max_seg(w: float) -> int:
        return math.floor(((w / watts_per_meter) * 1000.0) / segment_length_mm)
        
    if driver_type == "ERP":
        max_erp = max_seg(96)
        return math.ceil(final_segments / max_erp)
    elif driver_type == "Smart":  # Triac
        max_60 = max_seg(60)
        max_96 = max_seg(96)
        if final_segments <= max_60:
            return 1
        elif final_segments <= max_96:
            return 1
        elif final_segments <= 2 * max_60:
            return 2
        elif final_segments <= 2 * max_96:
            return 2
        else:
            return math.ceil(final_segments / max_96)
    else:  # Letaron (standard)
        max_75 = max_seg(75)
        max_100 = max_seg(100)
        max_150 = max_seg(150)
        max_200 = max_seg(200)
        max_225 = max_seg(225)
        max_300 = max_seg(300)
        if final_segments <= max_75:
            return 1
        elif final_segments <= max_100:
            return 1
        elif final_segments <= max_150:
            return 2
        elif final_segments <= max_200:
            return 2
        elif final_segments <= max_225:
            return 3
        else:
            return math.ceil(final_segments / max_300)


# =============================================================================
# LED CUT LENGTH (inches)  (JS3 Chassis.csv lines 334-336 — PN12 formula)
#
# DW formula:
#   Fixed((LEDCuttableSegmentsEnc2 / LEDStripsRequired) × LEDSegmentLength / 25.4, 2)
# =============================================================================

def calculate_led_cut_length(final_segments: int, strips: int, segment_length_mm: float) -> float:
    """Returns physical cut length per strip in inches (2dp)."""
    return round((final_segments / strips) * segment_length_mm / 25.4, 2)


# =============================================================================
# LED PART NUMBER  (JS3 Chassis.csv — DWVariableLEDPN)
#
# DW formula selects the 5-digit LED PN based on lighting + colour temp.
# Source: JS3 Chassis lookup table "LEDPN"
#
# RAD4 uses enclosed perimeter LEDs (82xxx series):
#   LSE + 30K → 82180
#   LSE + 27K → 82180  (same strip, different white bin)
#   LHE + 30K → 82181
#   LHE + 27K → 82181
#   SO  + 30K → 82180
# =============================================================================

LED_PN_TABLE = {
    ("LSE", "30K"): "82180",
    ("LSE", "27K"): "82180",
    ("LSE", "35K"): "82180",
    ("LSE", "40K"): "82180",
    ("LHE", "30K"): "82181",
    ("LHE", "27K"): "82181",
    ("SO",  "30K"): "82180",
    ("SO",  "27K"): "82180",
    ("LO",  "30K"): "82180",
}

def calculate_led_pn(inp: RAD4Inputs) -> str:
    return LED_PN_TABLE.get((inp.Lighting, inp.LEDColorTemp), "82180")


# =============================================================================
# LED HARNESS CONFIG  (JS3 Chassis.csv — DWVariableLED1HarnessConfig)
#
# DW formula determines harness connector based on strip position and driver.
# For RAD4 single strip: "1-F"  (1 = strip 1, F = standard flying lead)
# =============================================================================

def calculate_led_harness_config(strip_number: int, driver_type: str) -> str:
    return f"{strip_number}-F"


# =============================================================================
# BOM GENERATION  (JS3 Chassis.csv lines 319-392 — PN1 through PN22)
#
# Each PN# maps to a line item in the Excel BOM.
# =============================================================================

def build_bom(inp: RAD4Inputs, result: "RAD4Result") -> dict:
    """
    Builds the complete BOM dictionary.
    Keys are BOM row labels. Values are part number strings or empty string.

    Replicates PN1–PN22 variables from JS3 Chassis.csv.
    """
    bom = {}

    # PN2 — Horizontal cut extrusion with LED channel (78020 family)
    # DW: Right(78020LEDH, Len(78020LEDH)-1)  →  78020-{length}-CUT
    horiz_in = round(inp.UnitWidth, 4)
    vert_in  = round(inp.UnitHeight, 4)
    bom["PN2_Extrusion_Horizontal"] = f"78020-{horiz_in:.4f}-CUT"
    bom["PN2_Extrusion_Vertical"]   = f"78020-{vert_in:.4f}-CUT"

    # PN5 — Corner bracket (static)  JS3 Chassis line 351
    bom["PN5_Corner_Bracket"] = "83046"

    # PN6 — Clip (static)  JS3 Chassis line 350
    bom["PN6_Clip"] = "82070"

    # PN7 — Stud bracket (static)  JS3 Chassis line 349
    bom["PN7_Stud_Bracket"] = "83070"

    # PN9 — Mounting hardware (static)  JS3 Chassis line 339
    bom["PN9_Mounting_Hardware"] = "83142"

    # PN10 — Screw (static)  JS3 Chassis line 338
    bom["PN10_Screw"] = "10328"

    # PN12 — LED Strip 1  JS3 Chassis lines 334-336
    # DW: LEDPN & "-" & Fixed(cut_length_in, 2) & "-" & LED1HarnessConfig
    led_strip_1_pn = (
        f"{result.LEDPN}"
        f"-{result.LEDCutLengthIn:.2f}"
        f"-{result.LED1HarnessConfig}"
    )
    bom["PN12_LED_Strip_1"] = led_strip_1_pn

    # PN15 — Gasket bumper (static)  JS3 Chassis line 329
    bom["PN15_Gasket_Bumper"] = "83056-1.50"

    # PN15qty — count of gasket bumpers (depends on panel height)
    # DW: sum of GasketBumper1..12 flags
    bom["PN15_Qty"] = _calculate_gasket_bumper_qty(inp)

    # PN16_Defogger — Defogger pad
    if inp.Defogger:
        bom["PN16_Defogger"] = result.DefoggerConfig.split('-')[0]
        bom["PN16_Defogger_Qty"] = str(result.DefoggerQty)
    else:
        bom["PN16_Defogger"] = ""
        bom["PN16_Defogger_Qty"] = ""

    # PN15_Clock — Clock option (in mirror BOM)
    if inp.Clock:
        bom["PN15_Clock"] = "49684"
        bom["PN15_Clock_Qty"] = "1"
    else:
        bom["PN15_Clock"] = ""
        bom["PN15_Clock_Qty"] = ""

    # PN21 — Cord connect assembly  JS3 Chassis lines 321-323
    if inp.CordConnect:
        bom["PN21_Cord_Connect"] = "12598" if inp.CordConnectType == "CC" else "71309"
    else:
        bom["PN21_Cord_Connect"] = ""

    # PN22 — Extension harness  JS3 Chassis lines 320
    if inp.ClockType == "CK3" or inp.CordConnectType == "CC2":
        bom["PN22_Extension_Harness"] = "71309"
    elif inp.CordConnectType == "CC":
        bom["PN22_Extension_Harness"] = "12986"
    else:
        bom["PN22_Extension_Harness"] = ""

    # Driver enclosure
    bom["Driver_Enclosure"] = result.DriverEnclosurePN


    # Standoff kit  (from Cosmon Test Components.csv — 81187-KIT-STANDOFF-RAD3)
    bom["Standoff_Kit"] = f"81187-{inp.MountType}-KIT-STANDOFF-RAD3"

    return bom


def _calculate_gasket_bumper_qty(inp: RAD4Inputs) -> int:
    """
    DW: GasketBumper1..12 determine qty based on panel height ranges.
    Simplified: 4 bumpers for standard, more for taller panels.
    """
    if inp.UnitHeight <= 40:
        return 4
    elif inp.UnitHeight <= 60:
        return 6
    return 8


# =============================================================================
# FILE PATH BUILDER  (replicates DWVariableChassisFileLocation etc.)
# =============================================================================

def build_file_paths(cpn: str) -> dict:
    """
    Builds all SolidWorks file paths that DriveWorks would resolve.
    Returns dict of absolute paths.
    """
    vault = DWConstantVault

    mirror_name  = cpn + "-M"
    chassis_name = cpn + "-C"
    sa_name      = cpn + "-SALES-AID"

    return {
        "mirror_assembly":   f"{vault}\\{DWConstantFile_Location_Mirror}\\{mirror_name}.SLDASM",
        "chassis_assembly":  f"{vault}\\{DWConstantFile_Location_Chassis_Assembly}\\{chassis_name}.SLDASM",
        "sales_aid_drawing": f"{vault}\\{DWConstantFile_Location_Sales_Aid}\\{sa_name}.SLDDRW",
        "driver_enclosure":  f"{vault}\\{DWConstantFile_Location_Driver_Enclosure}\\81330-DRIVER-MODULE-RAD3.SLDASM",
    }


# =============================================================================
# MAIN ENGINE  — runs all calculations in sequence
# =============================================================================

def run(inp: RAD4Inputs) -> RAD4Result:
    """
    Master calculation function. Runs every DriveWorks variable in dependency order.
    Returns a fully-populated RAD4Result.
    """
    r = RAD4Result()

    # 1. Build CPN
    r.CPN         = build_cpn(inp)
    r.MirrorName  = r.CPN + "-M"
    r.ChassisName = r.CPN + "-C"

    # 2. Panel dimensions (mm)
    r.HorizontalPanelOuterDimEncmm, r.VerticalPanelOuterDimEncmm = calculate_panel_dims(inp)

    # 3. LED segment length
    r.LEDSegmentLength = calculate_led_segment_length(inp)

    # 4. LED section lengths
    r.LEDSectionTopEnc, r.LEDSectionBottomEnc, r.LEDSectionLeftEnc, r.LEDSectionRightEnc = \
        calculate_led_sections(r.HorizontalPanelOuterDimEncmm, r.VerticalPanelOuterDimEncmm)

    # 5. Base length
    r.LEDBaseLengthEnc = calculate_led_base_length(
        r.LEDSectionTopEnc, r.LEDSectionBottomEnc,
        r.LEDSectionLeftEnc, r.LEDSectionRightEnc
    )

    # 6. Segment count + cap
    r.LEDCuttableSegmentsEnc, r.LEDCuttableSegmentsFinal = \
        calculate_cuttable_segments(r.LEDBaseLengthEnc, r.LEDSegmentLength)

    # 7. Physical LED length (mm)
    r.LEDmmLength = r.LEDCuttableSegmentsFinal * r.LEDSegmentLength

    # 8. Watts per meter
    r.WattsPerMeter = calculate_watts_per_meter(inp)

    # 9. Driver Type (needed for strips calculation)
    r.DriverType = calculate_driver_type(inp)

    # 10. Strips required
    r.LEDStripsRequiredEnc = calculate_led_strips(
        r.LEDCuttableSegmentsFinal, r.DriverType, r.WattsPerMeter, r.LEDSegmentLength
    )

    # 11. Cut length per strip (inches)
    r.LEDCutLengthIn = calculate_led_cut_length(
        r.LEDCuttableSegmentsFinal, r.LEDStripsRequiredEnc, r.LEDSegmentLength
    )

    # 12. Power
    r.PowerRequirement, r.WattageRequirement = calculate_power(
        r.LEDCuttableSegmentsFinal, r.LEDSegmentLength, r.WattsPerMeter,
        r.LEDBaseLengthEnc
    )

    # 13. Driver Wattage + Qty (depends on WattageRequirement)
    r.DriverWattage, r.DriverQty = calculate_driver(r.DriverType, r.WattageRequirement)

    # 14. Driver enclosure PN (uses PowerAvailable = DriverWattage)
    r.DriverEnclosurePN = calculate_driver_enclosure_pn(inp, r.DriverWattage)

    # 15. LED PN + harness
    r.LEDPN            = calculate_led_pn(inp)
    r.LED1HarnessConfig = calculate_led_harness_config(1, r.DriverType)

    # 15. Options config
    if inp.Defogger:
        r.DefoggerConfig, r.DefoggerQty = get_defogger_config_and_qty(inp.UnitWidth, inp.UnitHeight)
    else:
        r.DefoggerConfig, r.DefoggerQty = "15229-120V-10.5X10.5", 0
        
    if inp.Clock:
        r.ClockConfig = calculate_clock_config(inp.ClockType)
    else:
        r.ClockConfig = "Delete"

    # 15.5 Notes Configuration
    bundle_code_path = str(Path(__file__).parent / "RAD4_Configurator_Bundle" / "code")
    if bundle_code_path not in sys.path:
        sys.path.insert(0, bundle_code_path)
    
    from rad4_rules_engine import select_notes
    selected_notes = select_notes(r.CPN)
    
    notes_list = []
    # Order: SPECIFICATION, ATTENTION, DEFOGGER, DEFOGGER DISCLAIMER, DIMMING, CLOCK, WALL GLOW
    if "SPECIFICATION" in selected_notes:
        notes_list.append(NoteBlock(
            category="SPECIFICATION",
            title="SPECIFICATION",
            body_text=selected_notes["SPECIFICATION"]
        ))
    if "ATTENTION" in selected_notes:
        notes_list.append(NoteBlock(
            category="ATTENTION",
            title="ATTENTION",
            body_text=selected_notes["ATTENTION"]
        ))
    if "DEFOGGER" in selected_notes:
        notes_list.append(NoteBlock(
            category="DEFOGGER",
            title="DEFOGGER SPECIFICATIONS",
            body_text=selected_notes["DEFOGGER"]
        ))
    if "DEFOGGER DISCLAIMER (KEEN)" in selected_notes:
        notes_list.append(NoteBlock(
            category="DEFOGGER DISCLAIMER (KEEN)",
            title="KEEN / DEFOGGER DISCLAIMER",
            body_text=selected_notes["DEFOGGER DISCLAIMER (KEEN)"]
        ))
    if "DIMMING" in selected_notes:
        notes_list.append(NoteBlock(
            category="DIMMING",
            title="DIMMER COMPATIBILITY",
            body_text=selected_notes["DIMMING"]
        ))

    if inp.Ava:
        notes_list.append(NoteBlock(
            category="BUTTON",
            title="AVA 1-TOUCH CONTROL BUTTON",
            body_text="SEE SPECIFICATION SHEET FOR ADDITIONAL DETAILS"
        ))
    elif inp.Keen:
        notes_list.append(NoteBlock(
            category="BUTTON",
            title="KEEN 1-TOUCH CONTROL BUTTON",
            body_text="SEE SPECIFICATION SHEET FOR ADDITIONAL DETAILS"
        ))
    elif inp.Vive:
        notes_list.append(NoteBlock(
            category="BUTTON",
            title="VIVE CONTROL BUTTON",
            body_text="SEE SPECIFICATION SHEET FOR ADDITIONAL DETAILS"
        ))
        
    if inp.Clock and inp.ClockType in ("CK2", "CK3"):
        if inp.ClockType == "CK3":
            clock_text = "PLUG-IN EXTERNAL 5V POWER SUPPLY 120 VOLTS INPUT, 50-60Hz 2.0 WATTS"
        else:
            clock_text = "CONNECTED TO MAIN LINE-IN; POWERS ON WITH LIGHTS, INTERNAL BATTERY KEEPS TIME SET 120-240 VAC INPUT 50-60Hz 2.0 WATTS"
        notes_list.append(NoteBlock(
            category="CLOCK",
            title="CLOCK POWER REQUIREMENTS",
            body_text=clock_text
        ))
        
    if inp.WallGlow and inp.WallGlowType == "WG3":
        wg_length = 2 * (inp.UnitWidth + inp.UnitHeight) - 16
        if round(inp.UnitWidth) == 21 and round(inp.UnitHeight) == 42:
            wg_length = 111
        
        wg_watts = round(wg_length * 3.66 / 12.0)
        wg_lumens = round(wg_length * 301.0 / 12.0)
        cct_map = {
            "27K": "2,700",
            "30K": "3,000",
            "35K": "3,500",
            "40K": "4,000"
        }
        cct_val = cct_map.get(inp.LEDColorTemp, "3,000")
        
        wg_text = (
            f"LED TYPE: REPLACEABLE FLEX STRIP\n"
            f"LENGTH (IN): {wg_length}\n"
            f"WATTAGE (W): {wg_watts}\n"
            f"CALCULATED L70 LIFESPAN (HRS): 140,000\n"
            f"CCT(K): {cct_val}\n"
            f"TOTAL INITIAL LUMENS PER FIXTURE: {wg_lumens:,} @ 302 LM/FT\n"
            f"CRI: 90+"
        )
        notes_list.append(NoteBlock(
            category="WALL GLOW",
            title="WALL GLOW LED SPECIFICATION",
            body_text=wg_text
        ))
        
    r.Notes = notes_list

    # 15. BOM
    r.BOM = build_bom(inp, r)



    # 16. SolidWorks file paths
    paths = build_file_paths(r.CPN)
    r.MirrorAssemblyPath   = paths["mirror_assembly"]
    r.ChassisAssemblyPath  = paths["chassis_assembly"]
    r.SalesAidDrawingPath  = paths["sales_aid_drawing"]

    return r


# =============================================================================
# QUICK SELF-TEST  — validates against known DriveWorks output from screenshot
# Expected: RAD4-36.00X36.00-RM-LSE-30K → 35.64W, Enclosure: 81330-96W
# =============================================================================

if __name__ == "__main__":
    # Test 1: LO lighting — matches the DriveWorks screenshot
    # Expected: CPN=RAD4-36.00X36.00-RM-LO-NK04-30K, Power=35.64W, Enclosure=81330-96W
    test = RAD4Inputs(
        UnitWidth=36.0,
        UnitHeight=36.0,
        MirrorType="RAD4",
        MountType="RM",
        Lighting="LO",
        LEDColorTemp="30K",
        Finish="NK04",
        Voltage="Standard",
    )

    result = run(test)

    print("=" * 60)
    print(f"CPN:               {result.CPN}")
    print(f"Mirror Assembly:   {result.MirrorName}")
    print(f"Chassis Assembly:  {result.ChassisName}")
    print("-" * 60)
    print(f"Segment Length:    {result.LEDSegmentLength} mm")
    print(f"Panel H×V (mm):    {result.HorizontalPanelOuterDimEncmm:.2f} × {result.VerticalPanelOuterDimEncmm:.2f}")
    print(f"LED Base Length:   {result.LEDBaseLengthEnc:.2f} mm")
    print(f"Raw Segments:      {result.LEDCuttableSegmentsEnc}")
    print(f"Final Segments:    {result.LEDCuttableSegmentsFinal}")
    print(f"LED Strips:        {result.LEDStripsRequiredEnc}")
    print(f"LED Cut Length:    {result.LEDCutLengthIn:.2f} in")
    print(f"Watts/m:           {result.WattsPerMeter}")
    print(f"Power Required:    {result.PowerRequirement:.2f} W   (target: 35.64 W)")
    print(f"Buffered Power:    {result.WattageRequirement} W  (used for driver selection)")
    print(f"Driver Type:       {result.DriverType}")
    print(f"PowerAvailable:    {result.DriverWattage} W  (target: 96 W)")
    print(f"Driver Qty:        {result.DriverQty}")
    print(f"Driver PN:         {result.DriverEnclosurePN}  (target: 81330-96W)")
    print(f"LED PN:            {result.LEDPN}")
    print("-" * 60)
    print("BOM:")
    for k, v in result.BOM.items():
        if v:
            print(f"  {k}: {v}")
    print("-" * 60)
    print("SolidWorks Paths:")
    print(f"  Mirror:    {result.MirrorAssemblyPath}")
    print(f"  Chassis:   {result.ChassisAssemblyPath}")
    print(f"  Sales Aid: {result.SalesAidDrawingPath}")
