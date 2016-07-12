from .helper import (compare_1000_times, api_packing_algorithm,
    space_after_packing, how_many_skus_fit)
from flask import Blueprint, request, jsonify, current_app
from fulfillment_api import messages as msg
from fulfillment_api.errors import BoxError
from ..authentication.login_required import (login_required,
                                             shotput_permission_required)
from ..crossdomain import crossdomain

blueprint = Blueprint('shipments', __name__)


@blueprint.route('/box_packing_api/pre_pack_boxes',
                 methods=['POST', 'OPTIONS'])
@crossdomain(api=True)
@login_required
@shotput_permission_required
def get_best_fit():
    '''
    A non-database calling
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
        "space": {
        "remaining_dimensional_blocks": [
          {
            "height": 8,
            "length": 9,
            "width": 1
          }
        ],
        "remaining_volume": 72
      }
    }
    '''
    json_data = request.get_json(force=True)
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
    return jsonify(space=space)


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
    sku_info = json_data['sku_info']
    box_info = json_data['box_info']
    return jsonify(how_many_skus_fit(sku_info, box_info))


@blueprint.route('/box_packing_api/compare_packing_efficiency',
                 methods=['GET', 'OPTIONS'])
@crossdomain(api=True)
@login_required
@shotput_permission_required
def compare_pack():
    '''
    and endpoint which can be used to verify the accuracy of
    shotput v pyshipping
    '''
    params = request.args.to_dict()
    current_app.log.data(params)
    trials = params.get('trials')
    return jsonify(compare_1000_times(trials))


@blueprint.route('/box_packing_api', methods=['POST', 'OPTIONS'])
@crossdomain(api=True)
@login_required
def box_packing_api():
    json_data = request.get_json(force=True)
    session = request.session
    try:
        boxes_info = json_data['boxes_info']
        skus_info = json_data['skus_info']
        options = json_data.get('options', {})
        best_package = api_packing_algorithm(session, boxes_info, skus_info,
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
    return jsonify(best_package=best_package)
