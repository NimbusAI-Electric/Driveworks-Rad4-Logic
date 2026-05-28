import os
import zipfile
import xml.etree.ElementTree as ET
import json

def analyze_driveworks_projects(root_dir):
    projects = []
    
    for dirpath, dirnames, filenames in os.walk(root_dir):
        if 'Test' in dirpath.split(os.sep) or 'Archive' in dirpath.split(os.sep) or 'Projects_Recovered' in dirpath.split(os.sep) or 'Specifications' in dirpath.split(os.sep):
            continue
            
        for file in filenames:
            if file.endswith('.driveprojx'):
                full_path = os.path.join(dirpath, file)
                try:
                    with zipfile.ZipFile(full_path, 'r') as z:
                        if 'driveProj/project.xml' in z.namelist():
                            xml_content = z.read('driveProj/project.xml')
                            tree = ET.fromstring(xml_content)
                            
                            namespaces = {'project': 'http://schemas.driveworks.co.uk/project/'}
                            
                            variables = []
                            constants = []
                            child_projects = []
                            documents = []
                            
                            # Note: The actual XML schema might vary slightly, but generally we can find text or names.
                            for elem in tree.iter():
                                tag = elem.tag
                                if tag.endswith('Variable'):
                                    name = elem.get('Name')
                                    if name: variables.append(name)
                                elif tag.endswith('Constant'):
                                    name = elem.get('Name')
                                    if name: constants.append(name)
                                elif tag.endswith('ChildSpecification'):
                                    proj_name = elem.get('ProjectName')
                                    if proj_name: child_projects.append(proj_name)
                                elif tag.endswith('Document'):
                                    name = elem.get('Name')
                                    if name: documents.append(name)

                            projects.append({
                                'Path': full_path,
                                'Name': file.replace('.driveprojx', ''),
                                'VariableCount': len(variables),
                                'ConstantCount': len(constants),
                                'VariablesSample': variables[:10],
                                'ConstantsSample': constants[:10],
                                'FromParentConstants': [c for c in constants if 'From_Parent' in c],
                                'ChildProjects': child_projects,
                                'Documents': documents
                            })
                except Exception as e:
                    projects.append({
                        'Path': full_path,
                        'Name': file.replace('.driveprojx', ''),
                        'Error': str(e)
                    })
                    
    return projects

if __name__ == '__main__':
    data = analyze_driveworks_projects(r'N:\Driveworks\Projects')
    with open(r'N:\Driveworks\project_analysis.json', 'w') as f:
        json.dump(data, f, indent=4)
    print("Analysis saved to N:\Driveworks\project_analysis.json")
