# Programmatic RAD4 SolidWorks Configurator
### Standalone Mirror Configurator bypassing DriveWorks

This repository contains the complete implementation of the standalone RAD4 mirror configurator. It replaces the DriveWorks project pipeline with a direct Python-driven backend that calculates mirror properties and uses the SolidWorks COM API to generate and save production models, drawing PDFs, and Excel BOM files.

---

## 1. Directory Structure

*   **`configurator/`**: Main application folder.
    *   `rad4_engine.py`: Replicates DriveWorks variable definitions, formulas, and math (BOM generation, LED pitch, segment count, wattage/driver selection, CPN parsing).
    *   `sw_api.py`: SolidWorks COM integration. Copies standard templates, updates custom scaled profiles (`72239` structural frame, `64792` diffuser), and customizes/replaces LED sub-assembly and part references.
    *   `server.py`: FastAPI server exposing `/release` (run full SW pipeline), `/preview` (calculate engine values instantly), and `/status` endpoints.
    *   `ui/`: Vanilla HTML/JS frontend that replicates the DriveWorks form fields (sizes, finishes, lighting, and dimming options).
*   **`docs/`**: Project documentation, implementation plans, and handovers.
    *   `01_implementation_plan.md`: Initial architecture plan.
    *   `02_v2_architecture_audit.md`: Deep-dive audit of original DriveWorks project.
    *   `03_RAD4_independent_plan.md`: Strategy for isolating RAD4 from other styles.
    *   `04_RAD4_full_logic_extraction.md`: Full extraction of variables and constraints.
    *   `05_agent_handover.md`: Handover guide for developers/AI agents.
*   **`scripts/`**: Historical extraction and unpacking utilities.
*   **`analysis/`**: Analytical spreadsheets and structural logs.

---

## 2. Getting Started

### Prerequisites
*   Windows OS (tested on Windows 10/11)
*   Python 3.9+
*   SolidWorks 2021 (with COM interface active)
*   Access to the engineering vault: `C:\EM Engineering Vault\`

### Installation
Clone the repository and install the dependencies:
```bash
pip install -r configurator/requirements.txt
```
*Note: Requirements include `fastapi`, `uvicorn`, `pywin32`, `openpyxl`.*

### Running the Configurator
1.  Start the FastAPI backend:
    ```bash
    python configurator/server.py
    ```
2.  Open the web UI by launching `configurator/ui/index.html` in your web browser.
3.  Fill in the mirror specifications and click the green **Release** button to trigger programmatic model generation in SolidWorks.

---

## 3. Core Features

*   **Custom Size Support**: Automatically matches standard templates, copies horizontal/vertical aluminum extrusions and diffusers, scales their sizes to custom dimensions (e.g. `36.22`), and updates assembly mate coordinates.
*   **LED Sizing Logic**: Computes exact LED strip segments (uncapped, matching DriveWorks mathematical perimeter) and generates custom LED parts (`RAD3-LED-*.SLDPRT`) and assemblies (`8218x-RAD3-*.SLDASM`) sized to the frame.
*   **Dynamic Title Blocks**: Injects custom properties (lumen counts, wattage, voltage, CPN, and finish names) directly into drawings and sheets.
*   **BOM Exporting**: Generates production-ready Bill of Materials exported to Excel files in `N:\AI Driveworks Output\`.
