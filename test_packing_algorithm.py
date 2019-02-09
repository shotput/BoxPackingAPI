from collections import namedtuple
from fulfillment_api.box_packing.packing_algorithm import (does_it_fit,
    best_fit, pack_boxes, SkuTuple, Packaging, setup_box_dictionary)
from fulfillment_api.errors import BoxError

from testing.shotput_tests import BaseShotputTestCase


class BoxSelectionAlgorithmTest(BaseShotputTestCase):

    # Note: sku and box dimensions should be input in ascending order
    # ex: sku_dims = [1,2,5] == GOOD, sku_dims = [2,5,1] == Infinite Loop
    def test_does_it_fit_true(self):
        '''
        test when sku does fit, returns True
        '''
        sku_dims = [4, 12, 14]
        box_dims = [4, 14, 22]

        self.assertEqual(True, does_it_fit(sku_dims, box_dims))

    def test_does_it_fit_false(self):
        '''
        test that when a sku does not fit, it returns False
        '''
        sku_dims = [4, 12, 14]
        box_dims = [3.99, 14, 14]

        self.assertEqual(False, does_it_fit(sku_dims, box_dims))

    def test_best_fit_exact_size(self):
        '''
        assert that if a sku is the same size as the box,
        the remaining_dimensions comes back empty
        '''
        sku_dims = [13, 13, 31]
        box_dims = [13, 13, 31]

        remaining_space = best_fit(sku_dims, box_dims)
        self.assertEqual(remaining_space, [])

    def test_best_fit_half_size(self):
        '''
        assert that if a sku is smaller than the box, but has two dimensions
        the same, it will return the empty space
        '''
        sku_dims = [13, 13, 31]
        box_dims = [13, 26, 31]

        remaining_space = best_fit(sku_dims, box_dims)
        self.assertEqual(remaining_space, [[13, 13, 31]])

    def test_best_fit_multiple_spaces(self):
        '''
        assert that if a sku is smaller than the box, but has two dimensions
        the same, it will return the empty space
        '''
        sku_dims = [13, 13, 31]
        box_dims = [20, 20, 31]

        remaining_space = best_fit(sku_dims, box_dims)
        self.assertEqual(remaining_space, [[7, 13, 31], [7, 20, 31]])

    def test_pack_boxes_one_sku(self):
        '''
        test exact fit one sku
        '''
        sku1 = SkuTuple('Sku1', [13, 13, 31], 0)
        sku_info = [sku1]
        box_dims = [13, 13, 31]

        packed_skus = pack_boxes(box_dims, sku_info)
        self.assertEqual(packed_skus, ([[sku1]]))

    def test_pack_boxes_two_sku_exact(self):
        '''
        test skus will go exactly into box
        '''
        sku1 = SkuTuple('Sku1', [13, 13, 31], 0)
        sku_info = [sku1, sku1]
        box_dims = [13, 26, 31]

        packed_skus = pack_boxes(box_dims, sku_info)
        self.assertEqual(packed_skus, ([[sku1, sku1]]))

    def test_pack_boxes_two_sku_two_box(self):
        '''
        test two skus of same size as box will go into two boxes
        '''
        sku = SkuTuple('Sku1', [13, 13, 31], 0)
        sku_info = [sku, sku]
        box_dims = [13, 13, 31]

        packed_skus = pack_boxes(box_dims, sku_info)
        self.assertEqual(packed_skus, ([[sku], [sku]]))

    def test_pack_boxes_three_sku_one_box(self):
        '''
        test odd sized skus will be rotated to fit
        '''
        sku1 = SkuTuple('Sku1', [13, 13, 31], 0)
        sku2 = SkuTuple('Sku2', [8, 13, 31], 0)
        sku3 = SkuTuple('Sku3', [5, 13, 31], 0)
        sku_info = [sku1, sku2, sku3]
        box_dims = [13, 26, 31]
        packed_skus = pack_boxes(box_dims, sku_info)
        self.assertEqual(packed_skus, ([[sku1, sku2, sku3]]))

    def test_pack_boxes_one_overflow(self):
        '''
        tests when there should be one overflow box
        '''
        sku = SkuTuple('Sku1', [1, 1, 1], 0)
        sku_info = [sku] * 28
        box_dims = [3, 3, 3]

        packed_skus = pack_boxes(box_dims, sku_info)
        self.assertEqual([[sku] * 27, [sku]], packed_skus)

    def test_pack_boxes_odd_sizes(self):
        '''
        test odd sized skus will be rotated to fit
        '''
        sku1 = SkuTuple('Sku1', [3, 8, 10], 0)
        sku2 = SkuTuple('Sku2', [1, 2, 5], 0)
        sku3 = SkuTuple('Sku3', [1, 2, 2], 0)
        sku_info = [sku1, sku2, sku2, sku3]
        box_dims = [10, 20, 20]

        packed_skus = pack_boxes(box_dims, sku_info)
        self.assertEqual([[sku1, sku2, sku2, sku3]], packed_skus)

    def test_slightly_larger_box(self):
        '''
        test inexact dimensions
        '''
        # Fails due to recursion limits reached
        sku = SkuTuple('Sku1', [4, 4, 12], 0)
        sku_info = [sku] * 2
        box_dims = [5, 8, 12]
        # box_dims = [4, 8, 12]  # passes

        packed_skus = pack_boxes(box_dims, sku_info)
        self.assertEqual(packed_skus, ([[sku, sku]]))

    def test_pack_3_boxes(self):
        '''
        test that multiple parcels will be selected
        '''
        sku = SkuTuple('Sku1', [4, 4, 12], 0)
        sku_info = [sku] * 3
        # sku_info = [['Sku1', [2, 2, 12]]] * 3  # no error
        # sku_info = [['Sku1', [4, 4, 12]]] * 2  # no error
        box_dims = [4, 4, 12]

        packed_skus = pack_boxes(box_dims, sku_info)
        self.assertEqual(packed_skus, ([[sku], [sku], [sku]]))

    def test_pack_boxes_dim_over_2(self):
        '''
        test that when length of sku <= length of box / 2 it packs along
        longer edge
        '''
        sku = SkuTuple('Sku1', [3, 4, 5], 0)
        sku_info = [sku] * 4

        box_dims = [6, 8, 10]

        packed_skus = pack_boxes(box_dims, sku_info)
        self.assertEqual(packed_skus, ([[sku, sku, sku, sku]]))

    def test_pack_boxes_odd_sizes_again(self):
        '''
        test skus with different dimensions will be rotated to fit into one box
        '''
        sku1 = SkuTuple('Sku1', [1, 18, 19], 0)
        sku2 = SkuTuple('Sku2', [17, 18, 18], 0)
        sku3 = SkuTuple('Sku3', [1, 17, 18], 0)
        sku_info = [sku1, sku2, sku3]

        box_dims = [18, 18, 19]

        packed_skus = pack_boxes(box_dims, sku_info)
        self.assertEqual(packed_skus, ([[sku1, sku2, sku3]]))

    def test_pack_boxes_100_skus(self):
        '''
        test many skus into one box with inexact fit
        '''
        sku = SkuTuple('Sku1', [5, 5, 5], 0)
        sku_info = [sku] * 100

        box_dims = [51, 51, 6]
        packed_skus = pack_boxes(box_dims, sku_info)

        self.assertEqual(len(packed_skus), 1)

    def test_pack_boxes_100_skus_2_boxes(self):
        '''
        test many skus separated into 2 boxes with exact fit
        '''
        sku = SkuTuple('Sku1', [5, 5, 5], 0)
        sku_info = [sku] * 100

        box_dims = [10, 25, 25]
        packed_skus = pack_boxes(box_dims, sku_info)

        self.assertEqual(len(packed_skus), 2)
        self.assertEqual(len(packed_skus[0]), 50)
        self.assertEqual(len(packed_skus[1]), 50)

    def test_pack_boxes_big_die_and_several_decks_of_cards(self):
        deck = SkuTuple('deck', [2, 8, 12], 0)
        die = SkuTuple('die', [8, 8, 8], 0)
        sku_info = [deck, deck, deck, deck, die]
        box_dims = [8, 8, 12]
        packed_skus = pack_boxes(box_dims, sku_info)
        self.assertEqual(len(packed_skus), 2)
        self.assertEqual(packed_skus, [[deck] * 4, [die]])

    def test_pack_boxes_tight_fit_many(self):
        '''
        tests a tight fit for non-cubic skus
        '''
        sku = SkuTuple('Sku1', [1, 3, 3], 0)
        sku_info = [sku] * 82
        box_dims = [9, 9, 9]
        packed_skus = pack_boxes(box_dims, sku_info)
        expected_return = [[sku] * 81, [sku]]
        self.assertEqual(2, len(packed_skus))
        self.assertEqual(expected_return, packed_skus)

    def test_pack_boxes_tight_fit_many_oblong(self):
        '''
        tests a tight fit for non-cubic skus
        '''
        sku = SkuTuple('Sku1', [1, 2, 3], 0)
        sku_info = [sku] * 107
        box_dims = [8, 9, 9]
        packed_skus = pack_boxes(box_dims, sku_info)
        expected_return = [[sku] * 106, [sku]]
        self.assertEqual(2, len(packed_skus))
        self.assertEqual(expected_return, packed_skus)

    def test_pack_boxes_tight_fit_many_oblong_inexact(self):
        '''
        tests that the algorithm remains at least as accurate as it already is
        if it were perfect, the first box would have 48 in it
        '''
        sku = SkuTuple('Sku1', [1, 2, 3], 0)
        sku_info = [sku] * 49
        box_dims = [4, 8, 9]
        packed_skus = pack_boxes(box_dims, sku_info)
        self.assertEqual(2, len(packed_skus))
        self.assertGreaterEqual(44, len(packed_skus[0]))

    def test_pack_boxes_flat_box(self):
        sku = SkuTuple('MFuelMock', [1.25, 7, 10], 0)
        sku_info = [sku] * 3
        box_dims = [3.5, 9.5, 12.5]
        packed_skus = pack_boxes(box_dims, sku_info)
        self.assertEqual(2, len(packed_skus))
        self.assertEqual(2, len(packed_skus[0]))


