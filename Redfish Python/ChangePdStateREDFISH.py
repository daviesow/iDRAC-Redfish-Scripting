#
#
# _author_ = Texas Roemer <Texas_Roemer@Dell.com>
# _version_ = 1.0
#
# Copyright (c) 2021, Dell, Inc.
#
# This software is licensed to you under the GNU General Public License,
# version 2 (GPLv2). There is NO WARRANTY for this software, express or
# implied, including the implied warranties of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. You should have received a copy of GPLv2
# along with this software; if not, see
# http://www.gnu.org/licenses/old-licenses/gpl-2.0.txt.
#


import requests, json, sys, re, time, warnings, argparse

from datetime import datetime

warnings.filterwarnings("ignore")

parser=argparse.ArgumentParser(description="Python script using Redfish API with OEM extension to change the PD state of a disk part of a virtual disk. Either set the disk to offline or bring back online (RAID 0 not supported)")
parser.add_argument('-ip',help='iDRAC IP address', required=True)
parser.add_argument('-u', help='iDRAC username', required=True)
parser.add_argument('-p', help='iDRAC password', required=True)
parser.add_argument('script_examples',action="store_true",help='ChangePdStateREDFISH.py -ip 192.168.0.120 -u root -p calvin -c y, this examples shows getting storage controller FQDDs. ChangePdStateREDFISH.py -ip 192.168.0.120 -u root -p calvin -d RAID.Mezzanine.1-1, this example will return all disks detected behind this storage controller and their current RAID status. ChangePdStateREDFISH.py -ip 192.168.0.120 -u root -p calvin -pd Disk.Bay.10:Enclosure.Internal.0-1:RAID.Mezzanine.1-1 -o offline, this example shows setting disk in bay 10 to offline.')
parser.add_argument('-c', help='Get server storage controller FQDDs, pass in \"y\"', required=False)
parser.add_argument('-d', help='Get server storage controller disk FQDDs and disk raid status only, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-v', help='Get current server storage controller virtual disk(s) and virtual disk type, pass in storage controller FQDD, Example "\RAID.Integrated.1-1\"', required=False)
parser.add_argument('-pd', help='Convert drive to offline or online, pass in the disk FQDD, Example \"Disk Disk.Bay.4:Enclosure.Internal.0-1:RAID.Slot.6-1\"', required=False)
parser.add_argument('-o', help='Convert drive to offline, pass in value \"offline\". Convert drive to online, pass in value \"online\"', required=False)


args=vars(parser.parse_args())

idrac_ip=args["ip"]
idrac_username=args["u"]
idrac_password=args["p"]


