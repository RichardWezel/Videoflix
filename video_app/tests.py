import os
import shutil
import tempfile
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from video_app.models import Video
from video_app.tasks import (
    VIDEO_LIST_CACHE_KEY,
    _ffmpeg_hls_cmd,
    _rewrite_segment_uris,
    _thumbnail_target,
    convert_to_hls,
    generate_thumbnail,
    hls_dir,
)
from video_app.api.views import SEGMENT_NAME_RE


def _create_user(email='test@test.com'):
    """Create an active user for authenticating requests in tests."""
    return get_user_model().objects.create_user(email=email, password='HansImGlück1987&', is_active=True)


def _create_video(**overrides):
    """Create a Video with sane defaults, overridable per test."""
    defaults = {'title': 'Sample Video', 'description': 'A sample.', 'category': 'Documentary'}
    defaults.update(overrides)
    return Video.objects.create(**defaults)


class TempMediaRootMixin:
    """Isolates MEDIA_ROOT to a fresh temp directory for the class, removed again afterwards."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._tmp_media_root = tempfile.mkdtemp()
        cls._media_root_override = override_settings(MEDIA_ROOT=cls._tmp_media_root)
        cls._media_root_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._media_root_override.disable()
        shutil.rmtree(cls._tmp_media_root, ignore_errors=True)
        super().tearDownClass()


class MetaVideoViewTest(APITestCase):
    """Tests for the video list endpoint (GET /api/video/)."""

    def setUp(self):
        cache.clear()
        self.user = _create_user()

    def test_list_requires_authentication(self):
        """Verifies that an anonymous request is rejected."""
        response = self.client.get(reverse('metavideo'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_list_returns_expected_fields(self):
        """Verifies that the serialized video contains exactly the documented fields."""
        _create_video()
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('metavideo'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expected_fields = {'id', 'created_at', 'title', 'description', 'thumbnail_url', 'category'}
        self.assertEqual(set(response.data[0].keys()), expected_fields)

    def test_list_orders_newest_first(self):
        """Verifies videos are ordered by created_at descending, per the model's Meta.ordering."""
        older = _create_video(title='Older')
        newer = _create_video(title='Newer')
        self.client.force_authenticate(user=self.user)
        response = self.client.get(reverse('metavideo'))
        titles = [v['title'] for v in response.data]
        self.assertEqual(titles, [newer.title, older.title])


class VideoListCacheTest(APITestCase):
    """Tests for the Redis caching behavior of the video list endpoint."""

    def setUp(self):
        cache.clear()
        self.user = _create_user()
        self.client.force_authenticate(user=self.user)

    def test_first_request_populates_the_cache(self):
        """Verifies a cache miss falls back to the DB and then fills the cache."""
        _create_video()
        self.assertIsNone(cache.get(VIDEO_LIST_CACHE_KEY))
        self.client.get(reverse('metavideo'))
        self.assertIsNotNone(cache.get(VIDEO_LIST_CACHE_KEY))

    def test_response_is_served_from_cache_without_hitting_the_db(self):
        """Verifies the view returns the cached value as-is, proving it didn't re-query an empty DB."""
        cached_entry = [{'id': 1, 'created_at': None, 'title': 'Cached Title',
                          'description': '', 'thumbnail_url': '', 'category': 'x'}]
        cache.set(VIDEO_LIST_CACHE_KEY, cached_entry)
        response = self.client.get(reverse('metavideo'))
        self.assertEqual(response.data, cached_entry)

    def test_cache_is_invalidated_on_video_save(self):
        """Verifies saving a Video clears the cached list."""
        self.client.get(reverse('metavideo'))
        self.assertIsNotNone(cache.get(VIDEO_LIST_CACHE_KEY))
        video = _create_video()
        video.title = 'Renamed'
        video.save()
        self.assertIsNone(cache.get(VIDEO_LIST_CACHE_KEY))

    def test_cache_is_invalidated_on_video_delete(self):
        """Verifies deleting a Video clears the cached list."""
        video = _create_video()
        self.client.get(reverse('metavideo'))
        video.delete()
        self.assertIsNone(cache.get(VIDEO_LIST_CACHE_KEY))


