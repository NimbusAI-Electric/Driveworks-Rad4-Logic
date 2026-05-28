"""
sw_api.py
=========
SolidWorks COM API bridge for the RAD4 configurator.

Replicates what DriveWorks does when it executes model rules:
  - Opens the top-level chassis assembly
  - Replaces components (panels, LEDs, driver enclosure, mirror sub-assembly)
  - Writes custom properties (PartNumber, Width, Height, Wattage, etc.)
  - Rebuilds and saves
  - Opens the Sales Aid drawing and saves as PDF

SolidWorks 2021 COM API reference:
  https://help.solidworks.com/2021/english/api/sldworksapi/

Usage:
    from sw_api import SolidWorksAPI
    from rad4_engine import RAD4Inputs, run

    inputs = RAD4Inputs(UnitWidth=36, UnitHeight=36, Lighting="LSE", ...)
    result = run(inputs)
    api = SolidWorksAPI()
    api.generate(inputs, result, output_dir=r"N:\\AI Driveworks Output")
"""

import os
import sys
import time
import logging
from pathlib import Path
from rad4_engine import RAD4Inputs, RAD4Result, DWConstantVault

log = logging.getLogger(__name__)


# =============================================================================
# COM CONSTANTS  (SolidWorks 2021 API enumerations)
# =============================================================================
swDocASSEMBLY  = 2
swDocDRAWING   = 3
swDocPART      = 1
swSaveAsCurrentVersion = 0
swCustomInfoText = 30
swCustomInfoDeleteUnused = 1
swRebuildOnActivation_UserDecision = 2
swSaveAsOptions_Silent = 1


# =============================================================================
# SOLIDWORKS API CLASS
# =============================================================================