def check_supported_idrac_version():
    response = requests.get('https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    if response.status_code == 401:
        print("\n- WARNING, unable to access iDRAC, check to make sure you are passing in valid iDRAC credentials")
        sys.exit()
    elif response.status_code != 200:
        print("\n- WARNING, iDRAC version installed does not support this feature using Redfish API")
        sys.exit()
    else:
        pass


def get_storage_controllers():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage' % idrac_ip,verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    print("\n- Server controller(s) detected -\n")
    controller_list=[]
    for i in data['Members']:
        controller_list.append(i['@odata.id'].split("/")[-1])
        print(i['@odata.id'].split("/")[-1])

    
def get_pdisks_check_raidstatus():
    disk_used_created_vds=[]
    available_disks=[]
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s' % (idrac_ip, args["d"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    drive_list=[]
    
    if data['Drives'] == []:
        print("\n- INFO, no drives detected for %s" % args["d"])
        sys.exit()
    else:
        
        for i in data[u'Drives']:
            drive_list.append(i[u'@odata.id'].split("/")[-1])
    print("\n- Drives detected for controller \"%s\" and RaidStatus\n" % args["d"])
    for i in drive_list:
      response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Drives/%s' % (idrac_ip, i),verify=False,auth=(idrac_username, idrac_password))
      data = response.json()
      
      print(" - Disk: %s, Raidstatus: %s" % (i, data[u'Oem'][u'Dell'][u'DellPhysicalDisk'][u'RaidStatus']))

              

def get_virtual_disks():
    response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/%s/Volumes' % (idrac_ip, args["v"]),verify=False,auth=(idrac_username, idrac_password))
    data = response.json()
    vd_list=[]
    if data['Members'] == []:
        print("\n- INFO, no volume(s) detected for %s" % args["v"])
        sys.exit()
    else:
        for i in data['Members']:
            vd_list.append(i['@odata.id'].split("/")[-1])
    print("\n- Volume(s) detected for %s controller -\n" % args["v"])
    for ii in vd_list:
        print("\n- Virtual Disk %s -\n" % ii)
        response = requests.get('https://%s/redfish/v1/Systems/System.Embedded.1/Storage/Volumes/%s' % (idrac_ip, ii),verify=False,auth=(idrac_username, idrac_password))
        data = response.json()
        for i in data.items():
            if i[0] == "Links":
                for ii in i[1]["Drives"]:
                    print("Disk: %s" % ii['@odata.id'].split("/")[-1])
            if i[0] == "VolumeType" or i[0] == "RAIDType":
                print("%s: %s" % (i[0], i[1]))


def change_pd_state():
    global job_id
    url = 'https://%s/redfish/v1/Dell/Systems/System.Embedded.1/DellRaidService/Actions/DellRaidService.ChangePDState' % (idrac_ip)
    headers = {'content-type': 'application/json'}
    payload={"State":"","TargetFQDD":args["pd"]}
    if args["o"].lower() == "offline":
        payload["State"] = "Offline"
    elif args["o"].lower() == "online":
        payload["State"] = "Online"
    else:
        print("- INFO, invalid value passed in for argument -o")
        sys.exit()
    
    
    response = requests.post(url, data=json.dumps(payload), headers=headers, verify=False,auth=(idrac_username,idrac_password))
    data = response.json()
    if response.status_code == 200 or response.status_code == 202:
        pass
        try:
            job_id = response.headers['Location'].split("/")[-1]
        except:
            print("- FAIL, unable to locate job ID in JSON headers output")
            sys.exit()
        print("- Job ID %s successfully created to change disk %s to %s" % (job_id, args["pd"], args["o"]))
    else:
        print("\n-FAIL, POST command failed to change disk %s to %s, status code %s returned" % (args["pd"], args["o"], response.status_code))
        data = response.json()
        print("\n-POST command failure results:\n %s" % data)
        sys.exit()

def loop_job_status():
    start_time=datetime.now()
    while True:
        req = requests.get('https://%s/redfish/v1/Managers/iDRAC.Embedded.1/Jobs/%s' % (idrac_ip, job_id), auth=(idrac_username, idrac_password), verify=False)
        current_time=(datetime.now()-start_time)
        statusCode = req.status_code
        if statusCode == 200:
            pass
        else:
            print("\n- FAIL, Command failed to check job status, return code is %s" % statusCode)
            print("Extended Info Message: {0}".format(req.json()))
            sys.exit()
        data = req.json()
        if str(current_time)[0:7] >= "2:00:00":
            print("\n- FAIL: Timeout of 2 hours has been hit, script stopped\n")
            sys.exit()
        elif "Fail" in data['Message'] or "fail" in data['Message'] or data['JobState'] == "Failed":
            print("- FAIL: job ID %s failed, failed message is: %s" % (job_id, data[u'Message']))
            sys.exit()
        elif data[u'JobState'] == "Completed":
            print("\n--- PASS, Final Detailed Job Status Results ---\n")
            for i in data.items():
                if "odata" in i[0] or "MessageArgs" in i[0] or "TargetSettingsURI" in i[0]:
                    pass
                else:
                    print("%s: %s" % (i[0],i[1]))
            break
        else:
            print("- INFO, job status not completed, current status: \"%s\"" % (data['Message']))
            time.sleep(3)
    

    

if __name__ == "__main__":
    check_supported_idrac_version()
    if args["c"]:
        get_storage_controllers()
    elif args["v"]:
        get_virtual_disks()
    elif args["pd"] and args["o"]:
        change_pd_state()
        loop_job_status()
    elif args["d"]:
        get_pdisks_check_raidstatus()
    else:
        print("- FAIL, invalid argument values or not all required parameters passed in")
        
    
    
        
            
        
        
