"""
sw_api.py
=========
SolidWorks COM API bridge for the RAD4 configurator.

Uses template copying and reference redirection (ReplaceReferencedDocument)
to generate configured mirror models, assemblies, drawings, and BOMs without
altering the original template files. Supports custom/decimal sizes by dynamically
mapping to the closest standard templates, copying the structural extrusions (72239)
and diffusers (64792), updating their length dimensions, and referencing them.
"""

import os
import shutil
import glob
import logging
import re
from pathlib import Path
import win32com.client as win32
import pythoncom
from rad4_engine import RAD4Inputs, RAD4Result, DWConstantVault

log = logging.getLogger(__name__)

# COM Constants
swDocASSEMBLY = 2
swDocDRAWING = 3
swSaveAsCurrentVersion = 0
swSaveAsOptions_Silent = 1

def _copy_file_writable(src: Path, dest: Path):
    if dest.exists():
        try:
            os.chmod(str(dest), 0o666)
            dest.unlink()
        except Exception as e:
            log.warning(f"Could not prepare destination file {dest} for copying: {e}")
    
    shutil.copyfile(str(src), str(dest))
    try:
        os.chmod(str(dest), 0o666)
    except Exception as e:
        log.warning(f"Could not make destination file writable {dest}: {e}")

def find_closest_template(directory: Path, pattern: str, width: float, height: float) -> Path:
    """
    Finds the template file in the directory that is closest in size to (width, height).
    """
    files = list(directory.glob(pattern))
    templates = []
    
    # Exclude generated/released files to avoid using configured mirrors as templates
    for f in files:
        name = f.name
        # Release files typically contain mount types or lighting codes
        if any(token in name for token in ["-RM-", "-SM-", "-LO-", "-SO-", "-LSE-", "-LHE-"]):
            continue
        # Standard templates have at most 3 dashes (e.g., RAD4-36.00X36.00-DF-M.SLDASM)
        if not name.lower().endswith(".slddrw") and name.count('-') > 3:
            continue
        templates.append(f)

    if not templates:
        raise FileNotFoundError(f"No templates matching pattern {pattern} found in {directory}")

    candidates = []
    size_re = re.compile(r'RAD4-(\d+\.\d+)X(\d+\.\d+)', re.IGNORECASE)

    for f in templates:
        m = size_re.search(f.name)
        if m:
            w_val = float(m.group(1))
            h_val = float(m.group(2))
            dist = abs(w_val - width) + abs(h_val - height)
            candidates.append((dist, len(f.name), f))

    if not candidates:
        log.warning(f"Could not parse sizes from templates in {directory}. Falling back to first match.")
        return templates[0]

    # Sort by distance first (ascending), then by length of file name (ascending)
    candidates.sort(key=lambda x: (x[0], x[1]))
    best_file = candidates[0][2]
        
    return best_file

