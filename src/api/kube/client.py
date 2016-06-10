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

import json
import logging
import urlparse

from tornado.gen import coroutine, Return
from tornado.concurrent import Future, chain_future
from tornado.httpclient import AsyncHTTPClient, HTTPError, HTTPRequest
from tornado.httputil import url_concat

from api.kube.exceptions import KubernetesException, ResourceNotFoundException
from api.kube.pods import Pods
from api.kube.resources import Resource, NamespacedResource


class HTTPClient(object):

    def __init__(self, endpoint, token=None):
        self.endpoint = endpoint
        self.token = token

        if endpoint.startswith("http"):
            self._base_url = self.endpoint
        else:
            self._base_url = "https://%s" % self.endpoint

        AsyncHTTPClient.configure("tornado.curl_httpclient.CurlAsyncHTTPClient", defaults=dict(validate_cert=False))

    def get_base_url(self):
        return self._base_url

    def build_url(self, url_path, **kwargs):
        if url_path.startswith("/"):
            url = self._base_url + url_path
        else:
            url = self._base_url + "/" + url_path

        params = dict()
        for kwarg in kwargs.iterkeys():
            if kwarg in url_path:
                params[kwarg] = kwargs[kwarg]

        return url.format(**params)

    def build_params(self, url, **kwargs):
        keys = kwargs.keys()
        for key in keys:
            if key in url:
                kwargs.pop(key)

        return kwargs

    def build_headers(self, content_type=None):
        headers = {"Authorization": "Bearer %s" % self.token}
        if content_type:
            headers["Content-type"] = content_type

        return headers

    @coroutine
    def request(self, url_path, method="GET", **kwargs):
        params = self.build_params(url_path, **kwargs)

        if not urlparse.urlparse(url_path).netloc:
            url = url_concat(self.build_url(url_path, **kwargs), params)
        else:
            url = url_concat(url_path, params)

        client = AsyncHTTPClient(force_instance=True)
        try:
            result = yield client.fetch(url, method=method, headers=self.build_headers())
            raise Return(result)
        finally:
            client.close()

    @coroutine
    def get(self, url_path, **kwargs):
        params = self.build_params(url_path, **kwargs)
        url = url_concat(self.build_url(url_path, **kwargs), params)

        client = AsyncHTTPClient(force_instance=True)
        try:
            result = yield client.fetch(url, method="GET", headers=self.build_headers())
            raise Return(result)
        finally:
            client.close()

    @coroutine
    def post(self, url_path, **kwargs):
        url = self.build_url(url_path, **kwargs)
        params = self.build_params(url_path, **kwargs)

        client = AsyncHTTPClient(force_instance=True)
        try:
            result = yield client.fetch(
                url,
                method="POST",
                headers=self.build_headers("application/json"),
                **params)

            raise Return(result)
        finally:
            client.close()

    @coroutine
    def put(self, url_path, **kwargs):
        url = self.build_url(url_path, **kwargs)
        params = self.build_params(url_path, **kwargs)

        client = AsyncHTTPClient(force_instance=True)
        try:
            result = yield client.fetch(
                url,
                method="PUT",
                headers=self.build_headers("application/json"),
                **params)

            raise Return(result)
        finally:
            client.close()

    @coroutine
    def delete(self, url_path, **kwargs):
        client = AsyncHTTPClient(force_instance=True)
        try:
            response = yield client.fetch(
                self.build_url(url_path, **kwargs),
                method="DELETE",
                headers=self.build_headers())
            raise Return(response)
        finally:
            client.close()

    @coroutine
    def patch(self, url_path, **kwargs):
        url = self.build_url(url_path, **kwargs)
        params = self.build_params(url_path, **kwargs)

        client = AsyncHTTPClient(force_instance=True)
        try:
            result = yield client.fetch(
                url,
                method="PATCH",
                headers=self.build_headers("application/merge-patch+json"),
                **params)

            raise Return(result)
        finally:
            client.close()

    def watch(self, url_path, on_data, **kwargs):
        local_data = dict(buffer="")

        class WatchFuture(Future):

            def cancel(self):
                client.close()
                logging.debug("AsyncHTTPClient closed")

        def data_callback(data):
            split_data = data.split("\n")
            for index, fragment in enumerate(split_data):
                if index + 1 < len(split_data):
                    on_data(json.loads(local_data["buffer"] + fragment))
                    local_data["buffer"] = ""
                else:
                    local_data["buffer"] += fragment

        params = self.build_params(url_path, **kwargs)
        url = url_concat(self.build_url(url_path, **kwargs), params)

        request = HTTPRequest(
            url=url,
            method="GET",
            headers=self.build_headers(),
            request_timeout=3600,
            streaming_callback=data_callback)

        client = AsyncHTTPClient(force_instance=True)
        future = WatchFuture()

        chain_future(client.fetch(request), future)
        return future


