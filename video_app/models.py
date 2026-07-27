from django.db import models

# Create your models here.
class Video(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=255)
    description = models.TextField()
    thumbnail_url = models.URLField(max_length=500)
    category = models.CharField(max_length=100)

    def __str__(self):
        return self.title   
    
    class Meta:
        verbose_name = "Video"
        verbose_name_plural = "Videos"
        odering = ['-created_at', 'title']
    