import os
import subprocess

from django.conf import settings

def _convert(source, size, suffix):
    """Convert a video file to a specified resolution using ffmpeg."""
    target_dir = os.path.join(settings.MEDIA_ROOT, 'videos')
    os.makedirs(target_dir, exist_ok=True)

    filename = os.path.splitext(os.path.basename(source))[0] + f'_{suffix}.mp4'
    target = os.path.join(target_dir, filename)

    cmd = [
        'ffmpeg', '-y', '-i', source,
        '-s', size,
        '-c:v', 'libx264', '-crf', '23',
        '-c:a', 'aac', '-strict', '-2',
        target,
    ]
    subprocess.run(cmd, capture_output=True)


def convert720p(source):
    _convert(source, 'hd720', '720p')


def convert480p(source):
    _convert(source, 'hd480', '480p')


def generate_thumbnail(video_id, source):
    """Generate a thumbnail for a video file using ffmpeg."""
    from .models import Video

    target_dir = os.path.join(settings.MEDIA_ROOT, 'thumbnails')
    os.makedirs(target_dir, exist_ok=True)

    filename = os.path.splitext(os.path.basename(source))[0] + '.jpg'
    target = os.path.join(target_dir, filename)

    cmd = ['ffmpeg', '-y', '-i', source, '-vframes', '1', target]
    subprocess.run(cmd, capture_output=True)

    thumbnail_url = settings.MEDIA_URL + 'thumbnails/' + filename
    Video.objects.filter(pk=video_id).update(thumbnail_url=thumbnail_url)