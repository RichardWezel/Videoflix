from django.contrib import admin
import import_export.admin  # type: ignore
from import_export import resources  # type: ignore

from .models import Video


class VideoResource(resources.ModelResource):
    class Meta:
        model = Video
        exclude = ('video_file',)


@admin.register(Video)
class VideoAdmin(import_export.admin.ImportExportModelAdmin):
    list_display = ['id', 'title', 'category', 'created_at']
    resource_class = VideoResource
