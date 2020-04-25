#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# (c) 2020, Julien BORDELLIER <git@julienbordellier.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


DOCUMENTATION = r'''
---
module: vultr_lb
short_description: Manages Load Balancers on Vultr
description:
  - Create and remove Load Balancers.
author: "Julien BORDELLIER (@jstoja)"
options:
  dcid:
    description:
      - DCID integer Location in which to create the load balancer.
    required: true
    type: int
  name:
    description: Text label that will be associated with the subscription.
    aliases: [ label ]
    required: true
    type: str
  config_ssl_redirect:
    description: Forces redirect from HTTP to HTTPS.
    type: bool
  sticky_sessions:
    description: Enables stick sessions for your load balancer.
    type: bool
  cookie_name:
    description: Name for your stick session.
    type: str
  balancing_algorithm:
    description: Balancing algorithm for your load balancer.
    choices: [ roundrobin, leastconn ]
    type: str
  health_check:
    description: Defines health checks for your attached backend nodes.
    type: dict
    suboptions:
      protocol:
        description: Connection protocol.
        choices: [ http, https ]
        type: str
      port:
        description: Connection port.
        type: int
      check_interval:
        description: Time in seconds to perform health check.
        type: int
      response_timeout:
        description: Time in seconds to wait for a health check response.
        type: int
      unhealthy_threshold:
        description: Number of failed attempts encountered before failover.
        type: int
      healthy_threshold:
        description: Number of failed attempts encountered before failover.
        type: int
      path:
        description:
          - Path to page used for health check.
          - The target page must return an HTTP 200 success code.
        type: str
  forwarding_rules:
    description: Defines forwarding rules that your load balancer will follow.
    type: list
    elements: dict
    suboptions:
      frontend_protocol:
        description: Endpoint protocol on load balancer side.
        choices:
          - http
          - https
          - tcp
        type: str
        required: true
      frontend_port:
        description: Endpoint port on load balancer side.
        type: int
        required: true
      backend_protocol:
        description: Endpoint protocol on instance side.
        choices:
          - http
          - https
          - tcp
        type: str
        required: true
      backend_port:
        description: Endpoint port on instance side.
        type: int
        required: true
  ssl_private_key:
    description: The SSL certificates private key.
    type: str
  ssl_certificate:
    description: The SSL Certificate.
    type: str
  ssl_chain:
    description: The SSL certificate chain.
    type: str
  state:
    description: State of the Load Balancer.
    default: present
    choices: [ present, absent ]
    type: str
extends_documentation_fragment:
- ngine_io.vultr.vultr

'''

EXAMPLES = r'''
- name: Ensure a Load Balancer exists
  ngine_io.vultr.vultr_lb:
    dcid: 1
    balancing_algorithm: leastconn
    label: web
    state: present
    forwarding_rules:
      - frontend_protocol: https
        frontend_port: 81
        backend_protocol: https
        backend_port: 81
  delegate_to: localhost
'''

RETURN = r'''
---
vultr_api:
  description: Response from Vultr API with a few additions/modification
  returned: success
  type: complex
  contains:
    api_account:
      description: Account used in the ini file to select the key
      returned: success
      type: str
      sample: default
    api_timeout:
      description: Timeout used for the API requests
      returned: success
      type: int
      sample: 60
    api_retries:
      description: Amount of max retries for the API requests
      returned: success
      type: int
      sample: 5
    api_retry_max_delay:
      description: Exponential backoff delay in seconds between retries up to this max delay value.
      returned: success
      type: int
      sample: 12
    api_endpoint:
      description: Endpoint used for the API requests
      returned: success
      type: str
      sample: "https://api.vultr.com"
vultr_lb:
  description: Response from Vultr API
  returned: success
  type: complex
  contains:
    SUBID:
      description: Unique identifier of a load balancer subscription.
      returned: success
      type: int
      sample: 1314217
    date_created:
      description: Date the Load Balancer was created.
      returned: success
      type: str
      sample: "2017-08-26 12:47:48"
    DCID:
      description: Location in which the Load Balancer was created.
      returned: success
      type: int
      sample: 1
    location:
      description: The physical localtion where the Load Balancer was created.
      returned: success
      type: str
      sample: "New Jersey"
    label:
      description: The name of the Load Balancer.
      returned: success
      type: str
      sample: "lb01"
    status:
      description: "Status of the subscription and will be one of: pending | active | suspended | closed."
      returned: success
      type: str
      sample: "active"
    ipv4:
      description: IPv4 of the Load Balancer.
      returned: success
      type: str
      sample: "203.0.113.20"
    ipv6:
      description: IPv6 of the Load Balancer.
      returned: success
      type: str
      sample: "fd06:30bd:6374:dc29:ffff:ffff:ffff:ffff"
'''

