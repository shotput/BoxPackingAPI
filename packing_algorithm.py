'''
This module is used for box packing

Uses the theory of first fit decending, rotating skus until they fit
for the first time. The skus are arranged but longest sku first
The boxes are arranged by smallest volume first
dimensions for individual skus, boxes and blocks are always arranged
    smallest to largest -- this is VERY important

data path:
--- from outside the module call packing_algorithm
--- get all the skus and their dimensions
--- select boxes that will probably work based on the longest dimensions of
    any of the skus
--- set a minimum number of boxes by weight, such that no box weights over
    70 pounds - or if the ops team decides on a smaller number
--- iterate through the useable boxes to pack them
    --- until there are no more skus to be packed, iterate through skus to
        pack arranged by sku with longest dimension first
    --- find the best fit for a sku in the box by iterating through the
        dimensions of the box, First check if a sku can fit long ways along
        a box dimension twice[1] then if a sku's longest side fits exactly
        Then if neither work, find the first dimension the sku sku fits into
    --- From there find the remaining dimensions of the box. Checking to
        make sure the sku does not need a specific rotation because of other
        dimenions. find ideal rotation of remaining dimensions based on the
        largest possible volume left over
    --- using the remaining_dimensions, if the smallest sku does not fit,
        disgard the block.
    --- move the sku packed into a list representing the box
    --- iterate through the remaining_dimensions until either there are no
        skus left to pack, or there are no remaining dimensions large enough
        for the skus
        --- if there are no more remaining_dimensions, add an empty box to
            the list of packed skus and begin the process over.
--- After all boxes have been packed, iterate through them to select the
    best box, and best flat rate box
    --- if there is nothing set, set it,
    --- if the number of parcels needed to pack all skus is less than the #
        of parcels needed for the currently set best box, reset the best box
    --- if the number of parcels needed is the same AND the volume of the
        box is less than the best box (OR FLAT_RATE: if the cost of the box
            is less than the cost of the current best box), reset it
    --- return a dictionary containing the best box and it's packed skus
        and if a flat rate box is chosen, a flat rate box and its packed
        skus

[1] - http://www.jstor.org/stable/pdf/223143.pdf, page 257
'''

from fulfillment_api.constants import usps_shipping
from fulfillment_api.errors import BoxError

from collections import namedtuple
from itertools import izip

from flask import current_app


Packaging = namedtuple('Package', 'box, skus_per_box, last_parcel')
SkuTuple = namedtuple('SkuTuple', 'sku_number, dimensions, weight')


def does_it_fit(sku_dims, box_dims):
    '''
    returns a boolean regarding whether or not
    a sku will fit into box_dimensions

    sku and box dimensions in ascending length order

    Args:
        sku_dims (List[int, int,  int])
        box_dims (List[int, int,  int])

    Returns:
        bool: whether or not the sku will fit in the box

    '''
    return all(box_dim >= sku_dim
               for box_dim, sku_dim in izip(box_dims, sku_dims))


def something_fits(skus, box_dims):
    '''
    iterates through all skus to see if one of them will fit in the dimensions
    given

    Args:
        skus (List[SkuTuple])
        box_dims (List[int, int, int])

    Returns
        bool: whether or not any of the skus fit into the box
    '''
    return any(does_it_fit(sku[1], box_dims) for sku in skus)


def get_side_2_side_3(sku_dims, box_dims, side_1):
    '''
    This is a rotation method to rotate the sku first checking if the sku
    MUST be rotated in a specific direction based on size constraints, then
    rotates it so it leaves the largest bulk volume left in the box

    Args:
        sku_dims (List[int, int int])
        box_dims (List[int, int int])
        side_1 (int): index of the side of the box the sku is placed along

    Returns:
        int, int: indexes of the box sides the skus will be placed along

    Exampls:
        >>> get_side_2_side_3([5,5,5], [5,10,10], 0)
        1, 2

        >>> get_side_2_side_3([5,6,8], [5,6,10], 2)
        1, 0
    '''
    if sku_dims[1] > box_dims[side_1 - 1]:
        side_2 = side_1 - 2
        side_3 = side_1 - 1
    elif sku_dims[1] > box_dims[side_1 - 2]:
        side_2 = side_1 - 1
        side_3 = side_1 - 2
    else:
        side_2 = (side_1 + 1) % 3
        side_3 = (side_1 + 2) % 3
    return side_2, side_3


def volume(dimensions):
    '''
    returns the volume of sku or box dimensions
    assumes its a rectangular prism

    Args:
        dimensions (List[int, int, int])

    Returns:
        int: volume
    '''
    return reduce(lambda x, y: x * y, dimensions)


