from fulfillment_api.authentication.products.simple_item import (
    get_item_dictionary_from_list)
from fulfillment_api.authentication.shipping_box import ShippingBox
from fulfillment_api.constants import units
from fulfillment_api.errors import BoxError
from fulfillment_api.util.unit_conversion import (convert_dimensional_units,
                                                  convert_mass_units)

from .packing_algorithm import (best_fit, does_it_fit,
                                insert_items_into_dimensions, pack_boxes,
                                packing_algorithm, ItemTuple, volume)

from collections import Counter
from itertools import izip
import math


def space_after_packing(item_info, box_info):
    '''
    returns the remaining space in a box after packing a item and
        the remaining block sizes within the box after an ideal fit
    assumes item and box dimensions are in the same units

    Args:

        product_info (Dict[{
                width: float
                height: float
                length: float
                weight: float
            }])
        box_info (Dict[{
                width: float
                height: float
                length: float
                weight: float
            }])

    Returns
        Dict[{
            'remaining_volume': float
            'remaining_dimensional_blocks': List[List[int, int, int]]
        }]
    '''

    item_dims = sorted([item_info['width'], item_info['height'],
                       item_info['length']])
    box_dims = sorted([box_info['width'], box_info['height'],
                       box_info['length']])

    if not does_it_fit(item_dims, box_dims):
        raise BoxError('Product with dimensions {} does not fit into a box with'
                       ' dimensions {}'
                       .format('X'.join(map(str, item_dims)),
                               'X'.join(map(str, item_dims))))
    remaining_dimensions = best_fit(item_dims, box_dims)
    blocks = [{
        'width': block[0],
        'height': block[1],
        'length': block[2]
    } for block in remaining_dimensions]
    remaining_volume = sum(volume(block) for block in remaining_dimensions)

    return {
        'remaining_volume': remaining_volume,
        'remaining_dimensional_blocks': blocks
    }


def how_many_items_fit(item_info, box_info, max_packed=None):
    '''
    returns the number of of items of a certain size can fit in a box, as well
        as the remaining volume
    assumes item and box dimensions are on in the same units

    Args:

        item_info (Dict[{
                width: float
                height: float
                length: float
                weight: float
            }])
        box_info (Dict[{
                width: float
                height: float
                length: float
                weight: float
            }])
        max_packed (int)

    Returns:
        Dict[{
            total_packed: int
            remaining_volume: float
        }]
    '''
    item_dims = sorted([item_info['width'], item_info['height'],
                       item_info['length']])
    box_dims = sorted([box_info['width'], box_info['height'],
                       box_info['length']])
    remaining_dimensions = [box_dims]
    remaining_volume = volume(box_dims)
    item = ItemTuple(None, item_dims, item_info.get('weight', 0))
    # a list of lists. each nested list is representative of a package
    items_packed = [[]]
    while remaining_dimensions != []:
        for block in remaining_dimensions:
            # items_to_pack is of length 4 at every loop because
            # insert_items_into_dimensions will pack up to 3 items at any given
            # time and then check that there are more items to pack before
            # continuing
            items_to_pack = [item, item, item, item]
            remaining_dimensions, items_packed = insert_items_into_dimensions(
                remaining_dimensions, items_to_pack, items_packed)
            # items_to_pack updates, insert items into dimensions may pack more
            # than one item and therefore we find the difference between the
            # length of the remaining items to pack and the original (4)
            remaining_volume -= volume(item_dims) * (4 - len(items_to_pack))
            if (max_packed is not None and
                    len(items_packed[0]) == int(max_packed)):
                # set remaining dimensions to empty to break from the while loop
                remaining_dimensions = []
                break
    return {
        'total_packed': len(items_packed[0]),
        'remaining_volume': remaining_volume
    }


def dim_to_cm(dim, dimension_units):
    return convert_dimensional_units(float(dim), dimension_units,
                                     to_unit=units.CENTIMETERS)


def weight_of_box_contents(box_contents):
    '''
    returns the weight of the package contents

    Args:
        box_contents (List[item_number])
        item_info (Dict[Dict[{
                'weight_g': int/float
            }]])
    Returns:
        float
    '''
    return sum(float(item.weight) for item in box_contents)


