# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2013, 2014 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from copy import copy
from datetime import timedelta
import os
import json

from eve.utils import config
from eve.versioning import versioned_id_field
from apps.publish.archive_publish import ArchivePublishService

from apps.validators import ValidatorsPopulateCommand
from superdesk.tests import TestCase
from apps.publish import init_app, publish_queue, RemoveExpiredPublishContent
from apps.legal_archive import LEGAL_ARCHIVE_NAME, LEGAL_ARCHIVE_VERSIONS_NAME, LEGAL_PUBLISH_QUEUE_NAME
from superdesk.utc import utcnow
from superdesk import get_resource_service
import superdesk
from apps.archive.archive import SOURCE as ARCHIVE


class ArchivePublishTestCase(TestCase):
    def init_data(self):
        self.subscribers = [{"_id": "1", "name": "sub1", "is_active": True, "can_send_takes_packages": False,
                             "media_type": "media", "sequence_num_settings": {"max": 10, "min": 1},
                             "destinations": [{"name": "dest1", "format": "nitf",
                                               "delivery_type": "ftp",
                                               "config": {"address": "127.0.0.1", "username": "test"}
                                               }]
                             },
                            {"_id": "2", "name": "sub2", "is_active": True, "can_send_takes_packages": False,
                             "media_type": "media", "sequence_num_settings": {"max": 10, "min": 1},
                             "destinations": [{"name": "dest2", "format": "AAP ANPA", "delivery_type": "filecopy",
                                               "config": {"address": "/share/copy"}
                                               },
                                              {"name": "dest3", "format": "AAP ANPA", "delivery_type": "Email",
                                               "config": {"recipients": "test@sourcefabric.org"}
                                               }]
                             },
                            {"_id": "3", "name": "sub3", "is_active": True, "can_send_takes_packages": True,
                             "media_type": "media", "sequence_num_settings": {"max": 10, "min": 1},
                             "destinations": [{"name": "dest1", "format": "nitf",
                                               "delivery_type": "ftp",
                                               "config": {"address": "127.0.0.1", "username": "test"}
                                               }]
                             }]

        self.articles = [{'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4f9',
                          '_id': '1',
                          'type': 'text',
                          'last_version': 3,
                          config.VERSION: 4,
                          'body_html': 'Test body',
                          'urgency': 4,
                          'headline': 'Two students missing',
                          'pubstatus': 'usable',
                          'firstcreated': utcnow(),
                          'byline': 'By Alan Karben',
                          'ednote': 'Andrew Marwood contributed to this article',
                          'dateline': 'Sydney',
                          'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                          'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                                      {'qcode': '04001002', 'name': 'Weather'}],
                          'state': 'published',
                          'expiry': utcnow() + timedelta(minutes=20),
                          'unique_name': '#1'},
                         {'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a974-xy4532fe33f9',
                          '_id': '2',
                          'last_version': 3,
                          config.VERSION: 4,
                          'body_html': 'Test body of the second article',
                          'urgency': 4,
                          'headline': 'Another two students missing',
                          'pubstatus': 'usable',
                          'firstcreated': utcnow(),
                          'byline': 'By Alan Karben',
                          'ednote': 'Andrew Marwood contributed to this article',
                          'dateline': 'Sydney',
                          'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                          'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                                      {'qcode': '04001002', 'name': 'Weather'}],
                          'expiry': utcnow() + timedelta(minutes=20),
                          'state': 'in_progress',
                          'publish_schedule': "2016-05-30T10:00:00+0000",
                          'type': 'text',
                          'unique_name': '#2'},
                         {'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4fa',
                          '_id': '3',
                          'last_version': 3,
                          config.VERSION: 4,
                          'body_html': 'Test body',
                          'urgency': 4,
                          'headline': 'Two students missing killed',
                          'pubstatus': 'usable',
                          'firstcreated': utcnow(),
                          'byline': 'By Alan Karben',
                          'ednote': 'Andrew Marwood contributed to this article killed',
                          'dateline': 'Sydney',
                          'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                          'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                                      {'qcode': '04001002', 'name': 'Weather'}],
                          'state': 'killed',
                          'expiry': utcnow() + timedelta(minutes=20),
                          'type': 'text',
                          'unique_name': '#3'},
                         {'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4fb',
                          '_id': '4',
                          'last_version': 3,
                          config.VERSION: 4,
                          'body_html': 'Take-1 body',
                          'urgency': 4,
                          'headline': 'Take-1 headline',
                          'abstract': 'Abstract for take-1',
                          'anpa-category': {'qcode': 'A', 'name': 'Sport'},
                          'pubstatus': 'done',
                          'firstcreated': utcnow(),
                          'byline': 'By Alan Karben',
                          'dateline': 'Sydney',
                          'slugline': 'taking takes',
                          'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                          'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                                      {'qcode': '04001002', 'name': 'Weather'}],
                          'state': 'in_progress',
                          'expiry': utcnow() + timedelta(minutes=20),
                          'type': 'text',
                          'unique_name': '#4'},
                         {'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4fg',
                          '_id': '5',
                          'last_version': 3,
                          config.VERSION: 4,
                          'body_html': 'Take-2 body',
                          'urgency': 4,
                          'headline': 'Take-2 headline',
                          'abstract': 'Abstract for take-1',
                          'anpa-category': {'qcode': 'A', 'name': 'Sport'},
                          'pubstatus': 'done',
                          'firstcreated': utcnow(),
                          'byline': 'By Alan Karben',
                          'dateline': 'Sydney',
                          'slugline': 'taking takes',
                          'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                          'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                                      {'qcode': '04001002', 'name': 'Weather'}],
                          'state': 'published',
                          'expiry': utcnow() + timedelta(minutes=20),
                          'type': 'text',
                          'unique_name': '#5'},
                         {'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4fc',
                          '_id': '6',
                          'last_version': 2,
                          config.VERSION: 3,
                          'type': 'composite',
                          'groups': [{'id': 'root', 'refs': [{'idRef': 'main'}], 'role': 'grpRole:NEP'},
                                     {
                                         'id': 'main',
                                         'refs': [
                                             {
                                                 'location': 'archive',
                                                 'guid': '5',
                                                 'type': 'text'
                                             },
                                             {
                                                 'location': 'archive',
                                                 'guid': '4',
                                                 'type': 'text'
                                             }
                                         ],
                                         'role': 'grpRole:main'}],
                          'firstcreated': utcnow(),
                          'expiry': utcnow() + timedelta(minutes=20),
                          'unique_name': '#6'},
                         {'guid': 'tag:localhost:2015:ab-69b961-2816-4b8a-a584-a7b402fed4fc',
                          '_id': '7',
                          'last_version': 2,
                          config.VERSION: 3,
                          'type': 'composite',
                          'package_type': 'takes',
                          'groups': [{'id': 'root', 'refs': [{'idRef': 'main'}], 'role': 'grpRole:NEP'},
                                     {
                                         'id': 'main',
                                         'refs': [
                                             {
                                                 'location': 'archive',
                                                 'guid': '5',
                                                 'sequence': 1,
                                                 'type': 'text'
                                             },
                                             {
                                                 'location': 'archive',
                                                 'guid': '4',
                                                 'sequence': 2,
                                                 'type': 'text'
                                             }
                                         ],
                                         'role': 'grpRole:main'}],
                          'firstcreated': utcnow(),
                          'expiry': utcnow() + timedelta(minutes=20),
                          'sequence': 2,
                          'unique_name': '#7'},
                         {'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4fb',
                          '_id': '8',
                          'last_version': 3,
                          config.VERSION: 4,
                          'body_html': 'Take-1 body',
                          'urgency': 4,
                          'headline': 'Take-1 headline',
                          'abstract': 'Abstract for take-1',
                          'anpa-category': {'qcode': 'A', 'name': 'Sport'},
                          'pubstatus': 'done',
                          'firstcreated': utcnow(),
                          'byline': 'By Alan Karben',
                          'dateline': 'Sydney',
                          'slugline': 'taking takes',
                          'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                          'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                                      {'qcode': '04001002', 'name': 'Weather'}],
                          'state': 'in_progress',
                          'expiry': utcnow() + timedelta(minutes=20),
                          'type': 'text',
                          'unique_name': '#8'},
                         {'_id': '7', 'urgency': 3, 'headline': 'creator', 'state': 'fetched'}]

    def setUp(self):
        super().setUp()
        with self.app.app_context():
            self.init_data()

            self.app.data.insert('subscribers', self.subscribers)
            self.app.data.insert('archive', self.articles)

            self.filename = os.path.join(os.path.abspath(os.path.dirname(__file__)), "validators.json")
            self.json_data = [
                {"_id": "kill_text", "act": "kill", "type": "text", "schema": {"headline": {"type": "string"}}},
                {"_id": "publish_text", "act": "publish", "type": "text", "schema": {}}]
            self.article_versions = self.__init_article_versions()

            with open(self.filename, "w+") as file:
                json.dump(self.json_data, file)
            init_app(self.app)

    def tearDown(self):
        super().tearDown()
        if self.filename and os.path.exists(self.filename):
            os.remove(self.filename)

    def __init_article_versions(self):
        return [{'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4f9',
                 versioned_id_field(): '8',
                 'type': 'text',
                 config.VERSION: 1,
                 'urgency': 4,
                 'pubstatus': 'usable',
                 'firstcreated': utcnow(),
                 'byline': 'By Alan Karben',
                 'dateline': 'Sydney',
                 'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                 'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                             {'qcode': '04001002', 'name': 'Weather'}],
                 'state': 'draft',
                 'expiry': utcnow() + timedelta(minutes=20),
                 'unique_name': '#8'},
                {'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4f9',
                 versioned_id_field(): '8',
                 'type': 'text',
                 config.VERSION: 2,
                 'urgency': 4,
                 'headline': 'Two students missing',
                 'pubstatus': 'usable',
                 'firstcreated': utcnow(),
                 'byline': 'By Alan Karben',
                 'dateline': 'Sydney',
                 'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                 'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                             {'qcode': '04001002', 'name': 'Weather'}],
                 'state': 'submitted',
                 'expiry': utcnow() + timedelta(minutes=20),
                 'unique_name': '#8'},
                {'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4f9',
                 versioned_id_field(): '8',
                 'type': 'text',
                 config.VERSION: 3,
                 'urgency': 4,
                 'headline': 'Two students missing',
                 'pubstatus': 'usable',
                 'firstcreated': utcnow(),
                 'byline': 'By Alan Karben',
                 'ednote': 'Andrew Marwood contributed to this article',
                 'dateline': 'Sydney',
                 'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                 'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                             {'qcode': '04001002', 'name': 'Weather'}],
                 'state': 'in_progress',
                 'expiry': utcnow() + timedelta(minutes=20),
                 'unique_name': '#8'},
                {'guid': 'tag:localhost:2015:69b961ab-2816-4b8a-a584-a7b402fed4f9',
                 versioned_id_field(): '8',
                 'type': 'text',
                 config.VERSION: 4,
                 'body_html': 'Test body',
                 'urgency': 4,
                 'headline': 'Two students missing',
                 'pubstatus': 'usable',
                 'firstcreated': utcnow(),
                 'byline': 'By Alan Karben',
                 'ednote': 'Andrew Marwood contributed to this article',
                 'dateline': 'Sydney',
                 'keywords': ['Student', 'Crime', 'Police', 'Missing'],
                 'subject': [{'qcode': '17004000', 'name': 'Statistics'},
                             {'qcode': '04001002', 'name': 'Weather'}],
                 'state': 'in_progress',
                 'expiry': utcnow() + timedelta(minutes=20),
                 'unique_name': '#8'}]

    def _get_legal_archive_details(self, article_id, publishing_action=None):
        archive_service = get_resource_service(LEGAL_ARCHIVE_NAME)
        archive_versions_service = get_resource_service(LEGAL_ARCHIVE_VERSIONS_NAME)
        publish_queue_service = get_resource_service(LEGAL_PUBLISH_QUEUE_NAME)

        article = archive_service.find_one(_id=article_id, req=None)
        article_versions = archive_versions_service.get(req=None, lookup={versioned_id_field(): article_id})

        lookup = {'item_id': article_id, 'publishing_action': publishing_action} if publishing_action else \
            {'item_id': article_id}
        queue_items = publish_queue_service.get(req=None, lookup=lookup)

        return article, article_versions, queue_items

    def test_publish(self):
        with self.app.app_context():
            ValidatorsPopulateCommand().run(self.filename)
            doc = self.articles[3].copy()

            get_resource_service('archive_publish').patch(id=doc['_id'], updates={'state': 'published'})
            published_doc = get_resource_service('archive').find_one(req=None, _id=doc['_id'])
            self.assertIsNotNone(published_doc)
            self.assertEquals(published_doc[config.VERSION], doc[config.VERSION] + 1)
            self.assertEquals(published_doc[config.CONTENT_STATE], ArchivePublishService().published_state)

    def test_queue_transmission(self):
        with self.app.app_context():
            queue_items = self.app.data.find('publish_queue', None, None)
            self.assertEquals(0, queue_items.count())

            doc = copy(self.articles[0])
            get_resource_service('archive_publish').queue_transmission(doc)
            queue_items = self.app.data.find('publish_queue', None, None)
            self.assertEquals(4, queue_items.count())

    def test_queue_transmission_wrong_article_type_fails(self):
        with self.app.app_context():
            queue_items = self.app.data.find('publish_queue', None, None)
            self.assertEquals(0, queue_items.count())

            doc = copy(self.articles[0])
            doc['type'] = 'image'
            no_formatters, queued = get_resource_service('archive_publish').queue_transmission(doc)

            queue_items = self.app.data.find('publish_queue', None, None)
            self.assertEquals(0, queue_items.count())
            self.assertEquals(4, len(no_formatters))
            self.assertFalse(queued)

    def test_queue_transmission_for_scheduled_publish(self):
        with self.app.app_context():
            queue_items = self.app.data.find('publish_queue', None, None)
            self.assertEquals(0, queue_items.count())

            doc = copy(self.articles[1])
            get_resource_service('archive_publish').queue_transmission(doc)

            queue_items = self.app.data.find('publish_queue', None, None)
            self.assertEquals(4, queue_items.count())
            self.assertEquals("2016-05-30T10:00:00+0000", queue_items[0]["publish_schedule"])
            self.assertEquals("2016-05-30T10:00:00+0000", queue_items[1]["publish_schedule"])
            self.assertEquals("2016-05-30T10:00:00+0000", queue_items[2]["publish_schedule"])
            self.assertEquals("2016-05-30T10:00:00+0000", queue_items[3]["publish_schedule"])

    def test_queue_transmission_for_digital_channels(self):
        with self.app.app_context():
            queue_items = self.app.data.find('publish_queue', None, None)
            self.assertEquals(0, queue_items.count())

            doc = copy(self.articles[1])
            get_resource_service('archive_publish').queue_transmission(doc, 'digital')
            queue_items = self.app.data.find('publish_queue', None, None)
            self.assertEquals(1, queue_items.count())
            self.assertEquals('3', queue_items[0]["subscriber_id"])

    def test_queue_transmission_for_wire_channels(self):
        with self.app.app_context():
            queue_items = self.app.data.find('publish_queue', None, None)
            self.assertEquals(0, queue_items.count())

            doc = copy(self.articles[1])
            get_resource_service('archive_publish').queue_transmission(doc, 'wire')
            queue_items = self.app.data.find('publish_queue', None, None)
            self.assertEquals(3, queue_items.count())
            expected_subscribers = ['1', '2']
            self.assertIn(queue_items[0]["subscriber_id"], expected_subscribers)
            self.assertIn(queue_items[1]["subscriber_id"], expected_subscribers)
            self.assertIn(queue_items[2]["subscriber_id"], expected_subscribers)

    def test_delete_from_queue_by_article_id(self):
        with self.app.app_context():
            queue_items = self.app.data.find('publish_queue', None, None)
            self.assertEquals(0, queue_items.count())

            doc = copy(self.articles[1])
            get_resource_service('archive_publish').queue_transmission(doc)
            queue_items = self.app.data.find('publish_queue', None, None)
            self.assertEquals(4, queue_items.count())

            publish_queue.PublishQueueService('publish_queue', superdesk.get_backend()).delete_by_article_id(doc['_id'])
            queue_items = self.app.data.find('publish_queue', None, None)
            self.assertEquals(0, queue_items.count())

    def test_remove_published_expired_content(self):
        with self.app.app_context():
            self.app.data.insert('archive_versions', self.article_versions)

            published_service = get_resource_service('published')
            text_archive = get_resource_service('text_archive')

            original = self.articles[0].copy()
            get_resource_service('archive_publish').queue_transmission(original)

            original[config.VERSION] += 1
            published_service.post([original])

            published_items = published_service.get_other_published_items(original['item_id'])
            self.assertEquals(1, published_items.count())

            published_service.update_published_items(original['item_id'], 'expiry', utcnow() + timedelta(minutes=-60))
            RemoveExpiredPublishContent().run()
            published_items = published_service.get_other_published_items(str(original['item_id']))
            self.assertEquals(0, published_items.count())

            item = text_archive.find_one(req=None, _id=str(original['_id']))
            self.assertEquals(item['item_id'], self.articles[0]['_id'])

            article_in_legal_archive, article_versions_in_legal_archive, queue_items = \
                self._get_legal_archive_details(original['item_id'])

            self.assertIsNotNone(article_in_legal_archive, 'Article cannot be none in Legal Archive')

            self.assertGreaterEqual(queue_items.count(), 1, 'Publish Queue Items must be greater than or equal to 1')
            for queue_item in queue_items:
                self.assertEquals(queue_item['item_id'], self.articles[0]['_id'])
                self.assertEquals(queue_item['item_version'], original[config.VERSION])

    def test_cannot_remove_scheduled_content(self):
        with self.app.app_context():
            published_service = get_resource_service('published')
            original = self.articles[1].copy()
            original[config.CONTENT_STATE] = 'scheduled'

            published_service.post([original])
            published_items = published_service.get_other_published_items(original['item_id'])
            self.assertEquals(1, published_items.count())

            RemoveExpiredPublishContent().run()
            published_items = published_service.get_other_published_items(original['item_id'])
            self.assertEquals(1, published_items.count())

    def test_remove_killed_expired_content(self):
        with self.app.app_context():
            published_service = get_resource_service('published')
            text_archive = get_resource_service('text_archive')

            original = self.articles[2].copy()

            get_resource_service('archive_publish').queue_transmission(original)

            original[config.VERSION] += 1
            published_service.post([original])

            published_items = published_service.get_other_published_items(original['item_id'])
            self.assertEquals(1, published_items.count())

            published_service.update_published_items(original['item_id'], 'expiry', utcnow() + timedelta(minutes=-60))

            RemoveExpiredPublishContent().run()
            published_items = published_service.get_other_published_items(str(original['item_id']))
            self.assertEquals(0, published_items.count())

            item = text_archive.find_one(req=None, _id=str(original['_id']))
            self.assertIsNone(item)

    def test_remove_published_and_killed_expired_content(self):
        with self.app.app_context():
            published_service = get_resource_service('published')
            text_archive = get_resource_service('text_archive')

            published = self.articles[2].copy()
            published[config.CONTENT_STATE] = 'published'

            get_resource_service('archive_publish').queue_transmission(published)
            published[config.VERSION] += 1
            published_service.post([published])

            published_items = published_service.get_other_published_items(published['item_id'])
            self.assertEquals(1, published_items.count())

            killed = self.articles[2].copy()
            killed[config.VERSION] += 1
            get_resource_service('archive_publish').queue_transmission(killed)
            killed[config.VERSION] += 1
            published_service.post([killed])

            published_items = published_service.get_other_published_items(published['item_id'])
            self.assertEquals(2, published_items.count())

            published_service.update_published_items(killed['item_id'], 'expiry', utcnow() + timedelta(minutes=-60))
            RemoveExpiredPublishContent().run()

            published_items = published_service.get_other_published_items(killed['item_id'])
            self.assertEquals(0, published_items.count())

            articles_in_text_archive = text_archive.get(req=None, lookup={'item_id': self.articles[2]['_id']})
            self.assertEquals(articles_in_text_archive.count(), 0)

    def test_remove_published_and_killed_content_separately(self):
        cmd = ValidatorsPopulateCommand()

        with self.app.app_context():
            cmd.run(self.filename)
            self.app.data.insert('archive_versions', self.article_versions)

            published_service = get_resource_service('published')
            text_archive = get_resource_service('text_archive')

            # Publishing an Article
            doc = self.articles[7]
            original = doc.copy()
            get_resource_service('archive_publish').patch(id=doc['_id'], updates={config.CONTENT_STATE: 'published'})

            published_items = published_service.get_other_published_items(original[config.ID_FIELD])
            self.assertEquals(1, published_items.count())

            # Setting the expiry date of the published article to 1 hr back from now
            published_service.update_published_items(
                original[config.ID_FIELD], 'expiry', utcnow() + timedelta(minutes=-60))

            # Killing the published article and manually inserting the version of the article as unittests use
            # service directly
            get_resource_service('archive_kill').patch(id=doc['_id'], updates={config.CONTENT_STATE: 'killed'})

            # Executing the Expiry Job for the Published Article and asserting the collections
            RemoveExpiredPublishContent().run()

            articles_in_text_archive = text_archive.get(req=None, lookup={'item_id': original[config.ID_FIELD]})
            self.assertEquals(articles_in_text_archive.count(), 0)

            published_items = published_service.get_other_published_items(str(original[config.ID_FIELD]))
            self.assertEquals(1, published_items.count())

            article_in_production = get_resource_service(ARCHIVE).find_one(req=None, _id=original[config.ID_FIELD])
            self.assertIsNotNone(article_in_production)
            self.assertEquals(article_in_production['state'], 'killed')
            self.assertEquals(article_in_production[config.VERSION], original[config.VERSION] + 2)

            # Validate the collections in Legal Archive
            article_in_legal_archive, article_versions_in_legal_archive, queue_items = \
                self._get_legal_archive_details(original[config.ID_FIELD])

            self.assertIsNotNone(article_in_legal_archive, 'Article cannot be none in Legal Archive')
            self.assertEquals(article_in_legal_archive['state'], 'published')

            self.assertIsNotNone(article_versions_in_legal_archive, 'Article Versions cannot be none in Legal Archive')
            self.assertEquals(article_versions_in_legal_archive.count(), 5)

            self.assertGreaterEqual(queue_items.count(), 1, 'Publish Queue Items must be greater than or equal to 1')

            # Setting the expiry date of the killed article to 1 hr back from now and running the job again
            published_service.update_published_items(
                original[config.ID_FIELD], 'expiry', utcnow() + timedelta(minutes=-60))
            RemoveExpiredPublishContent().run()

            articles_in_text_archive = text_archive.get(req=None, lookup={'item_id': original[config.ID_FIELD]})
            self.assertEquals(articles_in_text_archive.count(), 0)

            published_items = published_service.get_other_published_items(str(original[config.ID_FIELD]))
            self.assertEquals(0, published_items.count())

            article_in_production = get_resource_service(ARCHIVE).find_one(req=None, _id=original[config.ID_FIELD])
            self.assertIsNone(article_in_production)

            # Validate the collections in Legal Archive
            article_in_legal_archive, article_versions_in_legal_archive, queue_items = \
                self._get_legal_archive_details(original[config.ID_FIELD], publishing_action='killed')

            self.assertIsNotNone(article_in_legal_archive, 'Article cannot be none in Legal Archive')
            self.assertEquals(article_in_legal_archive['state'], 'killed')

            self.assertIsNotNone(article_versions_in_legal_archive, 'Article Versions cannot be none in Legal Archive')
            self.assertEquals(article_versions_in_legal_archive.count(), 6)

            for queue_item in queue_items:
                self.assertEquals(queue_item['item_id'], original[config.ID_FIELD])
                self.assertEquals(queue_item['item_version'], original[config.VERSION] + 2)

            self.assertGreaterEqual(queue_items.count(), 1, 'Publish Queue Items must be greater than or equal to 1')

    def test_processing_very_first_take(self):
        with self.app.app_context():
            doc = self.articles[4].copy()
            original_package, updated_package = get_resource_service('archive_publish').process_takes(
                doc, self.articles[6]['_id'], doc)

            self.assertIsNotNone(original_package)
            self.assertIsNotNone(updated_package)
            self.assertEqual(updated_package['body_html'], 'Take-2 body<br>')
            self.assertEqual(updated_package['headline'], 'Take-2 headline')

    def test_processing_second_take_where_first_take_published(self):
        with self.app.app_context():
            doc = self.articles[3].copy()
            original_package, updated_package = get_resource_service('archive_publish').process_takes(
                doc, self.articles[6]['_id'], doc)

            self.assertIsNotNone(original_package)
            self.assertIsNotNone(updated_package)
            self.assertEqual(updated_package['body_html'], 'Take-2 body<br>Take-1 body<br>')
            self.assertEqual(updated_package['headline'], 'Take-1 headline')

