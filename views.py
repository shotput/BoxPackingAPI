from flask import Blueprint, request, jsonify, current_app
from fulfillment_api import messages as msg
from fulfillment_api.errors import BoxError
from .helper import (compare_1000_times, api_packing_algorithm,
    space_after_packing, how_many_skus_fit, pre_pack_boxes)

from ..authentication.login_required import (login_required,
                                             shotput_permission_required)
from ..crossdomain import crossdomain

blueprint = Blueprint('shipments', __name__)


@blueprint.route('/box_packing_api/simple',
                 methods=['POST', 'OPTIONS'])
@crossdomain(api=True)
@login_required
@shotput_permission_required
def get_best_fit():
    '''
    A non-database calling endpoint which is a simple usage of the box packing
    algorithm which accepts json with skus and a single box.

    Returns:
        'skus_packed': List[Dict[
            skus_packed: Dict[sku, quantity]
            total_weight: float
    '''
    json_data = request.get_json(force=True)
    current_app.log.data(json_data)
    try:
        skus_info = json_data['skus_info']
        box_info = json_data['box_info']
        options = json_data.get('options', {})
    except KeyError as e:
        current_app.log.error(e)
        return jsonify(error=msg.missing_value_for(e)), 400
    try:
        skus_arrangement = pre_pack_boxes(box_info, skus_info, options)
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
    return jsonify(skus_packed=skus_arrangement)


@blueprint.route('/box_packing_api/remaining_volume',
                 methods=['POST', 'OPTIONS'])
@crossdomain(api=True)
@login_required
def get_space_after_packing():
    '''
    Non-database calling endpoint which calculates the remaining volume in a
    block after packing. Assumes box and sku are of same units
    Input:
    {
        "box_info": {
            "width": 9,
            "height": 8,
            "length": 5
        },
        "sku_info": {
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
        sku_info = json_data['sku_info']
        box_info = json_data['box_info']
        space = space_after_packing(sku_info, box_info)
    except KeyError as e:
        current_app.log.error(e)
        return jsonify(error=msg.missing_value_for(e.message)), 400
    except TypeError as e:
        current_app.log.error(e)
        return jsonify(error=msg.invalid_data), 400
    except BoxError as e:
        current_app.log.error(e)
        return jsonify(error=e.message), 400
    return jsonify(space)


@blueprint.route('/box_packing_api/capacity', methods=['POST', 'OPTIONS'])
@crossdomain(api=True)
@login_required
def how_many_fit():
    '''
    non-database hitting endpoint which calculates the capacity of a box
    given a sku size. Assumes dimensional units are the same.
    Same inputs as remaining_volume.
    Outputs:
    {
      "remaining_volume": 72,
      "total_packed": 1
    }
    '''
    json_data = request.get_json(force=True)
    current_app.log.data(json_data)
    sku_info = json_data['sku_info']
    box_info = json_data['box_info']
    max_packed = json_data.get('max_packed')
    try:
        return jsonify(how_many_skus_fit(sku_info, box_info, max_packed))
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


@blueprint.route('/box_packing_api/compare_packing_efficiency',
                 methods=['GET', 'OPTIONS'])
@crossdomain(api=True)
@login_required
@shotput_permission_required
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
def box_packing_api():
    '''
    a full access endpoint to the box algorithm, which accepts boxes and skus
    and returns the best box and the skus arrangement

    Outputs:
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
    json_data = request.get_json(force=True)
    current_app.log.data(json_data)
    try:
        boxes_info = json_data['boxes_info']
        skus_info = json_data['skus_info']
        options = json_data.get('options', {})
        best_package = api_packing_algorithm(boxes_info, skus_info, options)
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
    return jsonify(best_package=best_package)
