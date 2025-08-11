import os
import re
import json

# Define the dictionary to store the output of "esxcli storage filesystem list"
os_volumes = {}

# Run the command and store the output
output = os.popen("esxcli storage filesystem list").read()
#print(output)

# Parse the output and store it in the dictionary
lines = output.split('\n')
#print(lines)
for line in lines[2:]:
    if line.strip():
        mount_point, volume_name, uuid, mounted, mount_type, size, free = re.split(r"\s+", line)
        os_volumes[mount_point] = {"Volume Name": volume_name}
#print(os_volumes)

# Find the "Mount Point" that contains "datastore1" and assign it to "local_store"
local_store = None
for mount_p, volume_n in os_volumes.items():
    if "datastore1" in volume_n["Volume Name"]:
        local_store = mount_p
        '''
        print('================================================================================')
        print(f'Mount Point: {mount_p}')
        print(f'Volume Name: {volume_n["Volume Name"]}')
        print('================================================================================')
        '''
#print("The local store volume is:",local_store)

# Run the "stat" command and store the output
fs_output = os.popen(f"stat -f {local_store}").read()
#print("The command \"stat\" output is:",fs_output)

# Parse the output and extract the desired values
'''
block_size = int(re.search(r"Block size: (\d+)", fs_output).group(1))
total_blocks = int(re.search(r"Blocks: Total: (\d+)", fs_output).group(1))
free_blocks = int(re.search(r"Blocks: Free: (\d+)", fs_output).group(1))
available_blocks = free_blocks
total_inodes = int(re.search(r"Inodes: Total: (\d+)", fs_output).group(1))
free_inodes = int(re.search(r"Inodes: Free: (\d+)", fs_output).group(1))
'''
'''
block_size_match = re.search(r"Block size: (\d+)", fs_output)
if block_size_match:
    block_size = int(block_size_match.group(1))
else:
    print("Block size not found in the output.")

total_blocks_match = re.search(r"Blocks: Total: (\d+)", fs_output)
if total_blocks_match:
    total_blocks = int(total_blocks_match.group(1))
else:
    print("Total blocks not found in the output.")

free_blocks_match = re.search(r"Blocks: Free: (\d+)", fs_output)
if free_blocks_match:
    free_blocks = int(free_blocks_match.group(1))
else:
    print("Free blocks not found in the output.")

available_blocks = free_blocks

total_inodes_match = re.search(r"Inodes: Total: (\d+)", fs_output)
if total_inodes_match:
    total_inodes = int(total_inodes_match.group(1))
else:
    print("Total inodes not found in the output.")

free_inodes_match = re.search(r"Inodes: Free: (\d+)", fs_output)
if free_inodes_match:
    free_inodes = int(free_inodes_match.group(1))
else:
    print("Free inodes not found in the output.")
'''

pattern = r"(\w+): (.+)"
matches = re.findall(pattern, fs_output)
result = {}

for match in matches:
    key, value = match
    if key == "Block size":
        result["block_size"] = int(value)
    elif key == "Blocks":
        blocks = {}
        blocks["total"] = int(re.search(r"\d+", value.split(":")[1].strip()).group())
        blocks["free"] = int(re.search(r"\d+", value.split(":")[2].strip()).group())
        blocks["available"] = int(re.search(r"\d+", value.split(":")[2].strip()).group())
        result["blocks"] = blocks
    elif key == "Inodes":
        inodes = {}
        inodes["total"] = int(re.search(r"\d+", value.split(":")[1].strip()).group())
        inodes["free"] = int(re.search(r"\d+", value.split(":")[2].strip()).group())
        result["inodes"] = inodes

# Convert the dictionary to JSON
import json
json_result = json.dumps(result)

#print(json_result)

# Accessing the values in the JSON data

json_data = json.loads(json_result)

total_block = json_data["blocks"]["total"]
free_block = json_data["blocks"]["free"]
available_block = json_data["blocks"]["available"]

total_inode = json_data["inodes"]["total"]
free_inode = json_data["inodes"]["free"]

print('')
print('============= File System Status for ESXi local data store =============')
print("Total block:", total_block)
print("Free block:", free_block)
print("Available block:", available_block)
print("Total inode:", total_inode)
print("Free inode:", free_inode)