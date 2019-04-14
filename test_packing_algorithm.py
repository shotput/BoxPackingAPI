from collections import namedtuple
from packing_algorithm import (does_it_fit,
    best_fit, pack_boxes, ItemTuple, Packaging, setup_packages)
from errors import BoxError
import unittest


class BoxSelectionAlgorithmTest(unittest.TestCase):

    # Note: item and box dimensions should be input in ascending order
    # ex: item_dims = [1,2,5] == GOOD, item_dims = [2,5,1] == Infinite Loop
    def test_does_it_fit_true(self):
        '''
        test when item does fit, returns True
        '''
        item_dims = [4, 12, 14]
        box_dims = [4, 14, 22]

        self.assertEqual(True, does_it_fit(item_dims, box_dims))

    def test_does_it_fit_false(self):
        '''
        test that when a item does not fit, it returns False
        '''
        item_dims = [4, 12, 14]
        box_dims = [3.99, 14, 14]

        self.assertEqual(False, does_it_fit(item_dims, box_dims))

    def test_best_fit_exact_size(self):
        '''
        assert that if a item is the same size as the box,
        the remaining_dimensions comes back empty
        '''
        item_dims = [13, 13, 31]
        box_dims = [13, 13, 31]

        remaining_space = best_fit(item_dims, box_dims)
        self.assertEqual(remaining_space, [])

    def test_best_fit_half_size(self):
        '''
        assert that if a item is smaller than the box, but has two dimensions
        the same, it will return the empty space
        '''
        item_dims = [13, 13, 31]
        box_dims = [13, 26, 31]

        remaining_space = best_fit(item_dims, box_dims)
        self.assertEqual(remaining_space, [[13, 13, 31]])

    def test_best_fit_multiple_spaces(self):
        '''
        assert that if a item is smaller than the box, but has two dimensions
        the same, it will return the empty space
        '''
        item_dims = [13, 13, 31]
        box_dims = [20, 20, 31]

        remaining_space = best_fit(item_dims, box_dims)
        self.assertEqual(remaining_space, [[7, 13, 31], [7, 20, 31]])

    def test_pack_boxes_one_item(self):
        '''
        test exact fit one item
        '''
        item1 = ItemTuple('Item1', [13, 13, 31], 0)
        item_info = [item1]
        box_dims = [13, 13, 31]

        packed_items = pack_boxes(box_dims, item_info)
        self.assertEqual(packed_items, ([[item1]]))

    def test_pack_boxes_two_item_exact(self):
        '''
        test items will go exactly into box
        '''
        item1 = ItemTuple('Item1', [13, 13, 31], 0)
        item_info = [item1, item1]
        box_dims = [13, 26, 31]

        packed_items = pack_boxes(box_dims, item_info)
        self.assertEqual(packed_items, ([[item1, item1]]))

    def test_pack_boxes_two_item_two_box(self):
        '''
        test two items of same size as box will go into two boxes
        '''
        item = ItemTuple('Item1', [13, 13, 31], 0)
        item_info = [item, item]
        box_dims = [13, 13, 31]

        packed_items = pack_boxes(box_dims, item_info)
        self.assertEqual(packed_items, ([[item], [item]]))

    def test_pack_boxes_three_item_one_box(self):
        '''
        test odd sized items will be rotated to fit
        '''
        item1 = ItemTuple('Item1', [13, 13, 31], 0)
        item2 = ItemTuple('Item2', [8, 13, 31], 0)
        item3 = ItemTuple('Item3', [5, 13, 31], 0)
        item_info = [item1, item2, item3]
        box_dims = [13, 26, 31]
        packed_items = pack_boxes(box_dims, item_info)
        self.assertEqual(packed_items, ([[item1, item2, item3]]))

    def test_pack_boxes_one_overflow(self):
        '''
        tests when there should be one overflow box
        '''
        item = ItemTuple('Item1', [1, 1, 1], 0)
        item_info = [item] * 28
        box_dims = [3, 3, 3]

        packed_items = pack_boxes(box_dims, item_info)
        self.assertEqual([[item] * 27, [item]], packed_items)

    def test_pack_boxes_odd_sizes(self):
        '''
        test odd sized items will be rotated to fit
        '''
        item1 = ItemTuple('Item1', [3, 8, 10], 0)
        item2 = ItemTuple('Item2', [1, 2, 5], 0)
        item3 = ItemTuple('Item3', [1, 2, 2], 0)
        item_info = [item1, item2, item2, item3]
        box_dims = [10, 20, 20]

        packed_items = pack_boxes(box_dims, item_info)
        self.assertEqual([[item1, item2, item2, item3]], packed_items)

    def test_slightly_larger_box(self):
        '''
        test inexact dimensions
        '''
        # Fails due to recursion limits reached
        item = ItemTuple('Item1', [4, 4, 12], 0)
        item_info = [item] * 2
        box_dims = [5, 8, 12]
        # box_dims = [4, 8, 12]  # passes

        packed_items = pack_boxes(box_dims, item_info)
        self.assertEqual(packed_items, ([[item, item]]))

    def test_pack_3_boxes(self):
        '''
        test that multiple parcels will be selected
        '''
        item = ItemTuple('Item1', [4, 4, 12], 0)
        item_info = [item] * 3
        # item_info = [['Item1', [2, 2, 12]]] * 3  # no error
        # item_info = [['Item1', [4, 4, 12]]] * 2  # no error
        box_dims = [4, 4, 12]

        packed_items = pack_boxes(box_dims, item_info)
        self.assertEqual(packed_items, ([[item], [item], [item]]))

    def test_pack_boxes_dim_over_2(self):
        '''
        test that when length of item <= length of box / 2 it packs along
        longer edge
        '''
        item = ItemTuple('Item1', [3, 4, 5], 0)
        item_info = [item] * 4

        box_dims = [6, 8, 10]

        packed_items = pack_boxes(box_dims, item_info)
        self.assertEqual(packed_items, ([[item, item, item, item]]))

    def test_pack_boxes_odd_sizes_again(self):
        '''
        test items with different dimensions will be rotated to fit into one box
        '''
        item1 = ItemTuple('Item1', [1, 18, 19], 0)
        item2 = ItemTuple('Item2', [17, 18, 18], 0)
        item3 = ItemTuple('Item3', [1, 17, 18], 0)
        item_info = [item1, item2, item3]

        box_dims = [18, 18, 19]

        packed_items = pack_boxes(box_dims, item_info)
        self.assertEqual(packed_items, ([[item1, item2, item3]]))

    def test_pack_boxes_100_items(self):
        '''
        test many items into one box with inexact fit
        '''
        item = ItemTuple('Item1', [5, 5, 5], 0)
        item_info = [item] * 100

        box_dims = [51, 51, 6]
        packed_items = pack_boxes(box_dims, item_info)

        self.assertEqual(len(packed_items), 1)

    def test_pack_boxes_100_items_2_boxes(self):
        '''
        test many items separated into 2 boxes with exact fit
        '''
        item = ItemTuple('Item1', [5, 5, 5], 0)
        item_info = [item] * 100

        box_dims = [10, 25, 25]
        packed_items = pack_boxes(box_dims, item_info)

        self.assertEqual(len(packed_items), 2)
        self.assertEqual(len(packed_items[0]), 50)
        self.assertEqual(len(packed_items[1]), 50)

    def test_pack_boxes_big_die_and_several_decks_of_cards(self):
        deck = ItemTuple('deck', [2, 8, 12], 0)
        die = ItemTuple('die', [8, 8, 8], 0)
        item_info = [deck, deck, deck, deck, die]
        box_dims = [8, 8, 12]
        packed_items = pack_boxes(box_dims, item_info)
        self.assertEqual(len(packed_items), 2)
        self.assertEqual(packed_items, [[deck] * 4, [die]])

    def test_pack_boxes_tight_fit_many(self):
        '''
        tests a tight fit for non-cubic items
        '''
        item = ItemTuple('Item1', [1, 3, 3], 0)
        item_info = [item] * 82
        box_dims = [9, 9, 9]
        packed_items = pack_boxes(box_dims, item_info)
        expected_return = [[item] * 81, [item]]
        self.assertEqual(2, len(packed_items))
        self.assertEqual(expected_return, packed_items)

    def test_pack_boxes_tight_fit_many_oblong(self):
        '''
        tests a tight fit for non-cubic items
        '''
        item = ItemTuple('Item1', [1, 2, 3], 0)
        item_info = [item] * 107
        box_dims = [8, 9, 9]
        packed_items = pack_boxes(box_dims, item_info)
        expected_return = [[item] * 106, [item]]
        self.assertEqual(2, len(packed_items))
        self.assertEqual(expected_return, packed_items)

    def test_pack_boxes_tight_fit_many_oblong_inexact(self):
        '''
        tests that the algorithm remains at least as accurate as it already is
        if it were perfect, the first box would have 48 in it
        '''
        item = ItemTuple('Item1', [1, 2, 3], 0)
        item_info = [item] * 49
        box_dims = [4, 8, 9]
        packed_items = pack_boxes(box_dims, item_info)
        self.assertEqual(2, len(packed_items))
        self.assertGreaterEqual(44, len(packed_items[0]))

    def test_pack_boxes_flat_box(self):
        item = ItemTuple('MFuelMock', [1.25, 7, 10], 0)
        item_info = [item] * 3
        box_dims = [3.5, 9.5, 12.5]
        packed_items = pack_boxes(box_dims, item_info)
        self.assertEqual(2, len(packed_items))
        self.assertEqual(2, len(packed_items[0]))


