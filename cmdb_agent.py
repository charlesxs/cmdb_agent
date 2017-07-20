# coding=utf-8
#

import json
import re
import requests
import logging
from collecter import Collector
from config import *


VERSION = '0.1.0'

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s [%(levelname)s]  %(message)s',
                    filename=os.path.join(pdir, 'cmdb_agent.log'),
                    filemode='a')


class AssetReporter(object):
    def __init__(self):
        collector = Collector()
        self.server = collector.collect()
        self.search_url = '{0}/search/?lan_ip={1}'.format(server_url.rstrip('/'), self.server['lan_ip'])
        self.post_url = '{0}/asset/'.format(server_url.rstrip('/'))

    def _get_asset_type(self):
        vm_path = re.compile(r'vmware|kvm|xen|openvz', re.I)
        asset_type = '服务器'
        if vm_path.search(self.server['hw_system'][0]['product_name']):
            asset_type = '虚拟机'
        return asset_type

    def _calc_id(self):
        r = requests.get(self.post_url)
        if r.status_code != 200:
            raise Exception('get id fail from cmdb')
        data = r.json()
        if len(data) < 1:
            return '{0}000001'.format(serialnum_prefix)

        id_ = str(data[0]['id'] + 1)
        zero_length, id_length = 6, len(id_)
        suffix = '0' * (zero_length - id_length) + id_
        return serialnum_prefix + suffix

    def create_asset(self):
        info = {
            'serialnum': self._calc_id(),
            'idc': idc,
            'asset_type': self._get_asset_type(),
            'use': use,
            'server': self.server
        }
        r = requests.post(self.post_url, data=json.dumps(info), headers={'Content-Type': 'application/json'})
        if r.status_code != 201:
            raise Exception(r.text)
        return r.json()

    def get_asset_id(self):
        r = requests.get(self.search_url)
        if r.status_code == 200:
            return r.json()['id']
        return None

    def update_asset(self, asset_id):
        put_url = '{0}/{1}/'.format(self.post_url.rstrip('/'), asset_id)
        data = {'server': self.server}
        r = requests.put(put_url, data=json.dumps(data), headers={'Content-Type': 'application/json'})
        if r.status_code != 201:
            raise Exception(r.text)
        return r.json()

    def report(self):
        id_ = self.get_asset_id()
        if id_ is None:
            logging.warn('Asset is not register in cmdb server, create it.')
            return self.create_asset()

        return self.update_asset(id_)


if __name__ == '__main__':
    res = AssetReporter().report()
    logging.info(json.dumps(res))


