import json

from drf_yasg.views import get_schema_view

from rest_framework import mixins, permissions, renderers, status
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.response import Response
from rest_framework.schemas.generators import EndpointEnumerator

import mayan
from mayan.apps.organizations.settings import setting_organization_url_base_path
from mayan.apps.rest_api import generics

from .classes import BatchRequest, BatchRequestCollection, Endpoint
from .generics import RetrieveAPIView, ListAPIView
from .serializers import (
    BatchAPIRequestResponseSerializer, EndpointSerializer,
    ProjectInformationSerializer
)
from .schemas import openapi_info


class APIRoot(ListAPIView):
    swagger_schema = None
    serializer_class = EndpointSerializer

    def get_queryset(self):
        """
        get: Return a list of all API root endpoints. This includes the
        API version root and root services.
        """
        endpoint_api_version = Endpoint(
            label='API version root', viewname='rest_api:api_version_root'
        )
        endpoint_redoc = Endpoint(
            label='ReDoc UI', viewname='rest_api:schema-redoc'
        )
        endpoint_swagger = Endpoint(
            label='Swagger UI', viewname='rest_api:schema-swagger-ui'
        )
        endpoint_swagger_schema_json = Endpoint(
            label='API schema (JSON)', viewname='rest_api:schema-json',
            kwargs={'format': '.json'}
        )
        endpoint_swagger_schema_yaml = Endpoint(
            label='API schema (YAML)', viewname='rest_api:schema-json',
            kwargs={'format': '.yaml'}
        )
        return [
            endpoint_api_version,
            endpoint_swagger,
            endpoint_redoc,
            endpoint_swagger_schema_json,
            endpoint_swagger_schema_yaml
        ]


class APIVersionRoot(ListAPIView):
    swagger_schema = None
    serializer_class = EndpointSerializer

    def get_queryset(self):
        """
        get: Return a list of the API version resources and endpoint.
        """
        endpoint_enumerator = EndpointEnumerator()

        if setting_organization_url_base_path.value:
            url_index = 4
        else:
            url_index = 3

        # Extract the resource names from the API endpoint URLs
        parsed_urls = set()
        for entry in endpoint_enumerator.get_api_endpoints():
            try:
                url = entry[0].split('/')[url_index]
            except IndexError:
                """An unknown or invalid URL"""
            else:
                parsed_urls.add(url)

        endpoints = []
        for url in sorted(parsed_urls):
            if url:
                endpoints.append(
                    Endpoint(label=url)
                )

        return endpoints


class BatchRequestAPIView(mixins.ListModelMixin, generics.GenericAPIView):
    """
    post: Submit a batch API request.
    """
    serializer_class = BatchAPIRequestResponseSerializer

    def post(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def get_queryset(self):
        test_batch_requests = '''
        [
            {
                "name": "document_list_{{ view_request.user }}",
                "url": "/api/v4/search/advanced/documents.DocumentSearchResult/?label=8b3332489"
            },
            {
                "iterator": "document_list.data.results",
                "url": "/api/v4/documents/{{ iterator_instance.id }}/metadata/",
                "name": "document_metadata_{{ iterator_instance.id }}"
            }
        ]
        '''
        # ~ test_batch_requests = '''
        # ~ [
            # ~ {"url": "/api/v4/search/documents.DocumentSearchResult/?label=8b3332489", "name": "document_list"},
            # ~ {
                # ~ "iterator": "document_list.data.results",
                # ~ "url": "/api/v4/documents/{{ iterator_instance.id }}/",
                # ~ "name": "document_metadata_{{ iterator_instance.id }}"
            # ~ }
        # ~ ]
        # ~ '''


        test_batch_requests = '''
        [
            {
                "body": {"metadata_type_id": 1, "value": "{{ view_request.user.pk }}"},
                "method": "POST",
                "name": "document_metadata_set",
                "url": "/api/v4/documents/26/metadata/"
            },
            {
                "method": "GET",
                "name": "document_metadata_get",
                "url": "/api/v4/documents/26/metadata/"
            }
        ]
        '''

        test_batch_requests = '''
        [
            {
                "name": "document_list",
                "url": "/api/v4/search/advanced/documents.DocumentSearchResult/?label=8b3332489"
            },
            {
                "iterator": "document_list.data.results",
                "body": {"metadata_type_id": 1, "value": "{{ view_request.user.pk }}"},
                "method": "POST",
                "name": "document_metadata_set_{{ iterator_instance.id }}",
                "url": "/api/v4/documents/{{ iterator_instance.id }}/metadata/"
            },
            {
                "iterator": "document_list.data.results",
                "url": "/api/v4/documents/{{ iterator_instance.id }}/metadata/",
                "name": "document_metadata_get_{{ iterator_instance.id }}"
            }
        ]
        '''

        test_batch_requests = '''
        [
            {
                "include": "false",
                "name": "document_list",
                "url": "/api/v4/search/advanced/documents.DocumentSearchResult/?label=8b3332489"
            },
            {
                "include": "false",
                "iterators": ["document_list.data.results"],
                "url": "/api/v4/documents/{{ iterators.0.id }}/metadata/",
                "name": "document_metadata_get",
                "merge_key": "{{ data.document.id }}",
            },
            {
                "iterators": ["document_metadata_get", "iterators.0.id"],
                "url": "/api/v4/documents/{{ iterator_instance.id }}/metadata/",
                "name": "document_metadata_get_{{ iterator_instance.id }}"
            }
        ]
        '''

        batch_request_collection = BatchRequestCollection(requests_string=test_batch_requests)
        return batch_request_collection.execute(view_request=self.request._request)


class BrowseableObtainAuthToken(ObtainAuthToken):
    """
    Obtain an API authentication token.
    """
    renderer_classes = (renderers.BrowsableAPIRenderer, renderers.JSONRenderer)


class ProjectInformationAPIView(RetrieveAPIView):
    serializer_class = ProjectInformationSerializer

    def get_object(self):
        return mayan


schema_view = get_schema_view(
    info=openapi_info,
    public=True,
    permission_classes=(permissions.AllowAny,),
    validators=['flex', 'ssv']
)
