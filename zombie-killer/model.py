import logging

import peewee

FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(
    filename='log/zombie-killer.log', level=logging.INFO, format=FORMAT)
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

    @classmethod
    def save_follower_info(cls, info_list):
        # type: (list[{uid, weibo_count, follower_count}]) -> None
        total_created, total_updated = 0, 0
        with db.atomic():
            for uid, weibo_count, follower_count in info_list:
                f, created = cls.get_or_create(uid=uid)
                if created:
                    total_created += 1
                else:
                    total_updated += 1
                f.state = cls.State.FILLED
                f.weibo_count = weibo_count
                f.follower_count = follower_count
                f.save()
        logging.info(
            'Total created: %d, total updated: %d' %
            (total_created, total_updated))

    @classmethod
    def get_unfilled_uids(cls):
        rows = cls.select(cls.uid).where(cls.state == cls.State.NEW)
        return [row.uid for row in rows]
