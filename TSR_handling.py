#!/usr/bin/env python

##1, how to use
  ###copy TSR  logs to node_review folder
	python node_review.py -n archive_01_24_2022_02_20_53.zip/TSR20220610102211_<SN>.zip
	python node_review.py -n TSR20220610102211_<SN>.zip  -f 7.0.200
	python node_review.py -n TSR20220610102211_<SN>.zip  -f 4.7.100 -t 4.5.536
	python node_review.py -n TSR20220610102211_<SN>.zip -e archive_01_24_2022_02_20_53.zip -f 4.7.100 -t 4.5.536

 Assumed zip structure is:
    archive_xx_xx.zip    |
    |- TSRxx_xx.zip
        |- TSRxx_xx_pl.zip
           |- tsr/hardware...
    ....
    |- TSRxx_xx.zip
        |- TSRxx_xx_pl.zip
           |- tsr/hardware...
  or 
    |- TSRxx_xx.zip
        |- TSRxx_xx_pl.zip
           |- tsr/hardware...
        
##2, how to add more value to parse     
	###add a xpath and add to node_dict,here is an example.
	BIOSVersionStringXpath=".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_SystemView']/PROPERTY[@NAME='BIOSVersionString']/VALUE" 
    node_dict=parseXML(node_dict,myroot,BIOSVersionStringXpath,"bios")
	
##3, how to add node review rule.
    ### add a class ,implement BaseCheck, rewrite  do_check function .
	### add the check to perfomNodeCheck function, the following is an example.
	class NodeCompatibility(BaseCheck):
		def do_check(self):
			if (self.new_code_version.startswith('4.7') and self.exist_code_version.startswith('4.5')):
				print("\tNo allow downgrade from 4.7.x to 4.5.x")
				return False
			return True			
	def perfomNodeCheck(options,new_node_dict,exist_node_dict):
		NodeCompatibility(new_node_code_version,exist_node_code_version,new_node_dict,exist_node_dict)        