class HLSPlaylistViewTest(TempMediaRootMixin, APITestCase):
    """Tests for the HLS playlist endpoint (GET /api/video/<id>/<resolution>/index.m3u8)."""

    def setUp(self):
        self.user = _create_user()
        self.video = _create_video()

    def _url(self, movie_id, resolution):
        return reverse('video-hls-playlist', kwargs={'movie_id': movie_id, 'resolution': resolution})

    def _write_manifest(self, resolution, content='#EXTM3U\n000.ts/\n'):
        target_dir = hls_dir(self.video.pk, resolution)
        os.makedirs(target_dir, exist_ok=True)
        with open(os.path.join(target_dir, 'index.m3u8'), 'w') as f:
            f.write(content)

    def test_playlist_requires_authentication(self):
        """Verifies that an anonymous request is rejected."""
        response = self.client.get(self._url(self.video.pk, '720p'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_playlist_returns_404_for_unknown_video(self):
        """Verifies a nonexistent movie_id returns 404."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self._url(999999, '720p'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_playlist_returns_404_for_unknown_resolution(self):
        """Verifies a resolution outside RESOLUTIONS returns 404."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self._url(self.video.pk, '4k'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_playlist_returns_404_before_conversion_finished(self):
        """Verifies that a missing manifest file (conversion not done yet) returns 404."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self._url(self.video.pk, '720p'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_playlist_returns_manifest_when_available(self):
        """Verifies an existing manifest is served with the correct content type and body."""
        self._write_manifest('720p')
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self._url(self.video.pk, '720p'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'application/vnd.apple.mpegurl')
        content = b''.join(response.streaming_content).decode()
        self.assertIn('000.ts/', content)


class HLSSegmentViewTest(TempMediaRootMixin, APITestCase):
    """Tests for the HLS segment endpoint (GET /api/video/<id>/<resolution>/<segment>/)."""

    def setUp(self):
        self.user = _create_user()
        self.video = _create_video()

    def _url(self, movie_id, resolution, segment):
        return reverse(
            'video-hls-segment', kwargs={'movie_id': movie_id, 'resolution': resolution, 'segment': segment}
        )

    def _write_segment(self, resolution, name, content=b'binary-ts-data'):
        target_dir = hls_dir(self.video.pk, resolution)
        os.makedirs(target_dir, exist_ok=True)
        with open(os.path.join(target_dir, name), 'wb') as f:
            f.write(content)

    def test_segment_requires_authentication(self):
        """Verifies that an anonymous request is rejected."""
        response = self.client.get(self._url(self.video.pk, '720p', '000.ts'))
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_segment_returns_404_for_unknown_video(self):
        """Verifies a nonexistent movie_id returns 404."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self._url(999999, '720p', '000.ts'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_segment_returns_404_for_unknown_resolution(self):
        """Verifies a resolution outside RESOLUTIONS returns 404."""
        self._write_segment('720p', '000.ts')
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self._url(self.video.pk, '4k', '000.ts'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_segment_rejects_name_that_does_not_match_the_ts_pattern(self):
        """Verifies a non-.ts segment name (e.g. a traversal attempt like '..') is rejected before touching disk."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self._url(self.video.pk, '720p', '..'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_segment_returns_404_for_missing_file(self):
        """Verifies a syntactically valid but nonexistent segment returns 404."""
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self._url(self.video.pk, '720p', '000.ts'))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_segment_returns_file_when_available(self):
        """Verifies an existing segment is served with the correct content type and body."""
        self._write_segment('720p', '000.ts', content=b'fake-mpeg-ts-bytes')
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self._url(self.video.pk, '720p', '000.ts'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response['Content-Type'], 'video/MP2T')
        self.assertEqual(b''.join(response.streaming_content), b'fake-mpeg-ts-bytes')


class SegmentNameRegexTest(TestCase):
    """Unit tests for the path-traversal guard used by HLSSegmentView."""

    def test_accepts_typical_segment_names(self):
        for name in ('000.ts', '012.ts', 'segment_01-a.ts'):
            self.assertIsNotNone(SEGMENT_NAME_RE.match(name), name)

    def test_rejects_names_without_ts_extension(self):
        for name in ('index.m3u8', 'settings.py', '000', '..'):
            self.assertIsNone(SEGMENT_NAME_RE.match(name), name)

    def test_rejects_path_separators(self):
        for name in ('../../core/settings.py', 'sub/000.ts', '/etc/passwd'):
            self.assertIsNone(SEGMENT_NAME_RE.match(name), name)


class TasksHelperTest(TempMediaRootMixin, TestCase):
    """Unit tests for the small pure-ish helper functions in tasks.py."""

    def test_ffmpeg_hls_cmd_includes_source_and_target_size(self):
        cmd = _ffmpeg_hls_cmd('/media/videos/sample.mp4', 'hd720')
        self.assertEqual(cmd[0], 'ffmpeg')
        self.assertIn('/media/videos/sample.mp4', cmd)
        self.assertIn('hd720', cmd)
        self.assertIn('index.m3u8', cmd)

    def test_rewrite_segment_uris_appends_slash_to_segment_lines_only(self):
        target_dir = hls_dir(1, '720p')
        os.makedirs(target_dir, exist_ok=True)
        manifest_path = os.path.join(target_dir, 'index.m3u8')
        with open(manifest_path, 'w') as f:
            f.write('#EXTM3U\n#EXTINF:6.0,\n000.ts\n\n001.ts\n#EXT-X-ENDLIST\n')
        _rewrite_segment_uris(manifest_path)
        with open(manifest_path) as f:
            lines = f.read().splitlines()
        self.assertEqual(lines, ['#EXTM3U', '#EXTINF:6.0,', '000.ts/', '', '001.ts/', '#EXT-X-ENDLIST'])

    def test_rewrite_segment_uris_does_nothing_for_missing_file(self):
        _rewrite_segment_uris('/nonexistent/index.m3u8')  # should not raise

    def test_thumbnail_target_creates_dir_and_builds_jpg_path(self):
        target_dir, filename, target = _thumbnail_target('/media/videos/sample.mp4')
        self.assertTrue(os.path.isdir(target_dir))
        self.assertEqual(filename, 'sample.jpg')
        self.assertEqual(target, os.path.join(target_dir, filename))


class ConvertToHlsTaskTest(TempMediaRootMixin, TestCase):
    """Tests for tasks.convert_to_hls(), with ffmpeg itself mocked out."""

    @patch('video_app.tasks.subprocess.run')
    def test_creates_target_dir_and_invokes_ffmpeg_in_it(self, mock_run):
        convert_to_hls(video_id=1, source='/media/videos/sample.mp4', resolution='720p')
        target_dir = hls_dir(1, '720p')
        self.assertTrue(os.path.isdir(target_dir))
        mock_run.assert_called_once()
        called_cmd = mock_run.call_args[0][0]
        called_kwargs = mock_run.call_args[1]
        self.assertIn('hd720', called_cmd)
        self.assertEqual(called_kwargs['cwd'], target_dir)

    @patch('video_app.tasks.subprocess.run')
    def test_rewrites_manifest_produced_by_ffmpeg(self, mock_run):
        target_dir = hls_dir(2, '480p')

        def fake_ffmpeg_run(cmd, **kwargs):
            os.makedirs(target_dir, exist_ok=True)
            with open(os.path.join(target_dir, 'index.m3u8'), 'w') as f:
                f.write('#EXTM3U\n000.ts\n')

        mock_run.side_effect = fake_ffmpeg_run
        convert_to_hls(video_id=2, source='/media/videos/sample.mp4', resolution='480p')
        with open(os.path.join(target_dir, 'index.m3u8')) as f:
            self.assertIn('000.ts/', f.read())


class GenerateThumbnailTaskTest(TempMediaRootMixin, TestCase):
    """Tests for tasks.generate_thumbnail(), with ffmpeg itself mocked out."""

    def setUp(self):
        cache.clear()
        self.video = _create_video()

    @patch('video_app.tasks.subprocess.run')
    def test_sets_thumbnail_url_on_the_video(self, mock_run):
        generate_thumbnail(self.video.pk, '/media/videos/sample.mp4')
        self.video.refresh_from_db()
        self.assertEqual(self.video.thumbnail_url, '/media/thumbnails/sample.jpg')

    @patch('video_app.tasks.subprocess.run')
    def test_invalidates_the_video_list_cache(self, mock_run):
        """Regression test: Video.objects.update() bypasses post_save, so the task must invalidate itself."""
        cache.set(VIDEO_LIST_CACHE_KEY, 'stale-data')
        generate_thumbnail(self.video.pk, '/media/videos/sample.mp4')
        self.assertIsNone(cache.get(VIDEO_LIST_CACHE_KEY))


class VideoSignalsTest(TempMediaRootMixin, TestCase):
    """Tests for the post_save/post_delete signal handlers in signals.py."""

    def setUp(self):
        cache.clear()

    def _video_with_file(self):
        video_file = SimpleUploadedFile('sample.mp4', b'fake-bytes', content_type='video/mp4')
        return _create_video(video_file=video_file)

    @patch('video_app.signals.django_rq.get_queue')
    def test_new_video_with_file_enqueues_conversion_and_thumbnail_jobs(self, mock_get_queue):
        """3 resolutions + 1 thumbnail job = 4 enqueue calls."""
        mock_queue = mock_get_queue.return_value
        self._video_with_file()
        self.assertEqual(mock_queue.enqueue.call_count, 4)

    @patch('video_app.signals.django_rq.get_queue')
    def test_new_video_without_file_enqueues_nothing(self, mock_get_queue):
        _create_video()
        mock_get_queue.return_value.enqueue.assert_not_called()

    @patch('video_app.signals.django_rq.get_queue')
    def test_updating_an_existing_video_does_not_reenqueue_jobs(self, mock_get_queue):
        video = self._video_with_file()
        mock_get_queue.reset_mock()
        video.title = 'Updated title'
        video.save()
        mock_get_queue.return_value.enqueue.assert_not_called()

    @patch('video_app.signals.django_rq.get_queue')
    def test_deleting_video_removes_file_from_disk(self, mock_get_queue):
        video = self._video_with_file()
        file_path = video.video_file.path
        self.assertTrue(os.path.isfile(file_path))
        video.delete()
        self.assertFalse(os.path.isfile(file_path))

    def test_deleting_video_without_file_does_not_raise(self):
        video = _create_video()
        video.delete()
