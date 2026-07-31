from .models import Video
from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
import os

@receiver(post_save, sender=Video)
def video_post_save(sender, instance, created, **kwargs):
    print(f"Signal received: Video instance saved. ID: {instance.id}, title: {instance.title}, created: {created}")
    if created:
        # Add code to execute when a new video is created.
        print(f"New video created: {instance.title}")

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
