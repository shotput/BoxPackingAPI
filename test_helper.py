from fulfillment_api.box_packing.helper import (space_after_packing,
    how_many_skus_fit, pre_pack_boxes,
    api_packing_algorithm)
from fulfillment_api.errors import BoxError

from collections import Counter
from testing.shotput_tests import BaseShotputTestCase


class HowManySkusFitTest(BaseShotputTestCase):
    def test_exact_fit(self):
        box_info = {
            'height': 4,
            'width': 4,
            'length': 4
        }
        sku_info = {
            'height': 4,
            'width': 4,
            'length': 4
        }
        response = how_many_skus_fit(sku_info, box_info)
        self.assertEqual({
            'total_packed': 1,
            'remaining_volume': 0
        }, response)

    def test_five_fit_extra_space(self):
        box_info = {
            'height': 4,
            'width': 4,
            'length': 4
        }
        sku_info = {
            'height': 4,
            'width': 3,
            'length': 1
        }
        response = how_many_skus_fit(sku_info, box_info)
        self.assertEqual({
            'total_packed': 5,
            'remaining_volume': 4
        }, response)

    def test_lots_and_lots(self):
        box_info = {
            'height': 4,
            'width': 4,
            'length': 4
        }
        sku_info = {
            'height': 1,
            'width': 1,
            'length': 1
        }
        response = how_many_skus_fit(sku_info, box_info)
        self.assertEqual({
            'total_packed': 64,
            'remaining_volume': 0
        }, response)

    def test_max_packed(self):
        box_info = {
            'height': 4,
            'width': 4,
            'length': 4
        }
        sku_info = {
            'height': 1,
            'width': 1,
            'length': 1
        }
        response = how_many_skus_fit(sku_info, box_info, 8)
        self.assertEqual({
            'total_packed': 8,
            'remaining_volume': 56
        }, response)


class SpaceAfterPackingTest(BaseShotputTestCase):
    def test_exact_fit(self):
        box_info = {
            'height': 4,
            'width': 4,
            'length': 4
        }
        sku_info = {
            'height': 4,
            'width': 4,
            'length': 4
        }
        response = space_after_packing(sku_info, box_info)
        self.assertEqual({
            'remaining_volume': 0,
            'remaining_dimensional_blocks': []
        }, response)

    def test_additional_space(self):
        box_info = {
            'height': 4,
            'width': 4,
            'length': 4
        }
        sku_info = {
            'height': 2,
            'width': 2,
            'length': 2
        }
        response = space_after_packing(sku_info, box_info)
        self.assertEqual({
            'remaining_volume': 56,
            'remaining_dimensional_blocks': [
                {'width': 2, 'height': 2, 'length': 2},
                {'width': 2, 'height': 2, 'length': 4},
                {'width': 2, 'height': 4, 'length': 4}]
        }, response)


class PrePackBoxesTest(BaseShotputTestCase):

    def test_pre_pack_boxes_simple(self):
        '''
        tests to make sure we can get a pre-pack of boxes with basic non-db info
        '''
        skus_info = [{
            'width': 1,
            'height': 1,
            'length': 1,
            'weight': 1,
            'quantity': 1,
            'dimension_units': 'inches',
            'weight_units': 'grams',
            'product_name': 'TEST_SKU'
        }]
        box_info = {
            'width': 1,
            'height': 1,
            'length': 1,
            'weight': 1,
            'dimension_units': 'inches',
            'weight_units': 'grams'
        }
        options = {}
        self.assertEqual([{
            'packed_products': {'TEST_SKU': 1},
            'total_weight': 2
        }], pre_pack_boxes(box_info, skus_info, options))

    def test_pre_pack_boxes_too_heavy(self):
        '''
        tests to make sure that when a predefined max weight is provided it
        doesn't over load the boxes
        '''
        skus_info = [{
            'product_name': 'TEST_SKU',
            'width': 1,
            'height': 1,
            'length': 1,
            'weight': 3000,
            'quantity': 4,
            'dimension_units': 'inches',
            'weight_units': 'grams'
        }]
        box_info = {
            'width': 1,
            'height': 2,
            'length': 2,
            'weight': 0,
            'dimension_units': 'inches',
            'weight_units': 'grams'
        }
        options = {
            'max_weight': 8999
        }
        response = pre_pack_boxes(box_info, skus_info, options)
        self.assertEqual([
            {
                'packed_products': {'TEST_SKU': 2},
                'total_weight': 6000
            },
            {
                'packed_products': {'TEST_SKU': 2},
                'total_weight': 6000
            }
        ], response)


LONG_BOX = {
    'width': 4,
    'height': 4,
    'length': 8,
    'weight_units': 'grams',
    'dimensional_units': 'inches',
    'name': '4x4x8',
    'weight': 4
}

CUBE_BOX = {
    'width': 4,
    'height': 4,
    'length': 4,
    'weight_units': 'grams',
    'dimensional_units': 'inches',
    'name': '4x4x4',
    'weight': 4
}

TOO_SMALL_BOX = {
    'width': 2,
    'height': 2,
    'length': 2,
    'weight_units': 'grams',
    'dimensional_units': 'inches',
    'name': '2x2x2',
    'weight': 4
}