def api_packing_algorithm(boxes_info, items_info, options):
    '''
    non-database calling method which allows checking multiple boxes
    for packing efficiency

    Args:
        session (sqlalchemy.orm.session.Session)
        boxes_info (List[Dict(
                weight: float
                height: float
                length: float
                width: float
                dimension_units: ('inches', 'centimeters', 'feet', 'meters')
                weight_units: ('grams', 'pounds', 'kilograms', 'onces')
                name: String
            )])
        items_info (List[Dict(
                weight: float
                height: float
                length: float
                width: float
                dimension_units: ('inches', 'centimeters', 'feet', 'meters')
                weight_units: ('grams', 'pounds', 'kilograms', 'onces')
                product_name: String
            )])
        options (Dict(
                max_weight: float
            ))

    Returns:
        Dict[
            'package_contents': List[Dict[
                items_packed: Dict[item, quantity]
                total_weight: float
                'best_box': Dict[
                    weight: float
                    height: float
                    length: float
                    width: float
                    dimension_units: ('inches', 'centimeters', 'feet', 'meters')
                    weight_units: ('grams', 'pounds', 'kilograms', 'onces')
                    name: String
                ]
            ]
        ]
    '''
    boxes = []
    items = []
    if len(set(box['name'] for box in boxes_info)) < len(boxes_info):
        # non-unique names for the boxes have been used.
        raise BoxError('Please use unique boxes with unique names')
    min_box_dimensions = [None, None, None]
    for item in items_info:
        dimensions = sorted([float(item['width']), float(item['height']),
                             float(item['length'])])
        weight_units = item['weight_units']
        item_weight = convert_mass_units(float(item['weight']), weight_units,
                                        to_unit='grams')
        items += ([ItemTuple(item['product_name'], dimensions, item_weight)] *
                 item['quantity'])
        min_box_dimensions = [max(a, b) for a, b in izip(dimensions,
                                                         min_box_dimensions)]
    if options is not None:
        max_weight = int(options.get('max_weight', 31710))
    else:
        max_weight = 31710
    for box in boxes_info:
        dimension_units = box.get('dimension_units', units.CENTIMETERS)
        dimensions = sorted([dim_to_cm(box['width'], dimension_units),
                             dim_to_cm(box['length'], dimension_units),
                             dim_to_cm(box['height'], dimension_units)])
        if does_it_fit(min_box_dimensions, dimensions):
            box_weight_g = convert_mass_units(float(box['weight']),
                                              box['weight_units'],
                                              to_unit='grams')
            boxes.append({
                'box': ShippingBox(box['name'], box['name'],
                                   box.get('description', ''), None,
                                   box_weight_g, dimensions[0], dimensions[1],
                                   dimensions[2], 0),
                'dimensions': dimensions
            })
    if len(boxes) == 0:
        raise BoxError('Some of your products are too big for your boxes. '
                       'Please provide larger boxes.')
    # sort boxes by volume
    boxes = sorted(boxes, key=lambda box: volume(box['dimensions']))
    # send everything through the packing algorithm
    box_dictionary = packing_algorithm(items, boxes, max_weight)
    # only return the package, because these boxes don't have description so
    # flat_rate boxes won't be a thing - at least for now
    package_info = box_dictionary['package']
    package_contents_dict = [get_item_dictionary_from_list(parcel)
                             for parcel in package_info.items_per_box]
    package_contents = []
    best_box = [box for box in boxes_info
                if box['name'] == package_info.box.name][0]
    if package_info.last_parcel is not None:
        last_parcel = [box for box in boxes_info
                       if box['name'] == package_info.last_parcel.name][0]
    else:
        last_parcel = None
    for i, parcel in enumerate(package_contents_dict):
        if i == len(package_contents_dict) - 1 and last_parcel is not None:
            selected_box = last_parcel
            total_weight = package_info.last_parcel.weight_g
        else:
            selected_box = best_box
            total_weight = package_info.box.weight_g
        items_packed = {}
        for item, info in parcel.iteritems():
            items_packed[item] = info['quantity']
            total_weight += info['quantity'] * info['item'].weight
        package_contents.append({
            'packed_products': items_packed,
            'total_weight': total_weight,
            'box': selected_box
        })

    return {
        'packages': package_contents
    }


