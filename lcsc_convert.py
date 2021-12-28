#!/usr/bin/env python3
import requests
import json
import os
import sys

def printerr(instr, **kwargs):
    print(f"\033[1;31m{instr}\033[39m\033[0m", **kwargs)

def insert_footprint(footprint):
    # F2 "" 0 0 50 H I C CNN
    # F2 "digikey-footprints:LED_RGB_WP154A4SUREQBFZGC" 200 200 60 H I L C N N
    return f"F2 \"LCSC:{footprint}\" 200 200 60 H I L C N N\n"

def insert_datasheet(lcsc_pn):
    # F3 "http://www.ti.com/general/docs/suppproductinfo.tsp?distId=10&gotoUrl=http%3A%2F%2Fwww.ti.com%2Flit%2Fgpn%2Flmc6482" 200 300 60 H I L C N N
    return f"F3 \"https://lcsc.com/eda_search?q={lcsc_pn}\" 200 300 60 H I L C N N"

if len(sys.argv) != 2:
    printerr("Converter expects single argument, LCSC part number (e.g. C131042)")
    exit()

lcsc_pn = sys.argv[1] 
uuid_link = f"https://easyeda.com/api/products/{lcsc_pn}/svgs"
results = requests.get(uuid_link).json()

if len(results['result']) == 0:
    printerr(f"No components found with PN {lcsc_pn}")
    exit()

for lcsc_uuid in results['result'][:1]:
    lcsc_uuid = lcsc_uuid['component_uuid']
    print(f"Extracting component {lcsc_uuid}")
    link = f"https://easyeda.com/api/components/{lcsc_uuid}"

    # get list of files to see what ones it creates
    currentlines = []
    files = os.listdir(".")
    if "LCSC.lib" not in files:
        with open("LCSC.lib", 'w') as f:
            f.write("EESchema-LIBRARY Version 2.3\n#encoding utf-8\n#\n#End Library")
        files.append("LCSC.lib")

    with open("LCSC.lib") as f:
        currentlines = f.readlines()

    # RUN CONVERSION
    os.system(f"wget {link} -qO /tmp/component.json && lc2kicad -l /tmp/component.json")

    # Update LCSC.lib file to include new library, with reference to new footprint
    newfiles = [f for f in os.listdir(".") if f not in files]
    newlibl = sorted([f for f in newfiles if ".lib" in f])
    newfootl = [f for f in newfiles if ".kicad_mod" in f]

    if (len(newlibl) != 1 or len(newfootl) != 1) and len(results['result']) == 1:
        printerr("Unexpected number of new files in folder! oooops, cannot append to LCSC.lib")
        exit()

    if len(newfootl) == 0:
        # Footprint already exists
        # Search in /tmp/component.json to see if one can find the name of it.
        newfoot = ""
        with open("/tmp/component.json") as f:
            r = json.load(f)
            newfoot = r['result']['packageDetail']['title']
            print(f"Footprint already exists: {newfoot}")

    else: newfoot = newfootl[0][:-10] # cut off .kicad_mod

    partname = ""

    if len(newlibl) > 1 and len(results['result']) > 1: # dealing with subparts
        # take the header info out of the first one
        # and stick on the drawing information of the previous ones
        # with the 3rd last column replaced with the subpart number
        lines = []
        num_subparts = len(newlibl)

        # Header processing:
        # First extract symbol name and filter to get rid of .spX
        # Update F0 (reference) field to remove the . in the U?. (remnant of the EasyEDA symbol referencing)
        # Also update F1 and F2 fields for part number and footprint respectively
        # Update F3 field with link to datasheet
        with open(newlibl[0]) as f:
            for line in f.readlines():
                if "# " in line:
                    line = line.replace(".sp1", "") # it will always be first subpart because sorted list
                elif "DEF " in line:
                    line = line.split()
                    line[1] = line[1].replace(".sp1", "")
                    partname = line[1]
                    line[2] = line[2].replace("?.", "")  # remove ?. in U?.
                    line[-3] = str(num_subparts)
                    line = " ".join(line)
                elif "F0 " in line:
                    line = line.replace("?.", "")
                elif "F1 " in line:
                    line = line.replace(".sp1", "")
                elif "F2 " in line:
                    line = insert_footprint(newfoot) 
                elif "F3 " in line:
                    line = insert_datasheet(lcsc_pn)

                if "DRAW" in line:
                    line = line.strip()
                    lines.append(line)
                    break
                elif "EESchema" not in line and "encoding" not in line:
                    line = line.strip()
                    lines.append(line)
        
        part_idx_loc = {
            "A": 6,
            "C": 4,
            "P": 2,
            "S": 5,
            "T": 6,
            "B": 2,
            "X": 9 
        }

        for idx, lib in enumerate(newlibl):
            idx += 1 # 1-indexed :(
            with open(lib) as f:
                for line in f.readlines():
                    if line[0] in part_idx_loc:
                        line = line.split()
                        subpartnum = part_idx_loc[line[0]]
                        line[subpartnum] = str(idx)
                        line[subpartnum+1] = '1' # alternate de morgan shape (both)
                        line = " ".join(line)
                        lines.append(line.strip())
        
        lines += ["", "ENDDRAW", "ENDDEF"]
    elif len(newlibl) == 0:
        printerr("No new symbols created - check that there's not already these parts in this directory")
        exit()
    else:
        newlib = newlibl[0] # not dealing with subparts
        with open(newlib) as f:
            lines = f.readlines()[2:-3] # skip intro and outro
            if "DEF" in line:
                partname = line.split()[1]
            lines = [line if "F2 " not in line else insert_footprint(newfoot) for line in lines]
            lines = [line if "F3 " not in line else insert_datasheet(lcsc_pn) for line in lines]

    # check if part already exists
    already_in_lib = True
    try:
        _ = next(line for line in currentlines if partname in line)
    except StopIteration:
        already_in_lib = False
    if not already_in_lib:
        with open("LCSC.lib", 'w') as libf:
            lines = [line.strip() + "\n" for line in lines]
            libf.writelines(currentlines[:-3] + ["\n"] + lines + ["\n", "#\n", "#End Library\n"]) # skip endlib then add new library
    
    else:
        printerr("The part is already in the library")

    for newlib in newlibl:
        os.system(f"rm {newlib}")