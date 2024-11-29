# models/device_manager.py

import os
import subprocess
import re

class DeviceManager:
    def __init__(self):
        self.cuda_visible_devices = None

    def get_mig_uuids(self):
        result = subprocess.run(['nvidia-smi', '-L'], stdout=subprocess.PIPE, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Command 'nvidia-smi -L' failed with exit code {result.returncode}")
        
        output = result.stdout
        print(output)
    
        mig_uuid_pattern = re.compile(r'MIG-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
        
        mig_uuids = mig_uuid_pattern.findall(output)
        
        return mig_uuids

    def set_cuda_visible_devices(self, mig_uuids):
        mig_uuids_str = ','.join(mig_uuids)
        os.environ['CUDA_VISIBLE_DEVICES'] = mig_uuids_str
        print(f"CUDA_VISIBLE_DEVICES set to: {mig_uuids_str}")

    def set_cuda_visible_devices_mig(self):
        mig_uuids = self.get_mig_uuids()
        if mig_uuids:
            self.set_cuda_visible_devices(mig_uuids)
