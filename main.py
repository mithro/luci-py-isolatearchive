#!/usr/bin/env python

import webapp2
import models
import json

from google.appengine.api import taskqueue
from google.appengine.ext import deferred


class HelloWorld(webapp2.RequestHandler):
  def get(self, **kwargs):
    self.response.out.write('Sup?') 

  def post(self):
    swarming_request = json.loads(self.request.get('json'))
    archive_key = models.Archive.Key(swarming_request['base_tast_name'])

    @ndb.transactional
    def _():
      archive_entity = archive_key.Get()
      if not archive_entity:
        archive_entity = models.Archive(
            key=archive_key,
            initial_request=swarming_request)
        archive_entity.put()
        deferred.defer(PollArchive, key=archive_key, _transactional=True)
      return archive_entity
    archive_entity = _()


  archive_entity = archive_key.Get()
  not_finished = []
  for task in archive_entity.tasks:
    task.hash = poll(task.url)

    @ndb.transactional
    def check_all_done():
      archive_entity_update = archive_key.Get()

      # Don't poll tasks already completed
      if archive_entity_update['task'].hash is not None:
        continue

      if not task.hash:
        not_finished.append(task.url)

      # Save the updated task state. If this fails, we'll just run again.
      archive_entity_update.put()

    return archive_entity if all_finished else None
  archive_entity = check_all_done()



def PollArchive(key):
  @ndb.transactional
  def check_all_done():
    archive_entity = archive_key.Get()

    all_finished = True
    for task in archive_entity.tasks:
      # Don't poll tasks already completed
      if task.completed:
        continue

      task.hash = poll(task.url)
      if not task.hash:
        all_finished = False

    # Save the updated task state. If this fails, we'll just run again.
    archive_entity.put()
    return archive_entity if all_finished else None
  archive_entity = check_all_done()
  if archive_entity is not None:
    assert False, 'Not finished'

  if archive_entity.gcs_url:
    # We are already done, nothing to do here
    return

  uploaded_location = upload_to_gcs(archive_entity)

  @ndb.transactional
  def update_gcs_url(uploaded_location):
    archive_entity = archive_key.Get()
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