class SetupBoxDictionaryTest(BaseShotputTestCase):

    def make_generic_box(self, name, is_flat_rate, volume=None):
        TestBox = namedtuple('TestBox', 'name, description, total_cubic_cm')
        description = 'flat rate' if is_flat_rate else 'normal'
        volume = volume if volume is not None else 1000
        return TestBox(name=name, description=description,
                       total_cubic_cm=volume)

    def test_setup_box_dictionary(self):
        sku = SkuTuple('Sku1', [1, 2, 3], 0)
        normal_box = self.make_generic_box('NORM', False)
        flat_rate_box = self.make_generic_box('MediumFlatRateBox', True)
        packed_boxes = {normal_box: [[sku]],
                        flat_rate_box: [[sku]]}
        box_dictionary = setup_box_dictionary(packed_boxes)
        expected_return = {
            'flat_rate': Packaging(box=flat_rate_box, skus_per_box=[[sku]],
                                   last_parcel=None),
            'package': Packaging(box=normal_box, skus_per_box=[[sku]],
                                 last_parcel=None)
        }
        self.assertEqual(expected_return, box_dictionary)

    def test_setup_box_dictionary_three_flat_rates(self):
        '''
        assert that when there are two flat rates that require a different
        number of boxes, it selects the one that requires the fewest
        '''
        sku = SkuTuple('Sku1', [1, 2, 3], 0)
        normal_box = self.make_generic_box('NORM', False)
        large_box = self.make_generic_box('LargeFlatRateBox', True)
        med_box = self.make_generic_box('MediumFlatRateBox', True)
        small_box = self.make_generic_box('SmallFlatRateBox', True)
        packed_boxes = {normal_box: [[sku, sku]],
                        med_box: [[sku], [sku]],
                        large_box: [[sku, sku]],
                        small_box: [[sku], [sku]]}
        box_dictionary = setup_box_dictionary(packed_boxes)
        expected_return = {
            'flat_rate': Packaging(box=large_box, skus_per_box=[[sku, sku]],
                                   last_parcel=None),
            'package': Packaging(box=normal_box, skus_per_box=[[sku, sku]],
                                 last_parcel=None)
        }
        self.assertEqual(expected_return, box_dictionary)

    def test_setup_box_dictionary_fewest_parcels(self):
        '''
        asserts the the dictionary uses the smallest box with the fewest parcels
        and if flat rate has more parcels, don't even return it.
        '''
        sku = SkuTuple('Sku1', [1, 2, 3], 0)
        normal_box = self.make_generic_box('NORM', False)
        smaller_box = self.make_generic_box('Small', False, volume=500)
        med_box = self.make_generic_box('MediumFlatRateBox', True)
        packed_boxes = {normal_box: [[sku, sku]],
                        med_box: [[sku], [sku]],
                        smaller_box: [[sku], [sku]]}
        box_dictionary = setup_box_dictionary(packed_boxes)
        expected_return = {
            'flat_rate': None,
            'package': Packaging(box=normal_box, skus_per_box=[[sku, sku]],
                                 last_parcel=None)
        }
        self.assertEqual(expected_return, box_dictionary)

    def test_setup_box_dictionary_smaller_volume(self):
        '''
        asserts the the dictionary uses the smallest box with the fewest parcels
        '''
        sku = SkuTuple('Sku1', [1, 2, 3], 0)
        normal_box = self.make_generic_box('NORM', False)
        bigger_box = self.make_generic_box('Big', False, volume=2000)
        packed_boxes = {normal_box: [[sku, sku]],
                        bigger_box: [[sku, sku]]}
        box_dictionary = setup_box_dictionary(packed_boxes)
        expected_return = {
            'flat_rate': None,
            'package': Packaging(box=normal_box, skus_per_box=[[sku, sku]],
                                 last_parcel=None)
        }
        self.assertEqual(expected_return, box_dictionary)

    def test_setup_box_dictionary_flatrate_cheaper(self):
        '''
        asserts that it choses the cheaper flat rate
        '''
        sku = SkuTuple('Sku1', [1, 2, 3], 0)

        med_box = self.make_generic_box('MediumFlatRateBox', True)
        small_box = self.make_generic_box('SmallFlatRateBox', True)
        packed_boxes = {med_box: [[sku, sku]],
                        small_box: [[sku, sku]]}
        box_dictionary = setup_box_dictionary(packed_boxes)
        expected_return = {
            'flat_rate': Packaging(box=small_box, skus_per_box=[[sku, sku]],
                                 last_parcel=None),
            'package': None
        }
        self.assertEqual(expected_return, box_dictionary)

    def test_setup_box_dictionary_complex(self):
        '''
        asserts that in complex situations, it chooses the smallest,
        fewest parcels, cheapest box.
        '''
        sku = SkuTuple('Sku1', [1, 2, 3], 0)
        normal_box = self.make_generic_box('NORM', False)
        smaller_box = self.make_generic_box('Small', False, volume=500)
        bigger_box = self.make_generic_box('Big', False, volume=2000)
        med_box = self.make_generic_box('MediumFlatRateBox', True)
        small_box = self.make_generic_box('SmallFlatRateBox', True)
        large_box = self.make_generic_box('LargeFlatRateBox', True)
        packed_boxes = {med_box: [[sku, sku]],
                        small_box: [[sku], [sku]],
                        large_box: [[sku, sku]],
                        normal_box: [[sku, sku]],
                        bigger_box: [[sku, sku]],
                        smaller_box: [[sku], [sku]]
                        }
        expected_return = {
            'flat_rate': Packaging(box=med_box, skus_per_box=[[sku, sku]],
                                 last_parcel=None),
            'package': Packaging(box=normal_box, skus_per_box=[[sku, sku]],
                                 last_parcel=None),
        }
        box_dictionary = setup_box_dictionary(packed_boxes)
        self.assertEqual(expected_return, box_dictionary)

    def test_setup_box_dictionary_no_package(self):
        '''
        asserts that it does not return package when inefficient
        '''
        sku = SkuTuple('Sku1', [1, 2, 3], 0)

        normal_box = self.make_generic_box('Normal', False)
        med_box = self.make_generic_box('SmallFlatRateBox', True)
        packed_boxes = {med_box: [[sku, sku]],
                        normal_box: [[sku], [sku]]}
        box_dictionary = setup_box_dictionary(packed_boxes)
        expected_return = {
            'flat_rate': Packaging(box=med_box, skus_per_box=[[sku, sku]],
                                 last_parcel=None),
            'package': None
        }
        self.assertEqual(expected_return, box_dictionary)

    def test_setup_box_dictionary_no_packed_boxes(self):
        with self.assertRaises(BoxError) as context:
            setup_box_dictionary({})
        self.assertEqual('There are no packed boxes available to return.',
                         context.exception.message)