def best_fit(sku_dims, box_dims):
    '''
    assumes sku_dims and box_dims in order shortest to longest

    finds the shortest length of the box that is as long as the
        longest length of the sku

    uses first fit, then rotates for remaining largest volume block
    returns a list of the remaining dimensions in the box

    Args:
        sku_dims (List[int, int, int]): sorted sku dimensions
        box_dims (List[int, int, int]): sorted box dimensions
    Returns
        List[List[int, int, int],
             List[int, int, int],
             List[int, int, int]]: a list of the dimensions left in the box
                after a sku has been placed inside of it

    example:
        >>> best_fit([5,5,5], [10,10,10])
        [[5,5,5], [5,5,10], [5,10,10]]
    '''

    side_1 = None  # side of the box that we lay longest dimension of sku on
    blocks = []  # potential remaining dimensions
    # rotate box until we can set the skus longest side
    box_dims = list(box_dims)
    for i, b_dim in enumerate(box_dims):
        # choose the shortest side of the box we can stack the sku twice
        # on its longest side
        # based on theory of if b_dim / 2 >= s_dim, don't open a new bin
        #   (or don't rotate the box)
        if b_dim >= sku_dims[2] * 2:
            side_1 = i
            # block_1 is the upper layer of the box
            block_1 = sorted([box_dims[side_1] - sku_dims[2],
                              box_dims[i - 1], box_dims[i - 2]])
            blocks.append(block_1)
            # reset the box dimensions to being the height of the sku
            box_dims[i] = sku_dims[2]
            break

        elif b_dim == sku_dims[2]:
            # exact fit, move to next block
            side_1 = i
            break

    if side_1 is None:
        for i, b_dim in enumerate(box_dims):
            # if we can't do that, chose the shortest side of the box we can
            # stack the sku once on it's longest side
            if b_dim >= sku_dims[2]:
                side_1 = i
                block_1 = sorted([box_dims[side_1] - sku_dims[2],
                                  sku_dims[1], sku_dims[0]])
                blocks.append(block_1)
                break

    side_2, side_3 = get_side_2_side_3(sku_dims, box_dims, side_1)

    # option one for remaining dimensions
    block_2a = sorted([box_dims[side_1],
                       box_dims[side_2],
                       box_dims[side_3] - sku_dims[0]])
    block_3a = sorted([box_dims[side_1],
                       box_dims[side_2] - sku_dims[1],
                       sku_dims[0]])

    # option two for remaining dimensions
    block_2b = sorted([box_dims[side_1],
                       box_dims[side_2] - sku_dims[1],
                       box_dims[side_3]])
    block_3b = sorted([box_dims[side_1],
                       box_dims[side_3] - sku_dims[0],
                       sku_dims[1]])

    # select the option where block_2 and block_3 are closest in size
    # this operator has been tested and is 5-15% more accurate than
    # if volume(block_2a) > volume(block_2b)
    # DO NOT REVERT
    if volume(block_2a) < volume(block_2b):
        blocks.append(block_2a)
        blocks.append(block_3a)
    else:
        blocks.append(block_2b)
        blocks.append(block_3b)

    remaining_dimensions = []
    for block in blocks:
        # if the blocks smallest dimension is not 0, it has volume
        # and the block should be appended
        if block[0] != 0:
            remaining_dimensions.append(block)
    # sort unsorted_remaining_dimensions by volume
    remaining_dimensions = sorted(remaining_dimensions,
                                  key=lambda block: volume(block))
    return remaining_dimensions


def insert_skus_into_dimensions(remaining_dimensions, skus_to_pack,
                                skus_packed):
    block = remaining_dimensions[0]
    for sku in skus_to_pack:
        if does_it_fit(sku.dimensions, block):
            # if the sku fits, pack it, remove it from the skus to pack
            skus_packed[-1].append(sku)
            skus_to_pack.remove(sku)
            # find the remaining dimensions in the box after packing
            left_over_dimensions = best_fit(sku.dimensions, block)
            for left_over_block in left_over_dimensions:
                # only append left over block if at least one sku fits
                if something_fits(skus_to_pack, left_over_block):
                    remaining_dimensions.append(left_over_block)
            # if a sku fits, remaining dimensions will have changed
            # break out of loop
            break
    # remove the block from that remaining dimensions
    remaining_dimensions.pop(0)
    return remaining_dimensions, skus_packed


