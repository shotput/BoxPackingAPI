from fulfillment_api.authentication.shipping_box import ShippingBox
from fulfillment_api.constants import usps_shipping, units
from fulfillment_api.errors import BoxError
import fulfillment_api.messages as msg
from .helper import api_packing_algorithm
from .packing_algorithm import does_it_fit, packing_algorithm, ItemTuple

from itertools import izip
from sqlalchemy import or_


def is_packing_valid(item_quantities, box):
    items = []
    for item, quantity in item_quantities.iteritems():
        items.append({
            'product_name': item.id,

            'weight': item.weight_g,
            'weight_units': units.GRAMS,

            'width': item.width_cm,
            'height': item.height_cm,
            'length': item.length_cm,
            'dimension_units': units.CENTIMETERS,

            'quantity': quantity
        })
    try:
        packing = api_packing_algorithm([box], items, None)
        return len(packing['packages']) == 1
    except BoxError:
        return False
    return True


def select_useable_boxes(session, min_box_dimensions, team,
                         flat_rate_okay=False):
    '''
    queries the database for boxes that match criteria team, flat_rate, and size

    Args:
        session (sqlalchemy.orm.session.Session)
        min_box_dimensions (List[int, int, int])
        team (Team),
        flat_rate_okay (Boolean)

    Returns:
        List[Dict[{'box': ShippingBox,
                   'dimensions': List[int, int, int]}]]: a list of useable
            shipping boxes and their dimensions
    '''
    useable_boxes = []
    shipping_query = session.query(ShippingBox).filter(
        or_(ShippingBox.width_cm >= min_box_dimensions[2],
            ShippingBox.height_cm >= min_box_dimensions[2],
            ShippingBox.length_cm >= min_box_dimensions[2]),
        ShippingBox.is_available.is_(True),
        or_(ShippingBox.team_id == team.id,
            ShippingBox.team_id.is_(None)))
    if not flat_rate_okay:
        # only select boxes that are not flat or regional rate
        shipping_query = shipping_query.filter(
            ~ShippingBox.description.in_(usps_shipping.USPS_BOXES))

    boxes = shipping_query.all()

    for box in boxes:
        box_dims = sorted([box.width_cm, box.height_cm, box.length_cm])
        # make sure we only look at boxes where every item will fit
        if does_it_fit(min_box_dimensions, box_dims):
            useable_boxes.append({'box': box, 'dimensions': box_dims})
    # sort boxes by volume, smallest first and return
    return sorted(useable_boxes, key=lambda box: box['box'].total_cubic_cm)


def shotput_packing_algorithm(session, team, qty_per_item, flat_rate_okay=False,
                              zone=None, preferred_max_weight=None):
    '''
    from items provided, and boxes available, pack boxes with items

    - returns a dictionary of boxes with an 2D array of items packed
        in each parcel

    Args:
        session (sqlalchemy.orm.session.Session)
        team (Team)
        qty_per_item (Dict[str, Dict[{
            'item': SimpleItem,
            'quantity': int
        }]]): quantity of each item needing to be packed
        flat_rate_okay (boolean): whether or not usps flat and regional rate
            boxes can be used
        zone (int): usps regional shipping zone based on shotput Warehouse
        preferred_max_weight (int): max weight of a parcel if not 70lbs

    Returns:
        Dict[{
            package (Packaging[ShippingBox, List[List], ShippingBox]
            flat_rate (Packaging[ShippingBox, List[List], ShippingBox]
        }]

    Example:
    >>> shotput_packing_algorithm(session, team1, {item1: 1, item2: 3}, True)
    {
        'package': (box=<best_standard_box object>,
                    items_per_box= [[item1, item2], [item2, item2]],
                    last_parcel=<smaller_box object),
        'flat_rate': (box=<best_flat_rate object>,
                      items_per_box=[[item1], [item2, item2, item2]],
                      last_parcel=None)
    }
    '''
    unordered_items = []
    max_weight = preferred_max_weight or 31710
    min_box_dimensions = [None, None, None]

    for item_number, item_data in qty_per_item.iteritems():

        dimensions = sorted([item_data['item'].width_cm,
                             item_data['item'].height_cm,
                             item_data['item'].length_cm])
        min_box_dimensions = [max(a, b) for a, b in izip(dimensions,
                                                         min_box_dimensions)]
        unordered_items += ([ItemTuple(item_data['item'], dimensions,
                            item_data['item'].weight_g)] *
                           int(item_data['quantity']))

    useable_boxes = select_useable_boxes(session, min_box_dimensions, team,
                                         flat_rate_okay)
    # if weight is greater than max, make sure we are separating it into
    # multiple boxes

    if len(useable_boxes) == 0:
        raise BoxError(msg.boxes_too_small)

    box_dictionary = packing_algorithm(unordered_items, useable_boxes,
                                       max_weight, zone)
    if box_dictionary['package'] is not None:
        items_per_box = [[item.item_number for item in parcel]
                        for parcel in box_dictionary['package'].items_per_box]
        box_dictionary['package'] = box_dictionary['package']._replace(
            items_per_box=items_per_box)
    if box_dictionary['flat_rate'] is not None:
        items_per_box = [[item.item_number for item in parcel]
                        for parcel in box_dictionary['flat_rate'].items_per_box]
        box_dictionary['flat_rate'] = box_dictionary['flat_rate']._replace(
            items_per_box=items_per_box)

    return box_dictionary