"""

import os
import sys
import zipfile
import traceback
import shutil
import re
import json
import glob
import xml.etree.ElementTree as ET
import logging
import logging.handlers
from optparse import OptionParser

LOG_PATH = os.getcwd()
LOG_FILE = os.path.join(LOG_PATH, 'vxrail-node-review.log')

CODE_VERSION = '20250307'

def create_data_model(model, versions):
    return {version_id: {"Tag": "SimNode", "Model": model, **attributes} for version_id, attributes in versions.items()}

data_model_versions_14G = {
    "14G70131": {"BIOS": "2.9.4", "HBA": "16.17.01.00", "iDrac": "4.40.00.201"},
    "14G70241": {"BIOS": "2.11.2", "HBA": "16.17.01.00", "iDrac": "4.40.40.00"},
    "14G70300": {"BIOS": "2.11.2", "HBA": "16.17.01.00", "iDrac": "5.00.10.20"},
    "14G70320": {"BIOS": "2.12.2", "HBA": "16.17.01.00", "iDrac": "5.00.10.20"},
    "14G70350": {"BIOS": "2.12.2", "HBA": "16.17.01.00", "iDrac": "5.00.10.20"},
    "14G70370": {"BIOS": "2.13.3", "HBA": "16.17.01.00", "iDrac": "5.10.10.00"},
    "14G70371": {"BIOS": "2.13.3", "HBA": "16.17.01.00", "iDrac": "5.10.10.00"},
    "14G70372": {"BIOS": "2.13.3", "HBA": "16.17.01.00", "iDrac": "5.10.30.201"},
    "14G70400": {"BIOS": "2.14.2", "HBA": "16.17.01.00", "iDrac": "5.10.30.201"},
    "14G70401": {"BIOS": "2.14.2", "HBA": "16.17.01.00", "iDrac": "5.10.30.201"},
    "14G70405": {"BIOS": "2.16.1", "HBA": "16.17.01.00", "iDrac": "6.00.30.00"},
    "14G70410": {"BIOS": "2.16.1", "HBA": "16.17.01.00", "iDrac": "6.00.30.00"},
    "14G70411": {"BIOS": "2.16.1", "HBA": "16.17.01.00", "iDrac": "6.00.30.00"},
    "14G70450": {"BIOS": "2.17.1", "HBA": "16.17.01.00", "iDrac": "6.10.30.20"},
    "14G70451": {"BIOS": "2.17.1", "HBA": "16.17.01.00", "iDrac": "6.10.30.20"},
    "14G70452": {"BIOS": "2.17.1", "HBA": "16.17.01.00", "iDrac": "6.10.80.00"},
    "14G70480": {"BIOS": "2.19.1", "HBA": "16.17.01.00", "iDrac": "7.00.00.00"},
    "14G70481": {"BIOS": "2.19.1", "HBA": "16.17.01.00", "iDrac": "7.00.00.00"},
    "14G70482": {"BIOS": "2.19.1", "HBA": "16.17.01.00", "iDrac": "7.00.00.00"},
    "14G70483": {"BIOS": "2.20.1", "HBA": "", "iDrac": "7.00.00.00"},
    "14G70484": {"BIOS": "", "HBA": "", "iDrac": "7.00.00.171"},
    "14G70520": {"BIOS": "", "HBA": "", "iDrac": "7.00.00.171"},
    "14G70521": {"BIOS": "", "HBA": "", "iDrac": "7.00.00.171"},
    "14G70531": {"BIOS": "", "HBA": "", "iDrac": "7.00.00.173"},
    "14G70532": {"BIOS": "", "HBA": "", "iDrac": "7.00.00.173"},
    "14G70533": {"BIOS": "", "HBA": "", "iDrac": "7.00.00.173"},
    "14G70540": {"BIOS": "", "HBA": "", "iDrac": "7.00.00.174"},
    "14G80000": {"BIOS": "2.16.1", "HBA": "16.17.01.00", "iDrac": "6.00.30.00"},
    "14G80020": {"BIOS": "2.17.1", "HBA": "16.17.01.00", "iDrac": "6.10.30.00"},
    "14G80100": {"BIOS": "2.18.1", "HBA": "16.17.01.00", "iDrac": "6.10.80.00"},
    "14G80110": {"BIOS": "2.18.1", "HBA": "16.17.01.00", "iDrac": "6.10.80.00"},
    "14G80101": {"BIOS": "2.18.1", "HBA": "16.17.01.00", "iDrac": "6.10.80.00"},
    "14G80111": {"BIOS": "2.19.1", "HBA": "16.17.01.00", "iDrac": "6.10.80.00"},
    "14G80200": {"BIOS": "2.19.1", "HBA": "16.17.01.00", "iDrac": "7.00.00.00"},
    "14G80201": {"BIOS": "2.19.1", "HBA": "16.17.01.00", "iDrac": "7.00.00.00"},
    "14G80210": {"BIOS": "2.20.1", "HBA": "", "iDrac": "7.00.00.00"},
    "14G80211": {"BIOS": "", "HBA": "", "iDrac": "7.00.00.00"},
    "14G80212": {"BIOS": "", "HBA": "", "iDrac": "7.00.00.171"},
    "14G80213": {"BIOS": "", "HBA": "", "iDrac": "7.00.00.171"},
    "14G80300": {"BIOS": "", "HBA": "", "iDrac": "7.00.00.172"},
    "14G80310": {"BIOS": "", "HBA": "", "iDrac": "7.00.00.173"},
    "14G80311": {"BIOS": "", "HBA": "", "iDrac": "7.00.00.173"},
    "14G80320": {"BIOS": "", "HBA": "", "iDrac": "7.00.00.173"},
    "14G80321": {"BIOS": "", "HBA": "", "iDrac": "7.00.00.173"},

}

data_model_versions_15G = {
    "15G70241": {"BIOS": "1.2.4", "HBA": "15.15.15.00", "iDrac": "4.40.29.00"},
    "15G70300": {"BIOS": "1.3.8", "HBA": "15.15.15.00", "iDrac": "5.00.10.20"},
    "15G70320": {"BIOS": "1.3.8", "HBA": "17.15.08.00", "iDrac": "5.00.10.20"},
    "15G70350": {"BIOS": "1.3.8", "HBA": "17.15.08.00", "iDrac": "5.00.10.20"},
    "15G70370": {"BIOS": "1.5.4", "HBA": "17.15.08.00", "iDrac": "5.10.10.00"},
    "15G70371": {"BIOS": "1.5.4", "HBA": "17.15.08.00", "iDrac": "5.10.10.00"},
    "15G70372": {"BIOS": "1.5.4", "HBA": "17.15.08.00", "iDrac": "5.10.30.201"},
    "15G70400": {"BIOS": "1.6.5", "HBA": "17.15.08.00","iDrac": "5.10.30.201"},
    "15G70401": {"BIOS": "1.6.5", "HBA": "17.15.08.00","iDrac": "5.10.30.201"},
    "15G70405": {"BIOS": "1.8.2", "HBA": "17.15.08.00", "iDrac": "6.00.30.00"},
    "15G70410": {"BIOS": "1.8.2", "HBA": "17.15.08.00", "iDrac": "6.00.30.00"},
    "15G70411": {"BIOS": "1.8.2", "HBA": "17.15.08.00", "iDrac": "6.00.30.00"},
    "15G70450": {"BIOS": "1.9.2", "HBA": "22.15.05.00", "iDrac": "6.10.30.20"},
    "15G70451": {"BIOS": "1.9.2", "HBA": "22.15.05.00", "iDrac": "6.10.30.20"},
    "15G70452": {"BIOS": "1.9.2", "HBA": "22.15.05.00", "iDrac": "6.10.80.00"},
    "15G70480": {"BIOS": "1.11.2", "HBA": "24.15.10.00", "iDrac": "7.00.30.00"},
    "15G70481": {"BIOS": "1.11.2", "HBA": "24.15.10.00", "iDrac": "7.00.30.00"},
    "15G70482": {"BIOS": "1.12.1", "HBA": "24.15.10.00", "iDrac": "7.00.30.00"},
    "15G70483": {"BIOS": "1.12.1", "HBA": "", "iDrac": "7.00.30.00"},
    "15G70484": {"BIOS": "1.13.2", "HBA": "", "iDrac": "7.10.30.00"},
    "15G70520": {"BIOS": "1.13.2", "HBA": "", "iDrac": "7.10.30.00"},
    "15G70521": {"BIOS": "1.13.2", "HBA": "", "iDrac": "7.10.30.00"},
    "15G70530": {"BIOS": "1.14.1", "HBA": "", "iDrac": "7.10.50.00"},
    "15G70531": {"BIOS": "1.15.1", "HBA": "24.15.14.00", "iDrac": "7.10.50.10"},
    "15G70532": {"BIOS": "1.15.1", "HBA": "24.15.14.00", "iDrac": "7.10.50.10"},
    "15G70533": {"BIOS": "1.15.1", "HBA": "", "iDrac": "7.10.50.10"},
    "15G70540": {"BIOS": "1.15.2", "HBA": "", "iDrac": "7.10.90.00"},
    "15G80000": {"BIOS": "1.8.2", "HBA": "52.21.0-4606", "iDrac": "6.00.30.00"},
    "15G80010": {"BIOS": "1.8.2", "HBA": "", "iDrac": "6.00.30.00"},
    "15G80020": {"BIOS": "1.9.2", "HBA": "52.21.0-4606", "iDrac": "6.10.30.00"},
    "15G80100": {"BIOS": "1.10.2", "HBA": "", "iDrac": "6.10.80.00"},
    "15G80110": {"BIOS": "1.10.2", "HBA": "52.21.0-4606", "iDrac": "6.10.80.00"},
    "15G80101": {"BIOS": "1.10.2", "HBA": "52.21.0-4606", "iDrac": "6.10.80.00"},
    "15G80111": {"BIOS": "1.11.2", "HBA": "52.21.0-4606", "iDrac": "6.10.80.00"},
    "15G80200": {"BIOS": "1.11.2", "HBA": "52.21.0-4606", "iDrac": "7.00.30.00"},
    "15G80201": {"BIOS": "1.11.2", "HBA": "52.21.0-4606", "iDrac": "7.00.30.00"},
    "15G80210": {"BIOS": "1.12.1", "HBA": "52.26.0-5179", "iDrac": "7.00.60.201"},
    "15G80211": {"BIOS": "1.13.2", "HBA": "52.26.0-5179", "iDrac": "7.00.60.201"},
    "15G80212": {"BIOS": "1.13.2", "HBA": "52.26.0-5179", "iDrac": "7.00.60.201"},
    "15G80213": {"BIOS": "1.13.2", "HBA": "", "iDrac": "7.10.30.00"},
    "15G80300": {"BIOS": "1.14.1", "HBA": "", "iDrac": "7.00.00.172"},
    "15G80310": {"BIOS": "1.15.1", "HBA": "", "iDrac": "7.10.50.10"},
    "15G80311": {"BIOS": "1.15.1", "HBA": "", "iDrac": "7.10.50.10"},
    "15G80320": {"BIOS": "1.15.2", "HBA": "", "iDrac": "7.10.70.00"},
    "15G80321": {"BIOS": "1.15.2", "HBA": "", "iDrac": "7.10.70.00"},
}

data_model_versions_15GAMD = {
    "15GAMD70241": {"BIOS": "2.2.4", "HBA": "16.17.01.00", "iDrac": "4.40.40.00"},
    "15GAMD70300": {"BIOS": "2.3.6", "HBA": "16.17.01.00", "iDrac": "5.00.10.20"},
    "15GAMD70320": {"BIOS": "2.3.6", "HBA": "16.17.01.00", "iDrac": "5.00.10.20"},
    "15GAMD70350": {"BIOS": "2.5.5", "HBA": "16.17.01.00", "iDrac": "5.00.10.20"},
    "15GAMD70370": {"BIOS": "2.6.6", "HBA": "16.17.01.00", "iDrac": "5.10.10.00"},
    "15GAMD70371": {"BIOS": "2.6.6", "HBA": "16.17.01.00", "iDrac": "5.10.10.00"},
    "15GAMD70372": {"BIOS": "2.6.6", "HBA": "16.17.01.00", "iDrac": "5.10.30.201"},
    "15GAMD70400": {"BIOS": "2.7.3", "HBA": "16.17.01.00", "iDrac": "5.10.30.201"},
    "15GAMD70401": {"BIOS": "2.7.3", "HBA": "16.17.01.00", "iDrac": "5.10.30.201"},
    "15GAMD70405": {"BIOS": "2.9.3", "HBA": "16.17.01.00", "iDrac": "6.00.30.00"},
    "15GAMD70410": {"BIOS": "2.9.3", "HBA": "16.17.01.00", "iDrac": "6.00.30.00"},
    "15GAMD70411": {"BIOS": "2.9.3", "HBA": "16.17.01.00", "iDrac": "6.00.30.00"},
    "15GAMD70450": {"BIOS": "2.10.2", "HBA": "16.17.01.00", "iDrac": "6.10.30.20"},
    "15GAMD70451": {"BIOS": "2.10.2", "HBA": "16.17.01.00", "iDrac": "6.10.30.20"},
    "15GAMD70452": {"BIOS": "2.10.2", "HBA": "16.17.01.00", "iDrac": "6.10.80.00"},
    "15GAMD70480": {"BIOS": "2.12.4", "HBA": "24.15.10.00", "iDrac": "7.00.30.00"},
    "15GAMD70481": {"BIOS": "2.12.4", "HBA": "24.15.10.00", "iDrac": "7.00.30.00"},
    "15GAMD70482": {"BIOS": "2.12.4", "HBA": "24.15.10.00", "iDrac": "7.00.30.00"},
    "15GAMD70483": {"BIOS": "2.13.3", "HBA": "24.15.10.00", "iDrac": "7.00.30.00"},
    "15GAMD70484": {"BIOS": "2.14.1", "HBA": "", "iDrac": "7.10.30.00"},
    "15GAMD70520": {"BIOS": "2.14.1", "HBA": "", "iDrac": "7.10.30.00"},
    "15GAMD70521": {"BIOS": "2.14.1", "HBA": "", "iDrac": "7.10.30.00"},
    "15GAMD70531": {"BIOS": "2.16.0", "HBA": "", "iDrac": "7.10.50.10"},
    "15GAMD70532": {"BIOS": "2.16.0", "HBA": "", "iDrac": "7.10.50.10"},
    "15GAMD70533": {"BIOS": "2.16.0", "HBA": "", "iDrac": "7.10.50.10"},
    "15GAMD70540": {"BIOS": "2.16.0", "HBA": "", "iDrac": "7.10.90.00"},
    "15GAMD80000": {"BIOS": "2.9.3", "HBA": "16.17.01.00", "iDrac": "6.00.30.00"},
    "15GAMD80020": {"BIOS": "2.10.2", "HBA": "16.17.01.00", "iDrac": "6.10.30.00"},
    "15GAMD80100": {"BIOS": "2.11.4", "HBA": "16.17.01.00", "iDrac": "6.10.80.00"},
    "15GAMD80101": {"BIOS": "2.11.4", "HBA": "16.17.01.00", "iDrac": "6.10.80.00"},
    "15GAMD80110": {"BIOS": "2.11.4", "HBA": "16.17.01.00", "iDrac": "6.10.80.00"},
    "15GAMD80111": {"BIOS": "2.11.4", "HBA": "16.17.01.00", "iDrac": "6.10.80.00"},
    "15GAMD80200": {"BIOS": "2.12.4", "HBA": "24.15.10.00", "iDrac": "7.00.30.00"},
    "15GAMD80201": {"BIOS": "2.12.4", "HBA": "24.15.10.00", "iDrac": "7.00.30.00"},
    "15GAMD80210": {"BIOS": "2.13.3", "HBA": "24.15.14.00", "iDrac": "7.00.60.201"},
    "15GAMD80211": {"BIOS": "2.14.1", "HBA": "", "iDrac": "7.00.60.201"},
    "15GAMD80212": {"BIOS": "2.14.1", "HBA": "", "iDrac": "7.10.30.00"},
    "15GAMD80213": {"BIOS": "2.14.1", "HBA": "", "iDrac": "7.10.30.00"},
    "15GAMD80300": {"BIOS": "2.15.1", "HBA": "", "iDrac": "7.00.00.172"},
    "15GAMD80310": {"BIOS": "2.16.1", "HBA": "", "iDrac": "7.10.50.10"},
    "15GAMD80311": {"BIOS": "2.16.1", "HBA": "", "iDrac": "7.10.50.10"},
    "15GAMD80320": {"BIOS": "2.16.0", "HBA": "", "iDrac": "7.10.70.00"},
    "15GAMD80321": {"BIOS": "2.16.0", "HBA": "", "iDrac": "7.10.70.00"},
}

data_model_versions_15GVD = {
    "15GVD70420": {"BIOS": "1.0.2", "HBA": "", "iDrac": "6.00.19.00"},
    "15GVD70450": {"BIOS": "1.1.4", "HBA": "", "iDrac": "6.00.49.00"},
    "15GVD70451": {"BIOS": "1.1.4", "HBA": "", "iDrac": "6.00.49.00"},
    "15GVD70452": {"BIOS": "1.1.4", "HBA": "", "iDrac": "6.00.49.00"},
    "15GVD70453": {"BIOS": "1.1.4", "HBA": "", "iDrac": "6.00.49.00"},
    "15GVD70481": {"BIOS": "1.12.1", "HBA": "", "iDrac": "7.00.30.00"},
    "15GVD70482": {"BIOS": "1.12.1", "HBA": "", "iDrac": "7.00.30.00"},
    "15GVD70483": {"BIOS": "1.12.1", "HBA": "", "iDrac": "7.00.30.00"},
    "15GVD70484": {"BIOS": "1.14.1", "HBA": "", "iDrac": "7.10.30.00"},
    "15GVD70520": {"BIOS": "1.14.1", "HBA": "", "iDrac": "7.10.30.00"},
    "15GVD70521": {"BIOS": "1.14.1", "HBA": "", "iDrac": "7.10.30.00"},
    "15GVD70530": {"BIOS": "1.15.2", "HBA": "", "iDrac": "7.10.50.00"},
    "15GVD70531": {"BIOS": "1.16.1", "HBA": "", "iDrac": "7.10.50.10"},
    "15GVD70532": {"BIOS": "1.16.1", "HBA": "", "iDrac": "7.10.50.10"},
    "15GVD70533": {"BIOS": "1.16.1", "HBA": "", "iDrac": "7.10.50.10"},
    "15GVD70540": {"BIOS": "1.16.2", "HBA": "", "iDrac": "7.10.90.00"},
    "15GVD80210": {"BIOS": "1.13.3", "HBA": "", "iDrac": "7.00.60.201"},
    "15GVD80211": {"BIOS": "1.14.1", "HBA": "", "iDrac": "7.00.60.201"},
    "15GVD80212": {"BIOS": "1.14.1", "HBA": "", "iDrac": "7.10.30.00"},
    "15GVD80213": {"BIOS": "1.14.1", "HBA": "", "iDrac": "7.10.30.00"},
    "15GVD80300": {"BIOS": "1.15.2", "HBA": "", "iDrac": "7.00.00.172"},
    "15GVD80310": {"BIOS": "1.16.1", "HBA": "", "iDrac": "7.10.50.10"},
    "15GVD80311": {"BIOS": "1.16.1", "HBA": "", "iDrac": "7.10.50.10"},
    "15GVD80320": {"BIOS": "1.16.2", "HBA": "", "iDrac": "7.10.70.00"},
    "15GVD80321": {"BIOS": "1.16.2", "HBA": "", "iDrac": "7.10.70.00"},
}

data_model_versions_16G = {
    "16G70460": {"BIOS": "1.2.1", "HBA": "22.15.05.00", "iDrac": "6.10.39.00"},
    "16G70481": {"BIOS": "1.5.6", "HBA": "24.15.10.00", "iDrac": "7.00.30.00"},
    "16G70482": {"BIOS": "1.5.6", "HBA": "24.15.10.00", "iDrac": "7.00.30.00"},
    "16G70483": {"BIOS": "1.6.6", "HBA": "24.15.10.00", "iDrac": "7.00.30.00"},
    "16G70484": {"BIOS": "2.1.5", "HBA": "24.15.14.00", "iDrac": "7.10.30.05"},
    "16G70510": {"BIOS": "1.6.6", "HBA": "", "iDrac": "7.00.60.00"},
    "16G70520": {"BIOS": "2.1.5", "HBA": "", "iDrac": "7.10.30.05"},
    "16G70521": {"BIOS": "2.1.5", "HBA": "", "iDrac": "7.10.30.05"},
    "16G70531": {"BIOS": "2.2.7", "HBA": "24.15.14.00", "iDrac": "7.10.50.10"},
    "16G70532": {"BIOS": "2.2.7", "HBA": "24.15.14.00", "iDrac": "7.10.50.10"},
    "16G70533": {"BIOS": "2.2.7", "HBA": "24.15.14.00", "iDrac": "7.10.50.10"},
    "16G70540": {"BIOS": "2.4.4", "HBA": "24.15.14.00", "iDrac": "7.10.90.00"},
    "16G80120": {"BIOS": "1.5.6", "HBA": "", "iDrac": "7.00.30.00"},
    "16G80210": {"BIOS": "1.6.6", "HBA": "", "iDrac": "7.00.60.201"},
    "16G80211": {"BIOS": "2.1.5", "HBA": "", "iDrac": "7.00.60.201"},
    "16G80212": {"BIOS": "2.1.5", "HBA": "", "iDrac": "7.10.30.05"},
    "16G80213": {"BIOS": "2.1.5", "HBA": "", "iDrac": "7.10.30.05"},
    "16G80240": {"BIOS": "2.1.5", "HBA": "", "iDrac": "7.10.30.05"},
    "16G80300": {"BIOS": "2.2.7", "HBA": "", "iDrac": "7.00.00.172"},
    "16G80310": {"BIOS": "2.2.7", "HBA": "", "iDrac": "7.10.50.10"},
    "16G80311": {"BIOS": "2.2.7", "HBA": "", "iDrac": "7.10.50.10"},
    "16G80320": {"BIOS": "2.3.5", "HBA": "", "iDrac": "7.10.70.00"},
    "16G80321": {"BIOS": "2.3.5", "HBA": "", "iDrac": "7.10.70.00"},
}

data_model_versions_16GAMD = {
    "16GAMD70510": {"BIOS": "1.6.10", "HBA": "24.15.14.00", "iDrac": "7.00.60.00"},
    "16GAMD70520": {"BIOS": "1.7.2", "HBA": "", "iDrac": "7.10.30.00"},
    "16GAMD70521": {"BIOS": "1.8.3", "HBA": "", "iDrac": "7.10.30.00"},
    "16GAMD70530": {"BIOS": "1.8.3", "HBA": "", "iDrac": "7.10.50.00"},
    "16GAMD70531": {"BIOS": "1.8.3", "HBA": "24.15.14.00", "iDrac": "7.10.50.10"},
    "16GAMD70532": {"BIOS": "1.8.3", "HBA": "24.15.14.00", "iDrac": "7.10.50.10"},
    "16GAMD70533": {"BIOS": "1.8.3", "HBA": "24.15.14.00", "iDrac": "7.10.50.10"},
    "16GAMD70540": {"BIOS": "1.10.6", "HBA": "24.15.14.00", "iDrac": "7.10.90.00"},
    "16GAMD80300": {"BIOS": "1.8.3", "HBA": "24.15.14.00", "iDrac": "7.00.00.172"},
    "16GAMD80310": {"BIOS": "1.8.3", "HBA": "", "iDrac": "7.10.50.10"},
    "16GAMD80311": {"BIOS": "1.8.3", "HBA": "", "iDrac": "7.10.50.10"},
    "16GAMD80320": {"BIOS": "1.9.4", "HBA": "24.15.14.00", "iDrac": "7.10.70.00"},
    "16GAMD80321": {"BIOS": "1.9.4", "HBA": "24.15.14.00", "iDrac": "7.10.70.00"},
}

data_model_14G = create_data_model("VxRail 14G", data_model_versions_14G)
data_model_15G = create_data_model("VxRail 15G", data_model_versions_15G)
data_model_15GAMD = create_data_model("VxRail 15G", data_model_versions_15GAMD)
data_model_15GVD = create_data_model("VxRail 15G", data_model_versions_15GVD)
data_model_16G = create_data_model("VxRail 16G", data_model_versions_16G)
data_model_16GAMD = create_data_model("VxRail 16G", data_model_versions_16GAMD)

data_model = {}

def setup_logger():
    global log_n
    log_n = logging.getLogger(__name__)
    logging.basicConfig(level=logging.DEBUG,format='%(asctime)s - %(levelname)s - %(message)s',
                        datefmt='%y-%m-%d %H:%M',filename=LOG_FILE,filemode='w')
    # define a Handler which writes INFO messages or higher to the sys.stderr
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)
    # set a format which is simpler for console use
    console.setFormatter(logging.Formatter('%(message)s'))
    log_n.addHandler(console)

def in_red(s):
    """ red font in linux console"""
    return "%s[31;2m%s%s[0m" % (chr(27), s, chr(27))


def in_yellow(s):
    """ yellow font in linux console"""
    return "%s[33;2m%s%s[0m" % (chr(27), s, chr(27))


def in_green(s):
    """ green font in linux console"""
    return "%s[32;2m%s%s[0m" % (chr(27), s, chr(27))
    
def create_option_parser():
    '''Parse CLI arguments'''
    parser = OptionParser()
    parser.add_option('-n', '--new_node', dest="new_node", action='store',help='The new nodes TSR logs')
    parser.add_option('-e', '--exist_node', dest="exist_node", action='store',help='The exist nodes TSR logs')
    parser.add_option('-f', '--from_new_node_version', dest="from_new_node_version", action='store',help='The new   nodes code version')
    parser.add_option('-t', '--to_exist_node_version', dest="to_exist_node_version", action='store',help='The exist nodes code version')
    #parser.add_option('-m', '--model_of_vxrail', dest="model_of_vxrail", action='store', help='model of vxrail,support 14g/14G,15g/15G')
    #parser.add_option('-c', '--confirm_of_missing_new_tsr_logs', dest="confirm_of_missing_new_tsr_logs", action='store', help='confirm of missing new tsr logs')
    #parser.add_option('-o', '--object_of_from_to', dest="object_of_from_to", action='store', help='object_of_from_to')
    return parser

#def getSupportVersion():    
#    values = list(data_model.values())

def getSupportVDVersion():
    result = [key for key in data_model.keys() if "VD" in key] 
    result = [key.replace("15GVD", "") for key in result]
    return result   

def clean(targets):
    file_target = os.walk(targets)
    for path,dir_list,file_list in file_target:
        log_n.info(dir_list)

def parseXML(node_dict,xml_root,xpath_key,xpath_name):
    value= xml_root.findall(xpath_key)
    if not value: return node_dict

    node_dict[xpath_name]=value[0].text
    if value[0].text is not None:
         node_dict[xpath_name]=value[0].text.rstrip()
    return node_dict

def parseNicXML(node_dict,xml_root,xpath_key,xpath_name):
    value = xml_root.findall(xpath_key)
    nic_arr = list()
    for nic_value in value:
        nic_value_name= nic_value.text.split("-")[0].rstrip()
        if not(nic_value_name in nic_arr):
            nic_arr.append(nic_value_name)        
    node_dict[xpath_name]=nic_arr
    return node_dict
    
def parseNicNameAndVersionXML(node_dict,xml_root,xpath_key,xpath_name):
    value= xml_root.findall(xpath_key)
    nic_dict = {}
    for c in value:
        nic_name = c.find("PROPERTY[@NAME='ProductName']/VALUE").text.split("-")[0].rstrip()
        nic_version = c.find("PROPERTY[@NAME='FamilyVersion']/VALUE").text
        nic_dict[nic_name]=nic_version
    node_dict[xpath_name]=nic_dict
    return node_dict
    
def parseXMLWithReplace(node_dict,xml_root,xpath_key,xpath_name,replace_str,replace_str2):
    value = xml_root.findall(xpath_key)
    try:
        node_dict[xpath_name]=value[0].text.replace(replace_str,"").replace(replace_str2,"")
    except Exception as e:
        log_n.error(value) 
        raise Exception(e)
    return node_dict

def parseDiskModelXML(node_dict,xml_root,xpath_key,xpath_name):
    value= xml_root.findall(xpath_key)
    disk_model_arr = list()
    for c in value:
        disk_model_name = c.text.rstrip()
        if (not disk_model_name.startswith("MTFDDA") and not disk_model_name in["HFS1T9G3H2X069N", "HFS3T8G3H2X069N"] ): 
            continue
        if disk_model_name not in disk_model_arr:
            disk_model_arr.append(disk_model_name)
    node_dict[xpath_name]=disk_model_arr
    return node_dict

def parseCapableSpeedXML(node_dict,xml_root,xpath_key,xpath_name):
    value= xml_root.findall(xpath_key)
    disk_model_arr = list()
    for c in value:
        disk_capable_speed = c.text.rstrip()
        if (disk_capable_speed == 'Unknown' ): continue
        if "Gbps" in disk_capable_speed:
            disk_capable_speed = disk_capable_speed.replace(" Gbps","")
        elif "GT/s" in disk_capable_speed:
            disk_capable_speed = disk_capable_speed.replace(" GT/s","")        
        node_capable_speed_value_int = int(disk_capable_speed)
        
        if(node_capable_speed_value_int < 24): continue
        disk_model_arr.append(disk_capable_speed)
    node_dict[xpath_name]=disk_model_arr
    return node_dict

def parseDiskPartNumberXML(node_dict,xml_root,xpath_key,xpath_name):
    value= xml_root.findall(xpath_key)
    disk_dict = list()
    for c in value:
        ppid = c.find("PROPERTY[@NAME='PPID']/VALUE").text
        if not ppid: #missing sn of the disk.
           continue
        #if (ppid.find("-")):
        ppid = ppid.replace("-","")            
        disk_PN = ppid.rstrip()[3:8]
        media_type = c.find("PROPERTY[@NAME='MediaType']/VALUE").text
        if (not disk_PN in disk_dict and media_type == "1"): # 0,Hard Disk Drive  1,Solid State Drive
            disk_dict.append(disk_PN)
    node_dict[xpath_name] = disk_dict
    return node_dict

def parsePsuPartNumberXML(node_dict,xml_root,xpath_key,xpath_name):
    value= xml_root.findall(xpath_key)
    psu_dict = list()
    for c in value:
        ppid = c.find("PROPERTY[@NAME='PartNumber']/VALUE").text
        #if (ppid.find("-")):
        #    ppid = ppid.replace("-","")            
        psu_PN = ppid.rstrip()[1:6]
        #media_type = c.find("PROPERTY[@NAME='MediaType']/VALUE").text
        if (not psu_PN in psu_dict):
            psu_dict.append(psu_PN)
    node_dict[xpath_name] = psu_dict
    return node_dict
 
def parsePCISubDeviceIDXML(node_dict,xml_root,xpath_key,xpath_name):
    value= xml_root.findall(xpath_key)
    picSubDeviceID = 0
    for c in value:
        instanceIDDescription = c.find("PROPERTY[@NAME='InstanceID']/VALUE").text
        #print(pciSubDeviceDescription)
        if 'AHCI.SL.6-1' not in instanceIDDescription:
           continue
        picSubDeviceID = c.find("PROPERTY[@NAME='PCISubDeviceID']/VALUE").text
        #print(picSubDeviceID)
    node_dict[xpath_name] = picSubDeviceID
    return node_dict
    
def parseTSRToModel(node_dict,myroot):
    
    modelXpath = ".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_SystemView']/PROPERTY[@NAME='Model']/VALUE"     
    node_dict = parseXMLWithReplace(node_dict,myroot,modelXpath,"Model","VxRail ","")
    
    xpath_mapping = {
        "Hostname": ".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_SystemView']/PROPERTY[@NAME='HostName']/VALUE",
        "Tag": ".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_SystemView']/PROPERTY[@NAME='ServiceTag']/VALUE",
        "CPU": ".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_CPUView']/PROPERTY[@NAME='Model']/VALUE",
        "BIOS": ".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_SystemView']/PROPERTY[@NAME='BIOSVersionString']/VALUE",
        "CPLD": ".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_SystemView']/PROPERTY[@NAME='CPLDVersion']/VALUE",
        "iDrac": ".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_iDRACCardView']/PROPERTY[@NAME='FirmwareVersion']/VALUE",
        "PSU": ".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_PowerSupplyView']/PROPERTY[@NAME='FirmwareVersion']/VALUE",
        "HBA": ".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_ControllerView']/PROPERTY[@NAME='ControllerFirmwareVersion']/VALUE",
        "WitnessSledServiceTag": ".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_WitnessSledView']/PROPERTY[@NAME='ServiceTag']/VALUE",
        "WitnessSledIPv4Address": ".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_WitnessSledView']/PROPERTY[@NAME='IPv4Address1']/VALUE",
        "WitnessSensorReading": ".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_WitnessSledView']/PROPERTY[@NAME='WitnessSensorReading']/VALUE",
        "WitnessSledPowerState": ".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_WitnessSledView']/PROPERTY[@NAME='PowerState']/VALUE",
    }
    
    for key, xpath in xpath_mapping.items():
        node_dict = parseXML(node_dict, myroot, xpath, key)
    
    nicNameStringXpath=".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_NICView']" 
    node_dict = parseNicNameAndVersionXML(node_dict,myroot,nicNameStringXpath,"Nic")
    
    DiskModelXpath=".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_PhysicalDiskView']/PROPERTY[@NAME='Model']/VALUE"     
    node_dict = parseDiskModelXML(node_dict,myroot,DiskModelXpath,"DiskModel")
    
    DiskCapableSpeedXpath=".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_PhysicalDiskView']/PROPERTY[@NAME='MaxCapableSpeed']/DisplayValue"     
    node_dict = parseCapableSpeedXML(node_dict,myroot,DiskCapableSpeedXpath,"DiskCapableSpeed")
    
    DiskPPIdXpath=".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_PhysicalDiskView']"     
    node_dict = parseDiskPartNumberXML(node_dict,myroot,DiskPPIdXpath,"DiskPN")
    
    PsuPPIdXpath=".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_PowerSupplyView']"     
    node_dict = parsePsuPartNumberXML(node_dict,myroot,PsuPPIdXpath,"PsuPN")

    pciSubDeviceIDXpath=".//MESSAGE/SIMPLEREQ/VALUE.NAMEDINSTANCE/INSTANCE[@CLASSNAME='DCIM_PCIDeviceView']"     
    node_dict = parsePCISubDeviceIDXML(node_dict,myroot,pciSubDeviceIDXpath,"pciSubDeviceID")
    return node_dict

def unzip_to_folder(zip_file, dest_dir, ext_filter=''):
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    try:
        zfile = zipfile.ZipFile(zip_file)
        for filename in zfile.namelist():
            ext = os.path.splitext(os.path.basename(filename))[1]
            if (ext_filter and ext == ext_filter) or (ext_filter == ''):
                zfile.extract(filename, dest_dir)
    except zipfile.BadZipfile:
        log_n.error('Cannot extract {f}: Not a valid zipfile (BadZipfile Exception)'.format(f=zip_file))

def unzip(zip_file):
    try:
        zfile = zipfile.ZipFile(zip_file)
        for filename in zfile.namelist():
            zfile.extract(filename)
    except zipfile.BadZipfile:
        log_n.error('Cannot extract {f}: Not a valid zipfile (BadZipfile Exception)'.format(f=zip_file))

##extract TSR...zip
def extractTSR(exist_node_foler):               
    for e_file in os.listdir(exist_node_foler):
        if(e_file.endswith(".pl.zip")): 
            continue
        if(os.path.isdir(os.path.join(exist_node_foler, e_file))): 
            continue
        if(e_file.endswith("signature")): 
            continue
        e_base = os.path.splitext(os.path.basename(e_file))[0]
        unzip_to_folder(zip_file=os.path.join(exist_node_foler, e_file), dest_dir=exist_node_foler)

def extractTSRofpl(new_node_folder):
    ##extract  TSR...pl.zip
    for file in os.listdir(new_node_folder):
        base = os.path.splitext(os.path.basename(file))[0]
        if(not file.endswith(".pl.zip")): 
            continue
        unzip_to_folder(zip_file=os.path.join(new_node_folder, file), dest_dir=os.path.join(new_node_folder, base))

def parseFile(new_node_folder,new_node_dict):

    sysinfo_DCIM_View = os.path.join("tsr",os.path.join("hardware",os.path.join("sysinfo",os.path.join("inventory","sysinfo_DCIM_View.xml"))))

    for file in os.listdir(new_node_folder):
        tmp_new_node_dict={}
        base = os.path.splitext(os.path.basename(file))[0]
        if(not file.startswith("TSR")): 
            continue
        if(not file.endswith(".pl")): 
            continue
        if(not os.path.isdir(os.path.join(new_node_folder, file))):
            continue
              
        try:
            myroot = ET.parse(os.path.join(os.path.join(new_node_folder, file), sysinfo_DCIM_View)).getroot()
            tmp_new_node_dict = parseTSRToModel(tmp_new_node_dict,myroot)
            new_node_dict[file.replace(".pl","")] = tmp_new_node_dict
        except Exception as e:
            log_n.error("Meet exception while parse file: "+file) 
            log_n.exception(e)
            pass

def clean_temp_zip_fils(node_path):

    signature_file = os.path.join(node_path, 'signature')
    if os.path.isfile(signature_file):
        os.remove(signature_file)
        log_n.debug("Deleted file named 'signature': {}".format(signature_file))

    zip_files = glob.glob(os.path.join(node_path, '*.zip'))

    # Loop through the list of .zip files and remove each one
    for zip_file in zip_files:
        try:
            os.remove(zip_file)
            log_n.debug("Deleted file: {}".format(zip_file))
        except OSError as e:
            log_n.debug("Error: {} - {}".format(e.strerror,zip_file))
            
def parseNewTSRNode(options,new_node_dict):
    return parseTSRNode(options.new_node.strip(), new_node_dict, "new_node")

def parseExistTSRNode(options,exist_node_dict):
    return parseTSRNode(options.exist_node.strip(), exist_node_dict, "cur_node")

def parseTSRNode(node_file, node_dict, node_foler):

    node_path = os.path.join(os.getcwd(), node_foler)
    if os.path.exists(node_path):
        shutil.rmtree(node_path) 

    if not os.path.exists(node_path):
        os.makedirs(node_path)

    #new_node_file = options.new_node.strip()
    log_n.debug("node_file: {}".format(node_file))
    if node_file.endswith("zip"):
        if "TSR" in node_file:
            shutil.copy(node_file, node_foler)
        else:
            unzip_to_folder(node_file, node_foler)

    extractTSR(node_foler)
    extractTSRofpl(node_foler)
    parseFile(node_foler,node_dict) 
    clean_temp_zip_fils(node_path)

    return node_dict

def changeVxrailCodeVersionToInt(node_code_version):
    int_node_code_version = 0
    node_code_version = node_code_version.strip()
    node_code_version = node_code_version.replace("'","")
    node_code_version = node_code_version.replace("\'","")
    node_code_version = node_code_version.replace("\"","")
    node_code_version = node_code_version.replace(".","")
    node_code_version = node_code_version.replace(" ","")
    node_code_version = node_code_version.strip() 
    node_code_version = re.sub(u"([^\u0030-\u0039])","",node_code_version)
    node_code_version = node_code_version[0:5]

    int_node_code_version = int(node_code_version)
    return int_node_code_version
    
def is14GModel(node_model):
    return node_model in ['E560', 'E560F', 'G560', 'G560F', 'P570', 'P570F', 'V570', 'V570F', 'S570', 'D560', 'D560F', 'E560N', 'P580N']
   
def is15GModel(node_model):  
    return node_model in ['E660', 'E660F', 'P670F', 'V670F', 'E660N', 'S670', 'P670N', 'E665', 'E665F', 'E665N', 'R7515', 'E675F']
    
def is15GVDModel(node_model):  
    return node_model in ['VD-4520c', 'VD-4510c', 'VD-4000r', 'VD-4000w' ,'VD4000z']

def is15GIntelModel(node_model):  
    return node_model in ['E660', 'E660F', 'P670F', 'V670F', 'E660N', 'S670', 'P670N']

def is15GAMDModel(node_model):  
    return node_model in ['E665', 'E665F', 'E665N', 'R7515', 'E675F', 'P675N']

def is16GModel(node_model):  
    return node_model in ['VE-660', 'VP-760', 'VS-760', 'MC-760', 'MC-660', 'R760', 'R660']

def is16GAMDModel(node_model):
    return node_model in ['VP-7625', 'VE-6615']

class NodeCheckProperties:

    def __init__(self, new_node_code_version,exist_node_code_version,new_node_dict,exist_node_dict,suggestion_message,model,skip_message):
        self.new_node_code_version = new_node_code_version
        self.exist_node_code_version = exist_node_code_version
        self.new_node_dict = new_node_dict
        self.exist_node_dict = exist_node_dict
        self.model = model
        self.suggestion_message = suggestion_message
        #self.confirm_of_missing_new_tsr_logs = confirm
        self.skip_message = skip_message

    def get_new_node_code_version(self):
        return self.new_node_code_version
    
    def get_exist_node_code_version(self):
        return self.exist_node_code_version
    
    def get_new_node_dict(self):
        return self.new_node_dict

    def get_exist_node_dict(self):
        return self.exist_node_dict

    def get_model(self):
        return self.model

    def get_suggestion_message(self):
        return self.suggestion_message      
    
    #def get_confirm(self):
    #    return self.confirm_of_missing_new_tsr_logs

    def get_skip_message(self):
        return self.skip_message

class BaseCheck(object):
    def __init__(self, nodeCheckProperties):
        self.new_code_version = nodeCheckProperties.get_new_node_code_version()
        self.exist_code_version = nodeCheckProperties.get_exist_node_code_version()
        self.new_node_dict = nodeCheckProperties.get_new_node_dict()
        self.exist_node_dict = nodeCheckProperties.get_exist_node_dict()
        self.model = nodeCheckProperties.get_model()
        self.suggestion_message = nodeCheckProperties.get_suggestion_message()
        #self.confirm_of_missing_new_tsr_logs = nodeCheckProperties.get_confirm()
        self.skip_message = nodeCheckProperties.get_skip_message()
        self.perform()

    def perform(self):
    
        output_message = "..Skip!" 
        try:      
            check_value = self.do_check()        
            if check_value == True:
                output_message = "..Pass!"
            elif check_value == False:
               output_message = "..Fail!"
            else:
                output_message = "..Skip!" 
        except Exception as err:
            log_n.info(traceback.format_exc())        
        finally:
            log_n.info('Checking {0:50}  ==> {1:20}'.format(type(self).__name__, output_message))
            
    def do_check(self):
        pass

class NodeCompatibility(BaseCheck):
    def do_check(self):
        check_result = False
        if not self.new_code_version or not self.exist_code_version:
            log_n.debug("new_code_version or exist_code_version is null.")
            return
        if (self.new_code_version.startswith('4.7') and self.exist_code_version.startswith('4.5')):
            self.suggestion_message.append("  No support downgrade from 4.7.x to 4.5.x")
        else:
            check_result = True
        return check_result    
            

class NodeIdracCompatibility(BaseCheck):
    def do_check(self):
        check_result = False
        new_node_idrac_version = 0
        old_node_idrac_version = 0
        new_idrac_version = 0
        old_idrac_version = 0
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)
        if (vxrail_version >= 70300):
            # 70300 already install idrac 5.00.10.20
            return True
        if not self.new_node_dict or not self.exist_node_dict:
            log_n.debug("new_node_dict or exist_node_dict is null.")
            self.suggestion_message.append("NodeIdracCompatibility skip reason: no iDrac info from self.exist_node_dict, need manual check, refer KB190151.")
            return
        
        if not self.new_code_version or not self.exist_code_version:
            log_n.debug("new_code_version or exist_code_version is null.")
            self.suggestion_message.append("NodeIdracCompatibility skip reason: no iDrac info from self.exist_node_dict, need manual check, refer KB190151.")
            return
        
        for node_value in self.new_node_dict.values():
            new_idrac_version = node_value["iDrac"]
            new_node_idrac_version = node_value["iDrac"].replace(".","")[0:5]
            break
           
        for node_value in self.exist_node_dict.values():            
            old_idrac_version = node_value["iDrac"]
            if not old_idrac_version:
                self.suggestion_message.append("NodeIdracCompatibility skip reason: no iDrac info from self.exist_node_dict, need manual check, refer KB190151.")
                log_n.debug("No iDrac info from self.exist_node_dict")
                return
            old_node_idrac_version = node_value["iDrac"].replace(".","")[0:5]
            break
            
        if(int(new_node_idrac_version) > 44040 and int(old_node_idrac_version) < 44040):
            self.suggestion_message.append("Refer KB190151,source iDrac version is: "+new_idrac_version +",target iDrac version is: "+old_idrac_version)        
        if(int(new_node_idrac_version) > 50010 and int(old_node_idrac_version) < 42200):
            self.suggestion_message.append("iDrac downgrade need follow the sequence " +new_idrac_version +"> 4.40.40.00 > 4.40.10 > 4.22.00.201 > "+old_idrac_version)
        elif(int(new_node_idrac_version) > 50010 and int(old_node_idrac_version) < 44010):          
            self.suggestion_message.append("iDrac downgrade need follow the sequence " +new_idrac_version +"> 4.40.40.00 > 4.40.10 > "+old_idrac_version)
        elif(int(new_node_idrac_version) > 50010 and int(old_node_idrac_version) < 44040):          
            self.suggestion_message.append("iDrac downgrade need follow the sequence " +new_idrac_version +"> 4.40.40.00 > "+old_idrac_version)
        elif(int(new_node_idrac_version) > 44040 and int(old_node_idrac_version) < 42200):          
            self.suggestion_message.append("iDrac downgrade need follow the sequence " +new_idrac_version +"> 4.40.40.00 > 4.40.10 > 4.22.00.201 > "+old_idrac_version)
        elif(int(new_node_idrac_version) > 44040 and int(old_node_idrac_version) < 44010):          
            self.suggestion_message.append("iDrac downgrade need follow the sequence " +new_idrac_version +"> 4.40.40.00 > 4.40.10 > "+old_idrac_version)
        elif(int(new_node_idrac_version) > 44040 and int(old_node_idrac_version) < 44040):          
            self.suggestion_message.append("iDrac downgrade need follow the sequence " +new_idrac_version +"> 4.40.40.00 > "+old_idrac_version)        
        else:
            check_result = True
        return check_result

##VxRail 15G (E660, E660F, E660N, P670F, V670F) nodes are only supported from 7.0.210 and later. ... 
class Node15Gto47Compatibility(BaseCheck):
    def do_check(self): 
        check_result = False
        if not self.new_node_dict or not self.exist_code_version:
            log_n.debug("new_code_version or exist_code_version is null.")
            return
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)
        
        node_model = ''
        for node_value in self.new_node_dict.values():
            node_model = node_value["Model"]
            break
        if (vxrail_version < 70210 and node_model in ['E660', 'E660F', 'P670F', 'V670F']) or (vxrail_version < 70360 and node_model == 'P670N'):
            self.suggestion_message.append("  Refer KB20460,no support downgrade to " +self.exist_code_version+" on model "+node_value["Model"])
        elif (vxrail_version < 70320 and node_model in ['E660N', 'S670']):
            self.suggestion_message.append("  Refer KB20460,no support downgrade to " +self.exist_code_version+" on model "+node_value["Model"])
        elif (vxrail_version < 47500 and node_model in ['E665', 'E665F', 'E665N']) or (vxrail_version < 47520 and node_model in ['P675N', 'P675F']):
            self.suggestion_message.append("  Refer KB20460,no support downgrade to " +self.exist_code_version+" on model "+node_value["Model"]) 
        else:
            check_result = True
        return check_result
        
class NodeG560Compatibility(BaseCheck):
    def do_check(self): 
        check_result = False
        node_model = ''
        if not self.new_node_dict:
            log_n.debug("new_node_dict is null.")
            return
        for node_value in self.new_node_dict.values():
            node_model = node_value["Model"]
            break
        if (node_model == 'G560'):
            self.suggestion_message.append("  G560 downgrade cases have had issues bricking components - so downgrading a G560 is not normally recommended.")
        else:
            check_result = True
        return check_result
        
class NodeCpuCompatibility(BaseCheck):
    def do_check(self):
        check_result = True
        if not self.new_node_dict or not self.exist_code_version:
            log_n.debug("new_code_version or exist_code_version is null.")
            return
            
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)

        for node_value in self.new_node_dict.values():
            cpu_generation = node_value["CPU"].split()[3]
            cpu_type = cpu_generation[1]
            if(cpu_type == "2" and vxrail_version < 45400 and self.exist_code_version.startswith("4.5")):
                self.suggestion_message.append("It is not possible for these CPU's to run on revisions of VxRail lower than 4.5.400 and 4.5.400 due to firmware restrictions")
                check_result = False
            elif(cpu_type == "2" and vxrail_version < 47211 and self.exist_code_version.startswith("4.7")):
                self.suggestion_message.append("It is not possible for these CPU's to run on revisions of VxRail lower than 4.5.400 and 4.7.211 due to firmware restrictions")
                check_result = False

        return check_result

class NodeLog4jCompatibility(BaseCheck):
    def do_check(self):
        check_result = False
        if not self.exist_code_version:
            return
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)
        if(vxrail_version < 45471 and self.exist_code_version.startswith("4.5")) or (vxrail_version < 47541 and self.exist_code_version.startswith("4.7")):
            self.suggestion_message.append("  Refer KB194458, if downgrade to "+self.exist_code_version+", there is a log4j security vulnerability issue need customer's attention")     
        elif(vxrail_version < 70320 and self.exist_code_version.startswith("7.0")):
            self.suggestion_message.append("  Refer KB194458, if downgrade to "+self.exist_code_version+", there is a log4j security vulnerability issue need customer's attention")     
        else:
            check_result = True        
        return check_result

class NodeNicCompatibility(BaseCheck):
    def do_check(self):
    
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)
        if vxrail_version >= 70210:
           # Broadcom on 7.0.210 already install Firmware 21.80.16.95.
           return True
           
        if not self.new_node_dict or not self.exist_node_dict:
            log_n.debug("new_node_dict or exist_node_dict is null.")
            self.skip_message.append("NodeNicCompatibility skip for new_node_dict or exist_node_dict is null.")
            return
            
        check_result = False
        node_nic_name_list = {}
        node_nic_version = {}
        new_node_nic_version = {}

           
        for node_value in self.new_node_dict.values():
            node_nic_name_list = node_value["Nic"].keys()
            break
        if not node_nic_name_list:
            self.suggestion_message.append("NodeNicCompatibility skip reason: Nic in new_node_dict is null, need manual check, refer KB000205589")
            log_n.debug("Nic in new_node_dict is null.")
            return      
             
        for nic_value in node_nic_name_list:
            if("Mellanox" in  nic_value and vxrail_version < 45400 and self.exist_code_version.startswith("4.5")):
               self.suggestion_message.append("    No support for nodes with Mellanox CX4-LX NICs below 4.5.400 or 4.7.210.") 
            elif("Mellanox" in  nic_value and vxrail_version < 47200 and self.exist_code_version.startswith("4.7")):
               self.suggestion_message.append("    No support for nodes with Mellanox CX4-LX NICs below 4.5.400 or 4.7.210.")  

            elif("41112" in  nic_value and vxrail_version < 45400 and self.exist_code_version.startswith("4.5")):
               self.suggestion_message.append("    No support for nodes with Qlogic  FastlinQ NICs below 4.5.400 or 4.7.210.") 
            elif("41112" in  nic_value and vxrail_version < 47200 and self.exist_code_version.startswith("4.7")):
               self.suggestion_message.append("    No support for nodes with Qlogic  FastlinQ  NICs below 4.5.400 or 4.7.210.") 

            elif("41162" in  nic_value and vxrail_version < 45400 and self.exist_code_version.startswith("4.5")):
               self.suggestion_message.append("    No support for nodes with Qlogic  FastlinQ  NICs below 4.5.400 or 4.7.210.") 
            elif("41162" in  nic_value and vxrail_version < 47200 and self.exist_code_version.startswith("4.7")):
               self.suggestion_message.append("    No support for nodes with Qlogic  FastlinQ  NICs below 4.5.400 or 4.7.210.")  
            
            elif("41164" in  nic_value and vxrail_version < 45400 and self.exist_code_version.startswith("4.5")):
               self.suggestion_message.append("    No support for nodes with Qlogic  FastlinQ  NICs below 4.5.400 or 4.7.210.") 
            elif("41164" in  nic_value and vxrail_version < 47200 and self.exist_code_version.startswith("4.7")):
               self.suggestion_message.append("    No support for nodes with Qlogic  FastlinQ  NICs below 4.5.400 or 4.7.210.")
            elif("41262" in  nic_value and vxrail_version < 47520):
               self.suggestion_message.append("    No support for nodes with QL41262 NICs below  4.7.520.") 
            else:
               check_result = True
            
            for exist_node_value in self.exist_node_dict.values():
                node_nic_version_value = exist_node_value["Nic"].get(nic_value)
                #node_nic_version = exist_node_value["Nic"].values()
                #node_nic_version = int(exist_node_value["Nic"].values().replace(".","")[0:4])
                break
                
            for new_node_value in self.new_node_dict.values():
                new_node_nic_version_value = new_node_value["Nic"].get(nic_value)
                #new_node_nic_version = new_node_value["Nic"].values()
                #new_node_nic_version = int(new_node_value["Nic"].values().replace(".","")[0:4])
                break            
            
            if (not node_nic_version_value or not new_node_nic_version_value):
                break
                
            node_nic_version = int(node_nic_version_value.replace(".","")[0:4])
            new_node_nic_version = int(new_node_nic_version_value.replace(".","")[0:4])
            
            if(("X550" in  nic_value or "X710" in  nic_value ) and node_nic_version !=0 and  node_nic_version < 1889):
               self.suggestion_message.append("   X550,X710 NIC FW cannot be downgrade to lower than 18.8.9")
               check_result = False
               break
               
            if(("X710" in  nic_value) and node_nic_version !=0 and  node_nic_version <= 1959 and new_node_nic_version !=0 and new_node_nic_version > 2050):
               self.suggestion_message.append("   X710 NIC FW 20.5.x cannot be downgrade to lower than 19.5.x,It maybe possible to do a step downgrade ie go from 20.5.x to 20.0.x and then finally to 19.0.x as (https://dl.dell.com/FOLDER07174476M/1/fw_release_x710.txt?uid=2206cd98-9560-444b-d5a3-b9ae2a5b8f5f&fn=fw_release_x710.txt) is supporting these steps - however its is untested and the customer/account team will need to assume responsibility of the downgrade not working.")             
               check_result = False
               break
            
            if(("Broadcom" in  nic_value) and node_nic_version !=0 and  node_nic_version <= 2180 and new_node_nic_version !=0 and new_node_nic_version >= 2180):
               self.suggestion_message.append("   Please be aware the firmware that you wish to downgrade to 21.80.16.95 is exposed to a BCM57414 link down with fatal error, detail info refer KB000205589.")             
               check_result = False
               break
               
        return check_result
        
class NodeBios214Compatibility(BaseCheck):
    def do_check(self): 
        exist_node_bios = 0
        check_result = True
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)
        if vxrail_version >= 70400:
           # 14G70400("BIOS": "2.14.2") Bios214 (check for bios 2.14.2 above should not downgrade to old version)  KB 000203485
           return True
           
        if not self.new_node_dict or not self.exist_node_dict:
            log_n.debug("new_node_dict or exist_node_dict is null.")
            self.skip_message.append("NodeBios214Compatibility skip for new_node_dict or exist_node_dict is null.")
            return
           
        for node_value in self.exist_node_dict.values():
            exist_node_bios = int(node_value["BIOS"].replace(".","")[0:4])
            break
            
        if not exist_node_bios:
           self.suggestion_message.append("NodeBios214Compatibility skip reason: BIOS in exist_node_dict is null,need manual check, drefer KB 000203485")
           log_n.debug("BIOS in exist_node_dict is null.")
           return
            
        for node_value in self.new_node_dict.values():
            node_bios = int(node_value["BIOS"].replace(".","")[0:4])

            if (exist_node_bios !=0 and exist_node_bios <= 2140 and node_bios > 2140):
                self.suggestion_message.append("  Warning,do not manually apply BIOS below 2.14 to 14G systems - when downgraded , if they had TPM with TXT enabled, they would no longer be able to boot,refer KB 000203485.")
                check_result = False  
                break 
        return check_result

#HBA FW cannot be downgrade to lower than 15.17.09.06
class NodeHBA300Compatibility(BaseCheck):
    def do_check(self): 
        check_result = True 
        target_vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)
        if target_vxrail_version >= 70131:# 7.0.131 already fix this issue.  14G70131("HBA": "16.17.01.00")         
           return True
           
        if not self.exist_node_dict:
            log_n.debug("exist_node_dict is null.")
            self.skip_message.append("NodeHBA300Compatibility skip for exist_node_dict is null.")
            return
        for node_value in self.new_node_dict.values():
            node_model = node_value["Model"]
            break 
            
        if(not node_value["HBA"] and node_model.endswith("N")):
            log_n.debug("HBA in new_node_dict is null, and no need check on this model")
            return check_result
        
        if(not "HBA" in self.exist_node_dict.values()):
            #self.suggestion_message.append("NodeHBA300Compatibility skip reason: HBA in exist_code_version is null, need manual check")
            log_n.debug("HBA in exist_code_version is null.")
            self.skip_message.append("NodeHBA300Compatibility skip for HBA in exist_code_version is null.")
            return
            
        for node_value in self.exist_node_dict.values():            
            node_hba300 = int(node_value["HBA"].replace(".",""))
            if (not node_hba300 and node_hba300 < 15170906):
                self.suggestion_message.append("  HBA FW cannot be downgrade to lower than 15.17.09.06.")
                check_result = False  
                break 
        return check_result  

class NodeHBA355Compatibility(BaseCheck):
    def do_check(self): 
        check_result = True 
        if not self.new_node_dict or not self.exist_code_version:
            log_n.debug("new_code_version or exist_code_version is null.")
            self.skip_message.append("NodeHBA355Compatibility skip for new_code_version or exist_code_version is null.")            
            return
        for node_value in self.new_node_dict.values():
            node_model = node_value["Model"]
            break
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)
        if (is15GIntelModel(node_model) and vxrail_version < 70320): #15G Inter default is HBA355, AMD is HBA300,TODO to check detail.
            self.suggestion_message.append("  Any 15G downgrade to below 7.0.320 could impact a DU issue,See KB 000197161.")
            check_result = False                 
        return check_result  
        
# https://jira.gtie.dell.com/browse/VXT-1008
class NodeDiskModelWithMTFDDAKCompatibility(BaseCheck):
    def do_check(self): 
        check_result = True 
        if not self.new_node_dict or not self.exist_code_version:
            log_n.debug("new_code_version or exist_code_version is null.")
            self.skip_message.append("NodeDiskModelCompatibility skip for new_code_version or exist_code_version is null.")            
            return
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)
        if (vxrail_version >= 70401):
            return check_result 
        for node_value in self.new_node_dict.values():
            node_model = node_value["DiskModel"]
            for node_disk_model in node_model:            
                #print (node_disk_model)
                if node_disk_model.startswith("MTFDDAK"):
                    self.suggestion_message.append("  Disk model start with 'MTFDDAK', Node expansion  may meet failed at validation stage with error,See KB000208014.")
                    check_result = False  
                    break               
        return check_result

# https://jira.gtie.dell.com/browse/VXT-1223
class NodeDiskModelWithHFSCompatibility(BaseCheck):
    def do_check(self): 
        check_result = True 
        if not self.new_node_dict or not self.exist_code_version:
            log_n.debug("new_code_version or exist_code_version is null.")
            self.skip_message.append("NodeDiskModelCompatibility skip for new_code_version or exist_code_version is null.")            
            return
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)
        if (vxrail_version >= 70450 and self.exist_code_version.startswith("7")):
            return check_result 
        if (vxrail_version >= 80100 and self.exist_code_version.startswith("8")):
            return check_result

        for node_value in self.new_node_dict.values():
            node_model = node_value["DiskModel"]
            for node_disk_model in node_model:            
                #print (node_disk_model)
                if node_disk_model in ["HFS1T9G3H2X069N","HFS3T8G3H2X069N"]:
                    self.suggestion_message.append("Disk model  with 'HFS1T9G3H2X069N' or 'HFS3T8G3H2X069N', will fail to Upgrade SKHynix SE5110 SSD Firmware when LCM VxRail Cluster,See KB#000207549.")
                    check_result = False  
                    break               
        return check_result

# https://jira.gtie.dell.com/browse/VXT-1016 
class NodeDiskCapableSpeedCompatibility(BaseCheck):
    def do_check(self): 
        check_result = False 
        if not self.new_node_dict or not self.exist_code_version:
            log_n.debug("new_code_version or exist_code_version is null.")
            self.skip_message.append("NodeDiskCapableSpeedCompatibility skip for new_code_version or exist_code_version is null.")            
            return
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)
        if vxrail_version >= 70410: 
            return True
        
        for node_value in self.new_node_dict.values():
            diskPN = node_value["DiskPN"]
            self.suggestion_message.append("According to KB000211829, If the new node has SAS4 disk, for 15G node, the minimum supported VxRail version is 7.0.405;")
            self.suggestion_message.append("For 14G node, the minimum supported VxRail version is 7.0.410.  ( 7.0.370 is only allowed at the point of sale)")  
            self.suggestion_message.append("Please manually check if the new node has \"SAS4\" Interface via Qi website:")
            for dPN in diskPN:
                self.suggestion_message.append("https://quality.dell.com/Part/"+str(dPN))
        # for node_value in self.new_node_dict.values():
        #     node_model = node_value["DiskCapableSpeed"]
        #     for node_capable_speed in node_model: 
        #         if node_capable_speed ==  'Unknown' : 
        #             continue
        #             #self.suggestion_message.append("  There are some disks with unknown disk speed. So please check the disks status on the new node.")
        #             #return
        #         node_capable_speed_value = node_capable_speed.replace(" Gbps","")
        #         node_capable_speed_value_int = int(node_capable_speed_value)                
        #         #print (node_capable_speed_value_int)
        #         if node_capable_speed_value_int >= 24 and vxrail_version < 70370:
        #             self.suggestion_message.append("  24Gbs SAS4 drives required 14th Generation models require 7.0.370 or higher,15th Generation Intel and AMD models require 7.0.405 or higher.")
        #             check_result = False  
        #             break               
        return check_result  

#https://jira.gtie.dell.com/browse/VXT-1088
class NodeBossS2CardCompatibility(BaseCheck):
    def do_check(self): 
        check_result = True 
        if not self.new_node_dict or not self.exist_code_version:
            self.skip_message.append("NodeBossS2CardCompatibility skip for new_node_dict or exist_node_dict is null.")
            log_n.debug("new_code_version or exist_code_version is null.")
            return
        for node_value in self.new_node_dict.values():
            node_model = node_value["Model"]
            break
        if (not is15GModel(node_model)):
            return check_result
            
        for node_value in self.new_node_dict.values():
            pciSubDeviceID = node_value["pciSubDeviceID"]
            break
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)
        if (vxrail_version < 80100 and self.exist_code_version.startswith("8")) or vxrail_version < 70450:
            self.suggestion_message.append("")
            strPCISubDeviceID = ""
            if "2261" == pciSubDeviceID:
                strPCISubDeviceID = "PCISubDeviceID is 2261, it should be a BOSS V3 Card. "
            self.suggestion_message.append(strPCISubDeviceID + "According to KB000219975, This applies to 15G({})  nodes running 7.0.450 or 8.0.100 and above.".format(node_model))

            self.suggestion_message.append("You can manually double confirm the new node has BOSS V3 Card(Part Numbers are \"PKH3T\" or \"14YCM\") via Qi website:")
            for node_value in self.new_node_dict.values():
                node_Tag = node_value["Tag"]
                self.suggestion_message.append("https://quality.dell.com/Asset/"+node_Tag+"/components")
            check_result = False
        return check_result

tPSUList = ['YJ95T', '695Y3', '57TFT', 'TT5N8', '3D09N', '5222N', 'H66J1', 'FR0KX', 'J9N6W', '08PMK', 'P56GH']
#https://jira.gtie.dell.com/browse/VXT-1097
class NodePSUCompatibility(BaseCheck):
    def do_check(self): 
        check_result = True 
        if not self.new_node_dict or not self.exist_code_version:
            self.skip_message.append("NodePSUCompatibility skip for new_node_dict or exist_node_dict is null.")
            log_n.debug("new_code_version or exist_code_version is null.")
            return

        for node_value in self.new_node_dict.values():
            psuPN = node_value["PsuPN"]
            break
        
        tPSUMatch = False        
        for tPSU in psuPN:
            if tPSU in tPSUList:
               tPSUMatch = True
               break               
        if not tPSUMatch: 
            return check_result
        
        for node_value in self.new_node_dict.values():
            node_model = node_value["Model"]
            break
         
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)
        if vxrail_version >= 70410:
          return True
        kb_tpsu = "\nAccording to KB 000224567, Titanium Power Supply Unit(TPSU) " + "".join(psuPN) + " should not allow downgrades below VxRail"
        if vxrail_version >70000 and vxrail_version < 70405 and is15GModel(node_model):
            check_result = False
            self.suggestion_message.append(kb_tpsu +" 7.0.405+ for 15G")

        if vxrail_version < 47560:
            check_result = False
            self.suggestion_message.append(kb_tpsu + " 4.7.560")

        if vxrail_version >70000 and vxrail_version < 70410 and is14GModel(node_model):
            check_result = False
            self.suggestion_message.append(kb_tpsu + " 7.0.410+ for 14G")

        return check_result
        
#https://jira.gtie.dell.com/browse/VXT-1140 
class Node15G70480Compatibility(BaseCheck):
    def do_check(self): 
        check_result = True 
        if not self.new_node_dict or not self.exist_code_version:
            self.skip_message.append("Node15G70480Compatibility skip for new_node_dict or exist_node_dict is null.")            
            log_n.debug("new_code_version or exist_code_version is null.")
            return
        for node_value in self.new_node_dict.values():
            node_model = node_value["Model"]
            break
        if (not is15GModel(node_model)):
            return check_result        
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)
        if vxrail_version == 70480:
            check_result = False
            self.suggestion_message.append("According to VXT-1140, when downgrade a 15G node to 7.0.480 should check the KB000219320")
        return check_result

#https://jira.gtie.dell.com/browse/VXT-1172
class Node16GCompatibility(BaseCheck):
    def do_check(self): 
        check_result = True 
        if not self.new_node_dict and not self.exist_code_version:
            log_n.debug("new_code_version or exist_code_version is null.")
            return
        for node_value in self.new_node_dict.values():
            node_model = node_value["Model"]
            break
        if (not is16GModel(node_model)):
            return check_result     
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)
        if self.exist_code_version.startswith("7.0") and vxrail_version <70460:
            check_result = False
            self.suggestion_message.append("According to VXT-1172, 16G PowerEdge Intel platforms support from 7.0.460 and 8.0.120 on VE-660 and VP-760. ")
        if self.exist_code_version.startswith("8.0") and vxrail_version <80120:
            check_result = False
            self.suggestion_message.append("According to VXT-1172, 16G PowerEdge Intel platforms support from 7.0.460 and 8.0.120 on VE-660 and VP-760. ")
        return check_result
        
#https://jira.gtie.dell.com/browse/VXT-1474
class NodeModelCompatibility(BaseCheck):
    def do_check(self): 
        check_result = True 
        if not self.new_node_dict and not self.exist_code_version:
            log_n.debug("new_code_version or exist_code_version is null.")
            return
            
        for node_value in self.new_node_dict.values():
            node_model = node_value["Model"]
            break
           
        models_to_check_80210 = ['VD-4520c', 'VD-4510c', 'VD-4000r', 'VD-4000w' ,'VD4000z', 'VP-760', 'VE-660']        
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)
        if node_model in models_to_check_80210:
            if self.exist_code_version.startswith("8.0") and vxrail_version <80210:
                check_result = False
                self.suggestion_message.append("According to support-matrix and VXT-1474, model {} support from 8.0.210. ".format(node_model))
                
        models_to_check_80230 = ['VS-760']        
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)
        if node_model in models_to_check_80230:
            if self.exist_code_version.startswith("8.0") and vxrail_version <80230:
                check_result = False
                self.suggestion_message.append("According to support-matrix and VXT-1474, model {} support from 8.0.230. ".format(node_model))
                
        models_to_check_70510 = ['VE-6615', 'VP-7625']        
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)
        if node_model in models_to_check_70510:
            if self.exist_code_version.startswith("7.0") and vxrail_version <70510:
                check_result = False
                self.suggestion_message.append("According to support-matrix, model {} support from 7.0.510. ".format(node_model))
                
        return check_result
        
#KB 000221420
class Node15GVdBiosCompatibility(BaseCheck):
    def do_check(self): 
        check_result = True 

        for node_value in self.new_node_dict.values():
            node_model = node_value["Model"]
            break
        if not is15GVDModel(node_model):        
            return check_result
            
        new_node_bios_version = 0
        if not self.new_node_dict or not self.exist_node_dict:
            log_n.debug("new_node_dict or exist_node_dict is null.")
            self.skip_message.append("Node15GVdBiosCompatibility skip for new_node_dict or exist_node_dict is null.")
            return

        for node_value in self.new_node_dict.values():
            new_node_bios_version = int(node_value["BIOS"].replace(".", "")[0:4])
            break
        
        old_node_bios_version = 0
        #if "BIOS" not in list(self.old_node_dict.values()):    return
        for node_value in self.exist_node_dict.values():
            old_node_bios_version = int(node_value["BIOS"].replace(".", "")[0:4])
            break
        if new_node_bios_version == 0 or old_node_bios_version == 0:
            self.suggestion_message.append("Node15GVdBiosCompatibility skip reason: new_node_bios_version or old_node_bios_version is null ,need manual check, refer KB000221420 for more details.")
            log_n.debug("new_node_bios_version or old_node_bios_version is null.")
            return
            
        if (new_node_bios_version >= 1110 and old_node_bios_version <1110):
            self.suggestion_message.append("Inability to Downgrade XR4510c and XR4520c Systems after Installing BIOS Version 1.11.0 or Newer, refer KB000221420 for more details.")
            check_result = False  
        return check_result

#https://jira.gtie.dell.com/browse/VXT-1202
class NodeVdVersionSupportCompatibility(BaseCheck):
    def do_check(self): 
        check_result = True 


        for node_value in self.new_node_dict.values():
            node_model = node_value["Model"]
            break
        if not is15GVDModel(node_model):        
            return True
        
        vd_version = getSupportVDVersion()
        #print(vd_version)
        #print(self.exist_code_version)
       
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)
        #print(not str(vxrail_version) in vd_version)

        if self.exist_code_version.startswith("7.0") and not str(vxrail_version) in vd_version:
            self.suggestion_message.append("Not support version {} for model {} to downgrade".format(vxrail_version, node_model))
            check_result = False

        return check_result
 
# VXT-1333, the release versions 8.0.230 and 8.0.240 are hardware-released versions, which is why these two versions only support 16G appliance nodes.
class Node15Gto80230or80240(BaseCheck):
    def do_check(self): 
        check_result = True 

        for node_value in self.new_node_dict.values():
            node_model = node_value["Model"]
            break
        
        vxrail_version = changeVxrailCodeVersionToInt(self.exist_code_version)

        if is15GModel(node_model) or is15GVDModel(node_model):
            if self.exist_code_version in ['8.0.230', '8.0.240']:
                self.suggestion_message.append("Not support version {} for model {} to downgrade，the VxRail version 8.0.230 and 8.0.240 are hardware release version for 16G node.".format(vxrail_version, node_model))
                check_result = False

        return check_result

# VXT-1436
class Node16GBiosCompatibility(BaseCheck):
    def do_check(self): 
        check_result = True 

        for node_value in self.new_node_dict.values():
            node_cpu = node_value["CPU"]
            break
        pn_number =  node_cpu.split()[3]
        _5th_Gen_Intel_cpu_pn = ["5512U", "5515+", "5520+", "6526Y", "6530", "6534", "6538N", "6538Y+", "6542Y", "6544Y", "6548N", "6548Y+", "6554S", "6558Q"]
        log_n.debug("pn_number {}".format(pn_number))
        
        if pn_number not in _5th_Gen_Intel_cpu_pn:
           return check_result        
        node_bios =""
        for node_value in self.exist_node_dict.values():
            node_bios = node_value["BIOS"]
            break
        exist_node_bios = int(node_value["BIOS"].replace(".","")[0:4])
        log_n.debug("node_bios {}".format(node_bios))
        
        if exist_node_bios<200:  #2.0.0
            self.suggestion_message.append("BIOS version {} does not support downgrading for the {} . Please refer to KB000248675 for more details.".format(node_bios, node_cpu))
            check_result = False

        return check_result

def perfomNodeCheck(options,new_node_dict,exist_node_dict):

    if not options.from_new_node_version and not options.to_exist_node_version:
        log_n.info("New node version and  Current node version are all empty, exit.") 
        return
        
    if not new_node_dict and not exist_node_dict:
        log_n.info("New node info and  Current node info are all empty, please check the path .") 
        return
        
    new_node_code_version = options.from_new_node_version
    exist_node_code_version = options.to_exist_node_version

    model = ""
    #confirm = options.confirm_of_missing_new_tsr_logs
    log_n.info("\nNode checking:")
    suggestion_message = list()
    skip_message = list()

    nodeCheckProperties = NodeCheckProperties(new_node_code_version,exist_node_code_version,new_node_dict,exist_node_dict,suggestion_message,model,skip_message)
    NodeCompatibility(nodeCheckProperties)
    Node15Gto47Compatibility(nodeCheckProperties)
    NodeIdracCompatibility(nodeCheckProperties)
    NodeG560Compatibility(nodeCheckProperties)
    #NodeLog4jCompatibility(nodeCheckProperties)
    NodeCpuCompatibility(nodeCheckProperties)
    NodeNicCompatibility(nodeCheckProperties)
    NodeBios214Compatibility(nodeCheckProperties)
    NodeHBA300Compatibility(nodeCheckProperties)
    NodeHBA355Compatibility(nodeCheckProperties)
    NodeDiskModelWithMTFDDAKCompatibility(nodeCheckProperties)
    NodeDiskModelWithHFSCompatibility(nodeCheckProperties)
    NodeDiskCapableSpeedCompatibility(nodeCheckProperties)
    NodeBossS2CardCompatibility(nodeCheckProperties)
    NodePSUCompatibility(nodeCheckProperties)
    Node15G70480Compatibility(nodeCheckProperties)    
    Node16GCompatibility(nodeCheckProperties)
    Node15GVdBiosCompatibility(nodeCheckProperties)
    NodeVdVersionSupportCompatibility(nodeCheckProperties)
    Node15Gto80230or80240(nodeCheckProperties)    
    Node16GBiosCompatibility(nodeCheckProperties) 
    NodeModelCompatibility(nodeCheckProperties) 
    
    if len(skip_message) > 0:
        log_n.info("\nSkip Reasons:")
    for x in range(len(skip_message)):
        log_n.info(skip_message[x])

    log_n.info("\nSuggestions:")
    for x in range(len(suggestion_message)):
        log_n.info(suggestion_message[x])
    #if(options.confirm_of_missing_new_tsr_logs):
    #    log_n.info("Please note this check missing TSR log(customer unwilling to provide TSR's), can only get limit info, the customer should take the risk of this downgrade")
 
    if len(suggestion_message) >= 1:
        log_n.info("==> Overall Suggestion: Reject.")        
    
    log_n.info("\nPlease note this is an one-time suggestion for this specific request. As a general recommendation, we strongly encourage the customer ")
    log_n.info("adopt to up-to-date release of code as soon as possible. since we have multiple fixes (both software and security in later releases)")
    
def print_dict(dict):
    for key in dict.values():
        log_n.info(key)
        
def parseNewModelData(options):
    return_str = None    
    if(options.from_new_node_version):
        return_str = options.model_of_vxrail + options.from_new_node_version.replace(".","")
    return return_str

def parseOldModelData(options):
    return_str = None
    if(options.to_exist_node_version):
        return_str = options.model_of_vxrail + options.to_exist_node_version.replace(".","")
    return return_str
    
def parseModelData(options):
    return_str = None
    if(not options.new_node):
        return_str = options.model_of_vxrail + options.from_new_node_version.replace(".","")
    if(not options.exist_node):
        return_str = options.model_of_vxrail + options.to_exist_node_version.replace(".","")
    return return_str
 
def addAttributeToSimualtorModel(string_json):
        string_json['CPU'] = ''
        string_json['PsuPN'] = []
        string_json['DiskPN'] = []
        string_json['DiskCapableSpeed'] = []
        string_json['DiskModel'] = []
        string_json['CPLD'] = ''
        string_json['PSU'] = ''
        string_json['Nic'] = {}
        json.dumps(string_json)

#https://jira.gtie.dell.com/browse/VXT-1210
def check_firmware_with_martix(new_node_dict,new_model_data):
    new_node_dict_compare = {}
    
    for data_key in data_model:
        if(new_model_data.upper() == data_key):
            new_node_dict_compare = data_model[data_key]
            break

    new_node_dict_compare_dict = {
        key: value for key, value in new_node_dict_compare.items()
        if key in ['BIOS', 'HBA', 'iDrac']
    }
    #log_n.info(new_node_dict)
    log_n.info("\nVersion mismatch check:")
    for new_node_dict_key,new_node_dict_value in new_node_dict.items():
        log_n.info(new_node_dict_key)
    #for new_node_dict_value in new_node_dict.values():
        for key, value in new_node_dict_compare_dict.items():
            if key in new_node_dict_value:
                if value =="": #skip empty value.
                   continue
                if value != new_node_dict_value[key]:
                    #log_n.info(f"Version mismatch for {key}: from TSR log is: {new_node_dict_value[key]correct should be: {value}")
                    log_n.info("Version mismatch for {}: from TSR log is: {correct should be: {}".format(key, new_node_dict_value[key], value))
    #print (new_node_dict)   
    return

def set_vxrail_model(new_node_dict,options):
    node_model = ""
    for node_value in new_node_dict.values():
        node_model = node_value["Model"]
        break

    log_n.debug(node_model)
    if (is14GModel(node_model)):
        options.model_of_vxrail = '14g'
    elif (is15GModel(node_model)):
        options.model_of_vxrail = '15g'
    elif (is15GVDModel(node_model)):
        options.model_of_vxrail = '15gvd'
    elif (is15GAMDModel(node_model)):
        options.model_of_vxrail = '15gamd'
    elif (is16GAMDModel(node_model)):
        options.model_of_vxrail = '16gamd'
    elif (is16GModel(node_model)):
        options.model_of_vxrail = '16g'        
    else:
        log_n.error("No Model found Error.")
        exit(1)  
    return

def get_simulator_node(options, exist_node_dict):
    old_model_data = parseOldModelData(options)
    old_string_json = {}

    for data_key in data_model:
        if(old_model_data.upper() == data_key):
            old_string_json = data_model[data_key]                 
    if  not old_string_json:
         print("\nNo simulator model {}, please create a VXT for node_review to add it.".format(old_model_data))
         #return
    
    if(old_string_json):     
        addAttributeToSimualtorModel(old_string_json)
    
    if (not options.exist_node and old_string_json):
        exist_node_dict["TSR2000"] = old_string_json
    log_n.info("\nSim Old Node Info:")
    log_n.info(old_string_json)

def data_model_update():
    data_model.update(data_model_14G)
    data_model.update(data_model_15G)
    data_model.update(data_model_15GAMD)
    data_model.update(data_model_15GVD)
    data_model.update(data_model_16G)
    data_model.update(data_model_16GAMD)
    return data_model

def version_check(options):
    if options.from_new_node_version:
        log_n.info("New node code version: "+options.from_new_node_version)
    if options.to_exist_node_version:
        log_n.info("Cur node code version: "+options.to_exist_node_version)
    if(not options.from_new_node_version or not options.to_exist_node_version):
        log_n.info("\nMissing target or source vxrail version, no perform downgrade case check.")
        sys.exit(1)

def main():
    log_n.info("Running on version {}.".format(CODE_VERSION))   
    
    parser = create_option_parser()
    options, args = parser.parse_args()
    if (not options.new_node):
        log_n.error("Error: Not support new node data is empty.")
        parser.print_help() 
        sys.exit(1)
        
    version_check(options)
    
    new_node_dict = {}    
    if(options.new_node):
        parseNewTSRNode(options,new_node_dict)
    if not (len(new_node_dict) == 0):
        log_n.info("\nNew Node Info:")
        print_dict(new_node_dict)
    else:
       log_n.error("Cannot get the new node data, check input.")
       return
    
    exist_node_dict = {}    
    if(options.exist_node):
        parseExistTSRNode(options,exist_node_dict)   
    if not (len(exist_node_dict) == 0):
        log_n.info("\nCur Node Info:")
        print_dict(exist_node_dict)
        
    if not options.exist_node: 
        data_model_update()
        set_vxrail_model(new_node_dict,options)
        get_simulator_node(options, exist_node_dict)
    #if options.from_new_node_version: #only check new node firmare and need new vxrial code version.
    #   new_model_data = parseNewModelData(options)
    #   check_firmware_with_martix(new_node_dict, new_model_data)    
    #vxrail_version = changeVxrailCodeVersionToInt(options.to_exist_node_version)
    #if not options.exist_node and vxrail_version < 70410:    

    perfomNodeCheck(options,new_node_dict,exist_node_dict)

if __name__ == "__main__":
    setup_logger()
    try:
        main()
    except Exception as e:
        log_n.error("Error: {}".format(str(e)))
        log_n.error("Traceback: {}".format(traceback.format_exc()))
        exit(1)
