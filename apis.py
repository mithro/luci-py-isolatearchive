# Copyright 2015 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Classes representing the monitoring interface for tasks or devices."""

import base64
import httplib2

from google.appengine.api import memcache
from oauth2client.contrib.appengine import AppAssertionCredentials

from apiclient import discovery

# Obtain service account credentials and authorize HTTP connection.
credentials = AppAssertionCredentials(
    scope='https://www.googleapis.com/auth/userinfo.email')
http = credentials.authorize(httplib2.Http(memcache))

def _get_swarming_api(server='chromium-swarm.appspot.com'):
  # Build a service object for interacting with the API.
  api_root = 'https://%s/_ah/api' % server
  api = 'swarming'
  version = 'v1'
  discovery_url = '%s/discovery/v1/apis/%s/%s/rest' % (api_root, api, version)
  return discovery.build(
      api, version, discoveryServiceUrl=discovery_url, http=http)

swarming = _get_swarming_api()

def _get_isolate_api(server='isolateserver.appspot.com'):
  # Build a service object for interacting with the API.
  api_root = 'https://%s/_ah/api' % server
  api = 'isolateservice'
  version = 'v1'
  discovery_url = '%s/discovery/v1/apis/%s/%s/rest' % (api_root, api, version)
  return discovery.build(
      api, version, discoveryServiceUrl=discovery_url, http=http)

def get_item(digest_hash, namespace="default-gzip"):
  if len(digest_hash) == 40:
    hash_algo = 'SHA-1'
  elif len(digest_hash) == 64:
    hash_algo = 'SHA-256'

  if namespace.endswith('-gzip') or namespace.endswith('-flate'):
    compression = 'flate'
  else:
    compression = ''

  obj = isolate.retrieve({
      "digest": digest_hash,
      "namespace": {
          "namespace": namespace,
          "compression": compression,
          "digest_hash": hash_algo,
      },
  })

  if obj.get('content', None):
    data = base64.b64decode(obj['content'])
    return data

  # Do something else?
  return None

isolate = _get_isolate_api()
