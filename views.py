from fulfillment_api.api_verify import verify_box_api
from fulfillment_api.constants import permissions
from fulfillment_api.errors import APIError, BoxError
from fulfillment_api import messages as msg

from ..authentication.login_required import (login_required,
                                             shotput_permission_required)
from ..crossdomain import crossdomain
from ..permissions.decorators import view_requires_team_permission

from .helper import (api_packing_algorithm, compare_1000_times,
                     how_many_items_fit, pre_pack_boxes, space_after_packing)

from flask import Blueprint, current_app, jsonify, request

blueprint = Blueprint('box_packing', __name__)


@blueprint.route('/box_packing_api/basic',
                 methods=['POST', 'OPTIONS'])
@crossdomain(api=True)
@login_required
@verify_box_api
@view_requires_team_permission(permissions.box_packing_read)
def get_best_fit():
    '''
    A non-database calling endpoint which is a simple usage of the box packing
    algorithm which accepts json with items and a single box.

    Returns:
        'packages': List[Dict[
            items_packed: Dict[item, quantity]
            total_weight: float
    '''
    json_data = request.get_json(force=True)
    current_app.log.data(json_data)
    try:
        products_info = json_data['products_info']
        box_info = json_data['box_info']
        options = json_data.get('options', {})
    except KeyError as e:
        current_app.log.error(e)
        return jsonify(error=msg.missing_value_for(e)), 400
    try:
        items_arrangement = pre_pack_boxes(box_info, products_info, options)
    except BoxError as e:
        current_app.log.error(e)
        return jsonify(error=e.message), 400
    except TypeError as e:
        current_app.log.error(e)
        return jsonify(error='Invalid data in request.'), 400
    except ValueError as e:
        current_app.log.error(e)
        value = e.message.split(' ')[-1]
        return jsonify(error=('Invalid data in request. Check value {}'
                              .format(value))), 400
    except KeyError as e:
        current_app.log.error(e)
        return jsonify(error=msg.missing_value_for(e.message))
    except APIError as e:
        current_app.log.error(e)
        return jsonify(error=e.message), e.status_code
    return jsonify(packages=items_arrangement)


@blueprint.route('/box_packing_api/remaining_volume',
                 methods=['POST', 'OPTIONS'])
@crossdomain(api=True)
@login_required
@verify_box_api
@view_requires_team_permission(permissions.box_packing_read)
def get_space_after_packing():
    '''
    Non-database calling endpoint which calculates the remaining volume in a
    block after packing. Assumes box and item are of same units
    Input:
    {
        "box_info": {
            "width": 9,
            "height": 8,
            "length": 5
        },
        "item_info": {
            "width": 9,
            "height": 8,
            "length": 4
        }
    }
    Output:
    {
        "remaining_dimensional_blocks": [
          {
            "height": 8,
            "length": 9,
            "width": 1
          }
        ],
        "remaining_volume": 72
    }

    '''
    json_data = request.get_json(force=True)
    current_app.log.data(json_data)
    try:
        item_info = json_data['product_info']
        box_info = json_data['box_info']
        space = space_after_packing(item_info, box_info)
    except KeyError as e:
        current_app.log.error(e)
        return jsonify(error=msg.missing_value_for(e.message)), 400
    except TypeError as e:
        current_app.log.error(e)
        return jsonify(error=msg.invalid_data), 400
    except BoxError as e:
        current_app.log.error(e)
        return jsonify(error=e.message), 400
    except APIError as e:
        current_app.log.error(e)
        return jsonify(error=e.message), e.status_code
    return jsonify(space)


@blueprint.route('/box_packing_api/capacity', methods=['POST', 'OPTIONS'])
@crossdomain(api=True)
@login_required
@verify_box_api
@view_requires_team_permission(permissions.box_packing_read)
def how_many_fit():
    '''
    non-database hitting endpoint which calculates the capacity of a box
    given a item size. Assumes dimensional units are the same.
    Same inputs as remaining_volume.
    Outputs:
    {
      "remaining_volume": 72,
      "total_packed": 1
    }
    '''
    json_data = request.get_json(force=True)
    current_app.log.data(json_data)
    try:
        item_info = json_data['product_info']
        box_info = json_data['box_info']
        max_packed = json_data.get('max_packed')
        return jsonify(how_many_items_fit(item_info, box_info, max_packed))
    except KeyError as e:
        current_app.log.error(e)
        return jsonify(error=msg.missing_value_for(e.message)), 400
    except TypeError as e:
        current_app.log.error(e)
        return jsonify(error=msg.invalid_data), 400
    except BoxError as e:
        current_app.log.error(e)
        return jsonify(error=e.message)
    except ValueError as e:
        current_app.log.error(e)
        value = e.message.split(' ')[-1]
        return jsonify(error=('Invalid data in request. Check value {}'
                              .format(value))), 400
    except APIError as e:
        current_app.log.error(e)
        return jsonify(error=e.message), e.status_code


@blueprint.route('/box_packing_api/compare_packing_efficiency',
                 methods=['GET', 'OPTIONS'])
@crossdomain(api=True)
@login_required
@shotput_permission_required
@view_requires_team_permission(permissions.global_god_mode)
def compare_pack():
    '''
    endpoint which can be used to verify the accuracy of
    shotput v pyshipping
    '''
    params = request.args.to_dict()
    current_app.log.data(params)
    trials = params.get('trials')
    return jsonify(compare_1000_times(trials))


@blueprint.route('/box_packing_api/full', methods=['POST', 'OPTIONS'])
@crossdomain(api=True)
@login_required
@verify_box_api
@view_requires_team_permission(permissions.box_packing_read)
def box_packing_api():
    '''
    a full access endpoint to the box algorithm, which accepts boxes and items
    and returns the best box and the items arrangement

    Outputs:
        Dict[
           'package_contents': List[Dict[
                packed_prodcuts: Dict[item, quantity]
                total_weight: float
                box: Dict[
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
    json_data = request.get_json(force=True)
    current_app.log.data(json_data)
    try:
        boxes_info = json_data['boxes_info']
        products_info = json_data['products_info']
        options = json_data.get('options', {})
        package_contents = api_packing_algorithm(boxes_info, products_info,
                                                 options)
    except KeyError as e:
        current_app.log.error(e)
        return jsonify(error=msg.missing_value_for(e.message)), 400
    except TypeError as e:
        current_app.log.error(e)
        return jsonify(error=msg.invalid_data), 400
    except BoxError as e:
        current_app.log.error(e)
        return jsonify(error=e.message)
    except ValueError as e:
        current_app.log.error(e)
        value = e.message.split(' ')[-1]
        return jsonify(error=('Invalid data in request. Check value {}'
                              .format(value))), 400
    except APIError as e:
        current_app.log.error(e)
        return jsonify(error=e.message), e.status_code
    return jsonify(package_contents)
