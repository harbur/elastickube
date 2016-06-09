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

class InstancesActionCreatorService {
    constructor(actions, dispatcher, instancesAPI, namespacesStore) {
        'ngInject';

        this._instancesAPI = instancesAPI;
        this._actions = actions;
        this._dispatcher = dispatcher;
        this._namespacesStore = namespacesStore;

        instancesAPI.addOnCreatedListener((instance) => this._dispatcher.dispatch({
            type: this._actions.INSTANCE_DEPLOYED,
            instances: [instance]
        }));

        instancesAPI.addOnUpdatedListener((instance) => this._dispatcher.dispatch({ type: this._actions.INSTANCES_UPDATED, instance }));
        instancesAPI.addOnDeletedListener((instance) => this._dispatcher.dispatch({ type: this._actions.INSTANCES_DELETED, instance }));
    }

    deploy(namespace, chart, info) {
        const body = {
            uid: chart._id.$oid,
            namespace: _.get(namespace, 'metadata.name'),
            labels: info.labels
        };

        this._dispatcher.dispatch({ type: this._actions.INSTANCE_DEPLOY });

        return this._instancesAPI.create(body)
            .then((instances) => this._dispatcher.dispatch({ type: this._actions.INSTANCE_DEPLOYED, instances }));
    }

    destroy(namespace, chart) {
        const body = {
            kind: 'Chart',
            uid: chart._id.$oid,
            namespace: _.get(namespace, 'metadata.name')
        };

        return this._instancesAPI.remove(body);
    }

    delete(instance) {
        const body = {
            kind: instance.kind,
            name: instance.metadata.name,
            namespace: instance.metadata.namespace
        };

        return this._instancesAPI.remove(body);
    }

    subscribe(namespace) {
        this._dispatcher.dispatch({ type: this._actions.INSTANCES_SUBSCRIBE, namespace });

        return this._instancesAPI.subscribe({ namespace: namespace.metadata.name })
            .then((instances) => this._dispatcher.dispatch({ type: this._actions.INSTANCES_SUBSCRIBED, namespace, instances }));
    }

    unsubscribe(namespace) {
        this._dispatcher.dispatch({
            type: this._actions.INSTANCES_UNSUBSCRIBE,
            namespace
        });

        return this._instancesAPI.unsubscribe({ namespace: namespace.metadata.name })
            .then((x) => this._dispatcher.dispatch({
                type: this._actions.INSTANCES_UNSUBSCRIBED,
                namespace: this._namespacesStore.get(x)
            }));
    }
}

export default InstancesActionCreatorService;