def pre_pack_boxes(box_info, items_info, options):
    '''
    returns the packed items of one specific box based on item_info
    the item info input does not require a db call

    Args
        boxes_info (Dict[
                weight: float
                height: float
                length: float
                width: float
                dimension_units: ('inches', 'centimeters', 'feet', 'meters')
                weight_units: ('grams', 'pounds', 'kilograms', 'onces')
                name: String
            ])
        products_info (List[Dict[
                weight: float
                height: float
                length: float
                width: float
                dimension_units: ('inches', 'centimeters', 'feet', 'meters')
                weight_units: ('grams', 'pounds', 'kilograms', 'onces')
                product_name: String
            ])
        options (Dict[
                max_weight: float
            ])

    Returns
        List[Dict[{
            packed_products: Dict[item, qty],
            total_weight: float
        }]]
    '''
    dimension_units = box_info['dimension_units']
    box_dims = sorted([dim_to_cm(box_info['width'], dimension_units),
                       dim_to_cm(box_info['length'], dimension_units),
                       dim_to_cm(box_info['height'], dimension_units)])
    items_to_pack = []
    weight_units = box_info['weight_units']
    box_weight = convert_mass_units(box_info['weight'], weight_units,
                                    to_unit='grams')
    total_weight = box_weight
    max_weight = options.get('max_weight', 31710)  # given max weight or 70lbs
    for item in items_info:
        dimension_units = item['dimension_units']
        weight_units = item['weight_units']
        sorted_dims = sorted([dim_to_cm(item['height'], dimension_units),
                              dim_to_cm(item['length'], dimension_units),
                              dim_to_cm(item['width'], dimension_units)])
        if not does_it_fit(sorted_dims, box_dims):
            raise BoxError('Some of your items are too big for the box you\'ve'
                           ' selected. Please select a bigger box or contact'
                           ' ops@shotput.com.')
        item['weight_g'] = convert_mass_units(item['weight'], weight_units,
                                             to_unit='grams')
        items_to_pack += [ItemTuple(item['product_name'], sorted_dims,
                         int(item['weight_g']))] * int(item['quantity'])
        total_weight += item['weight_g'] * int(item['quantity'])
    items_to_pack = sorted(items_to_pack, key=lambda item: item.dimensions[2],
                          reverse=True)
    box_dims = sorted(box_dims)
    items_packed = pack_boxes(box_dims, items_to_pack)
    if math.ceil(float(total_weight) / max_weight) > len(items_packed):
        additional_box = []
        for items in items_packed:
            while weight_of_box_contents(items) + box_weight > max_weight:
                if (weight_of_box_contents(additional_box) +
                        items[-1].weight <= max_weight):
                    additional_box.append(items.pop())
                else:
                    items_packed.append(list(additional_box))
                    additional_box = [items.pop()]
        items_packed.append(additional_box)

    parcel_shipments = []
    for items in items_packed:
        item_qty = Counter()
        parcel_weight = box_weight
        for item in items:
            item_qty[item.item_number] += 1
            parcel_weight += item.weight
        parcel_shipments.append({'packed_products': dict(item_qty),
                                 'total_weight': parcel_weight})
    return parcel_shipments