class SolidWorksAPI:
    def __init__(self):
        self.swApp = None
        self._connect()

    def _connect(self):
        try:
            try:
                self.swApp = win32.GetActiveObject("SldWorks.Application")
                log.info("Connected to existing SolidWorks session.")
            except Exception:
                self.swApp = win32.Dispatch("SldWorks.Application.29") # SW2021
                self.swApp.Visible = True
                log.info("Launched new SolidWorks 2021 session.")
        except Exception as e:
            raise RuntimeError(f"Failed to connect to SolidWorks: {e}")

    def generate(self, inp: RAD4Inputs, result: RAD4Result, output_dir: str) -> dict:
        width = inp.UnitWidth
        height = inp.UnitHeight
        cpn = result.CPN
        vault = DWConstantVault

        log.info(f"Starting programmatic generation for: {cpn}")

        # Close all active documents to release file locks before copying
        try:
            self.swApp.CloseAllDocuments(True)
            log.info("Closed all open documents in SolidWorks.")
        except Exception as e:
            log.warning(f"Could not close open documents in SolidWorks: {e}")

        # 1. Resolve template paths dynamically using closest size match
        chassis_dir = Path(vault) / "Products" / "JS3" / "Assemblies" / "RAD4"
        mirror_dir = Path(vault) / "Products" / "JS3" / "Mirrors" / "RAD4"
        drawing_dir = chassis_dir

        template_chassis = find_closest_template(chassis_dir, "RAD4-*.SLDASM", width, height)
        template_mirror = find_closest_template(mirror_dir, "RAD4-*-M.SLDASM", width, height)
        template_drawing = find_closest_template(drawing_dir, "RAD4-*-SALES-AID.SLDDRW", width, height)

        log.info(f"Templates resolved:\n  Chassis: {template_chassis}\n  Mirror: {template_mirror}\n  Drawing: {template_drawing}")

        # Parse standard sizes from selected templates
        m_chassis = re.search(r'RAD4-(\d+\.\d+)X(\d+\.\d+)', template_chassis.name)
        temp_w = float(m_chassis.group(1)) if m_chassis else width
        temp_h = float(m_chassis.group(2)) if m_chassis else height

        # 2. Build custom extrusion parts/sub-assemblies if size is custom/decimal
        self._configure_custom_extrusions(vault, temp_w, temp_h, width, height)

        # 3. Define output copy paths
        out_mirror = mirror_dir / f"{cpn}-M.SLDASM"
        out_chassis = chassis_dir / f"{cpn}-C.SLDASM"
        out_drawing = Path(vault) / "Products" / "JS3" / "Sales Aid" / "RAD4" / f"{cpn}-SALES-AID.SLDDRW"
        
        # Ensure output directories exist
        out_drawing.parent.mkdir(parents=True, exist_ok=True)

        # 4. Copy templates to output paths
        log.info("Copying template files...")
        _copy_file_writable(template_mirror, out_mirror)
        _copy_file_writable(template_chassis, out_chassis)
        _copy_file_writable(template_drawing, out_drawing)
        log.info("Files copied successfully.")

        # 5. Replace Referenced Documents using COM API (needs files closed!)
        log.info("Updating references...")
        
        # In Mirror copy: Redirect horizontal & vertical extrusion sub-assemblies to the custom-sized versions
        comp_72_dir = Path(vault) / "Products" / "JS3" / "COMPONENTS" / "72000"
        is_custom_w = abs(width - temp_w) > 0.001
        is_custom_h = abs(height - temp_h) > 0.001

        if is_custom_w:
            ref_asm_w_temp = str(comp_72_dir / f"72239-XXX-{temp_w:.2f}.SLDASM")
            ref_asm_w_out = str(comp_72_dir / f"72239-XXX-{width:.2f}.SLDASM")
            if os.path.exists(ref_asm_w_out):
                success_ref = self.swApp.ReplaceReferencedDocument(str(out_mirror), ref_asm_w_temp, ref_asm_w_out)
                log.info(f"ReplaceReferencedDocument in Mirror (W Extrusion Asm) replacing {ref_asm_w_temp} with {ref_asm_w_out}: {success_ref}")

        if is_custom_h:
            # Replace vertical assembly with hole connector
            ref_asm_hn_temp = str(comp_72_dir / f"72239-XXX-{temp_h:.2f}-N.SLDASM")
            ref_asm_hn_out = str(comp_72_dir / f"72239-XXX-{height:.2f}-N.SLDASM")
            if os.path.exists(ref_asm_hn_out):
                success_ref = self.swApp.ReplaceReferencedDocument(str(out_mirror), ref_asm_hn_temp, ref_asm_hn_out)
                log.info(f"ReplaceReferencedDocument in Mirror (H Extrusion Asm N) replacing {ref_asm_hn_temp} with {ref_asm_hn_out}: {success_ref}")

            # Replace standard height assembly
            ref_asm_h_temp = str(comp_72_dir / f"72239-XXX-{temp_h:.2f}.SLDASM")
            ref_asm_h_out = str(comp_72_dir / f"72239-XXX-{height:.2f}.SLDASM")
            if os.path.exists(ref_asm_h_out):
                success_ref = self.swApp.ReplaceReferencedDocument(str(out_mirror), ref_asm_h_temp, ref_asm_h_out)
                log.info(f"ReplaceReferencedDocument in Mirror (H Extrusion Asm) replacing {ref_asm_h_temp} with {ref_asm_h_out}: {success_ref}")

        # LED Customization (replace reference in Mirror copy)
        # 1. Briefly open template mirror to locate the template LED sub-assembly path
        errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        temp_led_asm_path = None
        log.info(f"Opening template mirror briefly to locate LED sub-assembly: {template_mirror}")
        swTempMirror = self.swApp.OpenDoc6(str(template_mirror), swDocASSEMBLY, 1, "", errors, warnings)
        if swTempMirror:
            try:
                components = swTempMirror.GetComponents(True)
                for comp in components:
                    c_path = comp.GetPathName
                    if r"products\js3\components\82000" in c_path.lower() and c_path.lower().endswith(".sldasm"):
                        temp_led_asm_path = c_path
                        break
            except Exception as e:
                log.warning(f"Error reading components from template mirror: {e}")
            finally:
                self.swApp.CloseDoc(swTempMirror.GetTitle)

        if temp_led_asm_path:
            filename = os.path.basename(temp_led_asm_path)
            # Match e.g. 82181-RAD3-6050MM-84.00X36.00.SLDASM
            match = re.search(r'(\d+)-(RAD\d)-(\d+)MM-(\d+\.\d+)X(\d+\.\d+)\.SLDASM', filename, re.IGNORECASE)
            if match:
                temp_led_pn = match.group(1)
                temp_rad_ver = match.group(2)
                temp_len = match.group(3)
                temp_w_led = float(match.group(4))
                temp_h_led = float(match.group(5))
                
                target_led_pn = result.LEDPN
                
                # Compute physical perimeter to determine standard round length
                total_perimeter_mm = 2 * (width + height) * 25.4 - 49.58223168
                new_len = int(round(total_perimeter_mm / 50.0) * 50.0)
                
                # Check if replacement is needed (mismatched size or mismatched part number)
                needs_led_replace = (abs(width - temp_w_led) > 0.001 or 
                                     abs(height - temp_h_led) > 0.001 or 
                                     target_led_pn != temp_led_pn)
                
                if needs_led_replace:
                    new_sub_name = f"{target_led_pn}-{temp_rad_ver}-{new_len}MM-{width:.2f}X{height:.2f}.SLDASM"
                    new_sub_path = Path(vault) / "Products" / "JS3" / "COMPONENTS" / "82000" / new_sub_name
                    
                    new_part_name = f"{temp_rad_ver}-LED-{new_len}-{width:.2f}X{height:.2f}.SLDPRT"
                    new_part_path = Path(vault) / "Products" / "JS3" / "COMPONENTS" / "RAD4 LEDs" / new_part_name
                    
                    temp_part_name = f"{temp_rad_ver}-LED-{temp_len}-{temp_w_led:.2f}X{temp_h_led:.2f}.SLDPRT"
                    temp_part_path = Path(vault) / "Products" / "JS3" / "COMPONENTS" / "RAD4 LEDs" / temp_part_name
                    
                    if not new_sub_path.exists() or not new_part_path.exists():
                        log.info(f"Creating custom LED components since they do not exist: {new_sub_name}")
                        if not new_part_path.exists() and temp_part_path.exists():
                            _copy_file_writable(temp_part_path, new_part_path)
                            log.info(f"Configuring new LED part dimensions: {new_part_path}")
                            swPart = self.swApp.OpenDoc6(str(new_part_path), 1, 1, "", errors, warnings)
                            if swPart:
                                dim_d1 = swPart.Parameter("D1@MASTER SKETCH")
                                dim_d2 = swPart.Parameter("D2@MASTER SKETCH")
                                if dim_d1:
                                    dim_d1.SystemValue = width * 0.0254
                                if dim_d2:
                                    dim_d2.SystemValue = height * 0.0254
                                swPart.ForceRebuild3(False)
                                swPart.Save3(0, errors, warnings)
                                self.swApp.CloseDoc(swPart.GetTitle)
                        
                        if not new_sub_path.exists() and os.path.exists(temp_led_asm_path):
                            _copy_file_writable(Path(temp_led_asm_path), new_sub_path)
                            log.info(f"Replacing reference in new LED sub-assembly: {new_sub_path}")
                            self.swApp.ReplaceReferencedDocument(str(new_sub_path), str(temp_part_path), str(new_part_path))
                            # Open, rebuild, and save new sub-assembly
                            swAsm = self.swApp.OpenDoc6(str(new_sub_path), 2, 1, "", errors, warnings)
                            if swAsm:
                                swAsm.ForceRebuild3(False)
                                swAsm.Save3(0, errors, warnings)
                                self.swApp.CloseDoc(swAsm.GetTitle)
                    
                    # Replace in mirror assembly copy
                    ref_asm_temp = str(temp_led_asm_path)
                    ref_asm_out = str(new_sub_path)
                    success_ref = self.swApp.ReplaceReferencedDocument(str(out_mirror), ref_asm_temp, ref_asm_out)
                    log.info(f"ReplaceReferencedDocument in Mirror (LED Asm) replacing {ref_asm_temp} with {ref_asm_out}: {success_ref}")

        
        # Replace mirror in chassis copy
        ref_mirror_temp = None
        deps = self.swApp.GetDocumentDependencies2(str(out_chassis), True, True, False)
        if deps:
            for i in range(0, len(deps), 2):
                dep_path = deps[i+1] if i+1 < len(deps) else ""
                if dep_path and r"products\js3\mirrors\rad4" in dep_path.lower() and dep_path.lower().endswith("-m.sldasm"):
                    ref_mirror_temp = dep_path
                    break
        if not ref_mirror_temp:
            ref_mirror_temp = str(mirror_dir / f"RAD4-{temp_w:.2f}X{temp_h:.2f}-M.SLDASM")
            
        success = self.swApp.ReplaceReferencedDocument(str(out_chassis), str(ref_mirror_temp), str(out_mirror))
        log.info(f"ReplaceReferencedDocument (Chassis -> Mirror) replacing {ref_mirror_temp} with {out_mirror}: {success}")

        # Replace chassis in drawing copy (checking all possible template variant chassis names)
        m_drawing = re.search(r'RAD4-(\d+\.\d+)X(\d+\.\d+)', template_drawing.name)
        temp_w_d = float(m_drawing.group(1)) if m_drawing else width
        temp_h_d = float(m_drawing.group(2)) if m_drawing else height
        
        possible_temps = [
            str(chassis_dir / f"RAD4-{temp_w_d:.2f}X{temp_h_d:.2f}.SLDASM"),
            str(chassis_dir / f"RAD4-{temp_w_d:.2f}X{temp_h_d:.2f}-DF.SLDASM"),
            str(chassis_dir / f"RAD4-{temp_w_d:.2f}X{temp_h_d:.2f}-KG.SLDASM"),
        ]
        replaced = False
        for temp in possible_temps:
            if self.swApp.ReplaceReferencedDocument(str(out_drawing), temp, str(out_chassis)):
                replaced = True
                log.info(f"ReplaceReferencedDocument (Drawing -> Chassis) replacing {temp} with {out_chassis}: True")
                break
        if not replaced:
            log.warning("Could not automatically replace chassis reference in drawing.")

        # 6. Open and configure copies in SolidWorks
        errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
        warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)

        # A. Configure Mirror Assembly
        log.info(f"Opening Mirror copy: {out_mirror}")
        swMirror = self.swApp.OpenDoc6(str(out_mirror), swDocASSEMBLY, 1, "", errors, warnings)
        if swMirror:
            mirror_props = {
                "PartNumber": cpn + "-M",
                "Width": f"{width:.2f}",
                "Height": f"{height:.2f}",
            }
            self._set_custom_properties(swMirror, mirror_props)

            # Update size dimensions for planes and glass cut sketch
            mirror_dims = {
                "D1@LEFT": (width / 2.0) * 0.0254,
                "D1@RIGHT": (width / 2.0) * 0.0254,
                "D1@TOP": (height / 2.0) * 0.0254,
                "D1@BOTTOM": (height / 2.0) * 0.0254,
                "Glass Width@GlassCutSketch": (width - 1.5354) * 0.0254,
                "Glass Height@GlassCutSketch": (height - 1.5354) * 0.0254,
            }
            for name, val in mirror_dims.items():
                dim = swMirror.Parameter(name)
                if dim:
                    dim.SystemValue = val
                    log.info(f"Updated mirror dimension {name} to {val / 0.0254:.4f} in")
                else:
                    log.warning(f"Mirror dimension {name} not found in assembly.")
            
            # Traverse and configure/suppress option-specific components in mirror
            components = swMirror.GetComponents(True)
            if components:
                button_needed = inp.Ava or inp.Keen or inp.Vive
                for comp in components:
                    c_path = comp.GetPathName.lower()
                    c_name = comp.Name2
                    
                    if "js3-ava-keen-vive-1-button-assembly" in c_path:
                        if not button_needed:
                            comp.SetSuppression2(0)  # 0 = Suppressed
                            log.info(f"Suppressed button assembly component: {c_name}")
                        else:
                            comp.SetSuppression2(2)  # 2 = FullyResolved
                            # Determine configuration
                            button_config = None
                            if inp.Ava:
                                button_config = f"64167-{inp.DimmingType}"
                            elif inp.Keen:
                                if result.DriverQty < 2:
                                    button_config = f"61857-{inp.DimmingType}"
                                else:
                                    button_config = f"61857-{inp.DimmingType}-2"
                            elif inp.Vive:
                                button_config = "83047"
                                
                            if button_config:
                                comp.ReferencedConfiguration = button_config
                                log.info(f"Resolved button assembly and set configuration to: {button_config}")
                                
                    elif "58821-mirror-harness" in c_path:
                        if inp.Keen and result.DriverQty < 2:
                            comp.SetSuppression2(2)
                            log.info(f"Resolved Keen 1-Driver harness: {c_name}")
                        else:
                            comp.SetSuppression2(0)
                            log.info(f"Suppressed Keen 1-Driver harness: {c_name}")
                            
                    elif "64090-ava-mirror-harness" in c_path:
                        if inp.Ava or (inp.Keen and result.DriverQty >= 2):
                            comp.SetSuppression2(2)
                            log.info(f"Resolved Ava/Keen 2-Driver harness: {c_name}")
                        else:
                            comp.SetSuppression2(0)
                            log.info(f"Suppressed Ava/Keen 2-Driver harness: {c_name}")
                            
                    elif "64297-m-cable-harness-vive-1" in c_path:
                        if inp.Vive:
                            comp.SetSuppression2(2)
                            log.info(f"Resolved Vive harness: {c_name}")
                        else:
                            comp.SetSuppression2(0)
                            log.info(f"Suppressed Vive harness: {c_name}")
                            
                    elif "64091-ava-mirror-harness-df" in c_path:
                        if inp.Defogger:
                            comp.SetSuppression2(2)
                            log.info(f"Resolved Defogger harness: {c_name}")
                        else:
                            comp.SetSuppression2(0)
                            log.info(f"Suppressed Defogger harness: {c_name}")

            swMirror.ForceRebuild3(False)
            swMirror.Save3(0, errors, warnings)
            self.swApp.CloseDoc(swMirror.GetTitle)
            log.info("Mirror assembly configured and saved.")
        else:
            raise RuntimeError(f"Failed to open mirror assembly copy: {out_mirror}")

        # B. Configure Chassis Assembly
        log.info(f"Opening Chassis copy: {out_chassis}")
        swChassis = self.swApp.OpenDoc6(str(out_chassis), swDocASSEMBLY, 1, "", errors, warnings)
        if swChassis:
            # Set driver configuration
            components = swChassis.GetComponents(True)
            driver_found = False
            for comp in components:
                name = comp.Name2
                if "81330-DRIVER-MODULE" in name:
                    log.info(f"Found driver component: {name}, setting configuration to {result.DriverEnclosurePN}")
                    comp.ReferencedConfiguration = result.DriverEnclosurePN
                    driver_found = True
                    break
            if not driver_found:
                log.warning("Driver module component not found in Chassis assembly!")

            chassis_props = {
                "PartNumber": cpn + "-C",
                "Width": f"{width:.2f}",
                "Height": f"{height:.2f}",
                "Power_Required_W": f"{result.PowerRequirement:.2f}",
                "Power_Available_W": str(result.DriverWattage),
                "Driver_Qty": str(result.DriverQty),
                "Finish": inp.Finish,
                "LED_Color_Temp": inp.LEDColorTemp,
                "Lighting": inp.Lighting,
                "MountType": inp.MountType,
                "Voltage": inp.Voltage,
                "Driver_Type": result.DriverType,
                "Enclosure_PN": result.DriverEnclosurePN,
                "LED_PN": result.LEDPN,
                "LED_Cut_Length_In": f"{result.LEDCutLengthIn:.2f}",
                "LED_Segments": str(result.LEDCuttableSegmentsFinal),
                "LED_Strips": str(result.LEDStripsRequiredEnc),
            }
            self._set_custom_properties(swChassis, chassis_props)

            # Update SA sketch dimensions for layout and mates
            chassis_dims = {
                "D1@SA": width * 0.0254,
                "D7@SA": height * 0.0254,
            }
            for name, val in chassis_dims.items():
                dim = swChassis.Parameter(name)
                if dim:
                    dim.SystemValue = val
                    log.info(f"Updated chassis dimension {name} to {val / 0.0254:.4f} in")
                else:
                    log.warning(f"Chassis dimension {name} not found in assembly.")

            swChassis.ForceRebuild3(False)
            swChassis.Save3(0, errors, warnings)
            self.swApp.CloseDoc(swChassis.GetTitle)
            log.info("Chassis assembly configured and saved.")
        else:
            raise RuntimeError(f"Failed to open chassis assembly copy: {out_chassis}")

        # C. Configure Drawing and export PDF
        log.info(f"Opening Drawing copy: {out_drawing}")
        swDrawing = self.swApp.OpenDoc6(str(out_drawing), swDocDRAWING, 1, "", errors, warnings)
        if swDrawing:
            # Update drawing custom properties
            FINISH_MAP = {
                "BK": "MATTE BLACK", "BK05": "MATTE BLACK",
                "NK": "NATURAL NICKEL", "NK04": "NATURAL NICKEL",
                "CH": "POLISHED CHROME", "CH04": "POLISHED CHROME",
                "BN": "BRUSHED NICKEL", "BN04": "BRUSHED NICKEL",
                "BR": "BRUSHED BRONZE", "BR02": "BRUSHED BRONZE",
                "BZ24": "BRONZE", "BZ47": "BRONZE",
                "GU": "GUN METAL", "GU06": "GUN METAL",
                "WH": "WHITE", "WH01": "WHITE",
            }
            finish_name = FINISH_MAP.get(inp.Finish, inp.Finish)
            try:
                cct_val = int(inp.LEDColorTemp.replace('K', '')) * 100
                cct_str = f"{cct_val:,}"
            except Exception:
                cct_str = inp.LEDColorTemp

            # Lumens calculation: round(Length_In * LM_FT / 12.0)
            # Default to 302 LM/FT for LO/LSE.
            lm_ft = 302.0
            total_lumens = round(result.LEDCutLengthIn * lm_ft / 12.0)
            
            drawing_props = {
                "Sales Aid": f"RAD4-{width:.2f}X{height:.2f}-{inp.Finish}-{inp.LEDColorTemp}",
                "Frame Finish": finish_name,
                "ColorTemp": cct_str,
                "LEDLength": str(round(result.LEDCutLengthIn)),
                "Wattage": str(round(result.PowerRequirement)),
                "PowerRequirements": f"120 OR 277 VOLTS, {result.PowerRequirement / 120.0 * 0.9:.2f} OR {result.PowerRequirement / 277.0 * 0.9:.2f} AMPS",
                "Lumens": f"{total_lumens:,} @ 302 LM/FT",
                "PartNumber": cpn,
                "Description": f"RAD4 {width:.2f}X{height:.2f} {finish_name}",
            }
            self._set_custom_properties(swDrawing, drawing_props)
            log.info("Drawing custom properties set successfully.")

            # Run Python feature traversal to update Sheet 2 notes (mirror assembly and powerbox assembly)
            try:
                self._update_drawing_notes_via_python(swDrawing, cpn, result.DriverWattage)
            except Exception as e:
                log.error(f"Failed to update Sheet 2 notes via Python traversal: {e}")

            # Rebuild twice to ensure all properties propagate to title blocks
            swDrawing.ForceRebuild3(False)
            swDrawing.ForceRebuild3(False)

            # Export to PDF in target output directory
            os.makedirs(output_dir, exist_ok=True)
            pdf_path = os.path.join(output_dir, f"{cpn}-SALES-AID.PDF")
            export_data = self.swApp.GetExportFileData(1) # 1 = swExportPdfData
            success_pdf = swDrawing.Extension.SaveAs(pdf_path, 0, swSaveAsOptions_Silent, export_data, errors, warnings)
            log.info(f"PDF Export status: {success_pdf} to {pdf_path}")

            swDrawing.Save3(0, errors, warnings)
            self.swApp.CloseDoc(swDrawing.GetTitle)
            log.info("Drawing configured and saved.")
        else:
            raise RuntimeError(f"Failed to open drawing copy: {out_drawing}")

        # 7. Export BOM to Excel
        bom_path = os.path.join(output_dir, f"{cpn}-BOM.xlsx")
        self._export_bom(result, bom_path)

        return {
            "chassis_assembly": str(out_chassis),
            "mirror_assembly": str(out_mirror),
            "sales_aid_pdf": pdf_path,
            "bom": bom_path
        }

    def _configure_custom_extrusions(self, vault: str, temp_w: float, temp_h: float, width: float, height: float):
        """
        Creates custom size extrusion parts and sub-assemblies, opens them to set
        their extrusion length dimensions, and updates sub-assembly file references.
        """
        comp_72_dir = Path(vault) / "Products" / "JS3" / "COMPONENTS" / "72000"
        comp_64_dir = Path(vault) / "COMPONENTS" / "64000"
        comp_64_js3_dir = Path(vault) / "Products" / "JS3" / "COMPONENTS" / "64000"

        is_custom_w = abs(width - temp_w) > 0.001
        is_custom_h = abs(height - temp_h) > 0.001

        if not (is_custom_w or is_custom_h):
            return

        def copy_and_update_part(temp_part: Path, out_part: Path, length_val: float, dim_name: str):
            if not temp_part.exists():
                log.warning(f"Extrusion part template not found: {temp_part}")
                return
            if not out_part.exists():
                log.info(f"Copying part template: {temp_part} -> {out_part}")
                _copy_file_writable(temp_part, out_part)
            else:
                try:
                    os.chmod(str(out_part), 0o666)
                except Exception as e:
                    log.warning(f"Could not make existing file writable {out_part}: {e}")
            
            errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
            warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
            swModel = self.swApp.OpenDoc6(str(out_part), 1, 1, "", errors, warnings) # 1 = swDocPART
            if swModel:
                dim = swModel.Parameter(dim_name)
                if dim:
                    dim.SystemValue = length_val * 25.4 / 1000.0
                    log.info(f"Updated {out_part.name} dimension {dim_name} to {length_val} in")
                else:
                    feature = swModel.FirstFeature
                    found = False
                    while feature:
                        disp_dim = feature.GetFirstDisplayDimension
                        while disp_dim:
                            d = disp_dim.GetDimension
                            if d.Name.lower() == dim_name.split('@')[0].lower():
                                d.SystemValue = length_val * 25.4 / 1000.0
                                log.info(f"Updated {out_part.name} dimension {d.Name} in {feature.Name} to {length_val} in")
                                found = True
                                break
                            disp_dim = feature.GetNextDisplayDimension(disp_dim)
                        if found:
                            break
                        feature = feature.GetNextFeature
                swModel.ForceRebuild3(False)
                swModel.Save3(0, errors, warnings)
                self.swApp.CloseDoc(swModel.GetTitle)

        # A. Width Customization (Horizontal Extrusions)
        if is_custom_w:
            temp_alu_w = comp_72_dir / f"72239-{temp_w:.2f}-EXTRUSION-ALUMINUM.SLDPRT"
            out_alu_w = comp_72_dir / f"72239-{width:.2f}-EXTRUSION-ALUMINUM.SLDPRT"
            copy_and_update_part(temp_alu_w, out_alu_w, width, "D1@Extrusion")

            # Check both standard and JS3 locations
            temp_dif_w_standard = comp_64_dir / f"64792-{temp_w:.2f}-EXTRUSION-DIFFUSER.SLDPRT"
            temp_dif_w_js3 = comp_64_js3_dir / f"64792-{temp_w:.2f}-EXTRUSION-DIFFUSER.SLDPRT"
            
            if temp_dif_w_js3.exists():
                temp_dif_w = temp_dif_w_js3
                out_dif_w = comp_64_js3_dir / f"64792-{width:.2f}-EXTRUSION-DIFFUSER.SLDPRT"
            else:
                temp_dif_w = temp_dif_w_standard
                out_dif_w = comp_64_dir / f"64792-{width:.2f}-EXTRUSION-DIFFUSER.SLDPRT"

            copy_and_update_part(temp_dif_w, out_dif_w, width, "D1@Boss-Extrude1")

            temp_asm_w = comp_72_dir / f"72239-XXX-{temp_w:.2f}.SLDASM"
            out_asm_w = comp_72_dir / f"72239-XXX-{width:.2f}.SLDASM"
            if temp_asm_w.exists():
                if not out_asm_w.exists():
                    log.info(f"Copying sub-assembly: {temp_asm_w} -> {out_asm_w}")
                    _copy_file_writable(temp_asm_w, out_asm_w)
                else:
                    try:
                        os.chmod(str(out_asm_w), 0o666)
                    except Exception as e:
                        log.warning(f"Could not make existing file writable {out_asm_w}: {e}")
                self.swApp.ReplaceReferencedDocument(str(out_asm_w), str(temp_alu_w), str(out_alu_w))
                self.swApp.ReplaceReferencedDocument(str(out_asm_w), str(temp_dif_w_js3), str(out_dif_w))
                self.swApp.ReplaceReferencedDocument(str(out_asm_w), str(temp_dif_w_standard), str(out_dif_w))
                
                errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
                warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
                swAsm = self.swApp.OpenDoc6(str(out_asm_w), 2, 1, "", errors, warnings)
                if swAsm:
                    swAsm.ForceRebuild3(False)
                    swAsm.Save3(0, errors, warnings)
                    self.swApp.CloseDoc(swAsm.GetTitle)

        # B. Height Customization (Vertical Extrusions, standard & N)
        if is_custom_h:
            # Extrusion N (with slots/holes)
            temp_alu_hn = comp_72_dir / f"72239-{temp_h:.2f}-N-EXTRUSION-ALUMINUM.SLDPRT"
            out_alu_hn = comp_72_dir / f"72239-{height:.2f}-N-EXTRUSION-ALUMINUM.SLDPRT"
            copy_and_update_part(temp_alu_hn, out_alu_hn, height, "D1@Extrusion")

            # Standard Extrusion (non-N, used for standard height channels)
            temp_alu_h = comp_72_dir / f"72239-{temp_h:.2f}-EXTRUSION-ALUMINUM.SLDPRT"
            out_alu_h = comp_72_dir / f"72239-{height:.2f}-EXTRUSION-ALUMINUM.SLDPRT"
            copy_and_update_part(temp_alu_h, out_alu_h, height, "D1@Extrusion")

            # Check both standard and JS3 locations
            temp_dif_h_standard = comp_64_dir / f"64792-{temp_h:.2f}-EXTRUSION-DIFFUSER.SLDPRT"
            temp_dif_h_js3 = comp_64_js3_dir / f"64792-{temp_h:.2f}-EXTRUSION-DIFFUSER.SLDPRT"
            
            if temp_dif_h_js3.exists():
                temp_dif_h = temp_dif_h_js3
                out_dif_h = comp_64_js3_dir / f"64792-{height:.2f}-EXTRUSION-DIFFUSER.SLDPRT"
            else:
                temp_dif_h = temp_dif_h_standard
                out_dif_h = comp_64_dir / f"64792-{height:.2f}-EXTRUSION-DIFFUSER.SLDPRT"

            copy_and_update_part(temp_dif_h, out_dif_h, height, "D1@Boss-Extrude1")

            temp_asm_hn = comp_72_dir / f"72239-XXX-{temp_h:.2f}-N.SLDASM"
            out_asm_hn = comp_72_dir / f"72239-XXX-{height:.2f}-N.SLDASM"
            if temp_asm_hn.exists():
                if not out_asm_hn.exists():
                    log.info(f"Copying sub-assembly: {temp_asm_hn} -> {out_asm_hn}")
                    _copy_file_writable(temp_asm_hn, out_asm_hn)
                else:
                    try:
                        os.chmod(str(out_asm_hn), 0o666)
                    except Exception as e:
                        log.warning(f"Could not make existing file writable {out_asm_hn}: {e}")
                self.swApp.ReplaceReferencedDocument(str(out_asm_hn), str(temp_alu_hn), str(out_alu_hn))
                self.swApp.ReplaceReferencedDocument(str(out_asm_hn), str(temp_dif_h_js3), str(out_dif_h))
                self.swApp.ReplaceReferencedDocument(str(out_asm_hn), str(temp_dif_h_standard), str(out_dif_h))
                
                errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
                warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
                swAsm = self.swApp.OpenDoc6(str(out_asm_hn), 2, 1, "", errors, warnings)
                if swAsm:
                    swAsm.ForceRebuild3(False)
                    swAsm.Save3(0, errors, warnings)
                    self.swApp.CloseDoc(swAsm.GetTitle)

            temp_asm_h = comp_72_dir / f"72239-XXX-{temp_h:.2f}.SLDASM"
            out_asm_h = comp_72_dir / f"72239-XXX-{height:.2f}.SLDASM"
            if temp_asm_h.exists():
                if not out_asm_h.exists():
                    log.info(f"Copying sub-assembly: {temp_asm_h} -> {out_asm_h}")
                    _copy_file_writable(temp_asm_h, out_asm_h)
                else:
                    try:
                        os.chmod(str(out_asm_h), 0o666)
                    except Exception as e:
                        log.warning(f"Could not make existing file writable {out_asm_h}: {e}")
                self.swApp.ReplaceReferencedDocument(str(out_asm_h), str(temp_alu_h), str(out_alu_h))
                self.swApp.ReplaceReferencedDocument(str(out_asm_h), str(temp_dif_h_js3), str(out_dif_h))
                self.swApp.ReplaceReferencedDocument(str(out_asm_h), str(temp_dif_h_standard), str(out_dif_h))
                
                errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
                warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
                swAsm = self.swApp.OpenDoc6(str(out_asm_h), 2, 1, "", errors, warnings)
                if swAsm:
                    swAsm.ForceRebuild3(False)
                    swAsm.Save3(0, errors, warnings)
                    self.swApp.CloseDoc(swAsm.GetTitle)

    def _set_custom_properties(self, swModel, props: dict):
        mgr = swModel.Extension.CustomPropertyManager("")
        for key, val in props.items():
            mgr.Add3(key, 30, str(val), 1)
            mgr.Set2(key, str(val))

    def _export_bom(self, result: RAD4Result, output_xlsx_path: str):
        try:
            import openpyxl
            import datetime
            from openpyxl.styles import Font, PatternFill
        except ImportError:
            log.warning("openpyxl or datetime not installed — skipping Excel BOM.")
            return

        vault = DWConstantVault
        bom_dir = Path(vault) / "Products" / "JS3" / "Mirrors" / "RAD4"
        vault_bom_path = bom_dir / f"{result.CPN}-M-BOM.xlsx"

        # Search for a template in the vault
        bom_templates = list(bom_dir.glob("RAD4-*-M-BOM.xlsx"))
        template_copied = False

        if bom_templates:
            template_bom = bom_templates[0]
            log.info(f"Using vault BOM template: {template_bom}")
            try:
                # Copy to both locations
                _copy_file_writable(template_bom, Path(output_xlsx_path))
                _copy_file_writable(template_bom, vault_bom_path)
                template_copied = True
            except Exception as e:
                log.warning(f"Could not copy vault BOM template: {e}")

        if template_copied:
            try:
                # Open, update cells, and save to both locations
                for path_to_save in [output_xlsx_path, str(vault_bom_path)]:
                    wb = openpyxl.load_workbook(path_to_save)
                    ws = wb.active
                    
                    # Update cells based on defined named ranges / cell addresses
                    ws["D1"] = f"{result.CPN}-M"
                    ws["D2"] = datetime.datetime.now().strftime("%m/%d/%Y")
                    ws["D6"] = result.DriverEnclosurePN
                    ws["D7"] = "AI"
                    ws["D8"] = "AI"
                    ws["D9"] = datetime.datetime.now().strftime("%m/%d/%Y")
                    
                    wb.save(path_to_save)
                log.info(f"BOM exported with template format to {output_xlsx_path} and {vault_bom_path}")
                return
            except Exception as e:
                log.error(f"Error customizing template BOM: {e}. Falling back to basic BOM generation.")

        # Fallback to basic BOM generation from scratch
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "BOM"

        header_fill = PatternFill("solid", fgColor="1F3864")
        
        ws.cell(row=1, column=1, value=f"BOM — {result.CPN}")
        ws.merge_cells("A1:C1")
        ws.cell(row=1, column=1).font = Font(bold=True, size=12, color="FFFFFF")
        ws.cell(row=1, column=1).fill = header_fill

        headers = ["BOM Item", "Part Number", "Description"]
        for col, h in enumerate(headers, 1):
            cell = ws.cell(row=2, column=col, value=h)
            cell.font = Font(bold=True)
            cell.fill = PatternFill("solid", fgColor="D9E1F2")

        row = 3
        for item, pn in result.BOM.items():
            if pn:
                ws.cell(row=row, column=1, value=item.replace("_", " "))
                ws.cell(row=row, column=2, value=pn)
                row += 1

        ws.column_dimensions["A"].width = 35
        ws.column_dimensions["B"].width = 30
        ws.column_dimensions["C"].width = 40

        # Save to both target output and vault
        wb.save(output_xlsx_path)
        try:
            shutil.copyfile(output_xlsx_path, str(vault_bom_path))
            os.chmod(str(vault_bom_path), 0o666)
        except Exception as e:
            log.warning(f"Could not copy fallback BOM to vault: {e}")
            
        log.info(f"BOM exported (fallback) to: {output_xlsx_path}")

    def _update_drawing_notes_via_python(self, swDrawing, cpn: str, driver_wattage: float):
        powerbox = "81330-96W" if driver_wattage <= 96 else "81330-192W"
        log.info(f"Updating Sheet 2 notes in SolidWorks via design tree feature traversal (wattage: {driver_wattage}W)")
        
        # Traverse design tree features
        feat = swDrawing.FirstFeature
        while feat:
            if feat.GetTypeName2 == "DrSheet" and feat.Name.lower() == "sheet2":
                sf = feat.GetFirstSubFeature
                while sf:
                    if sf.GetTypeName2 in ["AbsoluteView", "UnfoldedView", "SectionAssemView"]:
                        view = sf.GetSpecificFeature2
                        if view:
                            note = view.GetFirstNote
                            while note:
                                text = note.GetText
                                if text and "mirror assembly:" in text.lower():
                                    new_text = f"MIRROR ASSEMBLY:  {cpn}-M\nPOWERBOX ASSEMBLY: {powerbox}"
                                    note.SetText(new_text)
                                    log.info(f"Successfully updated drawing note in view '{sf.Name}': {new_text}")
                                note = note.GetNext
                    sf = sf.GetNextSubFeature
            feat = feat.GetNextFeature

    def close(self):
        pass
