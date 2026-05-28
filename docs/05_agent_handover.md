# Developer & AI Agent Handover Guide
### Standalone RAD4 SolidWorks Configurator

Welcome! This guide outlines the project state, codebase architecture, and latest modifications so you can resume work immediately.

---

## 1. Project Context & Purpose

The goal of this project is to replace a complex **DriveWorks** mirror configurator with a standalone **Python + SolidWorks COM API** pipeline. The user interacts with a web interface, and the system dynamically computes engineering logic, drives SolidWorks 2021 programmatically to generate 3D models and Sales Aid drawings, and exports a production-ready BOM.

---

## 2. Core Codebase Structure

All codebase files are located in `n:\Driveworks\github_push\configurator\`:

*   **`rad4_engine.py`**:
    *   Replicates DriveWorks variables, formulas, and math in pure Python.
    *   Generates the Customer Part Number (CPN), determines the required LED segment counts, calculates driver wattage tier (e.g. `96W`, `192W`), driver quantity, and maps the final Bill of Materials (BOM) part numbers.
*   **`sw_api.py`**:
    *   Connects to the SolidWorks COM API (`SldWorks.Application`).
    *   Selects standard template files (chassis, mirror, and drawing) based on the closest size match.
    *   Maintains reference redirection logic for structural profiles (`72239` frame, `64792` diffuser) and custom LED sub-assemblies/parts.
    *   Opens assemblies, updates dimensions (extrusion lengths, layout sketches, planes, glass sketch bounds), updates custom drawing sheet properties, triggers rebuilds, exports PDF drawings, and saves files.
*   **`server.py`**:
    *   FastAPI backend that exposes `/release` (run full SW pipeline), `/preview` (return engine values instantly), and `/status` endpoints.
*   **`ui/`**:
    *   Vibrant, responsive vanilla HTML/JS frontend that replicates the original DriveWorks form fields.

---

## 3. Latest Work & Major Fixes

During the latest session, we resolved a critical bug regarding **LED Strip sizing on custom/mismatched configurations**:

1.  **Removed 74 Segment Cap**:
    *   In `rad4_engine.py`, we removed a hallucinated limit (`RAD4_MAX_SEGMENTS = 74`).
    *   DriveWorks logic has no physical limit on segment counts; the segment count is now determined dynamically by base perimeter divided by pitch (e.g. `108` segments for `82.00x36.00` LHE lighting).
2.  **Dynamic Driver Strip Division**:
    *   Implemented driver capacity checks matching DriveWorks XML rules. LED strips are automatically divided into multiple sections if their power draw exceeds driver wattage tiers (e.g. SO lighting dividing into 2 strips).
3.  **LED Assembly & Part Reference Replacement**:
    *   In `sw_api.py`, we implemented dynamic reference replacement for the LED sub-assembly.
    *   When generating custom sizes, the system opens the matched template briefly to locate the referenced LED sub-assembly (e.g., `82181-RAD3-6050MM-84.00X36.00.SLDASM` inside an `84.00` template).
    *   It computes the correct LED length rounded to the nearest `50` mm (e.g. `5950` mm for `82.00x36.00`).
    *   If they do not exist, it copies/renames the LED part and sub-assembly templates.
    *   It opens the new part, sets `D1@MASTER SKETCH` and `D2@MASTER SKETCH` in SolidWorks to match the custom width and height, and rebuilds.
    *   It redirects references inside the custom sub-assembly and the mirror assembly.
4.  **Verification**:
    *   Successfully verified using `scratch/test_e2e.py` for `82.00x36.00`. The generated mirror assembly correctly references `82181-RAD3-5950MM-82.00X36.00.SLDASM` which references `RAD3-LED-5950-82.00X36.00.SLDPRT` with Master Sketch width and height set to `82.00` and `36.00`.

---

## 4. How to Run, Test, and Resume

*   **Active Server**: The FastAPI server runs on port `8000` via `python server.py`.
*   **SolidWorks Environment**: Must run on the host with Vault accessible at `C:\EM Engineering Vault\`.
*   **Outputs**: All drawing PDFs, Excel BOMs, and customized assemblies are saved to `N:\AI Driveworks Output\`.
*   **Test Script**: You can run the end-to-end configuration pipeline directly using the scratch script:
    ```bash
    python C:\Users\g.muzio\.gemini\antigravity\brain\19488e01-31a2-4e09-bbcd-822eb2deaacf\scratch\test_e2e.py
    ```

### Recommended Next Steps:
1.  Verify the web UI frontend interaction with the `/release` endpoint.
2.  Expand testing to other custom and standard sizes (e.g., extremely tall wardrobe styles).
3.  Add additional feature checks (e.g., Defogger placement logic and TV cutout coordinates mapping).