class SolidWorksAPI:
    """
    Wraps the SolidWorks COM application object.
    All methods map directly to DriveWorks model rules or drawing rules.
    """

    def __init__(self):
        self.swApp   = None
        self.swModel = None
        self._connect()

    def _connect(self):
        """
        Attaches to a running SolidWorks 2021 instance (or launches one).
        Replicates DriveWorks connecting to the SolidWorks session.
        """
        try:
            import win32com.client as win32
            # Try to connect to existing running instance first
            try:
                self.swApp = win32.GetActiveObject("SldWorks.Application")
                log.info("Connected to existing SolidWorks session.")
            except Exception:
                # Launch a new instance
                self.swApp = win32.Dispatch("SldWorks.Application.29")  # 29 = SW2021
                self.swApp.Visible = True
                log.info("Launched new SolidWorks 2021 session.")
        except ImportError:
            raise RuntimeError(
                "win32com not installed. Run: pip install pywin32\n"
                "SolidWorks must be installed on this machine."
            )

    # =========================================================================
    # MAIN ENTRY POINT
    # =========================================================================

    def generate(self, inp: RAD4Inputs, result: RAD4Result, output_dir: str) -> dict:
        """
        Full pipeline — replicates one complete DriveWorks 'Release' run.

        Steps (matching DriveWorks execution order):
          1. Verify all required template files exist
          2. Open chassis assembly (top-level)
          3. Replace mirror sub-assembly component
          4. Replace LED strip component(s)
          5. Replace driver enclosure component
          6. Set all custom properties
          7. Rebuild and save model
          8. Open Sales Aid drawing
          9. Update drawing, save as PDF
          10. Export BOM to Excel
          11. Copy outputs to N:\\AI Driveworks Output
        """
        os.makedirs(output_dir, exist_ok=True)
        output_paths = {}

        log.info(f"Starting RAD4 generation for: {result.CPN}")

        # Step 1: Verify template files
        self._verify_templates(result)

        # Step 2-7: Build the model
        chassis_out = os.path.join(output_dir, f"{result.ChassisName}.SLDASM")
        self._build_chassis_assembly(inp, result, chassis_out)
        output_paths["chassis_assembly"] = chassis_out
        log.info(f"Chassis assembly saved: {chassis_out}")

        # Step 8-9: Sales Aid drawing
        sa_pdf_out = os.path.join(output_dir, f"{result.CPN}-SALES-AID.PDF")
        self._generate_sales_aid(result, sa_pdf_out)
        output_paths["sales_aid_pdf"] = sa_pdf_out
        log.info(f"Sales Aid PDF saved: {sa_pdf_out}")

        # Step 10: BOM Excel
        bom_out = os.path.join(output_dir, f"{result.CPN}-BOM.xlsx")
        self._export_bom(result, bom_out)
        output_paths["bom"] = bom_out
        log.info(f"BOM saved: {bom_out}")

        return output_paths

    # =========================================================================
    # STEP 1: TEMPLATE VERIFICATION
    # =========================================================================

    def _verify_templates(self, result: RAD4Result):
        """
        Checks that the SolidWorks template files exist before opening them.
        Replicates DriveWorks pre-flight check.
        """
        required = [
            result.ChassisAssemblyPath,
            result.MirrorAssemblyPath,
            result.SalesAidDrawingPath,
        ]
        missing = [p for p in required if not os.path.exists(p)]
        if missing:
            raise FileNotFoundError(
                "Required SolidWorks template files not found:\n" +
                "\n".join(f"  {p}" for p in missing)
            )

    # =========================================================================
    # STEPS 2-7: CHASSIS ASSEMBLY (MODEL RULES)
    # =========================================================================

    def _build_chassis_assembly(self, inp: RAD4Inputs, result: RAD4Result, output_path: str):
        """
        Opens the chassis template assembly and applies all DriveWorks model rules:
          - ReplaceComponent  (panels, LEDs, driver, mirror)
          - Set custom properties
          - Rebuild + SaveAs
        """
        # Open the top-level chassis template
        errors  = 0
        warnings = 0
        self.swModel = self.swApp.OpenDoc6(
            result.ChassisAssemblyPath,
            swDocASSEMBLY,
            1,          # swOpenDocOptions_Silent
            "",
            errors,
            warnings
        )
        if self.swModel is None:
            raise RuntimeError(f"Failed to open chassis assembly: {result.ChassisAssemblyPath}")

        swAssem = self.swModel

        # ── REPLACE COMPONENTS ────────────────────────────────────────────────

        # Mirror sub-assembly
        # DW model rule: mMirrorAssembly = <ReplaceFile> & MirrorAssemblyPath
        self._replace_component(swAssem, "RAD4-M",
                                result.MirrorAssemblyPath, "Default")

        # LED Strip(s)
        # DW model rule: LED1 = <ReplaceFile> & LED_PN & "-" & CutLength & "-" & HarnessConfig
        led_strip_path = (
            f"{DWConstantVault}\\Products\\JS3\\COMPONENTS\\RAD4 LEDs\\"
            f"{result.LEDPN}-{result.LEDCutLengthIn:.2f}-{result.LED1HarnessConfig}.SLDPRT"
        )
        self._replace_component(swAssem, "LED-STRIP-1",
                                led_strip_path, "Default")

        # Driver enclosure
        # DW model rule: DriverEnclosure = <ReplaceFile> & DWConstantVault & File_Location_Driver_Enclosure & DriverEnclosurePN
        driver_path = (
            f"{DWConstantVault}\\COMPONENTS\\81000\\"
            f"{result.DriverEnclosurePN}.SLDASM"
        )
        self._replace_component(swAssem, "DRIVER-ENCLOSURE",
                                driver_path, "Default")

        # ── SET CUSTOM PROPERTIES ─────────────────────────────────────────────
        # Replicates DriveWorks "Custom Properties" mappings for the assembly
        self._set_custom_properties(swAssem, inp, result)

        # ── REBUILD + SAVE ────────────────────────────────────────────────────
        self.swModel.ForceRebuild3(False)
        self.swModel.SaveAs3(output_path, 0, 0)
        log.info(f"Assembly rebuilt and saved to: {output_path}")

    def _replace_component(self, swAssem, component_name: str,
                           new_path: str, config_name: str):
        """
        Replaces a component in the assembly with a new file.
        Replicates DriveWorks <ReplaceFile> model rule.

        DW equivalent:
            pcomp:ComponentName = <ReplaceFile> & path & "|" & config
        """
        try:
            # Get component by name
            comp = swAssem.GetComponentByName(component_name + "-1")
            if comp is None:
                # Try without instance suffix
                comp = swAssem.GetComponentByName(component_name)
            if comp is None:
                log.warning(f"Component not found in assembly: {component_name}")
                return

            if not os.path.exists(new_path):
                log.warning(f"Replacement file not found: {new_path}")
                return

            comp.ReplaceComponent(new_path, config_name, True)
            log.debug(f"Replaced {component_name} → {new_path}")

        except Exception as e:
            log.error(f"Failed to replace {component_name}: {e}")

    def _set_custom_properties(self, swModel, inp: RAD4Inputs, result: RAD4Result):
        """
        Writes all custom properties to the assembly.
        Replicates DriveWorks Custom Properties mappings (the tab in the DW form).

        These properties drive the Sales Aid title block and drawing annotations.
        """
        mgr = swModel.Extension.CustomPropertyManager("")

        props = {
            # Core identification
            "PartNumber":       result.CPN,
            "Description":      f"RAD4 Mirror {inp.UnitWidth:.2f}\" x {inp.UnitHeight:.2f}\"",
            "Width":            f"{inp.UnitWidth:.2f}",
            "Height":           f"{inp.UnitHeight:.2f}",
            "MirrorType":       inp.MirrorType,
            "MountType":        inp.MountType,
            "Lighting":         inp.Lighting,
            "LED_Color_Temp":   inp.LEDColorTemp,
            "Finish":           inp.Finish,
            "Voltage":          inp.Voltage,

            # Electrical
            "Power_Required_W": f"{result.PowerRequirement:.2f}",
            "Power_Available_W": str(result.DriverWattage),
            "Driver_Type":      result.DriverType,
            "Driver_Qty":       str(result.DriverQty),
            "Enclosure_PN":     result.DriverEnclosurePN,

            # LED
            "LED_PN":           result.LEDPN,
            "LED_Cut_Length_In": f"{result.LEDCutLengthIn:.2f}",
            "LED_Segments":     str(result.LEDCuttableSegmentsFinal),
            "LED_Strips":       str(result.LEDStripsRequiredEnc),
        }

        for key, val in props.items():
            # swCustomInfoType = 30 (text), retVal = True if added, False if updated
            mgr.Add3(key, swCustomInfoText, val, swCustomInfoDeleteUnused)

        log.debug(f"Set {len(props)} custom properties on assembly.")

    # =========================================================================
    # STEPS 8-9: SALES AID DRAWING
    # =========================================================================

    def _generate_sales_aid(self, result: RAD4Result, output_pdf_path: str):
        """
        Opens the Sales Aid .SLDDRW template, triggers rebuild (which reads
        custom properties from the assembly via $PRPSHEET), then saves as PDF.

        DW equivalent: the RAD3 project's drawing rules write to the .SLDDRW
        which is linked to the chassis assembly via $PRPSHEET:{PropertyName}.
        """
        errors   = 0
        warnings = 0

        swDrawing = self.swApp.OpenDoc6(
            result.SalesAidDrawingPath,
            swDocDRAWING,
            1,       # swOpenDocOptions_Silent
            "",
            errors,
            warnings
        )
        if swDrawing is None:
            raise RuntimeError(
                f"Failed to open Sales Aid drawing: {result.SalesAidDrawingPath}"
            )

        # Force full rebuild — this pulls all $PRPSHEET values from the assembly
        swDrawing.ForceRebuild3(False)

        # Export as PDF
        export_data = self.swApp.GetExportFileData(1)  # 1 = swExportPdfData
        success = swDrawing.Extension.SaveAs(
            output_pdf_path,
            0,   # swSaveAsCurrentVersion
            1,   # swSaveAsOptions_Silent
            export_data,
            errors,
            warnings
        )
        if not success:
            log.warning(f"Sales Aid PDF export returned False. Check: {output_pdf_path}")

        # Save updated drawing
        swDrawing.Save3(swSaveAsCurrentVersion, errors, warnings)
        self.swApp.CloseDoc(result.SalesAidDrawingPath)

    # =========================================================================
    # STEP 10: BOM EXPORT
    # =========================================================================

    def _export_bom(self, result: RAD4Result, output_xlsx_path: str):
        """
        Exports the BOM to Excel.
        Uses openpyxl to write the BOM dict from rad4_engine directly.
        This replicates the DriveWorks "Autopilot" BOM Excel output.
        """
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment
        except ImportError:
            log.warning("openpyxl not installed — skipping Excel BOM. Run: pip install openpyxl")
            return

        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "BOM"

        # Header row
        header_fill = PatternFill("solid", fgColor="1F3864")
        header_font = Font(color="FFFFFF", bold=True)
        headers = ["BOM Item", "Part Number", "Description"]
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=h)
            cell.fill = header_fill
            cell.font = header_font
            cell.alignment = Alignment(horizontal="center")

        # Title block
        ws.cell(row=1, column=1, value=f"BOM — {result.CPN}")
        ws.merge_cells("A1:C1")
        ws.cell(row=1, column=1).font  = Font(bold=True, size=12)
        ws.cell(row=1, column=1).fill  = header_fill
        ws.cell(row=1, column=1).font  = Font(color="FFFFFF", bold=True, size=12)

        # Column headers
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=2, column=col, value=h)
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="D9E1F2")

        # BOM rows
        row = 3
        for item, pn in result.BOM.items():
            if pn:
                ws.cell(row=row, column=1, value=item.replace("_", " "))
                ws.cell(row=row, column=2, value=pn)
                row += 1

        # Column widths
        ws.column_dimensions["A"].width = 35
        ws.column_dimensions["B"].width = 30
        ws.column_dimensions["C"].width = 40

        wb.save(output_xlsx_path)
        log.info(f"BOM exported to: {output_xlsx_path}")

    # =========================================================================
    # CLEANUP
    # =========================================================================

    def close(self):
        """Closes all open documents and releases the COM object."""
        if self.swApp:
            try:
                self.swApp.ExitApp()
            except Exception:
                pass
