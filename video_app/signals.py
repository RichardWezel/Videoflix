import os

import django_rq
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete

from .models import Video
from .tasks import convert720p, convert480p

@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    """
    Signal triggered when a Video instance is saved.
    It enqueues tasks to convert the video to 720p and 480p resolutions if the instance is newly created.
    """
    print(f"Signal received: Video instance saved. ID: {instance.id}, title: {instance.title}, created: {created}")
    if created and instance.video_file:
        # Add code to execute when a new video is created.
        print(f"New video created: {instance.title}")
        queue = django_rq.get_queue('default')
        queue.enqueue(convert720p, instance.video_file.path)
        queue.enqueue(convert480p, instance.video_file.path)

def create_lecture(sender, instance, created, **kwargs):
    if created:
        # Add code to execute when a new lecture object is created.
        print("New object created")

post_save.connect(create_lecture, sender=Video)

@receiver(post_delete, sender=Video)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """
    Signal triggered when a Video instance is deleted.
    It deletes the related video file from the filesystem.
    """
    if instance.video_file:
        if os.path.isfile(instance.video_file.path):
            os.remove(instance.video_file.path)
            print(f"File deleted: {instance.video_file.path}")