def pack_boxes(box_dimensions, skus_to_pack):
    '''
    while loop to pack boxes
    The first available dimension to pack is the box itself.
    When you pack a sku into a box, find the best fit, which will change the
        dimensions available to pack skus into
    While there are still skus to pack and dimensions large enough to hold at
        least one of the skus, it will continue to pack the same box
    If there is no remaining space in the box large enough for a sku, a new
        dimension will be added to available
    After there are no more skus needing to be packed, returns a list lists of
        the skus in there 'boxes' (first box is first nested list, second is
        the second, etc.)
    Args:
        box_dimensions (List[int, int, int]): sorted list of box dimensions
        skus_to_pack (List[SkuTuple]): list of skus to pack as SkuTuples
            sorted by longest dimension
    returns:
        List[List[SimpleSku]]: list of lists including the skus in the
            number of boxes the are arranged into
    example:
    >>> pack_boxes([5,5,10], [[sku1, [5,5,10]], sku2, [5,5,6],
                   [sku3, [5,5,4]])
    [[sku1], [sku2, sku3]]
    '''
    # remaining_dimensions represents the available space into which skus can go
    # in List[List[int, int, int],] form where each nested List is a dimensional
    # block where space remains to be filled.
    remaining_dimensions = []
    skus_packed = []  # the skus that have been packed
    skus_to_pack_copy = list(skus_to_pack)
    while len(skus_to_pack_copy) > 0:
        current_app.log.info('len(skus_to_pack_copy): {}\nlen(skus_packed): {}'
                             .format(len(skus_to_pack_copy), len(skus_packed)))
        # keep going until there are no more skus to pack
        if len(remaining_dimensions) == 0:
            # if there is no room for more skus in the last parcel,
            # append an empty parcel with the full box dimensions
            # and append an empty parcel to the list of skus packed
            remaining_dimensions = [box_dimensions]
            skus_packed.append([])
        # iterate through remaining dimensions to pack boxes
        for block in remaining_dimensions:
            remaining_dimensions, skus_packed = insert_skus_into_dimensions(
                remaining_dimensions, skus_to_pack_copy, skus_packed)
    return skus_packed


def compare_flat_rate_prices(zone, box, best_flat_rate_box):
    '''
    format key for FLAT_RATE_COSTS dict
    if description is flat rate, take the sku number
    if it is not, format based on the zone and box

    Args:
        zone (int): usps zone based on Shotput Warehouse location in Oakland
        box (ShippingBox): a flat rate shipping box
        best_flat_rate_box (ShippingBox or None): previously selected best
            flat rate box
    Returns:
        ShippingBox: the flat/regional rate shipping box with the best rate
    '''
    if best_flat_rate_box is None:
        return box

    if box.description == usps_shipping.FLAT_RATE:
        box_key = box.name
    elif box.description == usps_shipping.REGIONAL_RATE:
        if zone is None:
            # we don't need to compare regional boxes
            return best_flat_rate_box
        box_key = '{}_{}'.format(box.name[-1], zone)
    # get the cost of the box in question
    box_cost = usps_shipping.FLAT_RATE_COSTS[box_key]
    # format key
    if best_flat_rate_box.description == usps_shipping.FLAT_RATE:
        best_box_key = best_flat_rate_box.name
    elif best_flat_rate_box.description == usps_shipping.REGIONAL_RATE:
        best_box_key = '{}_{}'.format(best_flat_rate_box.name[-1], zone)
    # get the cost for the current best box
    best_box_cost = usps_shipping.FLAT_RATE_COSTS[best_box_key]

    # return the cheaper box
    return best_flat_rate_box if box_cost > best_box_cost else box


