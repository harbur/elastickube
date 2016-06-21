"""
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
"""

import logging

from bson.objectid import ObjectId
from tornado.gen import coroutine, Return

from data.query import Query, ObjectNotFoundError


class InstancesActions(object):

    def __init__(self, settings, user):
        logging.info("Initializing InstancesActions")

        self.kube = settings["kube"]
        self.database = settings["database"]
        self.user = user

    @coroutine
    def check_permissions(self, operation, document):
        logging.debug("check_permissions for user %s and operation %s on instances", self.user["username"], operation)
        if self.user["role"] != "administrator":
            namespace = yield Query(self.database, "Namespaces").find_one({"name": document["namespace"]})
            if self.user["username"] not in namespace["members"]:
                raise Return(False)

        raise Return(True)

    @coroutine
    def create(self, document):
        logging.debug("Creating instance for request %s", document)

        namespace = document["namespace"]

        chart = yield Query(self.database, "Charts", manipulate=True).find_one({"_id": ObjectId(document["uid"])})
        if chart is None:
            raise ObjectNotFoundError("Cannot find Chart %s" % document["uid"])

        result = []
        for resource in chart["resources"]:
            if "labels" in document:
                if "labels" in resource["metadata"]:
                    resource["metadata"]["labels"].update(document["labels"])
                else:
                    resource["metadata"]["labels"] = document["labels"]
            response = yield self.kube[self.kube.get_resource_type(resource["kind"])].post(
                resource, namespace=namespace)
            result.append(response)

        raise Return(result)

    @coroutine
    def delete(self, document):
        logging.debug("Deleting instance for request %s", document)

        # Delete all manifests inside Chart
        if document["kind"] == "Chart":
            logging.debug("Deleting Chart entries %s", document["uid"])
            namespace = document["namespace"]

            chart = yield Query(self.database, "Charts", manipulate=True).find_one({"_id": ObjectId(document["uid"])})

            if chart is None:
                raise ObjectNotFoundError("Cannot find Chart %s" % document["uid"])

            response = []
            for manifest in chart["resources"]:
                logging.debug("Deleting Chart manifest %s", manifest["metadata"]["name"])
                kind = manifest["kind"]
                name = manifest["metadata"]["name"]

                if kind == "ReplicationController" or kind == "ReplicaSet" or kind == "Deployment":
                    response = yield self.kube[self.kube.get_resource_type(kind)].patch(
                        name, dict(spec=dict(replicas=0)), namespace=namespace)
                    logging.debug("Updated %s %s", kind, response)

                response = yield self.kube[self.kube.get_resource_type(kind)].delete(
                    name, namespace=namespace)
        else:
            logging.debug("Deleting manifest item %s", document["name"])
            kind = document["kind"]
            name = document["name"]
            namespace = document["namespace"]

            if kind == "ReplicationController" or kind == "ReplicaSet" or kind == "Deployment":
                response = yield self.kube[self.kube.get_resource_type(kind)].patch(
                    name, dict(spec=dict(replicas=0)), namespace=namespace)
                logging.debug("Updated %s %s", kind, response)

            response = yield self.kube[self.kube.get_resource_type(kind)].delete(
                name, namespace=namespace)
        raise Return(response)
