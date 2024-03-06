# -*- coding: utf-8 -*-
#
# Copyright (c) 2024 Virtual Cable S.L.U.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
#
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#    * Neither the name of Virtual Cable S.L. nor the names of its contributors
#      may be used to endorse or promote products derived from this software
#      without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
'''
Author: Adolfo Gómez, dkmaster at dkmon dot com
'''
import logging
import os
import socket
import sys

from unittest import TestCase, mock

from uds import tools, types

logger = logging.getLogger(__name__)


class TestClient(TestCase):
    def test_save_temp_file(self) -> None:
        out_filename = tools.save_temp_file(content='1234')
        # Ensure file exists
        self.assertTrue(os.path.exists(out_filename))

        # Remove it and try with a provided name
        os.unlink(out_filename)
        out_filename = tools.save_temp_file(content='1234', filename='test.txt')
        self.assertTrue(os.path.exists(out_filename))
        os.unlink(out_filename)

    def test_read_temp_file(self) -> None:
        out_filename = tools.save_temp_file(content='1234')
        self.assertEqual(tools.read_temp_file(out_filename), '1234')
        os.unlink(out_filename)

    def test_test_server(self) -> None:
        # Test with a server that does not exists
        # Create a local listener for testing
        with mock.patch('socket.create_connection') as create_connection:
            create_connection.return_value = mock.MagicMock()
            self.assertTrue(tools.test_server('localhost', 1234))
            # Now, failure
            create_connection.side_effect = Exception('Test')
            self.assertFalse(tools.test_server('localhost', 1234))

    def test_find_application(self) -> None:
        # For windows, we will test cmd.exe, for linux and macos, we will test sh
        if sys.platform.startswith('win'):
            self.assertIsInstance(tools.find_application('cmd.exe'), str)  # Found and is a string
        else:
            self.assertIsInstance(tools.find_application('sh'), str)  # Found and is a string

        # Now, a non existent application
        self.assertIsNone(tools.find_application('nonexistentapplication'))

    def test_gethostname(self) -> None:
        self.assertEqual(tools.gethostname(), socket.gethostname())

    def test_register_for_delayed_deletion(self) -> None:
        # Just call it, nothing to test here
        tools.register_for_delayed_deletion('a', False)
        tools.register_for_delayed_deletion('b', True)
        # Ensure has been added to the list tools._unlink_files
        self.assertIn(types.RemovableFile('a', False), tools._unlink_files)
        self.assertIn(types.RemovableFile('b', True), tools._unlink_files)

    def test_unlink_files(self) -> None:
        # Just call it, nothing to test here
        # Clear _unlink_files
        tools._unlink_files.clear()
        for early_stage in [True, False]:
            for path in range(10):
                rmfile = types.RemovableFile(str(path), early_stage)
                tools._unlink_files.append(rmfile)
        # Mock os.unlink
        with mock.patch('os.unlink') as unlink:
            # Also time.sleep, to do not wait
            with mock.patch('time.sleep'):
                for early_stage in [True, False]:
                    unlink.reset_mock()
                    tools.unlink_files(early_stage)
                    self.assertEqual(unlink.call_count, 10)
                    self.assertEqual(unlink.call_args_list, [mock.call(str(x)) for x in range(10)])

        # Now, tools._unlink_files should be empty
        self.assertEqual(len(tools._unlink_files), 0)

    def test_awaitable_tasks(self) -> None:
        tools.add_task_to_wait(mock.sentinel.first, False)
        tools.add_task_to_wait(mock.sentinel.second, True)

        self.assertIn(types.AwaitableTask(mock.sentinel.first, False), tools._awaitable_tasks)
        self.assertIn(types.AwaitableTask(mock.sentinel.second, True), tools._awaitable_tasks)

    def test_wait_tasks_finish(self) -> None:
        tools._awaitable_tasks.clear()
        # Just call it, nothing to test here
        # Mock tools.process_iter
        join_mock = mock.Mock(spec=['join', 'pid'])
        wait_mock = mock.Mock(spec=['wait', 'pid'])
        join_mock.pid = 1234
        wait_mock.pid = 1234

        with mock.patch('uds.tools.process_iter') as _process_iter:
            for wait_subprocesses in [True, False]:
                for m in (join_mock, wait_mock):
                    tools._awaitable_tasks.append(types.AwaitableTask(m, wait_subprocesses))

            tools.wait_for_tasks()

            # Now, tools._awaitable_tasks should be empty
            self.assertEqual(len(tools._awaitable_tasks), 0)
            
            # And every mock should have been called twice, with no arguments
            join_mock.join.assert_called_with()
            wait_mock.wait.assert_called_with()
            
            # also process_iter should have been called twice, once for each type of wait with wait_subprocesses True value
            self.assertEqual(_process_iter.call_count, 2)