class SetupBoxDictionaryTest(unittest.TestCase):

    def make_generic_box(self, name, volume=None):
        TestBox = namedtuple('TestBox', 'name, description, total_cubic_cm')
        description = 'normal'
        volume = volume if volume is not None else 1000
        return TestBox(name=name, description=description,
                       total_cubic_cm=volume)

    def test_setup_packages(self):
        item = ItemTuple('Item1', [1, 2, 3], 0)
        normal_box = self.make_generic_box('NORM')

        packed_boxes = {normal_box: [[item]]}
        box_dictionary = setup_packages(packed_boxes)
        expected_return = Packaging(
            box=normal_box, items_per_box=[[item]], last_parcel=None)
        self.assertEqual(expected_return, box_dictionary)

    def test_setup_packages_three_flat_rates(self):
        '''
        assert that when there are two flat rates that require a different
        number of boxes, it selects the one that requires the fewest
        '''
        item = ItemTuple('Item1', [1, 2, 3], 0)
        normal_box = self.make_generic_box('NORM')
        packed_boxes = {normal_box: [[item, item]]}
        box_dictionary = setup_packages(packed_boxes)
        expected_return = Packaging(
            box=normal_box, items_per_box=[[item, item]], last_parcel=None)
        self.assertEqual(expected_return, box_dictionary)

    def test_setup_packages_fewest_parcels(self):
        '''
        asserts the the dictionary uses the smallest box with the fewest parcels
        and if flat rate has more parcels, don't even return it.
        '''
        item = ItemTuple('Item1', [1, 2, 3], 0)
        normal_box = self.make_generic_box('NORM')
        smaller_box = self.make_generic_box('Small', volume=500)

        packed_boxes = {normal_box: [[item, item]],
                        smaller_box: [[item], [item]]}
        box_dictionary = setup_packages(packed_boxes)
        expected_return = Packaging(
            box=normal_box, items_per_box=[[item, item]], last_parcel=None)
        self.assertEqual(expected_return, box_dictionary)

    def test_setup_packages_smaller_volume(self):
        '''
        asserts the the dictionary uses the smallest box with the fewest parcels
        '''
        item = ItemTuple('Item1', [1, 2, 3], 0)
        normal_box = self.make_generic_box('NORM')
        bigger_box = self.make_generic_box('Big', volume=2000)
        packed_boxes = {normal_box: [[item, item]],
                        bigger_box: [[item, item]]}
        box_dictionary = setup_packages(packed_boxes)
        expected_return = Packaging(
            box=normal_box, items_per_box=[[item, item]], last_parcel=None)
        self.assertEqual(expected_return, box_dictionary)

    def test_setup_packages_complex(self):
        '''
        asserts that in complex situations, it chooses the smallest,
        fewest parcels, cheapest box.
        '''
        item = ItemTuple('Item1', [1, 2, 3], 0)
        normal_box = self.make_generic_box('NORM')
        smaller_box = self.make_generic_box('Small', volume=500)
        bigger_box = self.make_generic_box('Big', volume=2000)
        packed_boxes = {
            normal_box: [[item, item]],
            bigger_box: [[item, item]],
            smaller_box: [[item], [item]]
        }
        expected_return = Packaging(
            box=normal_box, items_per_box=[[item, item]], last_parcel=None)
        box_dictionary = setup_packages(packed_boxes)
        self.assertEqual(expected_return, box_dictionary)

    def test_setup_packages_no_packed_boxes(self):
        with self.assertRaises(BoxError) as context:
            setup_packages({})
        self.assertEqual('There are no packed boxes available to return.',
                         context.exception.message)
