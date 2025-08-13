# video_player/admin.py

from django.contrib import admin
from .models import Video, Chapter

class ChapterInline(admin.TabularInline):
    model = Chapter
    extra = 0

@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    inlines = [ChapterInline]
    list_display = ('title', 'uploaded_at')

admin.site.register(Chapter)
