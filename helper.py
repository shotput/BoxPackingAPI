from fulfillment_api.authentication.shipping_box import ShippingBox
from fulfillment_api.constants import usps_shipping, units
from fulfillment_api.errors import BoxError
import fulfillment_api.messages as msg
from fulfillment_api.util.unit_conversion import (convert_dimensional_units,
                                                  convert_mass_units)

from .packing_algorithm import (packing_algorithm, does_it_fit, SkuTuple,
                                volume, pack_boxes, best_fit,
                                insert_skus_into_dimensions)

from collections import Counter
from itertools import izip
import math


def space_after_packing(sku_info, box_info):
    '''
    returns the remaining space in a box after packing a sku and
        the remaining block sizes within the box after an ideal fit
    assumes sku and box dimensions are in the same units

    Args:

        sku_info (Dict[{
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

    sku_dims = sorted([sku_info['width'], sku_info['height'],
                       sku_info['length']])
    box_dims = sorted([box_info['width'], box_info['height'],
                       box_info['length']])

    if does_it_fit(sku_dims, box_dims):
        remaining_dimensions = best_fit(sku_dims, box_dims)
        blocks = [{
            'width': block[0],
            'height': block[1],
            'length': block[2]
        } for block in remaining_dimensions]
        remaining_volume = sum(volume(block) for block in remaining_dimensions)
    else:
        raise BoxError('Sku with dimensions {} does not fit into a box with '
                       'dimensions {}'.format('X'.join(sku_dims),
                                              'X'.join(box_dims)))
    return {
        'remaining_volume': remaining_volume,
        'remaining_dimensional_blocks': blocks
    }


def how_many_skus_fit(sku_info, box_info, max_packed=None):
    '''
    returns the number of of skus of a certain size can fit in a box, as well
        as the remaining volume
    assumes sku and box dimensions are on in the same units

    Args:

        sku_info (Dict[{
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
    sku_dims = sorted([sku_info['width'], sku_info['height'],
                       sku_info['length']])
    box_dims = sorted([box_info['width'], box_info['height'],
                       box_info['length']])
    remaining_dimensions = [box_dims]
    remaining_volume = volume(box_dims)
    sku = SkuTuple(None, sku_dims, sku_info.get('weight', 0))
    skus_packed = [[]]
    while remaining_dimensions != []:
        # skus_to_pack is of length 4 at every loop so there will be enough to
        # fill each of the remaining blocks
        for block in remaining_dimensions:
            skus_to_pack = [sku, sku, sku, sku]
            remaining_dimensions, skus_packed = insert_skus_into_dimensions(
                remaining_dimensions, skus_to_pack, skus_packed)
            # skus_to_pack updates, insert skus into dimensions may pack more
            # tahn one sku
            remaining_volume -= volume(sku_dims) * (4 - len(skus_to_pack))
            if max_packed is not None and len(skus_packed[0]) == max_packed:
                break
    return {
        'total_packed': len(skus_packed[0]),
        'remaining_volume': remaining_volume
    }


def get_sku_dictionary_from_list(skus):
    '''
    Takes a list of SimpleSkus and translates into dictionary format

    Args:
        skus (List[SimpleSku])
    Returns
        Dict[str, Dict[{
            'sku': SimpleSku,
            'quantity': int
        }]]

        A dictionary with sku numbers as keys and a dict with 'sku' and
        'quantity', containing the related SimpleSku and the quantity originally
        in `skus`.
    '''
    simple_skus = {}
    qty_per_sku = Counter()
    for sku in skus:
        qty_per_sku[sku.sku_number] += 1
        if sku.sku_number not in simple_skus:
            simple_skus[sku.sku_number] = sku
    return {sku_number: {'sku': sku, 'quantity': qty_per_sku[sku_number]}
            for sku_number, sku in simple_skus.iteritems()}


def dim_to_cm(dim, dimension_units):
    return convert_dimensional_units(float(dim), dimension_units,
                                     to_unit=units.CENTIMETERS)


def weight_of_box_contents(box_contents):
    '''
    returns the weight of the package contents

    Args:
        box_contents (List[sku_number])
        sku_info (Dict[Dict[{
                'weight_g': int/float
            }]])
    Returns:
        float
    '''
    return sum(float(sku.weight) for sku in box_contents)


def api_packing_algorithm(boxes_info, skus_info, options):
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
                name: Sting
            )])
        skus_info (List[Dict(
                weight: float
                height: float
                length: float
                width: float
                dimension_units: ('inches', 'centimeters', 'feet', 'meters')
                weight_units: ('grams', 'pounds', 'kilograms', 'onces')
                sku_number: Sting
            )])
        options (Dict(
                max_weight: float
            ))

    Returns:
        Dict[
            'best_box': Dict[
                weight: float
                height: float
                length: float
                width: float
                dimension_units: ('inches', 'centimeters', 'feet', 'meters')
                weight_units: ('grams', 'pounds', 'kilograms', 'onces')
                name: Sting
            ]
            'package_contents': List[Dict[
                skus_packed: Dict[sku, quantity]
                total_weight: float
            ],
            'last_parcel': Dict[
                weight: float
                height: float
                length: float
                width: float
                dimension_units: ('inches', 'centimeters', 'feet', 'meters')
                weight_units: ('grams', 'pounds', 'kilograms', 'onces')
                name: Sting
            ]
        ]
    '''
    boxes = []
    skus = []
    if len(set(box['name'] for box in boxes_info)) < len(boxes_info):
        # non-unique names for the boxes have been used.
        raise BoxError('Please use unique names for your boxes')
    min_box_dimensions = [None, None, None]
    for sku in skus_info:
        dimensions = sorted([float(sku['width']), float(sku['height']),
                             float(sku['length'])])
        weight_units = sku['weight_units']
        sku_weight = convert_mass_units(float(sku['weight']), weight_units,
                                        to_unit='grams')
        skus += ([SkuTuple(sku['sku_number'], dimensions, sku_weight)] *
                 sku['quantity'])
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
        raise BoxError('Some of your skus are too big for your boxes, Please '
                       'provide larger boxes.')
    # sort boxes by volume
    boxes = sorted(boxes, key=lambda box: volume(box['dimensions']))
    # send everything through the packing algorithm
    box_dictionary = packing_algorithm(skus, boxes, max_weight)
    # only return the package, because these boxes don't have description so
    # flat_rate boxes won't be a thing - at least for now
    package_info = box_dictionary['package']
    package_contents_dict = [get_sku_dictionary_from_list(parcel)
                             for parcel in package_info.skus_per_box]
    package_contents = []
    for parcel in package_contents_dict:
        skus_packed = {}
        total_weight = package_info.box.weight_g
        for sku, info in parcel.iteritems():
            skus_packed[sku] = info['quantity']
            total_weight += info['quantity'] * info['sku'].weight
        package_contents.append({
            'skus_packed': skus_packed,
            'total_weight': total_weight
        })

    best_box = [box for box in boxes_info
                if box['name'] == package_info.box.name][0]
    if package_info.last_parcel is not None:
        last_parcel = [box for box in boxes_info
                       if box['name'] == package_info.last_parcel.name][0]
    else:
        last_parcel = None
    return {
        'best_box': best_box,
        'package_contents': package_contents,
        'last_parcel': last_parcel
    }


def pre_pack_boxes(box_info, skus_info, options):
    '''
    returns the packed skus of one specific box based on sku_info
    the sku info input does not require a db call

    List[int, int, int], List[Dict[str, str], Dict[str, str] -> List[List[int]]
    '''
    dimension_units = box_info['dimension_units']
    box_dims = sorted([dim_to_cm(box_info['width'], dimension_units),
                       dim_to_cm(box_info['length'], dimension_units),
                       dim_to_cm(box_info['height'], dimension_units)])
    skus_to_pack = []
    weight_units = box_info['weight_units']
    box_weight = convert_mass_units(box_info['weight'], weight_units,
                                    to_unit='grams')
    total_weight = box_weight
    max_weight = options.get('max_weight', 31710)  # given max weight or 70lbs
    for sku_number, info in skus_info.iteritems():
        dimension_units = info['dimension_units']
        weight_units = info['weight_units']
        sorted_dims = sorted([dim_to_cm(info['height'], dimension_units),
                              dim_to_cm(info['length'], dimension_units),
                              dim_to_cm(info['width'], dimension_units)])
        if not does_it_fit(sorted_dims, box_dims):
            raise BoxError('Some of your skus are too big for the box you\'ve'
                           ' selected. Please select a bigger box or contact'
                           ' ops@shotput.com.')
        info['weight_g'] = convert_mass_units(info['weight'], weight_units,
                                              to_unit='grams')
        skus_to_pack += [SkuTuple(sku_number, sorted_dims,
                         int(info['weight_g']))] * int(info['quantity'])
        total_weight += info['weight_g'] * int(info['quantity'])
    skus_to_pack = sorted(skus_to_pack, key=lambda sku: sku[1][2], reverse=True)
    box_dims = sorted(box_dims)
    skus_packed = pack_boxes(box_dims, skus_to_pack)
    if math.ceil(float(total_weight) / max_weight) > len(skus_packed):
        additional_box = []
        for skus in skus_packed:
            while weight_of_box_contents(skus) > max_weight:
                if (weight_of_box_contents(additional_box) +
                        float(skus[-1].weight) <= max_weight):
                    additional_box.append(skus.pop())
                else:
                    skus_packed.append([sku for sku in additional_box])
                    additional_box = [skus.pop()]
        skus_packed.append(additional_box)

    parcel_shipments = []
    for skus in skus_packed:
        sku_qty = Counter()
        parcel_weight = box_weight
        for sku in skus:
            sku_qty[sku.sku_number] += 1
            parcel_weight += sku.weight
        parcel_shipments.append({'packed_skus': dict(sku_qty),
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
            shotput_last_parcel = returned['shotput']['skus_per_parcel'][-1]
            py_last_parcel = returned['pyshipping']['skus_per_parcel'][-1]
            if shotput_last_parcel > py_last_parcel:
                winner = 'pyshipping'
                # results['when_tied']['errors'].append(returned)
            elif shotput_last_parcel < py_last_parcel:
                winner = 'shotput'
            else:
                winner = 'tie'
                if returned['shotput']['num_parcels'] == 1:
                    results['when_tied']['all_in_one_bin'] += 1
            results['when_tied'][winner] += 1
        # if returned['best_results'] == 'pyshipping':
        #     results['number_of_parcels']['errors'].append(returned)
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
    skus = []
    py_skus = []
    box_dims = sorted([randint(100, 200), randint(100, 200),
                       randint(100, 200)])
    num_skus = 500
    for _ in xrange(num_skus):
        sku_dims = sorted([randint(20, 100), randint(20, 100),
                           randint(20, 100)])
        skus.append(SkuTuple(str(volume(sku_dims)), sku_dims, 0))
        py_skus.append(Package((sku_dims[0], sku_dims[1], sku_dims[2]), 0))
    start = time()
    skus_packed = pack_boxes(box_dims, skus)
    end = time()
    shotput = {
        'num_parcels': len(skus_packed),
        'skus_per_parcel': [len(parcel) for parcel in skus_packed],
        'time': end - start
    }
    py_box = Package((box_dims[0], box_dims[1], box_dims[2]), 0)
    start = time()
    py_skus_packed = binpack.packit(py_box, py_skus)
    end = time()
    pyshipping = {
        'num_parcels': len(py_skus_packed[0]),
        'skus_per_parcel': [len(parcel) for parcel in py_skus_packed[0]],
        'time': end - start
    }
    if len(skus_packed) > len(py_skus_packed[0]):
        best_results = 'pyshipping'
    elif len(skus_packed) < len(py_skus_packed[0]):
        best_results = 'shotput'
    else:
        best_results = 'tie'
    return {'shotput': shotput,
            'pyshipping': pyshipping,
            'best_results': best_results}
