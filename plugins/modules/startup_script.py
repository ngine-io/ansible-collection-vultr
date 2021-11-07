#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (c) 2021, René Moser <mail@renemoser.net>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


DOCUMENTATION = '''
---
module: startup_script
short_description: Manages startup scripts on Vultr.
description:
  - Create, update and remove startup scripts.
version_added: "2.0.0"
author: "René Moser (@resmo)"
options:
  name:
    description:
      - The script name.
    required: true
    type: str
  type:
    description:
      - The script type, can not be changed once created.
    default: boot
    choices: [ boot, pxe ]
    aliases: [ script_type ]
    type: str
  script:
    description:
      - The script source code.
      - Required if I(state=present).
    type: str
  state:
    description:
      - State of the script.
    default: present
    choices: [ present, absent ]
    type: str
extends_documentation_fragment:
- ngine_io.vultr.vultr_v2
'''

EXAMPLES = '''
- name: ensure a pxe script exists, source from a file
  ngine_io.vultr.startup_script:
    name: my_web_script
    script_type: pxe
    script: "{{ lookup('file', 'path/to/script') }}"

- name: ensure a boot script exists
  ngine_io.vultr.startup_script:
    name: vultr_startup_script
    script: "#!/bin/bash\necho Hello World > /root/hello"

- name: ensure a script is absent
  ngine_io.vultr.startup_script:
    name: my_web_script
    state: absent
'''

RETURN = '''
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
      sample: "https://api.vultr.com/v2"
vultr_startup_script:
  description: Response from Vultr API
  returned: success
  type: complex
  contains:
    id:
      description: ID of the startup script.
      returned: success
      type: str
      sample: 249395
    name:
      description: Name of the startup script.
      returned: success
      type: str
      sample: my startup script
    script:
      description: The source code of the startup script.
      returned: success
      type: str
      sample: "#!/bin/bash\necho Hello World > /root/hello"
    type:
      description: The type of the startup script.
      returned: success
      type: str
      sample: pxe
    date_created:
      description: Date the startup script was created.
      returned: success
      type: str
      sample: 2020-10-10T01:56:20+00:00
    date_modified:
      description: Date the startup script was modified.
      returned: success
      type: str
      sample: 2020-10-10T01:56:20+00:00
'''

import base64
from ansible.module_utils.basic import AnsibleModule
from ..module_utils.vultr_v2 import (
    AnsibleVultr,
    vultr_argument_spec,
)

class AnsibleVultrStartupScript(AnsibleVultr):

  def query(self, resource_id=None):
      resource = super(AnsibleVultrStartupScript, self).query(resource_id=resource_id)
      if resource and 'script' not in resource:
          resource = super(AnsibleVultrStartupScript, self).query(resource_id=resource['id'])
      return resource

  def get_result(self, resource):
      if resource:
          resource['script'] = base64.b64decode(resource['script']).decode()
      self.result[self.namespace] = resource
      self.module.exit_json(**self.result)


def main():
    argument_spec = vultr_argument_spec()
    argument_spec.update(dict(
        name=dict(type='str', required=True),
        script=dict(type='str',),
        type=dict(type='str', default='boot', choices=['boot', 'pxe'], aliases=['script_type']),
        state=dict(type='str', choices=['present', 'absent'], default='present'),
    ))

    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ('state', 'present', ['script']),
        ],
        supports_check_mode=True,
    )

    vultr = AnsibleVultrStartupScript(
          module=module,
          namespace="vultr_startup_script",
          resource_path = "/startup-scripts",
          ressource_result_key_singular="startup_script",
          resource_create_param_keys=['name', 'type', 'script'],
          resource_update_param_keys=['name', 'script'],
      )

    if module.params.get('state') == "absent":
        vultr.absent()
    else:
        module.params['script'] = base64.b64encode(module.params['script'].encode())
        vultr.present()

if __name__ == '__main__':
    main()
