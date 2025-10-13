import pytest
from unittest.mock import patch
from yt_api import fetch_metadata

@patch('yt_api.requests.get')
def test_fetch_metadata_success(mock_get):
    mock_get.return_value.json.return_value = {'items': [{'id': 'abc', 'snippet': {'title': 'test'}}]}
    result = fetch_metadata('abc')
    assert result['title'] == 'test'

@patch('yt_api.requests.get')
def test_fetch_metadata_failure(mock_get):
    mock_get.side_effect = Exception('API error')
    with pytest.raises(Exception):
        fetch_metadata('xyz')
