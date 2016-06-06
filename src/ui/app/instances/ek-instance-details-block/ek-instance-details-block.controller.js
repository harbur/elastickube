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

import moment from 'moment';

class InstanceDetailsBlockController {
    constructor($scope, instanceStore, instancesStore) {
        'ngInject';

        const onChange = () => {
            this.instance = instanceStore.getInstance();
        };

        this._instancesStore = instancesStore;

        this.instance = instanceStore.getInstance();

        instanceStore.addChangeListener(onChange);

        switch (this.instance.kind) {

            case 'Service':
                this.details = this._createServiceDetails();
                break;

            case 'ReplicationController':
                this.details = this._createReplicationControllerDetails();
                break;

            case 'ReplicaSet':
                this.details = this._createReplicaSetDetails();
                break;

            case 'DaemonSet':
                this.details = this._createDaemonSetDetails();
                break;

            case 'Deployment':
                this.details = this._createDeploymentDetails();
                break;

            default:
                this.details = this._createPodDetails();
        }

        $scope.$on('$destroy', () => instanceStore.removeChangeListener(onChange));
    }

    _createServiceDetails() {
        const details = {};

        details.Kind = this.instance.kind;
        details['Start Time'] = moment.utc(this.instance.metadata.creationTimestamp).local().format('ddd, D MMM GGGG HH:mm:ss');

        return _.omitBy(details, _.isEmpty);
    }

    _createPodDetails() {
        const details = {};

        details.Kind = this.instance.kind;
        details['Image(s)'] = _.chain(this.instance.spec.containers).map((x) => x.image).join(', ').value();
        details.Node = this.instance.spec.nodeName;
        details['Start Time'] = moment.utc(this.instance.metadata.creationTimestamp).local().format('ddd, D MMM GGGG HH:mm:ss');
        details['IP(s)'] = this.instance.status.podIP;

        return _.omitBy(details, _.isEmpty);
    }

    _createReplicationControllerDetails() {
        const details = {};

        details.Kind = this.instance.kind;
        details['Volume(s)'] = _.chain(this.instance.spec.template.spec.volumes).map((x) => x.name).join(', ').value();
        details['Start Time'] = moment.utc(this.instance.metadata.creationTimestamp).local().format('ddd, D MMM GGGG HH:mm:ss');
        details.Replicas = `${this.instance.status.replicas}/${this.instance.spec.replicas} replicas created`;

        return _.omitBy(details, _.isEmpty);
    }

    _createReplicaSetDetails() {
        const details = {};

        details.Kind = this.instance.kind;
        details['Volume(s)'] = _.chain(this.instance.spec.template.spec.volumes).map((x) => x.name).join(', ').value();
        details['Start Time'] = moment.utc(this.instance.metadata.creationTimestamp).local().format('ddd, D MMM GGGG HH:mm:ss');
        details.Replicas = `${this.instance.status.replicas}/${this.instance.spec.replicas} replicas created`;

        return _.omitBy(details, _.isEmpty);
    }

    _createDaemonSetDetails() {
        const details = {};

        details.Kind = this.instance.kind;
        details['Volume(s)'] = _.chain(this.instance.spec.template.spec.volumes).map((x) => x.name).join(', ').value();
        details['Start Time'] = moment.utc(this.instance.metadata.creationTimestamp).local().format('ddd, D MMM GGGG HH:mm:ss');
        details.Replicas = `${this.instance.status.currentNumberScheduled}/${this.instance.status.desiredNumberScheduled} created`;

        return _.omitBy(details, _.isEmpty);
    }

    _createDeploymentDetails() {
        const details = {};

        details.Kind = this.instance.kind;
        details['Volume(s)'] = _.chain(this.instance.spec.template.spec.volumes).map((x) => x.name).join(', ').value();
        details['Start Time'] = moment.utc(this.instance.metadata.creationTimestamp).local().format('ddd, D MMM GGGG HH:mm:ss');
        details.Replicas = `${this.instance.status.replicas}/${this.instance.spec.replicas} replicas created`;

        return _.omitBy(details, _.isEmpty);
    }
}

export default InstanceDetailsBlockController;
