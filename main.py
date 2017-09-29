#!/usr/bin/env python

import hashlib
import json
import logging
import models
import random
import urllib
import webapp2

from google.appengine.api import taskqueue
from google.appengine.ext import ndb
from google.appengine.ext import deferred

import apis


class HelloWorld(webapp2.RequestHandler):
  def get(self, **kwargs):
    if self.request.get('task_name', None) is None:
      self.response.out.write('''Swarming output.json:
      <form action='/'  method='POST'>
      <textarea name='json'></textarea>
      <input type='submit'>
      </form>
      ''')
      return
    archive_key = models.Archive.Key(self.request.get('task_name'))
    archive_entity = archive_key.get()
    if archive_entity.gcs_url:
      return webapp2.redirect(archive_entity.gcs_url.encode('utf-8'))
    else:
      self.response.out.write('Still Waiting') 

  def post(self):
    swarming_request = json.loads(self.request.get('json'))
    archive_key = models.Archive.Key(swarming_request['base_task_name'])

    @ndb.transactional
    def _():
      archive_entity = archive_key.get()
      if not archive_entity:
        archive_entity = models.Archive(
            key=archive_key,
            initial_request=swarming_request)
        archive_entity.put()

        # Insert all of the tasks as entities under our parent.
        for json_task_name, json_task in swarming_request['tasks'].iteritems():
          # The id for this key is auto generated (thus why we specify 0).
          task_key = ndb.Key(models.Task, 0, parent=archive_key)
          task = models.Task(
              key=task_key,
              task_id=json_task['task_id'],
              task_name=json_task_name)
          task.put()
        # Only poll the archive if this commit succeeds.
        deferred.defer(
            PollArchive, archive_key=archive_key,
            _transactional=True,
            _retry_options=taskqueue.TaskRetryOptions(
              max_backoff_seconds=6.0,
              min_backoff_seconds=3.0,
              task_age_limit=60*60,  # 1 hour
              ))
      return archive_entity
    archive_entity = _()
    return webapp2.redirect(
        '/?%s' % urllib.urlencode({'task_name': swarming_request['base_task_name']}))


def DoUploadToGCS(archive_entity):
  tasks = list(models.Task.TasksQuery(parent_key=archive_entity.key))
  if random.random() < 0.1:
    assert False, 'Oops, an error occurred'
  return 'http://localhost.localdomain/%s' % archive_entity.key.string_id()


def PollSingleTask(task_id):
  r = random.random()
  if r < 0.1:
    assert False, 'Oops, an error occurred'

  data = apis.swarming.task().result(task_id=task_id).execute()
  print json.dumps(data, sort_keys=True, indent=4)

def PollArchive(archive_key):
  @ndb.transactional
  def get_tasks_to_process():
    ret = []
    for task in models.Task.TasksQuery(parent_key=archive_key):
      if task.output_hash is None:
        # Still work to do
        ret.append(task)
    return ret
  tasks_to_process = get_tasks_to_process()

  @ndb.transactional
  def update_task_with_hash(task_key, new_hash):
    task = task_key.get()
    if task.output_hash is None:
      task.output_hash = new_hash
      task.put()
    elif task.output_hash != new_hash:
      logging.error('Found a conflicting hash for %r, was %r is now %r', task_key, task.hash, new_hash)

  all_finished = True
  for task in tasks_to_process:
    new_hash = PollSingleTask(task.task_id)
    if not new_hash:
      all_finished = False
      continue
    update_task_with_hash(task.key, new_hash)

  if not all_finished:
    assert False, 'Need to defer the task into the future to try again.'

  @ndb.transactional
  def _():
    archive_entity = archive_key.get()
    if archive_entity.polling_finished:
      return
    archive_entity.polling_finished = True
    archive_entity.put()
    deferred.defer(
        UploadToGCS, archive_key=archive_key,
        _transactional=True,
        _retry_options=taskqueue.TaskRetryOptions(
          max_backoff_seconds=60.0, min_backoff_seconds=30.0))
  _()

def UploadToGCS(archive_key):
  archive_entity = archive_key.get()
  if archive_entity.gcs_url:
    # We are already done, nothing to do here
    return
  # NOTE: It is possible that this function may be called twice simultaneously (so we need to handle that case)
  uploaded_location = DoUploadToGCS(archive_entity)

  @ndb.transactional
  def update_gcs_url(uploaded_location):
    archive_entity = archive_key.get()
    if archive_entity.gcs_url and archive_entity.gcs_url != uploaded_location:
      # Someone else already uploaded the blob. Delete our copy.
      return False
    archive_entity.gcs_url = uploaded_location
    archive_entity.put()
    return True
  if not update_gcs_url(uploaded_location):
    # Fixme: Delete our blob, it is a duplicate.
    pass

Application = webapp2.WSGIApplication(
  routes=[
    ('/', HelloWorld),
  ],
  debug=True)
