import pytest
from vectordbs.elasticsearch_store import ElasticSearchStore
from vectordbs.tests.test_base_store import BaseStoreTest

ELASTICSEARCH_INDEX = "test_elasticsearch_index"


class TestElasticSearchStore(BaseStoreTest):
    # Add this line to define the store_class attribute
    store_class = ElasticSearchStore

    @pytest.fixture
    def store(self):
        store = ElasticSearchStore()
        store.collection_name = ELASTICSEARCH_INDEX
        store.create_collection(ELASTICSEARCH_INDEX,
                                "sentence-transformers/all-minilm-l6-v2")
        yield store
        store.delete_collection(ELASTICSEARCH_INDEX)

    # Add any ElasticSearch-specific test cases here
