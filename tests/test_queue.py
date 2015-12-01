﻿# coding: utf-8

#-------------------------------------------------------------------------
# Copyright (c) Microsoft.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#--------------------------------------------------------------------------
import unittest
from datetime import datetime, timedelta
from azure.storage import AccessPolicy
from azure.storage.queue import (
    QueueService,
    QueueSharedAccessPermissions,
    QueueMessageFormat,
)
from azure.common import (
    AzureHttpError,
    AzureConflictHttpError,
    AzureMissingResourceHttpError,
)
from tests.common_recordingtestcase import (
    TestMode,
    record,
)
from tests.testcase import StorageTestCase

#------------------------------------------------------------------------------
TEST_QUEUE_PREFIX = 'mytestqueue'
#------------------------------------------------------------------------------


class StorageQueueTest(StorageTestCase):

    def setUp(self):
        super(StorageQueueTest, self).setUp()

        self.qs = self._create_storage_service(QueueService, self.settings)

        self.test_queues = []

    def tearDown(self):
        if not self.is_playback():
            for queue_name in self.test_queues:
                try:
                    self.qs.delete_queue(queue_name)
                except:
                    pass
        return super(StorageQueueTest, self).tearDown()

    def _get_queue_reference(self):
        queue_name = self.get_resource_name(TEST_QUEUE_PREFIX + str(len(self.test_queues)))
        self.test_queues.append(queue_name)
        return queue_name

    def _create_queue(self):
        queue_name = self._get_queue_reference()
        self.qs.create_queue(queue_name)
        return queue_name

    @record
    def test_create_queue_service_empty_key(self):
        try:
            queue_service = QueueService('testaccount', '')
            self.fail('Passing an empty key to create account should fail.')
        except ValueError as e:
            self.assertTrue(str(e) == 'You need to provide an account name and account key when creating a storage service')

    @record
    def test_create_queue(self):
        # Action
        queue_name = self._get_queue_reference()
        self.qs.create_queue(queue_name)
        result = self.qs.get_queue_metadata(queue_name)
        self.qs.delete_queue(queue_name)

        # Asserts
        self.assertIsNotNone(result)
        self.assertEqual(result['x-ms-approximate-messages-count'], '0')

    @record
    def test_create_queue_already_exist(self):
        # Action
        queue_name = self._get_queue_reference()
        created1 = self.qs.create_queue(queue_name)
        created2 = self.qs.create_queue(queue_name)

        # Asserts
        self.assertTrue(created1)
        self.assertFalse(created2)

    @record
    def test_create_queue_fail_on_exist(self):
        # Action
        queue_name = self._get_queue_reference()
        created = self.qs.create_queue(queue_name, None, True)
        with self.assertRaises(AzureConflictHttpError):
            self.qs.create_queue(queue_name, None, True)

        # Asserts
        self.assertTrue(created)

    @record
    def test_create_queue_with_options(self):
        # Action
        queue_name = self._get_queue_reference()
        self.qs.create_queue(
            queue_name,
            metadata={'val1': 'test', 'val2': 'blah'})
        result = self.qs.get_queue_metadata(queue_name)

        # Asserts
        self.assertIsNotNone(result)
        self.assertEqual(3, len(result))
        self.assertEqual(result['x-ms-approximate-messages-count'], '0')
        self.assertEqual('test', result['x-ms-meta-val1'])
        self.assertEqual('blah', result['x-ms-meta-val2'])

    @record
    def test_delete_queue_not_exist(self):
        # Action
        queue_name = self._get_queue_reference()
        deleted = self.qs.delete_queue(queue_name)

        # Asserts
        self.assertFalse(deleted)

    @record
    def test_delete_queue_fail_not_exist_not_exist(self):
        # Action
        queue_name = self._get_queue_reference()
        with self.assertRaises(AzureMissingResourceHttpError):
            self.qs.delete_queue(queue_name, True)

        # Asserts

    @record
    def test_delete_queue_fail_not_exist_already_exist(self):
        # Action
        queue_name = self._get_queue_reference()
        created = self.qs.create_queue(queue_name)
        deleted = self.qs.delete_queue(queue_name, True)

        # Asserts
        self.assertTrue(created)
        self.assertTrue(deleted)

    @record
    def test_list_queues(self):
        # Action
        queues = self.qs.list_queues()

        # Asserts
        self.assertIsNotNone(queues)
        self.assertTrue(len(self.test_queues) <= len(queues))

    @record
    def test_list_queues_with_options(self):
        # Arrange
        for i in range(0, 4):
            self._create_queue()

        # Action
        queues_1 = self.qs.list_queues(prefix=TEST_QUEUE_PREFIX, max_results=3)
        queues_2 = self.qs.list_queues(
            prefix=TEST_QUEUE_PREFIX,
            marker=queues_1.next_marker,
            include='metadata')

        # Asserts
        self.assertIsNotNone(queues_1)
        self.assertEqual(3, len(queues_1))
        self.assertIsNotNone(queues_1[0])
        self.assertIsNone(queues_1[0].metadata)
        self.assertNotEqual('', queues_1[0].name)
        # Asserts
        self.assertIsNotNone(queues_2)
        self.assertTrue(len(self.test_queues) - 3 <= len(queues_2))
        self.assertIsNotNone(queues_2[0])
        self.assertIsNotNone(queues_2[0].metadata)
        self.assertNotEqual('', queues_2[0].name)

    @record
    def test_list_queues_with_metadata(self):
        # Action
        queue_name = self._create_queue()
        self.qs.set_queue_metadata(
            queue_name,
            metadata={'val1': 'test', 'val2': 'blah'})

        queue = self.qs.list_queues(queue_name, max_results=1, include='metadata')[0]

        # Asserts
        self.assertIsNotNone(queue)
        self.assertEqual(queue_name, queue.name)
        self.assertIsNotNone(queue.metadata)
        self.assertEqual(len(queue.metadata), 2)
        self.assertEqual(queue.metadata['val1'], 'test')

    @record
    def test_set_queue_metadata(self):
        # Action
        queue_name = self._create_queue()
        self.qs.set_queue_metadata(
            queue_name,
            metadata={'val1': 'test', 'val2': 'blah'})
        result = self.qs.get_queue_metadata(queue_name)
        self.qs.delete_queue(queue_name)

        # Asserts
        self.assertIsNotNone(result)
        self.assertEqual(3, len(result))
        self.assertEqual('0', result['x-ms-approximate-messages-count'])
        self.assertEqual('test', result['x-ms-meta-val1'])
        self.assertEqual('blah', result['x-ms-meta-val2'])

    @record
    def test_put_message(self):
        # Action.  No exception means pass. No asserts needed.
        queue_name = self._create_queue()
        self.qs.put_message(queue_name, 'message1')
        self.qs.put_message(queue_name, 'message2')
        self.qs.put_message(queue_name, 'message3')
        self.qs.put_message(queue_name, 'message4')

    @record
    def test_get_messages(self):
        # Action
        queue_name = self._create_queue()
        self.qs.put_message(queue_name, 'message1')
        self.qs.put_message(queue_name, 'message2')
        self.qs.put_message(queue_name, 'message3')
        self.qs.put_message(queue_name, 'message4')
        result = self.qs.get_messages(queue_name)

        # Asserts
        self.assertIsNotNone(result)
        self.assertEqual(1, len(result))
        message = result[0]
        self.assertIsNotNone(message)
        self.assertNotEqual('', message.id)
        self.assertEqual('message1', message.content)
        self.assertNotEqual('', message.pop_receipt)
        self.assertEqual('1', message.dequeue_count)

        self.assertIsInstance(message.insertion_time, datetime)
        self.assertIsInstance(message.expiration_time, datetime)
        self.assertIsInstance(message.time_next_visible, datetime)

    @record
    def test_get_messages_with_options(self):
        # Action
        queue_name = self._create_queue()
        self.qs.put_message(queue_name, 'message1')
        self.qs.put_message(queue_name, 'message2')
        self.qs.put_message(queue_name, 'message3')
        self.qs.put_message(queue_name, 'message4')
        result = self.qs.get_messages(
            queue_name, num_messages=4, visibility_timeout=20)

        # Asserts
        self.assertIsNotNone(result)
        self.assertEqual(4, len(result))

        for message in result:
            self.assertIsNotNone(message)
            self.assertNotEqual('', message.id)
            self.assertNotEqual('', message.content)
            self.assertNotEqual('', message.pop_receipt)
            self.assertEqual('1', message.dequeue_count)
            self.assertNotEqual('', message.insertion_time)
            self.assertNotEqual('', message.expiration_time)
            self.assertNotEqual('', message.time_next_visible)

    @record
    def test_peek_messages(self):
        # Action
        queue_name = self._create_queue()
        self.qs.put_message(queue_name, 'message1')
        self.qs.put_message(queue_name, 'message2')
        self.qs.put_message(queue_name, 'message3')
        self.qs.put_message(queue_name, 'message4')
        result = self.qs.peek_messages(queue_name)

        # Asserts
        self.assertIsNotNone(result)
        self.assertEqual(1, len(result))
        message = result[0]
        self.assertIsNotNone(message)
        self.assertNotEqual('', message.id)
        self.assertNotEqual('', message.content)
        self.assertIsNone(message.pop_receipt)
        self.assertEqual('0', message.dequeue_count)
        self.assertNotEqual('', message.insertion_time)
        self.assertNotEqual('', message.expiration_time)
        self.assertIsNone(message.time_next_visible)

    @record
    def test_peek_messages_with_options(self):
        # Action
        queue_name = self._create_queue()
        self.qs.put_message(queue_name, 'message1')
        self.qs.put_message(queue_name, 'message2')
        self.qs.put_message(queue_name, 'message3')
        self.qs.put_message(queue_name, 'message4')
        result = self.qs.peek_messages(queue_name, num_messages=4)

        # Asserts
        self.assertIsNotNone(result)
        self.assertEqual(4, len(result))
        for message in result:
            self.assertIsNotNone(message)
            self.assertNotEqual('', message.id)
            self.assertNotEqual('', message.content)
            self.assertIsNone(message.pop_receipt)
            self.assertEqual('0', message.dequeue_count)
            self.assertNotEqual('', message.insertion_time)
            self.assertNotEqual('', message.expiration_time)
            self.assertIsNone(message.time_next_visible)

    @record
    def test_clear_messages(self):
        # Action
        queue_name = self._create_queue()
        self.qs.put_message(queue_name, 'message1')
        self.qs.put_message(queue_name, 'message2')
        self.qs.put_message(queue_name, 'message3')
        self.qs.put_message(queue_name, 'message4')
        self.qs.clear_messages(queue_name)
        result = self.qs.peek_messages(queue_name)

        # Asserts
        self.assertIsNotNone(result)
        self.assertEqual(0, len(result))

    @record
    def test_delete_message(self):
        # Action
        queue_name = self._create_queue()
        self.qs.put_message(queue_name, 'message1')
        self.qs.put_message(queue_name, 'message2')
        self.qs.put_message(queue_name, 'message3')
        self.qs.put_message(queue_name, 'message4')
        result = self.qs.get_messages(queue_name)
        self.qs.delete_message(
            queue_name, result[0].id, result[0].pop_receipt)
        result2 = self.qs.get_messages(queue_name, num_messages=32)

        # Asserts
        self.assertIsNotNone(result2)
        self.assertEqual(3, len(result2))

    @record
    def test_update_message(self):
        # Action
        queue_name = self._create_queue()
        self.qs.put_message(queue_name, 'message1')
        list_result1 = self.qs.get_messages(queue_name)
        self.qs.update_message(queue_name,
                               list_result1[0].id,
                               list_result1[0].pop_receipt,
                               0)
        list_result2 = self.qs.get_messages(queue_name)

        # Asserts
        self.assertIsNotNone(list_result2)
        message = list_result2[0]
        self.assertIsNotNone(message)
        self.assertEqual(list_result1[0].id, message.id)
        self.assertEqual('message1', message.content)
        self.assertEqual('2', message.dequeue_count)
        self.assertIsNotNone(message.pop_receipt)
        self.assertIsNotNone(message.insertion_time)
        self.assertIsNotNone(message.expiration_time)
        self.assertIsNotNone(message.time_next_visible)

    @record
    def test_update_message_content(self):
        # Action
        queue_name = self._create_queue()
        self.qs.put_message(queue_name, 'message1')
        list_result1 = self.qs.get_messages(queue_name)
        self.qs.update_message(queue_name,
                               list_result1[0].id,
                               list_result1[0].pop_receipt,
                               0,
                               content='new text',)
        list_result2 = self.qs.get_messages(queue_name)

        # Asserts
        self.assertIsNotNone(list_result2)
        message = list_result2[0]
        self.assertIsNotNone(message)
        self.assertEqual(list_result1[0].id, message.id)
        self.assertEqual('new text', message.content)
        self.assertEqual('2', message.dequeue_count)
        self.assertIsNotNone(message.pop_receipt)
        self.assertIsNotNone(message.insertion_time)
        self.assertIsNotNone(message.expiration_time)
        self.assertIsNotNone(message.time_next_visible)

    def test_sas_read(self):
        # SAS URL is calculated from storage key, so this test runs live only
        if TestMode.need_recordingfile(self.test_mode):
            return

        # Arrange
        queue_name = self._create_queue()
        self.qs.put_message(queue_name, 'message1')
        token = self.qs.generate_shared_access_signature(
            queue_name,
            QueueSharedAccessPermissions.READ,
            datetime.utcnow() + timedelta(hours=1),
            datetime.utcnow() - timedelta(minutes=5)
        )

        # Act
        service = QueueService(
            account_name=self.settings.STORAGE_ACCOUNT_NAME,
            sas_token=token,
        )
        self._set_service_options(service, self.settings)
        result = service.peek_messages(queue_name)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(1, len(result))
        message = result[0]
        self.assertIsNotNone(message)
        self.assertNotEqual('', message.id)
        self.assertEqual('message1', message.content)

    def test_sas_add(self):
        # SAS URL is calculated from storage key, so this test runs live only
        if TestMode.need_recordingfile(self.test_mode):
            return

        # Arrange
        queue_name = self._create_queue()
        token = self.qs.generate_shared_access_signature(
            queue_name,
            QueueSharedAccessPermissions.ADD,
            datetime.utcnow() + timedelta(hours=1),
        )

        # Act
        service = QueueService(
            account_name=self.settings.STORAGE_ACCOUNT_NAME,
            sas_token=token,
        )
        self._set_service_options(service, self.settings)
        result = service.put_message(queue_name, 'addedmessage')

        # Assert
        result = self.qs.get_messages(queue_name)
        self.assertEqual('addedmessage', result[0].content)

    def test_sas_update(self):
        # SAS URL is calculated from storage key, so this test runs live only
        if TestMode.need_recordingfile(self.test_mode):
            return

        # Arrange
        queue_name = self._create_queue()
        self.qs.put_message(queue_name, 'message1')
        token = self.qs.generate_shared_access_signature(
            queue_name,
            QueueSharedAccessPermissions.UPDATE,
            datetime.utcnow() + timedelta(hours=1),
        )
        result = self.qs.get_messages(queue_name)

        # Act
        service = QueueService(
            account_name=self.settings.STORAGE_ACCOUNT_NAME,
            sas_token=token,
        )
        self._set_service_options(service, self.settings)
        service.update_message(
            queue_name,
            result[0].id,
            result[0].pop_receipt,
            visibility_timeout=0,
            content='updatedmessage1',
        )

        # Assert
        result = self.qs.get_messages(queue_name)
        self.assertEqual('updatedmessage1', result[0].content)

    def test_sas_process(self):
        # SAS URL is calculated from storage key, so this test runs live only
        if TestMode.need_recordingfile(self.test_mode):
            return

        # Arrange
        queue_name = self._create_queue()
        self.qs.put_message(queue_name, 'message1')
        token = self.qs.generate_shared_access_signature(
            queue_name,
            QueueSharedAccessPermissions.PROCESS,
            datetime.utcnow() + timedelta(hours=1),
        )

        # Act
        service = QueueService(
            account_name=self.settings.STORAGE_ACCOUNT_NAME,
            sas_token=token,
        )
        self._set_service_options(service, self.settings)
        result = service.get_messages(queue_name)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(1, len(result))
        message = result[0]
        self.assertIsNotNone(message)
        self.assertNotEqual('', message.id)
        self.assertEqual('message1', message.content)

    def test_sas_signed_identifier(self):
        # SAS URL is calculated from storage key, so this test runs live only
        if TestMode.need_recordingfile(self.test_mode):
            return

        # Arrange
        access_policy = AccessPolicy()
        access_policy.start = '2011-10-11'
        access_policy.expiry = '2018-10-12'
        access_policy.permission = QueueSharedAccessPermissions.READ

        identifiers = {'testid': access_policy}

        queue_name = self._create_queue()
        resp = self.qs.set_queue_acl(queue_name, identifiers)

        self.qs.put_message(queue_name, 'message1')

        token = self.qs.generate_shared_access_signature(
            queue_name,
            id='testid'
        )

        # Act
        service = QueueService(
            account_name=self.settings.STORAGE_ACCOUNT_NAME,
            sas_token=token,
        )
        self._set_service_options(service, self.settings)
        result = service.peek_messages(queue_name)

        # Assert
        self.assertIsNotNone(result)
        self.assertEqual(1, len(result))
        message = result[0]
        self.assertIsNotNone(message)
        self.assertNotEqual('', message.id)
        self.assertEqual('message1', message.content)

    @record
    def test_get_queue_acl(self):
        # Arrange
        queue_name = self._create_queue()

        # Act
        acl = self.qs.get_queue_acl(queue_name)

        # Assert
        self.assertIsNotNone(acl)
        self.assertEqual(len(acl), 0)

    @record
    def test_get_queue_acl_iter(self):
        # Arrange
        queue_name = self._create_queue()

        # Act
        acl = self.qs.get_queue_acl(queue_name)
        for signed_identifier in acl:
            pass

        # Assert
        self.assertIsNotNone(acl)
        self.assertEqual(len(acl), 0)

    @record
    def test_get_queue_acl_with_non_existing_queue(self):
        # Arrange
        queue_name = self._get_queue_reference()

        # Act
        with self.assertRaises(AzureMissingResourceHttpError):
            self.qs.get_queue_acl(queue_name)

        # Assert

    @record
    def test_set_queue_acl(self):
        # Arrange
        queue_name = self._create_queue()

        # Act
        resp = self.qs.set_queue_acl(queue_name)

        # Assert
        self.assertIsNone(resp)
        acl = self.qs.get_queue_acl(queue_name)
        self.assertIsNotNone(acl)

    @record
    def test_set_queue_acl_with_empty_signed_identifiers(self):
        # Arrange
        queue_name = self._create_queue()

        # Act
        resp = self.qs.set_queue_acl(queue_name, dict())

        # Assert
        self.assertIsNone(resp)
        acl = self.qs.get_queue_acl(queue_name)
        self.assertIsNotNone(acl)
        self.assertEqual(len(acl), 0)

    @record
    def test_set_queue_acl_with_signed_identifiers(self):
        # Arrange
        queue_name = self._create_queue()

        # Act
        access_policy = AccessPolicy(permission=QueueSharedAccessPermissions.READ,
                                     expiry='2011-10-12',
                                     start='2011-10-11')
        identifiers = {'testid': access_policy}

        resp = self.qs.set_queue_acl(queue_name, identifiers)

        # Assert
        self.assertIsNone(resp)
        acl = self.qs.get_queue_acl(queue_name)
        self.assertIsNotNone(acl)
        self.assertEqual(len(acl), 1)
        self.assertTrue('testid' in acl)

    @record
    def test_set_queue_acl_with_non_existing_queue(self):
        # Arrange
        queue_name = self._get_queue_reference()

        # Act
        with self.assertRaises(AzureMissingResourceHttpError):
            self.qs.set_queue_acl(queue_name)

        # Assert

    @record
    def test_with_filter(self):
        # Single filter
        called = []

        def my_filter(request, next):
            called.append(True)
            return next(request)
        qc = self.qs.with_filter(my_filter)
        queue_name = self._create_queue()
        qc.put_message(queue_name, 'message1')

        self.assertTrue(called)

        del called[:]

        # Chained filters
        def filter_a(request, next):
            called.append('a')
            return next(request)

        def filter_b(request, next):
            called.append('b')
            return next(request)

        qc = self.qs.with_filter(filter_a).with_filter(filter_b)
        qc.put_message(queue_name, 'message1')

        self.assertEqual(called, ['b', 'a'])

    @record
    def test_unicode_create_queue_unicode_name(self):
        # Action
        queue_name = u'啊齄丂狛狜'

        with self.assertRaises(AzureHttpError):
            # not supported - queue name must be alphanumeric, lowercase
            self.qs.create_queue(queue_name)

        # Asserts

    @record
    def test_unicode_get_messages_unicode_data(self):
        # Action
        queue_name = self._create_queue()
        self.qs.put_message(queue_name, u'message1㚈')
        result = self.qs.get_messages(queue_name)

        # Asserts
        self.assertIsNotNone(result)
        self.assertEqual(1, len(result))
        message = result[0]
        self.assertIsNotNone(message)
        self.assertNotEqual('', message.id)
        self.assertEqual(u'message1㚈', message.content)
        self.assertNotEqual('', message.pop_receipt)
        self.assertEqual('1', message.dequeue_count)
        self.assertNotEqual('', message.insertion_time)
        self.assertNotEqual('', message.expiration_time)
        self.assertNotEqual('', message.time_next_visible)

    @record
    def test_unicode_update_message_unicode_data(self):
        # Action
        queue_name = self._create_queue()
        self.qs.put_message(queue_name, 'message1')
        list_result1 = self.qs.get_messages(queue_name)
        self.qs.update_message(queue_name,
                               list_result1[0].id,
                               list_result1[0].pop_receipt,
                               content=u'啊齄丂狛狜',
                               visibility_timeout=0)
        list_result2 = self.qs.get_messages(queue_name)

        # Asserts
        self.assertIsNotNone(list_result2)
        message = list_result2[0]
        self.assertIsNotNone(message)
        self.assertNotEqual('', message.id)
        self.assertEqual(u'啊齄丂狛狜', message.content)
        self.assertNotEqual('', message.pop_receipt)
        self.assertEqual('2', message.dequeue_count)
        self.assertNotEqual('', message.insertion_time)
        self.assertNotEqual('', message.expiration_time)
        self.assertNotEqual('', message.time_next_visible)

#------------------------------------------------------------------------------
if __name__ == '__main__':
    unittest.main()