from django.db import models

class Video(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    thumbnail_url = models.URLField(max_length=500, blank=True)
    category = models.CharField(max_length=100)
    video_file = models.FileField(upload_to='videos/', blank=True, null=True)

    def __str__(self):
        return self.title   
    
    class Meta:
        verbose_name = "Video"
        verbose_name_plural = "Videos"
        ordering: list[str] = ['-created_at', 'title']
    