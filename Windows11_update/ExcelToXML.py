import pandas as pd
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom

# Configuration
excel_file_path = "\ladjitfstech\Lansweeper_win10_to_11\win11_09_07_SCRIPT.xlsx"  # Replace with your UNC path
xml_file_path = "\ladjitfstech\Lansweeper_win10_to_11\HostOwners.xml"    # Replace with output UNC path

try:
    # Read Excel file
    df = pd.read_excel(excel_file_path, engine='openpyxl')
    
    # Verify required columns
    if not {'Hostname', 'Owner'}.issubset(df.columns):
        raise ValueError("Excel file must contain 'Hostname' and 'Owner' columns")

    # Create XML structure
    root = ET.Element("Hosts")
    
    # Iterate through DataFrame rows
    for _, row in df.iterrows():
        host = ET.SubElement(root, "Host")
        ET.SubElement(host, "Hostname").text = str(row['Hostname'])
        ET.SubElement(host, "Owner").text = str(row['Owner'])

    # Pretty-print and save XML
    rough_string = ET.tostring(root, encoding='unicode')
    parsed = minidom.parseString(rough_string)
    pretty_xml = parsed.toprettyxml(indent="  ")

    with open(xml_file_path, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)
    
    print(f"XML file created at {xml_file_path}")

except Exception as e:
    print(f"Error: {e}")