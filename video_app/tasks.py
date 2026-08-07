import os
import subprocess

from django.conf import settings
from django.core.cache import cache

RESOLUTIONS = {
    '480p': 'hd480',
    '720p': 'hd720',
    '1080p': 'hd1080',
}

VIDEO_LIST_CACHE_KEY = 'video_list'


def hls_dir(video_id, resolution):
    """Return the target directory for a video's HLS files at a given resolution."""
    return os.path.join(settings.MEDIA_ROOT, 'hls', str(video_id), resolution)

def _ffmpeg_hls_cmd(source, size):
    """Build the ffmpeg argument list that segments a video into an HLS playlist at the given size."""
    return [
        'ffmpeg', '-y', '-i', source,
        '-s', size,
        '-c:v', 'libx264', '-crf', '23',
        '-c:a', 'aac', '-strict', '-2',
        '-hls_time', '6',
        '-hls_playlist_type', 'vod',
        '-hls_segment_filename', '%03d.ts',
        'index.m3u8',
    ]

def convert_to_hls(video_id, source, resolution):
    """Segment a video file into an HLS playlist (index.m3u8 + .ts segments) at a given resolution.

    Segment filenames are kept relative (e.g. '000.ts') so the playlist can be rewritten to point at the
    authenticated segment API endpoint instead of a filesystem path.
    """
    target_dir = hls_dir(video_id, resolution)
    os.makedirs(target_dir, exist_ok=True)
    cmd = _ffmpeg_hls_cmd(source, RESOLUTIONS[resolution])
    subprocess.run(cmd, capture_output=True, cwd=target_dir)
    _rewrite_segment_uris(os.path.join(target_dir, 'index.m3u8'))


def _rewrite_segment_uris(playlist_path):
    """Append a trailing slash to each segment reference so it matches the segment API route."""
    if not os.path.isfile(playlist_path):
        return

    with open(playlist_path, 'r') as f:
        lines = f.readlines()

    with open(playlist_path, 'w') as f:
        for line in lines:
            stripped = line.rstrip('\n')
            if stripped and not stripped.startswith('#'):
                stripped += '/'
            f.write(stripped + '\n')


def _thumbnail_target(source):
    """Build the target directory and file path for a video's thumbnail."""
    target_dir = os.path.join(settings.MEDIA_ROOT, 'thumbnails')
    os.makedirs(target_dir, exist_ok=True)
    filename = os.path.splitext(os.path.basename(source))[0] + '.jpg'
    return target_dir, filename, os.path.join(target_dir, filename)

def generate_thumbnail(video_id, source):
    """Generate a thumbnail for a video file using ffmpeg."""
    from .models import Video

    _target_dir, filename, target = _thumbnail_target(source)
    subprocess.run(['ffmpeg', '-y', '-i', source, '-vframes', '1', target], capture_output=True)

    thumbnail_url = settings.MEDIA_URL + 'thumbnails/' + filename
    Video.objects.filter(pk=video_id).update(thumbnail_url=thumbnail_url)
    cache.delete(VIDEO_LIST_CACHE_KEY)
