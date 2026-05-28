import os, glob
import xml.etree.ElementTree as ET

def search_xml(root_dir, terms):
    for root_path, _, files in os.walk(root_dir):
        for file in files:
            if not file.endswith('.xml'): continue
            path = os.path.join(root_path, file)
            try:
                tree = ET.parse(path)
                root = tree.getroot()
                for elem in root.iter():
                    text = (elem.text or '') + ' ' + str(elem.attrib)
                    for term in terms:
                        if term.lower() in text.lower():
                            print(f"Match in {path}:")
                            print(f"  Tag: {elem.tag}")
                            print(f"  Attribs: {elem.attrib}")
                            t = elem.text or ""
                            print(f"  Text: {t[:500]}")
                            print('-'*40)
            except Exception as e:
                pass

search_xml(r'N:\Driveworks\temp', ['ReloadOrReplace', 'Sales Aid', 'View 7', 'PowerRequirement', 'MaxSegments', '74', 'Frost_Inset', 'Sketch Refresh', 'Driver_Qty'])