from ansible.module_utils.basic import AnsibleModule
from ..module_utils.vultr import (
    Vultr,
    vultr_argument_spec,
)


HEALTH_CHECK_SPEC = {
    'protocol': {'type': 'str', 'choices': ['http', 'https']},
    'port': {'type': 'int'},
    'path': {'type': 'str'},
    'check_interval': {'type': 'int'},
    'response_timeout': {'type': 'int'},
    'unhealthy_threshold': {'type': 'int'},
    'healthy_threshold': {'type': 'int'},
}


FORWARDING_RULE_SPEC = {
    'frontend_protocol': {'type': 'str', 'choices': ['http', 'https', 'tcp'], 'required': True},
    'frontend_port': {'type': 'int', 'required': True},
    'backend_protocol': {'type': 'str', 'choices': ['http', 'https', 'tcp'], 'required': True},
    'backend_port': {'type': 'int', 'required': True},
}


class AnsibleVultrLoadBalancer(Vultr):

    def __init__(self, module):
        super(AnsibleVultrLoadBalancer, self).__init__(module, "vultr_lb")

        self.returns = {
        }

    def get_lb(self):
        lb_list = self.api_query(path="/v1/loadbalancer/list")
        lb_name = self.module.params.get('name').lower()
        found_lbs = []

        if lb_list:
            found_lbs = [lb for lb in lb_list if lb['name'] is lb_name]

        if len(found_lbs) in (0, 1):
            self.module.warn("Found more than 1 or no Vultr Load Balancer matching name")
            return {}

        return found_lbs[0]

    def present_lb(self):
        lb = self.get_lb()
        if not lb:
            lb = self._create_lb(lb)
        return lb

    def _create_lb(self, lb):
        self.result['changed'] = True
        data = {
            'DCID': self.module.params.get('dcid'),
            'label': self.module.params.get('name'),
        }

        def add_param_if_exists(d, param):
            value = self.module.params.get(param)
            if value:
                d[param] = value

        optional_params = [
            'config_ssl_redirect',
            'sticky_sessions',
            'cookie_name',
            'balancing_algorithm',
            'health_check',
            'forwarding_rules',
            'ssl_private_key',
            'ssl_certificate',
            'ssl_chain'
        ]

        for param in optional_params:
            add_param_if_exists(data, param)

        # StickSessions should be either 'on' or 'off'
        if 'sticky_sessions' in data:
            ss_values = {True: 'on', False: 'off'}
            data['sticky_sessions'] = ss_values[data['sticky_sessions']]

        self.result['diff']['before'] = {}
        self.result['diff']['after'] = data

        if not self.module.check_mode:
            self.api_query(
                path="/v1/loadbalancer/create",
                method="POST",
                data=data
            )
            lb = self.get_lb()
        return lb

    def absent_lb(self):
        lb = self.get_lb()
        if lb:
            self.result['changed'] = True

        data = {
            'label': lb['name'],
        }

        self.result['diff']['before'] = lb
        self.result['diff']['after'] = {}

        if not self.module.check_mode:
            self.api_query(
                path="/v1/loadbalancer/create",
                method="POST",
                data=data
            )
        return lb


def main():
    argument_spec = vultr_argument_spec()
    argument_spec.update({
        'name': {
            'required': True,
            'aliases': ['label'],
            'type': 'str',
        },
        'dcid': {
            'required': True,
            'type': 'int',
        },
        'config_ssl_redirect': {
            'type': 'bool',
        },
        'sticky_sessions': {
            'type': 'bool',
        },
        'cookie_name': {
            'type': 'str',
        },
        'balancing_algorithm': {
            'type': 'str',
            'choices': ['roundrobin', 'leastconn'],
        },
        'health_check': {
            'type': 'dict',
            'options': HEALTH_CHECK_SPEC,
        },
        'forwarding_rules': {
            'type': 'list',
            'elements': 'dict',
            'options': FORWARDING_RULE_SPEC,
        },
        'ssl_private_key': {
            'type': 'str',
        },
        'ssl_certificate': {
            'type': 'str',
        },
        'ssl_chain': {
            'type': 'str',
        },
        'state': {
            'choices': ['present', 'absent'],
            'default': 'present',
            'type': 'str',
        },
    })

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[],
        supports_check_mode=True,
    )

    vultr_lb = AnsibleVultrLoadBalancer(module)
    if module.params.get('state') == "absent":
        lb = vultr_lb.absent_lb()
    else:
        lb = vultr_lb.present_lb()

    result = vultr_lb.get_result(lb)
    module.exit_json(**result)


if __name__ == '__main__':
    main()