def test_can_publish_article(self):
        with self.app.app_context():
            self.subscribers[0]['publish_filter'] = {'filter_id': 1, 'filter_type': 'blocking'}
            self.app.data.insert('filter_conditions',
                                 [{'_id': 1,
                                   'field': 'headline',
                                   'operator': 'like',
                                   'value': 'tor',
                                   'name': 'test-1'}])
            self.app.data.insert('filter_conditions',
                                 [{'_id': 2,
                                   'field': 'urgency',
                                   'operator': 'in',
                                   'value': 2,
                                   'name': 'test-2'}])
            self.app.data.insert('filter_conditions',
                                 [{'_id': 3,
                                   'field': 'headline',
                                   'operator': 'endswith',
                                   'value': 'tor',
                                   'name': 'test-3'}])
            self.app.data.insert('filter_conditions',
                                 [{'_id': 4,
                                   'field': 'urgency',
                                   'operator': 'in',
                                   'value': '2,3,4',
                                   'name': 'test-4'}])
            self.app.data.insert('publish_filters',
                                 [{'_id': 1,
                                   'publish_filter': [[{"fc": [4, 3]}], [{"fc": [1, 2]}]],
                                   'name': 'pf-1'}])
            can_it = get_resource_service('archive_publish').\
                can_publish(self.subscribers[0], self.articles[6])

            self.assertFalse(can_it)

            self.subscribers[0]['publish_filter']['filter_type'] = 'permitting'

            can_it = get_resource_service('archive_publish').\
                can_publish(self.subscribers[0], self.articles[6])

            self.assertTrue(can_it)

            self.subscribers[0].pop('publish_filter')
