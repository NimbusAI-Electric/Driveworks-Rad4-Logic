"""
server.py
=========
FastAPI backend server for the RAD4 configurator.

Wires the web UI form → rad4_engine → sw_api → SolidWorks.
Run with:  python server.py
Then open: http://localhost:8000
"""

import os
import json
import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional

from rad4_engine import RAD4Inputs, run as engine_run
from sw_api import SolidWorksAPI

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)

OUTPUT_DIR = r"N:\AI Driveworks Output"

app = FastAPI(title="RAD4 Configurator", version="1.0")
app.mount("/ui", StaticFiles(directory="ui"), name="ui")


# =============================================================================
# REQUEST / RESPONSE MODELS
# =============================================================================

class ConfigRequest(BaseModel):
    """Maps exactly to the DriveWorks form fields."""
    UnitWidth:       float  = 36.0
    UnitHeight:      float  = 36.0
    MountType:       str    = "RM"
    Lighting:        str    = "LSE"
    LEDColorTemp:    str    = "30K"
    Finish:          str    = "NK04"
    Voltage:         str    = "Standard"
    DimmingType:     str    = ""
    Ava:             bool   = False
    AvaLocation:     str    = "Center"
    Keen:            bool   = False
    KeenLocation:    str    = "Center"
    Clock:           bool   = False
    ClockType:       str    = ""
    ClockLocation:   str    = "Right"
    CordConnect:     bool   = False
    CordConnectType: str    = ""
    Defogger:        bool   = False
    NightLight:      bool   = False
    NightLightType:  str    = ""
    NonBrilliant:    bool   = False
    Savvy:           bool   = False
    TV:              bool   = False
    TVSize:          str    = ""
    Vive:            bool   = False
    ViveType:        str    = ""
    WallGlow:        bool   = False
    WallGlowType:    str    = ""
    Wardrobe:        bool   = False


# =============================================================================
# ROUTES
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("ui/index.html", "r") as f:
        return HTMLResponse(content=f.read())


@app.post("/preview")
async def preview(req: ConfigRequest):
    """
    Returns live CPN, power calc, and enclosure — no SolidWorks interaction.
    Drives the live preview at the bottom of the configurator form.
    """
    inp = _map_request(req)
    result = engine_run(inp)
    return JSONResponse({
        "CPN":             result.CPN,
        "PowerRequired":   round(result.PowerRequirement, 2),
        "PowerAvailable":  result.DriverWattage,
        "Enclosure":       result.DriverEnclosurePN,
        "LEDSegments":     result.LEDCuttableSegmentsFinal,
        "LEDCutLength":    result.LEDCutLengthIn,
        "DriverType":      result.DriverType,
        "DriverQty":       result.DriverQty,
        "BOM":             result.BOM,
        "Paths": {
            "mirror":   result.MirrorAssemblyPath,
            "chassis":  result.ChassisAssemblyPath,
            "salesaid": result.SalesAidDrawingPath,
        }
    })


@app.post("/release")
async def release(req: ConfigRequest):
    """
    Runs the full DriveWorks pipeline:
      engine → SolidWorks COM → model + drawing + BOM
    Equivalent to clicking the green 'Release' button in DriveWorks.
    """
    inp = _map_request(req)
    result = engine_run(inp)

    log.info(f"RELEASE triggered for: {result.CPN}")

    try:
        api = SolidWorksAPI()
        output_paths = api.generate(inp, result, OUTPUT_DIR)
        return JSONResponse({
            "status":  "success",
            "CPN":     result.CPN,
            "outputs": output_paths
        })
    except Exception as e:
        log.error(f"Release failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _map_request(req: ConfigRequest) -> RAD4Inputs:
    """Maps the API request to a RAD4Inputs dataclass."""
    return RAD4Inputs(
        UnitWidth       = req.UnitWidth,
        UnitHeight      = req.UnitHeight,
        MirrorType      = "RAD4",
        MountType       = req.MountType,
        Lighting        = req.Lighting,
        LEDColorTemp    = req.LEDColorTemp,
        Finish          = req.Finish,
        Voltage         = req.Voltage,
        Dimming         = bool(req.DimmingType),
        DimmingType     = req.DimmingType,
        Ava             = req.Ava,
        AvaLocation     = req.AvaLocation,
        Keen            = req.Keen,
        KeenLocation    = req.KeenLocation,
        Clock           = req.Clock,
        ClockType       = req.ClockType,
        ClockLocation   = req.ClockLocation,
        CordConnect     = req.CordConnect,
        CordConnectType = req.CordConnectType,
        Defogger        = req.Defogger,
        NightLight      = req.NightLight,
        NightLightType  = req.NightLightType,
        NonBrilliant    = req.NonBrilliant,
        Savvy           = req.Savvy,
        TV              = req.TV,
        TVSize          = req.TVSize,
        Vive            = req.Vive,
        ViveType        = req.ViveType,
        WallGlow        = req.WallGlow,
        WallGlowType    = req.WallGlowType,
        Wardrobe        = req.Wardrobe,
    )


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