def compare_1000_times(trials=None):
    results = {
        'number_of_parcels': {
            'pyshipping': 0,
            'shotput': 0,
            'tie': 0,
            'errors': []
        },
        'when_tied': {
            'pyshipping': 0,
            'shotput': 0,
            'tie': 0,
            'all_in_one_bin': 0,
            'errors': []
        },
        'time_efficiency': {
            'pyshipping': 0,
            'shotput': 0,
            'tie': 0
        }
    }
    shotput_time = 0
    pyshipping_time = 0
    trials = int(trials or 1000)
    parcels_diff = []
    percent_saved = []
    for _ in xrange(trials):
        returned = compare_pyshipping_with_shotput()
        results['number_of_parcels'][returned['best_results']] += 1
        # interpret data when there is a tie
        if returned['best_results'] == 'tie':
            shotput_last_parcel = returned['shotput']['items_per_parcel'][-1]
            py_last_parcel = returned['pyshipping']['items_per_parcel'][-1]
            if shotput_last_parcel > py_last_parcel:
                winner = 'pyshipping'
                results['when_tied']['errors'].append(returned)
            elif shotput_last_parcel < py_last_parcel:
                winner = 'shotput'
            else:
                winner = 'tie'
                if returned['shotput']['num_parcels'] == 1:
                    results['when_tied']['all_in_one_bin'] += 1
            results['when_tied'][winner] += 1
        if returned['best_results'] == 'pyshipping':
            results['number_of_parcels']['errors'].append(returned)
        fastest = ('shotput', 'pyshipping', 'tie')[(
            returned['shotput']['time'] > returned['pyshipping']['time']) +
            (returned['shotput']['time'] <= returned['pyshipping']['time'])]
        results['time_efficiency'][fastest] += 1
        shotput_time += returned['shotput']['time']
        pyshipping_time += returned['pyshipping']['time']
        saved = (returned['pyshipping']['num_parcels'] -
                 returned['shotput']['num_parcels'])
        if not (returned['best_results'] == 'tie' and
                returned['shotput']['num_parcels'] == 1):
            parcels_diff.append(saved)
            percent_saved.append(float(saved) /
                                 returned['pyshipping']['num_parcels'])

    # regression analysis
    parcels_diff = sorted(parcels_diff)
    percent_saved = sorted(percent_saved)
    parcels_diff_regression = {}
    percent_saved_regression = {}
    sample_size = trials - results['when_tied']['all_in_one_bin']
    parcels_diff_regression['mean'] = sum(parcels_diff) / float(sample_size)
    percent_saved_regression['mean'] = sum(percent_saved) / float(sample_size)
    parcels_diff_regression['median'] = parcels_diff[sample_size / 2 - 1]
    percent_saved_regression['median'] = percent_saved[sample_size / 2 - 1]
    parcels_diff_regression['standard_deviation'] = math.sqrt(sum(
        math.pow(x - parcels_diff_regression['mean'], 2)
        for x in parcels_diff) * (1.0 / float(sample_size)))
    percent_saved_regression['standard_deviation'] = math.sqrt(sum(
        math.pow(x - percent_saved_regression['mean'], 2)
        for x in percent_saved) * (1.0 / float(sample_size)))
    results['parcels_diff_regression'] = parcels_diff_regression
    results['percent_saved_regression'] = percent_saved_regression
    results['shotput_time_avg'] = shotput_time / float(trials)
    results['pyshipping_time_avg'] = pyshipping_time / float(trials)
    return results


def compare_pyshipping_with_shotput():
    from random import randint
    from pyshipping import binpack_simple as binpack
    from pyshipping.package import Package
    from time import time
    items = []
    py_items = []
    box_dims = sorted([randint(100, 200), randint(100, 200),
                       randint(100, 200)])
    num_items = 500
    for _ in xrange(num_items):
        item_dims = sorted([randint(20, 100), randint(20, 100),
                           randint(20, 100)])
        items.append(ItemTuple(str(volume(item_dims)), item_dims, 0))
        py_items.append(Package((item_dims[0], item_dims[1], item_dims[2]), 0))
    start = time()
    items_packed = pack_boxes(box_dims, items)
    end = time()
    shotput = {
        'num_parcels': len(items_packed),
        'items_per_parcel': [len(parcel) for parcel in items_packed],
        'time': end - start
    }
    py_box = Package((box_dims[0], box_dims[1], box_dims[2]), 0)
    start = time()
    py_items_packed = binpack.packit(py_box, py_items)
    end = time()
    pyshipping = {
        'num_parcels': len(py_items_packed[0]),
        'items_per_parcel': [len(parcel) for parcel in py_items_packed[0]],
        'time': end - start
    }
    if len(items_packed) > len(py_items_packed[0]):
        best_results = 'pyshipping'
    elif len(items_packed) < len(py_items_packed[0]):
        best_results = 'shotput'
    else:
        best_results = 'tie'
    return {'shotput': shotput,
            'pyshipping': pyshipping,
            'best_results': best_results}
