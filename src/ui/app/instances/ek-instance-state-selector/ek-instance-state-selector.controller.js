/*
Copyright 2016 ElasticBox All rights reserved.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

class InstanceStateSelectorController {
    constructor($scope) {
        'ngInject';

        this.states = [
            { display: 'all', kind: 'all' },
            {
                display: 'Pods', kind: 'Pod', filters: [
                { display: 'Running', state: 'Running' },
                { display: 'Pending', state: 'Pending' },
                { display: 'Terminating', state: 'Terminating' },
                { display: 'Failed', state: 'Failed' }]
            },
            { display: 'Deployments', kind: 'Deployment' },
            { display: 'ReplicaSets', kind: 'ReplicaSet' },
            { display: 'DaemonSets', kind: 'DaemonSet' },
            { display: 'ReplicationControllers', kind: 'ReplicationController' },
            { display: 'Services', kind: 'Service' }];
        this.selectedState = { state: _.first(this.states) };

        $scope.$watchCollection('ctrl.instances', (x) => this.stateValues = countStates(x));
    }

    selectState(state, substate) {
        this.selectedState = { state, substate };
    }
}

function countStates(instances) {
    return _.chain(instances).reduce((result, value) => {
        const state = _.get(value, 'status.phase');

        if (_.isUndefined(result[value.kind])) {
            result[value.kind] = { total: 0 };
        }

        const element = result[value.kind];

        element.total++;
        if (state) {
            if (_.isUndefined(_.get(element.state, state))) {
                _.set(element, `state.${state}`, 0);
            }
            element.state[state]++;
        }

        return result;
    }, {}).value();
}

export default InstanceStateSelectorController;
