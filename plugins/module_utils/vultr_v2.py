# -*- coding: utf-8 -*-
# Copyright (c) 2021, René Moser <mail@renemoser.net>
# Simplified BSD License (see licenses/simplified_bsd.txt or https://opensource.org/licenses/BSD-2-Clause)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

import time
import random
from ansible.module_utils._text import to_text, to_native
from ansible.module_utils.urls import fetch_url

from ansible.module_utils.basic import env_fallback
from ansible.module_utils.urls import fetch_url
from ansible.module_utils._text import to_text


VULTR_USER_AGENT = 'Ansible Vultr v2'


def vultr_argument_spec():
    return dict(
          api_endpoint=dict(
            type='str',
            fallback=(env_fallback, ['VULTR_API_ENDPOINT']),
            default='https://api.vultr.com/v2',
        ),
        api_key=dict(
            type='str',
            fallback=(env_fallback, ['VULTR_API_KEY']),
            no_log=True,
            required=True,
        ),
        api_timeout=dict(
            type='int',
            fallback=(env_fallback, ['VULTR_API_TIMEOUT']),
            default=60,
        ),
        api_retries=dict(
            type='int',
            fallback=(env_fallback, ['VULTR_API_RETRIES']),
            default=5
        ),
        api_retry_max_delay=dict(
            type='int',
            fallback=(env_fallback, ['VULTR_API_RETRY_MAX_DELAY']),
            default=12,
        )
    )


class AnsibleVultr:

    def __init__(
        self,
        module,
        namespace,
        resource_path,
        ressource_result_key_singular,
        ressource_result_key_plural=None,
        resource_key_name="name",
        resource_create_param_keys=None,
        resource_update_param_keys=None,

        ):

        self.module = module
        self.namespace = namespace

        # The API resource path e.g ssh_key
        self.ressource_result_key_singular = ressource_result_key_singular

        # The API result data key e.g ssh_keys
        self.ressource_result_key_plural = ressource_result_key_plural or "%ss" % ressource_result_key_singular

        # The API resource path e.g /ssh-keys
        self.resource_path = resource_path

        # The name key of the resource, usually 'name'
        self.resource_key_name = resource_key_name

        # List of params used to create the resource
        self.resource_create_param_keys = resource_create_param_keys or ['name']

        # List of params used to update the resource
        self.resource_update_param_keys = resource_update_param_keys or ['name']

        self.result = {
            'changed': False,
            namespace: dict(),
            'diff': dict(before=dict(), after=dict()),
            'vultr_api': {
                'api_timeout': module.params['api_timeout'],
                'api_retries': module.params['api_retries'],
                'api_retry_max_delay': module.params['api_retry_max_delay'],
                'api_endpoint': module.params['api_endpoint'],
            },
        }

        self.headers = {
            'Authorization': "Bearer %s" % self.module.params['api_key'],
            'User-Agent': VULTR_USER_AGENT,
            'Accept': 'application/json',
        }

    def api_query(self, path, method="GET", data=None):

        retry_max_delay = self.module.params['api_retry_max_delay']
        randomness = random.randint(0, 1000) / 1000.0

        for retry in range(0, self.module.params['api_retries']):
            resp, info = fetch_url(
                self.module,
                self.module.params['api_endpoint'] + path,
                method=method,
                data=self.module.jsonify(data),
                headers=self.headers,
                timeout=self.module.params['api_timeout'],
            )

            # 429 Too Many Requests
            if info['status'] != 429:
                break

            # Vultr has a rate limiting requests per second, try to be polite
            # Use exponential backoff plus a little bit of randomness
            delay = 2 ** retry + randomness
            if delay > retry_max_delay:
                delay = retry_max_delay + randomness
            time.sleep(delay)

        # Success with content
        if info['status'] in (200, 201):
            return self.module.from_json(to_text(resp.read(), errors='surrogate_or_strict'))

        # Success without content
        if info['status'] in (404, 204):
            return None

        self.module.fail_json(
            msg='Failure while calling the Vultr API v2 with %s for "%s".' % (method, path),
            fetch_url_info=info
        )

    def query(self):
        resources = self.api_query(path=self.resource_path)
        if resources:
            for resource in resources[self.ressource_result_key_plural]:
                if resource.get(self.resource_key_name) == self.module.params.get(self.resource_key_name):
                    return resource
        return dict()

    def present(self):
        resource = self.query()
        if not resource:
            self.create()
        else:
            self.update(resource)

    def create(self):
        data = dict()
        for param in self.resource_create_param_keys:
            data[param] = self.module.params.get(param)

        self.result['changed'] = True
        resource = dict()

        self.result['diff']['before'] = dict()
        self.result['diff']['after'] = data

        if not self.module.check_mode:
            resource = self.api_query(
                path=self.resource_path,
                method="POST",
                data=data,
            )
        return self.get_result(resource.get(self.ressource_result_key_singular) if resource else dict())

    def is_diff(self, data, resource):
        for key, value in data.items():
            if value is not None:
                if not resource.get(key) or resource.get(key) != value:
                    return True
        return False

    def update(self, resource):
        data = dict()
        for param in self.resource_update_param_keys:
            data[param] = self.module.params.get(param)

        if self.is_diff(data, resource):
            self.result['changed'] = True

            self.result['diff']['before'] = dict(**resource)
            self.result['diff']['after'] = dict(**resource)
            self.result['diff']['after'].update(data)

            if not self.module.check_mode:
                self.api_query(
                    path="%s/%s" % (self.resource_path, resource['id']),
                    method="PATCH",
                    data=data,
                )
                # TODO: query by ID
                resource = self.query()

        return self.get_result(resource)

    def absent(self):
        resource = self.query()
        if resource:
            self.result['changed'] = True

            self.result['diff']['before'] = dict(**resource)
            self.result['diff']['after'] = dict()

            if not self.module.check_mode:
                self.api_query(
                    path="%s/%s" % (self.resource_path, resource['id']),
                    method="DELETE",
                )
        return self.get_result(resource)

    def get_result(self, resource):
        self.result[self.namespace] = resource
        self.module.exit_json(**self.result)
