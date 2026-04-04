import asyncio
from plugins.file_rename import extract_season_episode, extract_quality

def test_extract_season_episode():
    assert extract_season_episode("Show S01E02.mkv") == ("01", "02")
    assert extract_season_episode("Show Season 1 Episode 2.mkv") == ("1", "2")
    assert extract_season_episode("Show [S01][E02].mkv") == ("01", "02")
    assert extract_season_episode("Show Episode 13.mkv") == (None, "13")

def test_extract_quality():
    assert extract_quality("Show 1080p.mkv") == "1080p"
    assert extract_quality("Show [720p].mkv") == "720p"
    assert extract_quality("Show 4k.mkv") == "4k"

    assert extract_quality("Show 1080.mkv") == "1080p"
    assert extract_quality("Show 720 WEB-DL.mkv") == "720p"
    assert extract_quality("Show WEBRip 1080p.mkv") == "1080p"
from plugins.file_rename import extract_languages

def test_extract_languages():
    assert extract_languages("Show Hindi English 1080p.mkv") == "Hindi, English"
    assert extract_languages("Show Dual Audio 720p.mkv") == "Dual Audio"
    assert extract_languages("Show.mkv") == "Unknown"

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from plugins.file_rename import process_queue, user_queues

def test_extract_quality_no_boundaries():
    assert extract_quality("show_720p_video.mkv") == "720p"
    assert extract_quality("show_1080_video.mkv") == "1080p"

def test_extract_languages_no_boundaries():
    assert extract_languages("show_telugu_audio.mkv") == "Telugu"
    assert extract_languages("show_multi_audio_video.mkv") == "Multi"

def test_extract_languages_indian():
    assert extract_languages("Movie_Marathi_DVDRip.mkv") == "Marathi"
    assert extract_languages("Film Bengali audio.mp4") == "Bengali"
