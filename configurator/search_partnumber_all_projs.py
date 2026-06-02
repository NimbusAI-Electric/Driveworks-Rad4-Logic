import zipfile
import xml.etree.ElementTree as ET
import sys

sys.stdout.reconfigure(encoding='utf-8')

PROJECTS = {
    "JS3_Parent":  r"N:\Driveworks\Projects\JS3\JS3.driveprojx",
    "JS3_Chassis": r"N:\Driveworks\Projects\JS3 Chassis\JS3 Chassis.driveprojx",
    "JS3_Mirror":  r"N:\Driveworks\Projects\JS3 Mirror\JS3 Mirror.driveprojx",
    "RAD3":        r"N:\Driveworks\Projects\RAD3\RAD3.driveprojx",
}

for proj_name, proj_path in PROJECTS.items():
    print(f"\n================ PROJECT: {proj_name} ================")
    with zipfile.ZipFile(proj_path, 'r') as z:
        for filename in z.namelist():
            if filename.endswith('.xml'):
                content = z.read(filename).decode('utf-8', errors='replace')
                if "Variable" in content or "Rule" in content:
                    root = ET.fromstring(content)
                    for elem in root.iter():
                        tag = elem.tag.split('}')[-1]
                        if tag in ("Variable", "SpecialVariable", "Rule"):
                            name = elem.attrib.get('StoreName') or elem.attrib.get('Name') or elem.attrib.get('Id') or elem.attrib.get('Name')
                            rule = elem.attrib.get('Rule') or elem.attrib.get('rule') or elem.attrib.get('Formula')
                            if not rule:
                                formula_elem = elem.find('{*}Formula') or elem.find('Formula')
                                if formula_elem is not None:
                                    rule = formula_elem.text
                            
                            if name and any(x == name for x in ["DWVariablePartNumber", "PartNumber", "CPN", "RadCPN", "DWVariableRadCPN"]):
                                print(f"  [{tag}] {name} = {rule}")
