import logging

import peewee

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(
    filename='log/model.log', level=logging.INFO, format=FORMAT)
# Suppress other logging.
for k in logging.Logger.manager.loggerDict:
    logging.getLogger(k).setLevel(logging.WARNING)

db = peewee.SqliteDatabase('data/followers.db')


class Follower(peewee.Model):

    # Required fields.
    uid = peewee.CharField(primary_key=True)
    state = peewee.FixedCharField(max_length=10)
    # Optional.
    weibo_count = peewee.IntegerField(null=True)
    follower_count = peewee.IntegerField(null=True)

    class Meta:
        database = db

    class State(object):
        NEW = 'new'  # Only has UID, no info populated.
        FILLED = 'filled'  # Info populated, but didn't go thorough analysis.
        DELETED = 'deleted'  # Already deleted.
        CLEAR = 'clear'  # Analyzed and decided to keep.

    @classmethod
    def save_uids(cls, uids):
        # type: (list[str]) -> None
        total_created = 0
        with db.atomic():
            for uid in uids:
                _, created = cls.create_or_get(uid=uid, state=cls.State.NEW)
                total_created += 1 if created else 0
        logging.info('Total created: %d' % total_created)
