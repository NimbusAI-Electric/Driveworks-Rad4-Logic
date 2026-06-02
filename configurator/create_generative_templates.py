"""
create_generative_templates.py
==============================
Programmatic template builder for the generative RAD4 SolidWorks configurator.
Creates a clean, blank skeleton part and a master template assembly, saving
them in the configurator/templates folder.
"""

import win32com.client as win32
import pythoncom
import sys
import os
from pathlib import Path

def main():
    print("Connecting to SolidWorks...")
    try:
        swApp = win32.GetActiveObject("SldWorks.Application")
    except Exception:
        swApp = win32.Dispatch("SldWorks.Application.29")
    swApp.Visible = True

    # Paths
    templates_dir = Path(r"N:\Driveworks\github_push\configurator\templates")
    templates_dir.mkdir(parents=True, exist_ok=True)

    skeleton_path = templates_dir / "RAD4-SKELETON.SLDPRT"
    assembly_path = templates_dir / "RAD4-MASTER-ASSEMBLY.SLDASM"

    part_template = r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\lang\english\Tutorial\part.prtdot"
    assembly_template = r"C:\Program Files\SOLIDWORKS Corp\SOLIDWORKS\lang\english\Tutorial\assem.asmdot"

    errors = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)
    warnings = win32.VARIANT(pythoncom.VT_BYREF | pythoncom.VT_I4, 0)

    # -------------------------------------------------------------------------
    # 1. Create skeleton part (RAD4-SKELETON.SLDPRT)
    # -------------------------------------------------------------------------
    if not skeleton_path.exists():
        print(f"Creating skeleton part from template: {part_template}")
        swPart = swApp.NewDocument(part_template, 0, 0, 0)
        if not swPart:
            print("Failed to create part from template path.")
            sys.exit(1)

        # Disable dimension dialog (swInputDimValOnCreate = 10)
        orig_toggle = swApp.GetUserPreferenceToggle(10)
        swApp.SetUserPreferenceToggle(10, False)

        # Select Front Plane via feature loop
        feature = swPart.FirstFeature
        front_plane_feature = None
        while feature:
            if feature.GetTypeName2 == "RefPlane" and "front" in feature.Name.lower():
                front_plane_feature = feature
                break
            feature = feature.GetNextFeature

        if not front_plane_feature:
            print("Could not locate Front Plane feature.")
            swApp.CloseDoc(swPart.GetTitle)
            sys.exit(1)

        front_plane_feature.Select2(False, 0)
        swPart.SketchManager.InsertSketch(True)

        # Draw center rectangle 36x36 in (0.9144 x 0.9144 m)
        swPart.SketchManager.CreateCenterRectangle(0, 0, 0, 0.4572, 0.4572, 0)

        swSketch = swPart.SketchManager.ActiveSketch
        segments = swSketch.GetSketchSegments

        horiz_line = None
        vert_line = None
        for seg in segments:
            if not seg.ConstructionGeometry:
                start_pt = seg.GetStartPoint2
                end_pt = seg.GetEndPoint2
                dx = abs(end_pt.X - start_pt.X)
                dy = abs(end_pt.Y - start_pt.Y)
                if dy < 1e-6 and horiz_line is None:
                    horiz_line = seg
                elif dx < 1e-6 and vert_line is None:
                    vert_line = seg

        # Add width dimension
        if horiz_line:
            horiz_line.Select2(False, 0)
            swPart.AddDimension2(0.0, 0.6, 0.0)

        # Add height dimension
        if vert_line:
            vert_line.Select2(False, 0)
            swPart.AddDimension2(0.6, 0.0, 0.0)

        swPart.SketchManager.InsertSketch(True)

        # Rename sketch feature to SkeletonSketch
        f = swPart.FirstFeature
        sketch_feat = None
        while f:
            if f.GetTypeName2 in ["ProfileFeature", "Sketch"]:
                f.Name = "SkeletonSketch"
                sketch_feat = f
                break
            f = f.GetNextFeature

        # Rename dimensions inside sketch to Width and Height
        if sketch_feat:
            display_dim = sketch_feat.GetFirstDisplayDimension
            count = 0
            while display_dim:
                dim = display_dim.GetDimension
                if count == 0:
                    dim.Name = "Width"
                elif count == 1:
                    dim.Name = "Height"
                count += 1
                display_dim = sketch_feat.GetNextDisplayDimension(display_dim)

        swPart.ForceRebuild3(False)

        # Restore dimension popup state
        swApp.SetUserPreferenceToggle(10, orig_toggle)

        # Save and close Part
        print(f"Saving skeleton part to {skeleton_path}...")
        swPart.SaveAs3(str(skeleton_path), 0, 1)
        swApp.CloseDoc(swPart.GetTitle)
        print("Skeleton part created successfully.")
    else:
        print(f"Skeleton part already exists at: {skeleton_path}")

    # Open skeleton part in background/memory first before inserting
    print(f"Opening skeleton part in memory: {skeleton_path}")
    swPartDoc = swApp.OpenDoc6(str(skeleton_path), 1, 1, "", errors, warnings)
    if not swPartDoc:
         print("Warning: failed to open skeleton part in memory, proceeding anyway...")

    # -------------------------------------------------------------------------
    # 2. Create master template assembly (RAD4-MASTER-ASSEMBLY.SLDASM)
    # -------------------------------------------------------------------------
    print(f"\nCreating master assembly from template: {assembly_template}")
    swAsm = swApp.NewDocument(assembly_template, 0, 0, 0)
    if not swAsm:
        print("Failed to create assembly from template path.")
        sys.exit(1)

    asm_title = swAsm.GetTitle
    print(f"Activating assembly document: {asm_title}")
    swApp.ActivateDoc3(asm_title, True, 2, errors)

    print(f"Inserting skeleton part {skeleton_path.name} into assembly...")
    try:
        # Call AddComponent4 on assembly doc
        swComp = swAsm.AddComponent4(str(skeleton_path), "", 0.0, 0.0, 0.0)
        if swComp:
            print(f"Successfully inserted component: {swComp.Name2}")
        else:
            print("Direct call returned None, trying via swApp.ActiveDoc...")
            active_doc = swApp.ActiveDoc
            swComp = active_doc.AddComponent4(str(skeleton_path), "", 0.0, 0.0, 0.0)
            if swComp:
                print(f"Successfully inserted component via ActiveDoc: {swComp.Name2}")
            else:
                print("Failed to insert skeleton component via both methods.")
                swApp.CloseDoc(asm_title)
                if swPartDoc:
                    swApp.CloseDoc(swPartDoc.GetTitle)
                sys.exit(1)
    except Exception as e:
        print(f"Exception during AddComponent4: {e}")
        swApp.CloseDoc(asm_title)
        if swPartDoc:
             swApp.CloseDoc(swPartDoc.GetTitle)
        sys.exit(1)

    swAsm.ForceRebuild3(False)

    # Save and close Assembly
    print(f"Saving master assembly to {assembly_path}...")
    swAsm.SaveAs3(str(assembly_path), 0, 1)
    swApp.CloseDoc(asm_title)
    
    if swPartDoc:
         swApp.CloseDoc(swPartDoc.GetTitle)
         
    print("Master assembly created successfully.")

if __name__ == "__main__":
    main()
