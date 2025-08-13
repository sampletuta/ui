from django.db import models

# Create your models here.
# video_player/models.py


class Video(models.Model):
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='videos/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class Chapter(models.Model):
    video = models.ForeignKey(Video, related_name='chapters', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    start_time = models.DurationField(help_text="Time offset from start, e.g., 00:05:33")
    thumbnail = models.ImageField(upload_to='chapters/') #should be a thumbnail of the video at the start time

    def __str__(self):
        return f"{self.title} - {self.start_time}"
