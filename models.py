import hashlib

from google.appengine.ext import ndb

class Task(ndb.Model):
  task_id = ndb.TextProperty()
  task_name = ndb.TextProperty()
  url = ndb.TextProperty()
  hash = ndb.BlobProperty()
  
  @classmethod
  def TasksQuery(cls, parent_key):
    return cls.query(ancestor=parent_key)


class Archive(ndb.Model):
  gcs_url = ndb.TextProperty()
  polling_finished = ndb.BooleanProperty()
  created_date = ndb.DateTimeProperty(auto_now_add=True)
  last_updated_date = ndb.DateTimeProperty(auto_now=True)

  initial_request = ndb.JsonProperty()

  @classmethod
  def Key(cls, archive_key):
    return ndb.Key(cls, hashlib.sha256(archive_key).hexdigest())