CUBE_SKU = {
    'width': 4,
    'height': 4,
    'length': 4,
    'product_name': 'TEST',
    'weight_units': 'grams',
    'dimensional_units': 'inches',
    'weight': 100
}


class ApiPackingAlgorithmTest(BaseShotputTestCase):

    def setUp(self):
        super(ApiPackingAlgorithmTest, self).setUp()
        self.boxes = {
            '4x4x4': CUBE_BOX,
            '4x4x8': LONG_BOX,
            '2x2x2': TOO_SMALL_BOX
        }
        self.skus = {
            '4x4x4': CUBE_SKU
        }

    def test_api_packing_algorithm_max_weight(self):
        products = [{
            'width': 10,
            'height': 10,
            'length': 5,
            'weight': 100,
            'quantity': 1,
            'dimension_units': 'centimeters',
            'weight_units': 'grams',
            'product_name': 'AG-123'
        }, {
            'width': 10,
            'height': 5,
            'length': 5,
            'weight': 100,
            'quantity': 4,
            'dimension_units': 'centimeters',
            'weight_units': 'grams',
            'product_name': 'AG-456'
        }]

        result = api_packing_algorithm([{
            'width': 10,
            'height': 10,
            'length': 20,
            'weight': 50,
            'dimension_units': 'centimeters',
            'weight_units': 'grams',
            'name': 'Box-1'
        }, {
            'width': 5,
            'height': 10,
            'length': 20,
            'weight': 50,
            'dimension_units': 'centimeters',
            'weight_units': 'grams',
            'name': 'Box-2'
        }], products, {
            'max_weight': 300
        })

        expected_counts = Counter()
        for product in products:
            expected_counts[product['product_name']] += product['quantity']

        packed_counts = Counter()
        for package in result['packages']:
            self.assertLessEqual(package['total_weight'], 300)

            for sku_number, quantity in package['packed_products'].iteritems():
                packed_counts[sku_number] += quantity

        self.assertEqual(expected_counts, packed_counts)

    def test_api_packing_algorithm_simple(self):
        boxes_info = [self.boxes['4x4x8']]
        sku = self.skus['4x4x4']
        sku['quantity'] = 2
        skus_info = [sku]
        packed_products = api_packing_algorithm(boxes_info, skus_info, None)
        expected_return = {
            'packages': [{
                'box': self.boxes['4x4x8'],
                'packed_products': {'TEST': 2},
                'total_weight': 204.0
            }]
        }
        self.assertEqual(expected_return, packed_products)

    def test_api_packing_algorithm_two_boxes(self):
        boxes_info = [self.boxes['4x4x4'], self.boxes['4x4x8']]
        sku = self.skus['4x4x4']
        sku['quantity'] = 2
        skus_info = [sku]
        packed_products = api_packing_algorithm(boxes_info, skus_info, None)
        expected_return = {
            'packages': [{
                'box': self.boxes['4x4x8'],
                'packed_products': {'TEST': 2},
                'total_weight': 204.0
            }]
        }
        self.assertEqual(expected_return, packed_products)

    def test_api_packing_algorithm_last_parcel(self):
        boxes_info = [self.boxes['4x4x4'], self.boxes['4x4x8']]
        sku = self.skus['4x4x4']
        sku['quantity'] = 3
        skus_info = [sku]

        packed_products = api_packing_algorithm(boxes_info, skus_info, None)
        expected_return = {
            'packages': [
                {
                    'packed_products': {'TEST': 2},
                    'total_weight': 204,
                    'box': self.boxes['4x4x8']
                },
                {
                    'box': self.boxes['4x4x4'],
                    'packed_products': {'TEST': 1},
                    'total_weight': 104.0
                }
            ]
        }
        self.assertEqual(expected_return, packed_products)

    def test_api_packing_too_small(self):
        boxes_info = [self.boxes['2x2x2']]
        sku = self.skus['4x4x4']
        sku['quantity'] = 3
        skus_info = [sku]

        with self.assertRaises(BoxError) as context:
            api_packing_algorithm(boxes_info, skus_info, None)
        self.assertEqual('Some of your products are too big for your boxes. '
                         'Please provide larger boxes.',
                         context.exception.message)

    def test_api_packing_max_weight(self):
        boxes_info = [self.boxes['4x4x8'], self.boxes['4x4x4']]
        sku = self.skus['4x4x4']
        sku['quantity'] = 2
        skus_info = [sku]
        options = {'max_weight': 200}

        expected_return = {
            'packages': [
                {
                    'box': self.boxes['4x4x4'],
                    'packed_products': {'TEST': 1},
                    'total_weight': 104.0
                },
                {
                    'box': self.boxes['4x4x4'],
                    'packed_products': {'TEST': 1},
                    'total_weight': 104.0
                }
            ]
        }
        packed_products = api_packing_algorithm(boxes_info, skus_info, options)
        self.assertEqual(expected_return, packed_products)

    def test_api_packing_non_unique(self):
        boxes_info = [self.boxes['4x4x4'], self.boxes['4x4x4']]
        sku = self.skus['4x4x4']
        sku['quantity'] = 2
        skus_info = [sku]

        with self.assertRaises(BoxError) as context:
            api_packing_algorithm(boxes_info, skus_info, None)
        self.assertEqual('Please use unique boxes with unique names',
                         context.exception.message)
