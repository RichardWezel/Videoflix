import os

import django_rq
from django.core.cache import cache
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete

from .models import Video
from .tasks import RESOLUTIONS, convert_to_hls, generate_thumbnail, VIDEO_LIST_CACHE_KEY

@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    """
    Signal triggered when a Video instance is saved.
    If the instance is newly created and has a video file, it enqueues tasks to convert the video to HLS
    (index.m3u8 + segments) for every supported resolution, and to generate a thumbnail.
    """
    cache.delete(VIDEO_LIST_CACHE_KEY)
    if created and instance.video_file:
        queue = django_rq.get_queue('default', autocommit=True)
        for resolution in RESOLUTIONS:
            queue.enqueue(convert_to_hls, instance.pk, instance.video_file.path, resolution)
        queue.enqueue(generate_thumbnail, instance.pk, instance.video_file.path)


@receiver(post_delete, sender=Video)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Signal triggered when a Video instance is deleted.
    It deletes the related video file from the filesystem.
    """
    cache.delete(VIDEO_LIST_CACHE_KEY)
    if instance.video_file:
        if os.path.isfile(instance.video_file.path):
            os.remove(instance.video_file.path)
