from .helper import (compare_1000_times, api_packing_algorithm,
    space_after_packing, how_many_skus_fit)
from flask import Blueprint, request, jsonify, current_app

from ..authentication.login_required import (login_required,
                                             shotput_permission_required)
from ..crossdomain import crossdomain

blueprint = Blueprint('shipments', __name__)


@blueprint.route('/pack_boxes/remaining_volume', methods=['POST', 'OPTIONS'])
@crossdomain(api=True)
@login_required
def get_space_after_packing():
    json_data = request.get_json(force=True)
    sku_info = json_data['sku_info']
    box_info = json_data['box_info']
    return jsonify(space_after_packing(sku_info, box_info))


@blueprint.route('/pack_boxes/how_many_fit', methods=['POST', 'OPTIONS'])
@crossdomain(api=True)
@login_required
def how_many_fit():
    json_data = request.get_json(force=True)
    sku_info = json_data['sku_info']
    box_info = json_data['box_info']
    return jsonify(how_many_skus_fit(sku_info, box_info))


@blueprint.route('/compare_packing_efficiency', methods=['GET', 'OPTIONS'])
@crossdomain(api=True)
@login_required
def compare_pack():
    params = request.args.to_dict()
    current_app.log.data(params)
    trials = params.get('trials')
    return jsonify(compare_1000_times(trials))


@blueprint.route('/box_packing_api', methods=['POST', 'OPTIONS'])
@crossdomain(api=True)
@login_required
def box_packing_api():
    json_data = request.get_json(force=True)
    try:
        boxes_info = json_data['boxes_info']
        skus_info = json_data['skus_info']
        options = json_data.get('options', {})
        best_package = api_packing_algorithm(boxes_info, skus_info, options)
    except KeyError as e:
        current_app.log.error(e)
        return jsonify(error=msg.missing_value_for(e.message)), 400
    return jsonify(best_package=best_package)
