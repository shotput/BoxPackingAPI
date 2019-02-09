from fulfillment_api.constants import api_settings, permissions

from testing.decorators import login_as, permission_required_test
from testing.shotput_tests import BaseShotputTestCaseWithData
from testing.test_data import require_data


class GetBestFitTest(BaseShotputTestCaseWithData):
    @require_data(users='rect')
    @login_as('rect')
    @permission_required_test('rect', 'rectangles', 'shotput',
                              permissions.box_packing_read,
                              setup=False, success_status=400,
                              test_api_keys='api_key',
                              api_type=api_settings.BOX_PACKING)
    def test_get_best_fit_forbidden(self, token, api_key):
        token = token if api_key is None else None
        api_key = '' if api_key is None else '?key={}'.format(api_key.get_key())
        return self.post_json('/box_packing_api/basic{}'.format(api_key), token)


class GetSpaceAfterPackingTest(BaseShotputTestCaseWithData):
    @require_data(users='rect')
    @login_as('rect')
    @permission_required_test('rect', 'rectangles', 'shotput',
                              permissions.box_packing_read,
                              setup=False, success_status=400,
                              test_api_keys='api_key',
                              api_type=api_settings.BOX_PACKING)
    def test_get_space_after_packing_forbidden(self, token, api_key):
        token = token if api_key is None else None
        api_key = '' if api_key is None else '?key={}'.format(api_key.get_key())
        return self.post_json('/box_packing_api/remaining_volume{}'
                              .format(api_key), token)


class HowManyFitTest(BaseShotputTestCaseWithData):
    @require_data(users='rect')
    @login_as('rect')
    @permission_required_test('rect', 'rectangles', 'shotput',
                              permissions.box_packing_read,
                              setup=False, success_status=400,
                              test_api_keys='api_key',
                              api_type=api_settings.BOX_PACKING)
    def test_how_many_fit_forbidden(self, token, api_key):
        token = token if api_key is None else None
        api_key = '' if api_key is None else '?key={}'.format(api_key.get_key())
        return self.post_json(
            '/box_packing_api/capacity{}'.format(api_key), token)


class BoxPackingApiTest(BaseShotputTestCaseWithData):
    @require_data(users='rect')
    @login_as('rect')
    @permission_required_test('rect', 'rectangles', 'shotput',
                              permissions.box_packing_read,
                              setup=False, success_status=400,
                              test_api_keys='api_key',
                              api_type=api_settings.BOX_PACKING)
    def test_box_packing_api_forbidden(self, token, api_key):
        token = token if api_key is None else None
        api_key = '' if api_key is None else '?key={}'.format(api_key.get_key())
        return self.post_json('/box_packing_api/full{}'.format(api_key), token)


class ComparePackTest(BaseShotputTestCaseWithData):
    def setUp(self):
        super(ComparePackTest, self).setUp()
        self.data.users['admin'].groups = []
        self.session.commit()

    @require_data(users='admin')
    @login_as('admin')
    @permission_required_test('admin', 'shotput', 'shotput',
                              permissions.global_god_mode,
                              setup=False, test_api_keys='api_key',
                              api_type=api_settings.BOX_PACKING)
    def test_compare_pack_forbidden(self, token, api_key):
        token = token if api_key is None else None
        api_key = '' if api_key is None else '?key={}'.format(api_key.get_key())
        return self.get_json('/box_packing_api/compare_packing_efficiency{}'
                             .format(api_key), token, args={'trials': 1})
