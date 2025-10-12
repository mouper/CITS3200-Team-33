from background_runner import process_video_metadata

def test_process_video_metadata_handles_empty():
    result = process_video_metadata({})
    assert result is None  # or appropriate default

def test_process_video_metadata_parses_fields():
    video = {"title": "Test Video", "views": "1000"}
    processed = process_video_metadata(video)
    assert processed["views"] == 1000
