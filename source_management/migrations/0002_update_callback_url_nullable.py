# Generated manually to fix callback_url NOT NULL constraint

from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ('source_management', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='videoprocessingjob',
            name='callback_url',
            field=models.URLField(blank=True, help_text='Callback URL for external service (optional for pull-based status checking)', null=True),
        ),
    ]