def setup_box_dictionary(packed_boxes, zone=None):
    if len(packed_boxes) == 0:
        raise BoxError('There are no packed boxes available to return.')
    best_boxes = {}
    # determine best flat rate and best package
    for box, packed_skus in packed_boxes.iteritems():
        is_flat_rate = box.description in usps_shipping.USPS_BOXES
        key = 'flat_rate' if is_flat_rate else 'package'
        min_boxes = best_boxes.get(key, {}).get('num_parcels')

        # if there are no boxes set, min boxes will be None,
        # and box_packs_better will be True
        box_packs_better = (len(packed_skus) < min_boxes
                            if min_boxes is not None else True)

        box_packs_same = (len(packed_skus) == min_boxes
                          if min_boxes is not None else True)

        if box_packs_better:
            # set the new best box
            best_boxes[key] = {
                'box': box,
                'num_parcels': len(packed_skus)
            }
        elif box_packs_same:
            # check a few comparisons
            if is_flat_rate:
                # check to see which one is cheapest
                best_boxes[key]['box'] = compare_flat_rate_prices(
                    zone, box, best_boxes[key]['box'])

            elif box.total_cubic_cm < best_boxes[key]['box'].total_cubic_cm:
                best_boxes[key]['box'] = box
            # else the box is not smaller
        # else the box does not pack better

    # set up box dictionary
    box_dictionary = {
        'flat_rate': None,
        'package': None
    }
    best_flat_rate = best_boxes.get('flat_rate')
    best_package = best_boxes.get('package')
    if (best_package is not None and
            (best_flat_rate is None or
            best_package['num_parcels'] <= best_flat_rate['num_parcels'])):
        box_dictionary['package'] = Packaging(best_package['box'],
            packed_boxes[best_package['box']], None)

    if (best_flat_rate is not None and
            (best_package is None or
            best_flat_rate['num_parcels'] <= best_package['num_parcels'])):
        box_dictionary['flat_rate'] = Packaging(best_flat_rate['box'],
            packed_boxes[best_flat_rate['box']], None)
    return box_dictionary


def packing_algorithm(unordered_skus, useable_boxes, max_weight,
                      zone=None):
    '''
    from skus provided, and boxes available, pack boxes with skus

    - returns a dictionary of boxes with an 2D array of skus packed
        in each parcel

    Args:
        unordered_skus (List[SkuTuple])
        useable_boxes (List(Dict[{
            'dimensions': List(int, int, int)
            'box': ShippingBox
        }]))
        min_boxes_by_weight (Int)
        zone (Int?)

    Raises:
        BoxError when no box could fit some SKU.

    Example:
    >>> packing_algorithm([sku1, sku2], [], {sku1: 1, sku2: 3}, True)
    {
        'package': (box=<best_standard_box object>,
                    skus_per_box= [[SkuTuple, SkuTuple], [SkuTuple, SkuTuple]],
                    last_parcel=<smaller_box object>),
        'flat_rate': (box=<best_flat_rate object>,
                      skus_per_box=[[SkuTuple], [SkuTuple, SkuTuple, SkuTuple]],
                      last_parcel=None)
    }
    '''
    packed_boxes = {}
    # sort skus by longest dimension, longest first
    skus_to_pack = sorted(unordered_skus, key=lambda sku: sku.dimensions[2],
                          reverse=True)
    # pack the biggest skus first then progressively pack the smaller ones
    for box_index, box_dict in enumerate(useable_boxes):
        current_app.log.info('Trying box {}'.format(box_index))
        box = box_dict['box']
        packed_skus = pack_boxes(box_dict['dimensions'], skus_to_pack)
        current_app.log.info('Boxes packed')
        # additional box starts as the last parcel
        additional_box = []
        for skus in packed_skus:
            # if the weight of the contents of the box are greater than the
            # given max weight
            if sum(sku.weight for sku in skus) + box.weight_g > max_weight:
                if ((sum(sku.weight for sku in additional_box) +
                        float(skus[-1].weight) + box.weight_g) <= max_weight):
                    # if the additional box weight + the last sku is less than
                    # the max weight, add it to the box
                    additional_box.append(skus.pop())
                else:
                    # else start a new box and append the additional box to the
                    # packed_skus
                    packed_skus.append(additional_box)
                    additional_box = [skus.pop()]
        if len(additional_box) > 0:
            packed_skus.append(additional_box)
        packed_boxes[box_dict['box']] = packed_skus

    current_app.log.info('Setting up box dictionary')

    box_dictionary = setup_box_dictionary(packed_boxes, zone)

    # repack the last parcel into a smaller box
    if (box_dictionary['package'] is not None and
            len(box_dictionary['package'].skus_per_box) > 1):
        package = box_dictionary['package']
        # repack the last parcels, see if they should go in a smaller box
        smallest_skus_to_pack = package.skus_per_box[-1]
        for box_dict in useable_boxes:
            # using non-flat rate boxes and those already smaller than the
            # currently set box
            smaller_box = box_dict['box']
            if (smaller_box.description not in usps_shipping.USPS_BOXES and
                    smaller_box.total_cubic_cm < package.box.total_cubic_cm):
                packed_skus = pack_boxes(box_dict['dimensions'],
                                         smallest_skus_to_pack)
                if len(packed_skus) == 1:
                    box_dictionary['package'] = package._replace(
                        last_parcel=smaller_box)
                    break

    return box_dictionary
