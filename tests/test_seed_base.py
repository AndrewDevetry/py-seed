"""
****************************************************************************************************
:copyright (c) 2019-2022, Alliance for Sustainable Energy, LLC, and other contributors.

All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted
provided that the following conditions are met:

Redistributions of source code must retain the above copyright notice, this list of conditions
and the following disclaimer.

Redistributions in binary form must reproduce the above copyright notice, this list of conditions
and the following disclaimer in the documentation and/or other materials provided with the
distribution.

Neither the name of the copyright holder nor the names of its contributors may be used to endorse
or promote products derived from this software without specific prior written permission.

Redistribution of this software, without modification, must refer to the software by the same
designation. Redistribution of a modified version of this software (i) may not refer to the
modified version by the same designation, or by any confusingly similar designation, and
(ii) must refer to the underlying software originally provided by Alliance as “URBANopt”. Except
to comply with the foregoing, the term “URBANopt”, or any confusingly similar designation may
not be used to refer to any modified version of this software or any modified version of the
underlying software originally provided by Alliance without the prior written consent of Alliance.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR
IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND
FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER
IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
****************************************************************************************************
"""

# Imports from Third Party Modules
import pytest
import unittest
import uuid
from datetime import date
from pathlib import Path

# Local Imports
from pyseed.seed_client import SeedProperties


@pytest.mark.integration
class SeedBaseTest(unittest.TestCase):
    @classmethod
    def setup_class(cls):
        """setup for all of the tests below"""
        cls.organization_id = 1

        # The seed-config.json file needs to be added to the project root directory
        # If running SEED locally for testing, then you can run the following from your SEED root directory:
        #    ./manage.py create_test_user_json --username user@seed-platform.org --file ../py-seed/seed-config.json --pyseed
        config_file = Path('seed-config.json')
        cls.seed_client = SeedProperties(cls.organization_id, connection_config_filepath=config_file)

        cls.organization_id = 1

    @classmethod
    def teardown_class(cls):
        # remove all of the test buildings?
        pass

    def test_get_create_delete_cycle(self):
        all_cycles = self.seed_client.get_cycles()
        cycle_count = len(all_cycles['cycles'])
        assert cycle_count >= 1

        # create a new unique cycle
        unique_id = str(uuid.uuid4())[:8]
        cycle = self.seed_client.get_or_create_cycle(
            f'test cycle {unique_id}', date(2021, 1, 1), date(2022, 1, 1)
        )
        assert cycle['cycles']['name'] == f'test cycle {unique_id}'
        cycle_id = cycle['cycles']['id']
        all_cycles = self.seed_client.get_cycles()
        assert len(all_cycles['cycles']) == cycle_count + 1
        # verify that it won't be created again
        cycle = self.seed_client.get_or_create_cycle(
            f'test cycle {unique_id}', date(2021, 1, 1), date(2022, 1, 1)
        )
        assert cycle_id == cycle['cycles']['id']
        all_cycles = self.seed_client.get_cycles()
        assert len(all_cycles['cycles']) == cycle_count + 1

        # now delete the new cycle
        self.seed_client.delete_cycle(cycle_id)
        all_cycles = self.seed_client.get_cycles()
        assert len(all_cycles['cycles']) == cycle_count

    def test_create_cycle(self):
        cycle = self.seed_client.create_cycle('new cycle', date(2021, 6, 1), date(2022, 6, 1))
        cycle_id = cycle['cycles']['id']
        assert cycle is not None

        # test the setting of the ID
        cycle = self.seed_client.get_or_create_cycle('new cycle', None, None, set_cycle_id=True)
        assert self.seed_client.cycle_id == cycle_id

        # clean up the cycle
        self.seed_client.delete_cycle(cycle_id)

    def test_cycle_multiple_names_warning(self):
        ids_to_delete = []
        for _i in range(0, 5):
            cycle = self.seed_client.create_cycle('new cycle', date(2021, 6, 1), date(2022, 6, 1))
            ids_to_delete.append(cycle['cycles']['id'])

        cycle = self.seed_client.get_or_create_cycle('new cycle', None, None)

        # now delete the new cycles
        for id in ids_to_delete:
            self.seed_client.delete_cycle(id)

        # not catching anything at the moment
        assert True

    def test_get_or_create_dataset(self):
        dataset_name = 'seed-salesforce-test-data'
        dataset = self.seed_client.get_or_create_dataset(dataset_name)
        assert dataset['name'] == dataset_name
        assert dataset['super_organization'] == self.seed_client.client.org_id
        assert dataset is not None

    def test_get_column_mapping_profiles(self):
        result = self.seed_client.get_column_mapping_profiles()
        assert len(result) >= 1

        # There should only be one default BuildingSync mapping profile
        result = self.seed_client.get_column_mapping_profiles('BuildingSync Default')
        assert len(result) == 1

    def test_get_column_mapping_profile(self):
        result = self.seed_client.get_column_mapping_profile('does not exist')
        assert result is None

        # There should always be a portolio manager default unless the
        # user removed it.
        result = self.seed_client.get_column_mapping_profile('Portfolio Manager Defaults')
        assert isinstance(result, dict)
        assert len(result['mappings']) > 0

    def test_create_column_mapping_profile_with_file(self):
        profile_name = 'new profile'
        result = self.seed_client.create_or_update_column_mapping_profile_from_file(
            profile_name,
            'tests/data/test-seed-data-mappings.csv'
        )
        assert result is not None
        assert len(result['mappings']) == 14

        # delete some of the mappings and update
        mappings = result['mappings']
        for index in range(5, 0, -1):
            mappings.pop(index)
        result = self.seed_client.create_or_update_column_mapping_profile(
            profile_name,
            mappings
        )
        assert len(result['mappings']) == 9

        # restore with the original call
        result = self.seed_client.create_or_update_column_mapping_profile_from_file(
            profile_name,
            'tests/data/test-seed-data-mappings.csv'
        )
        assert len(result['mappings']) == 14

    def test_get_labels(self):
        result = self.seed_client.get_labels()
        assert len(result) > 10

        # find a set of two labels
        result = self.seed_client.get_labels(filter_by_name=['Compliant', 'Violation'])
        assert len(result) == 2

        # find single field
        result = self.seed_client.get_labels(filter_by_name=['Call'])
        assert len(result) == 1
        assert result[0]['name'] == 'Call'
        assert not result[0]['show_in_list']

        # find nothing field
        result = self.seed_client.get_labels(filter_by_name=['Does not Exist'])
        assert len(result) == 0