class KubeClient(object):

    # Cannot be generated from the API
    RESOURCE_TO_KIND_MAPPING = {
        "bindings": "Binding",
        "componentstatuses": "ComponentStatus",
        "endpoints": "Endpoints",
        "events": "Event",
        "horizontalpodautoscalers": "HorizontalPodAutoscaler",
        "ingresses": "Ingress",
        "jobs": "Jobs",
        "limitranges": "LimitRange",
        "namespaces": "Namespace",
        "nodes": "Node",
        "persistentvolumeclaims": "PersistentVolumeClaim",
        "persistentvolumes": "PersistentVolume",
        "pods": "Pod",
        "podtemplates": "PodTemplate",
        "replicationcontrollers": "ReplicationController",
        "replicasets": "ReplicaSet",
        "daemonsets": "DaemonSet",
        "deployments": "Deployment",
        "resourcequotas": "ResourceQuota",
        "scale": "Scale",
        "configmaps": "ConfigMap",
        "secrets": "Secret",
        "serviceaccounts": "ServiceAccount",
        "services": "Service"
    }

    def __init__(self, endpoint, token=None):
        self.http_client = HTTPClient(endpoint, token)
        self.resources = {}
        self.kind_to_resource = {}

    def __getitem__(self, item):
        return getattr(self, item)

    def __getattr__(self, item):
        return self.resources[item]

    @coroutine
    def build_resources(self):
        api_versions_response = yield self.http_client.get("/api")
        api_versions = json.loads(api_versions_response.body).get("versions", [])
        if len(api_versions) > 0:
            api_version = api_versions[0]
        else:
            raise Return()

        yield self._build_api_resources(api_version)

        response = yield self.http_client.get("/apis")
        apis_groups = json.loads(response.body).get("groups", [])
        if len(apis_groups) > 0 and len(apis_groups[0].get("versions", [])) > 0:
            for api_group in apis_groups:
                group_version = api_group.get("versions", [])[0].get("groupVersion", [])
        else:
            raise Return()

        yield self._build_api_extensions(group_version)

    def get_resource_type(self, kind):
        if kind not in self.kind_to_resource.keys():
            raise ResourceNotFoundException("Resource %s not found." % kind)

        return self.kind_to_resource[kind]

    @staticmethod
    def format_error(error):
        if error.code != 599:
            error_message = error.response.body
            error_method = error.response.request.method
            error_url = error.response.effective_url

            if error_message:
                return "{0} {1} returned {2}: {3}".format(error_method, error_url, error.code, error_message)
            else:
                return "{0} {1} returned {2}".format(error_method, error_url, error.code)
        else:
            return error.message

    @coroutine
    def get(self, url_path, **kwargs):
        try:
            response = yield self.http_client.get(url_path, **kwargs)
        except HTTPError as http_error:
            message = self.format_error(http_error)

            if http_error.code == 404:
                raise ResourceNotFoundException(message)
            else:
                raise KubernetesException(message, http_error.code)

        raise Return(json.loads(response.body))

    @coroutine
    def put(self, url_path, **kwargs):
        try:
            response = yield self.http_client.put(url_path, **kwargs)
        except HTTPError as http_error:
            message = self.format_error(http_error)

            if http_error.code == 404:
                raise ResourceNotFoundException(message)
            else:
                raise KubernetesException(message, http_error.code)

        raise Return(json.loads(response.body))

    @coroutine
    def post(self, url_path, **kwargs):
        try:
            response = yield self.http_client.post(url_path, **kwargs)
        except HTTPError as http_error:
            raise KubernetesException(self.format_error(http_error), http_error.code)

        raise Return(json.loads(response.body))

    @coroutine
    def delete(self, url_path, **kwargs):
        try:
            response = yield self.http_client.delete(url_path, **kwargs)
        except HTTPError as http_error:
            message = self.format_error(http_error)

            if http_error.code == 404:
                raise ResourceNotFoundException(message)
            else:
                raise KubernetesException(message, http_error.code)

        raise Return(json.loads(response.body))

    @coroutine
    def patch(self, url_path, **kwargs):
        try:
            response = yield self.http_client.patch(url_path, **kwargs)
        except HTTPError as http_error:
            message = self.format_error(http_error)

            if http_error.code == 404:
                raise ResourceNotFoundException(message)
            else:
                raise KubernetesException(message, http_error.code)

        raise Return(json.loads(response.body))

    def watch(self, url_path, on_data, **kwargs):
        return self.http_client.watch(url_path, on_data, **kwargs)

    @coroutine
    def _build_api_resources(self, api_version):
        response = yield self.http_client.get("/api/%s" % api_version)

        resources = json.loads(response.body).get("resources", [])
        for resource in resources:
            if "/" in resource["name"]:
                continue

            if resource["name"] in self.RESOURCE_TO_KIND_MAPPING.keys():
                self.kind_to_resource[self.RESOURCE_TO_KIND_MAPPING[resource["name"]]] = resource["name"]

            if resource["namespaced"]:
                # FIXME: generate it from swagger api
                if resource["name"] == "pods":
                    self.resources[resource["name"]] = Pods(self, "/api/%s" % api_version, resource["name"])
                else:
                    self.resources[resource["name"]] = NamespacedResource(self,
                                                                          "/api/%s" % api_version,
                                                                          resource["name"])
            else:
                self.resources[resource["name"]] = Resource(self, "/api/%s" % api_version, resource["name"])

    @coroutine
    def _build_api_extensions(self, group_version):
        response = yield self.http_client.get("/apis/%s" % group_version)
        for resource in json.loads(response.body).get("resources", []):
            if "/status" in resource["name"]:
                continue

            if resource["name"] in self.resources.keys():
                continue

            resource_name = resource["name"].split("/")[-1] if "/" in resource["name"] else resource["name"]
            if resource_name in self.RESOURCE_TO_KIND_MAPPING.keys():
                self.kind_to_resource[self.RESOURCE_TO_KIND_MAPPING[resource_name]] = resource_name

            if resource["namespaced"]:
                self.resources[resource["name"]] = NamespacedResource(
                    self, "/apis/%s" % group_version, resource["name"])
            else:
                self.resources[resource["name"]] = Resource(self, "/apis/%s" % group_version, resource["name"])
