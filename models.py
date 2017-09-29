from google.appengine.ext import ndb

class Task(ndb.Model):
  url = ndb.TextProperty()
  hash = ndb.BlobProperty()


class Archive(ndb.Model):
  tasks = ndb.LocalStructuredProperty(Isolates, repeated=True)
  gcs_url = ndb.TextProperty()
  created_date = ndb.DateTimeProperty(auto_now_add=True)
  last_updated_date = ndb.DateTimeProperty(auto_now=True)

  initial_request = ndb.JsonProperty()

  @classmethod
  def Key(cls, archive_key):
    return ndb.Key(cls, hashlib.sha256(archive_key).hexdigest())
