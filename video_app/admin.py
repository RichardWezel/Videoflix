from django.contrib import admin
from import_export.admin import ImportExportModelAdmin
from import_export import resources

from .models import Video


class VideoResource(resources.ModelResource):
    class Meta:
        model = Video


@admin.register(Video)
class VideoAdmin(ImportExportModelAdmin):
    list_display = ['id', 'title', 'category', 'created_at']
    resource_class = VideoResource
