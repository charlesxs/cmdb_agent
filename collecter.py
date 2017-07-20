# coding=utf-8
#

import re
import platform
import socket
from tools import Command


class Collector(object):
    def __init__(self):
        self.collectors = [LinuxCollector(),
                           WinCollector()]

    def collect(self):
        system = platform.system()
        for collector in self.collectors:
            if collector.platform == system:
                return collector.collect()
        return None

    def register_collector(self, collector):
        self.collectors.append(collector)

    def unregister_collector(self, collector):
        self.collectors.remove(collector)


class LinuxCollector(object):
    def __init__(self):
        self.platform = platform.system()
        self._addrs = None

    def __eq__(self, other):
        return (self.__class__.__name__ ==
                other.__class__.__name__)

    def collect(self):
        """
        :return: dict , {
                            'logical_cpu': String,
                            'logical_memory': String,
                            'logical_disk': String,
                            'hostname': String,
                            'os': String,
                            'lan_ip':  String(IP Type),
                            'wan_ip': String or None,
                            'networkinterface': [
                                {
                                    'name': String,
                                    'mac': String,
                                    'ip': String,
                                    'state': 0 or 1
                                },
                                ....
                            ],
                            'memory': [
                                {
                                    'serialnum': String,
                                    'part_number': String,
                                    'speed': String,
                                    'manufacturer': Number,
                                    'locator': String,
                                    'size': String,
                                },
                                ....
                            ],
                            'cpu': [
                                {
                                    'socket': String,
                                    'family': String,
                                    'version': String,
                                    'speed': String,
                                    'cores': Number,
                                    'characteristics': String
                                },
                                ....
                            ],
                            'hw_system': [
                                {
                                    'serialnum': String,
                                    'manufacturer': String,
                                    'product_name': String,
                                    'uuid': String
                                }
                            ],
                            'disk': [
                                ....
                            ]
                        }
        
        collect the system information
        """
        self._addrs = self._collect_addrs()

        return {
            'logical_cpu': self._collect_logical_cpu(),
            'logical_memory': self._collect_logical_memory(),
            'logical_disk': self._collect_logical_disk(),
            'hostname': socket.gethostname(),
            'os': ' '.join(platform.dist()[:-1]),
            'lan_ip': self._collect_ip(lan=True),
            'wan_ip': self._collect_ip(wan=True),
            'networkinterface': self._addrs,
            'memory': self._collect_memorys(),
            'cpu': self._collect_cpus(),
            'hw_system': self._collect_hw_system(),
            'disk': self._collect_disks()
        }

    @staticmethod
    def _collect_logical_disk():
        pat = re.compile(r'^\s+[0-9]+')
        disk = Command('df').execute().split('\n')
        disk_sum = 0
        for i, line in enumerate(disk):
            fields = line.split()
            if line.startswith('/dev/') and len(fields) >= 2:
                disk_sum += int(fields[1])
            elif pat.search(line) and disk[i-1].startswith('/dev/'):
                disk_sum += int(fields[0])
        return '{0} GB'.format(disk_sum / 1024 / 1024)

    @staticmethod
    def _collect_logical_memory():
        res = Command('free -m') | Command("awk '/Mem:/{print $2}'")
        return '{0} MB'.format(res)

    @staticmethod
    def _collect_logical_cpu():
        return Command("awk -F: '/model name/{print $2}' /proc/cpuinfo") | Command('uniq -d')

    @staticmethod
    def ipick_data(cmd, line_flag):
        output = Command(cmd).execute().split('\n')
        data = []
        for d in output:
            if line_flag.match(d):
                if data:
                    yield data
                data = []
            data.append(d)
        yield data

    def _collect_addrs(self):
        addrs = []
        exclude_name = re.compile(r'^(docker|veth|bridge|lo|br[^0-9]|vnet|vir)')
        for addr in self.ipick_data('ip addr show', line_flag=re.compile(r'^[0-9]+:')):
            current_addr = {'state': 0, 'ip': None}
            for i, v in enumerate(addr):
                vlist = [k.strip() for k in v.strip().split()]
                if i == 0:
                    name = vlist[1].strip(':')
                    if exclude_name.match(name):
                        break
                    if 'state UP' in v:
                        current_addr['state'] = 1
                    current_addr['name'] = name
                elif vlist[0] == 'link/ether':
                    current_addr['mac'] = vlist[1]
                elif vlist[0] == 'inet' and not current_addr.get('ip'):
                    current_addr['ip'] = vlist[1].split('/')[0]

            if len(current_addr) >= 4:
                addrs.append(current_addr)
        return addrs

    def _collect_ip(self, lan=False, wan=False):
        private_addr_prefix = re.compile(r'(^192\.168|^172\.16|^172\.17|^10\.)')
        for addr in self._addrs:
            ip = addr['ip']
            if ip is not None and private_addr_prefix.match(ip) and lan:
                return ip
            if ip is not None and not private_addr_prefix.match(ip) and wan:
                return ip
        return None

    def _collect_memorys(self):
        memorys, sizepat = [], re.compile(r'^\s*Size:\s+[0-9]+')
        key_map = {
            'Locator': 'locator',
            'Speed': 'speed',
            'Manufacturer': 'manufacturer',
            'Serial Number': 'serialnum',
            'Part Number': 'part_number'
        }

        for memory in self.ipick_data('dmidecode -t memory',
                                      line_flag=re.compile(r'^Memory Device')):
            current_memory = {}
            for m in memory:
                mlist = [i.strip() for i in m.strip().split(':')]
                if len(mlist) <= 1:
                    continue

                if mlist[0] == 'Size':
                    if not sizepat.match(m):
                        break
                    current_memory['size'] = mlist[-1].strip()
                elif mlist[0] in key_map:
                    current_memory[key_map[mlist[0]]] = mlist[1].strip()

            if len(current_memory) == 6:
                memorys.append(current_memory)
        return memorys

    def _collect_cpus(self):
        cpus = []
        key_map = {
            'Socket Designation': 'socket',
            'Family': 'family',
            'Version': 'version',
            'Current Speed': 'speed',
            'Core Enabled': 'cores',
        }

        for cpu in self.ipick_data('dmidecode -t processor',
                                   line_flag=re.compile(r'^Processor Information')):
            current_cpu = {'characteristics': "64-bit"}
            for k, c in enumerate(cpu):
                clist = [i.strip() for i in c.strip().split(':')]
                if len(clist) <= 1 and clist[0] != 'Characteristics':
                    continue

                if clist[0] in key_map and clist[1]:
                    current_cpu[key_map[clist[0]]] = clist[1]
                elif clist[0] == 'Characteristics':
                    chars = ','.join([p.strip() for p in cpu[k+1:] if not p.startswith('Handle')])
                    current_cpu['characteristics'] = chars[:200]
            if len(current_cpu) == 6:
                cpus.append(current_cpu)
        return cpus

    def _collect_hw_system(self):
        hw_system = []
        key_map = {
            'Serial Number': 'serialnum',
            'Manufacturer': 'manufacturer',
            'Product Name': 'product_name',
            'UUID': 'uuid'
        }

        for system in self.ipick_data('dmidecode -t system',
                                      line_flag=re.compile(r'^Handle 0x')):
            current_system = {}
            for i, s in enumerate(system):
                slist = [i.strip() for i in s.strip().split(':')]
                if i == 1 and s.strip() != 'System Information':
                    break
                if len(slist) <= 1:
                    continue

                if slist[0] in key_map:
                    current_system[key_map[slist[0]]] = slist[1]
            if len(current_system) == 4:
                hw_system.append(current_system)
        return hw_system

    def _collect_disks(self):
        return []


class WinCollector(object):
    def __init__(self):
        self.platform = platform.system()
        self.info = {}

    def __eq__(self, other):
        return (self.__class__.__name__ ==
                other.__class__.__name__)

    def collect(self):
        pass


if __name__ == '__main__':
    import json
    a = Collector()
    print(json.dumps(a.collect()))

